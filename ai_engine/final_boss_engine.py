"""Build a hybrid LumiTrace recommendation index.

This optional advanced script merges three signal families into
`final_boss_vectors.json`:

- BERT semantic vectors from `movie_vectors.json`
- MovieLens collaborative SVD vectors
- MovieLens/Tag Genome style vectors

The public demo does not require this file. Use it only when you want to
experiment with a hybrid BERT + collaborative + tag-profile index.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


LATENT_DIM = 64
MIN_RATINGS_PER_MOVIE = 100
OUTPUT_FILE = "final_boss_vectors.json"


def find_file(directory: Path, patterns: list[str]) -> Path | None:
    """Find the first file matching any pattern under a directory."""
    for pattern in patterns:
        matches = glob.glob(str(directory / "**" / pattern), recursive=True)
        if matches:
            return Path(matches[0])
    return None


def load_links(data_path: Path) -> tuple[dict[int, int], dict[int, int]]:
    """Load MovieLens movie ID to TMDB ID mappings."""
    print("[1/5] Loading ID mappings from links.csv...")
    links_file = find_file(data_path, ["links.csv"])
    if not links_file:
        print(f"   links.csv was not found under {data_path}")
        return {}, {}

    print(f"   file: {links_file}")
    links = pd.read_csv(links_file)
    ml_to_tmdb: dict[int, int] = {}
    tmdb_to_ml: dict[int, int] = {}

    for _, row in links.iterrows():
        movie_id = row.get("movieId")
        tmdb_id = row.get("tmdbId")
        if pd.notna(movie_id) and pd.notna(tmdb_id):
            ml_id = int(movie_id)
            tmdb = int(tmdb_id)
            ml_to_tmdb[ml_id] = tmdb
            tmdb_to_ml[tmdb] = ml_id

    print(f"   mapped movies: {len(ml_to_tmdb):,}")
    return ml_to_tmdb, tmdb_to_ml


def train_svd_vectors(data_path: Path, ml_to_tmdb: dict[int, int]) -> dict[int, list[float]]:
    """Train collaborative SVD vectors and map them to TMDB IDs."""
    print("[2/5] Training collaborative SVD vectors...")
    ratings_file = find_file(data_path, ["ratings.csv"])
    if not ratings_file:
        print(f"   ratings.csv was not found under {data_path}")
        return {}

    print(f"   file: {ratings_file}")
    ratings = pd.read_csv(ratings_file)
    print(f"   raw ratings: {len(ratings):,}")

    movie_counts = ratings.groupby("movieId").size()
    valid_movies = movie_counts[movie_counts >= MIN_RATINGS_PER_MOVIE].index
    filtered = ratings[ratings["movieId"].isin(valid_movies)]
    print(f"   filtered ratings: {len(filtered):,}")
    print(f"   valid movies: {len(valid_movies):,}")

    user_ids = filtered["userId"].unique()
    movie_ids = filtered["movieId"].unique()
    if len(user_ids) == 0 or len(movie_ids) == 0:
        print("   no ratings remain after filtering")
        return {}

    user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
    movie_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
    idx_to_movie = {idx: mid for mid, idx in movie_to_idx.items()}

    row = filtered["userId"].map(user_to_idx)
    col = filtered["movieId"].map(movie_to_idx)
    user_means = filtered.groupby("userId")["rating"].mean()
    centered = filtered["rating"].values - filtered["userId"].map(user_means).values

    matrix = csr_matrix((centered, (row, col)), shape=(len(user_ids), len(movie_ids)))
    dimensions = min(LATENT_DIM, max(1, min(matrix.shape) - 1))
    print(f"   matrix: {matrix.shape[0]:,} users x {matrix.shape[1]:,} movies")
    print(f"   SVD dimensions: {dimensions}")

    _, sigma, vt = svds(matrix.astype(float), k=dimensions)
    movie_vectors = normalize(vt.T * sigma, norm="l2", axis=1)

    svd_vectors: dict[int, list[float]] = {}
    for idx, ml_id in idx_to_movie.items():
        tmdb_id = ml_to_tmdb.get(int(ml_id))
        if tmdb_id:
            svd_vectors[tmdb_id] = movie_vectors[idx].tolist()

    print(f"   SVD vectors: {len(svd_vectors):,}")
    return svd_vectors


def find_genome_file(genome_path: Path) -> Path | None:
    candidates = [
        genome_path / "scores" / "glmer.csv",
        genome_path / "scores" / "tagdl.csv",
        genome_path / "genome-scores.csv",
    ]
    for path in candidates:
        if path.exists():
            return path

    for file_name in glob.glob(str(genome_path / "**" / "*.csv"), recursive=True):
        lower = file_name.lower()
        if "glmer" in lower or "tagdl" in lower or "genome" in lower:
            return Path(file_name)
    return None


def train_genome_vectors(genome_path: Path, ml_to_tmdb: dict[int, int]) -> dict[int, list[float]]:
    """Train compact tag-profile vectors from a MovieLens Genome dataset."""
    print("[3/5] Training Genome tag-profile vectors...")
    if not genome_path.exists():
        print(f"   genome path does not exist: {genome_path}")
        return {}

    genome_file = find_genome_file(genome_path)
    if not genome_file:
        print("   no Genome CSV file was found")
        return {}

    print(f"   file: {genome_file}")
    genome = pd.read_csv(genome_file)
    print(f"   rows: {len(genome):,}")
    print(f"   columns: {list(genome.columns)}")

    cols = {column.lower(): column for column in genome.columns}
    if {"movieid", "tagid", "relevance"}.issubset(cols):
        genome_matrix = genome.pivot(index=cols["movieid"], columns=cols["tagid"], values=cols["relevance"])
    elif {"item_id", "tag", "score"}.issubset(cols):
        genome_matrix = genome.pivot(index=cols["item_id"], columns=cols["tag"], values=cols["score"])
    elif "item" in cols and "tag" in cols:
        score_col = cols.get("score") or genome.columns[2]
        genome_matrix = genome.pivot(index=cols["item"], columns=cols["tag"], values=score_col)
    elif len(genome.columns) > 10:
        id_col = genome.columns[0]
        genome_matrix = genome.set_index(id_col).select_dtypes(include=[np.number])
    else:
        print("   unrecognized Genome format")
        return {}

    genome_matrix = genome_matrix.fillna(0)
    if genome_matrix.empty:
        print("   Genome matrix is empty")
        return {}

    dimensions = min(LATENT_DIM, genome_matrix.shape[1])
    print(f"   matrix: {genome_matrix.shape[0]:,} movies x {genome_matrix.shape[1]:,} tags")
    print(f"   PCA dimensions: {dimensions}")

    pca = PCA(n_components=dimensions)
    reduced = pca.fit_transform(genome_matrix.values)
    reduced = normalize(reduced, norm="l2", axis=1)
    explained = sum(pca.explained_variance_ratio_) * 100
    print(f"   explained variance: {explained:.1f}%")

    genome_vectors: dict[int, list[float]] = {}
    for idx, ml_id in enumerate(genome_matrix.index.tolist()):
        try:
            ml_id_int = int(ml_id)
        except (TypeError, ValueError):
            continue
        tmdb_id = ml_to_tmdb.get(ml_id_int)
        if tmdb_id:
            genome_vectors[tmdb_id] = reduced[idx].tolist()

    print(f"   Genome vectors: {len(genome_vectors):,}")
    return genome_vectors


def load_bert_vectors(bert_file: Path) -> dict[int, dict[str, Any]]:
    """Load BERT vectors generated by the LumiTrace bootstrapper."""
    print("[4/5] Loading BERT semantic vectors...")
    if not bert_file.exists():
        print(f"   BERT vector file was not found: {bert_file}")
        return {}

    with bert_file.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    bert_vectors: dict[int, dict[str, Any]] = {}
    for movie in raw_data:
        if not isinstance(movie, dict) or "id" not in movie:
            continue
        vector = movie.get("vector") or movie.get("bert_vector")
        if not vector:
            continue
        tmdb_id = int(movie["id"])
        bert_vectors[tmdb_id] = {
            "vector": vector,
            "title": movie.get("title", ""),
            "overview": movie.get("overview", ""),
            "poster_path": movie.get("poster_path"),
            "release_date": movie.get("release_date", ""),
            "vote_average": movie.get("vote_average", 0),
            "vote_count": movie.get("vote_count", 0),
            "genre_ids": movie.get("genre_ids", []),
        }

    print(f"   BERT vectors: {len(bert_vectors):,}")
    return bert_vectors


def merge_and_save(
    svd_vectors: dict[int, list[float]],
    genome_vectors: dict[int, list[float]],
    bert_vectors: dict[int, dict[str, Any]],
    output_file: Path,
) -> list[dict[str, Any]]:
    """Merge available vectors into the hybrid final index."""
    print("[5/5] Merging vectors...")
    all_tmdb_ids = set(bert_vectors.keys())
    if not all_tmdb_ids:
        return []

    has_svd = sum(1 for tmdb_id in all_tmdb_ids if tmdb_id in svd_vectors)
    has_genome = sum(1 for tmdb_id in all_tmdb_ids if tmdb_id in genome_vectors)
    has_all = sum(1 for tmdb_id in all_tmdb_ids if tmdb_id in svd_vectors and tmdb_id in genome_vectors)

    print("   coverage:")
    print(f"   SVD: {has_svd:,}/{len(all_tmdb_ids):,}")
    print(f"   Genome: {has_genome:,}/{len(all_tmdb_ids):,}")
    print(f"   complete hybrid: {has_all:,}/{len(all_tmdb_ids):,}")

    final_data: list[dict[str, Any]] = []
    for tmdb_id, bert_data in bert_vectors.items():
        final_data.append(
            {
                "id": tmdb_id,
                "title": bert_data.get("title", ""),
                "overview": bert_data.get("overview", ""),
                "poster_path": bert_data.get("poster_path"),
                "release_date": bert_data.get("release_date", ""),
                "vote_average": bert_data.get("vote_average", 0),
                "vote_count": bert_data.get("vote_count", 0),
                "genre_ids": bert_data.get("genre_ids", []),
                "bert_vector": bert_data["vector"],
                "svd_vector": svd_vectors.get(tmdb_id),
                "genome_vector": genome_vectors.get(tmdb_id),
            }
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(final_data, file, ensure_ascii=False)

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   saved: {output_file}")
    print(f"   file size: {file_size:.2f} MB")
    return final_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a hybrid LumiTrace vector index.")
    parser.add_argument("--ratings_path", default="./ml-32m/", help="Folder containing MovieLens ratings.csv and links.csv.")
    parser.add_argument("--genome_path", default="./genome-2021/", help="Folder containing a Genome CSV dataset.")
    parser.add_argument("--bert_file", default="movie_vectors.json", help="BERT vector file generated by the bootstrapper.")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output hybrid vector file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ratings_path = Path(args.ratings_path)
    genome_path = Path(args.genome_path)
    bert_file = Path(args.bert_file)
    output_file = Path(args.output)

    print("LumiTrace hybrid vector builder")
    print("=" * 36)
    print(f"ratings path: {ratings_path}")
    print(f"genome path: {genome_path}")
    print(f"BERT file: {bert_file}")
    print(f"output: {output_file}")

    ml_to_tmdb, _ = load_links(ratings_path)
    if not ml_to_tmdb:
        print("Cannot continue without links.csv mappings.")
        return 1

    svd_vectors = train_svd_vectors(ratings_path, ml_to_tmdb)
    genome_vectors = train_genome_vectors(genome_path, ml_to_tmdb)
    bert_vectors = load_bert_vectors(bert_file)
    if not bert_vectors:
        print("Cannot continue without BERT vectors. Run tools/bootstrap_recommender.py first.")
        return 1

    final_data = merge_and_save(svd_vectors, genome_vectors, bert_vectors, output_file)
    print("=" * 36)
    print(f"Hybrid vector build complete: {len(final_data):,} movies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
