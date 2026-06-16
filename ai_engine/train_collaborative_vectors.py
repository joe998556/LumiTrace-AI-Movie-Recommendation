"""Train MovieLens collaborative filtering vectors for LumiTrace.

This optional advanced script builds normalized movie latent vectors from a
MovieLens ratings dataset and maps them to TMDB IDs through `links.csv`.

Example:
    python ai_engine/train_collaborative_vectors.py --data_path ./movielens/ml-latest-small/
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds


LATENT_DIM = 64
MIN_RATINGS_PER_MOVIE = 50
MIN_RATINGS_PER_USER = 20
OUTPUT_FILE = "collaborative_vectors.json"


def load_movielens_data(data_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load MovieLens ratings, movies, and TMDB links."""
    print("Loading MovieLens data...")

    ratings_file = data_path / "ratings.csv"
    movies_file = data_path / "movies.csv"
    links_file = data_path / "links.csv"

    for path in (ratings_file, movies_file, links_file):
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

    ratings = pd.read_csv(ratings_file)
    movies = pd.read_csv(movies_file)
    links = pd.read_csv(links_file)

    print(f"   ratings.csv: {len(ratings):,} rows")
    print(f"   movies.csv: {len(movies):,} rows")
    print(f"   links.csv: {len(links):,} rows")
    return ratings, movies, links


def filter_data(ratings: pd.DataFrame) -> pd.DataFrame:
    """Filter sparse rating history before SVD."""
    print("Filtering sparse rating data...")
    original_count = len(ratings)

    movie_counts = ratings.groupby("movieId").size()
    valid_movies = movie_counts[movie_counts >= MIN_RATINGS_PER_MOVIE].index

    user_counts = ratings.groupby("userId").size()
    valid_users = user_counts[user_counts >= MIN_RATINGS_PER_USER].index

    filtered = ratings[
        ratings["movieId"].isin(valid_movies)
        & ratings["userId"].isin(valid_users)
    ]

    print(f"   original ratings: {original_count:,}")
    print(f"   filtered ratings: {len(filtered):,}")
    print(f"   valid movies: {len(valid_movies):,}")
    print(f"   valid users: {len(valid_users):,}")
    return filtered


def build_user_item_matrix(ratings: pd.DataFrame) -> tuple[csr_matrix, dict[int, int]]:
    """Build a centered sparse user-item matrix."""
    print("Building user-item matrix...")

    user_ids = ratings["userId"].unique()
    movie_ids = ratings["movieId"].unique()

    user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
    movie_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
    idx_to_movie = {idx: mid for mid, idx in movie_to_idx.items()}

    row = ratings["userId"].map(user_to_idx)
    col = ratings["movieId"].map(movie_to_idx)
    user_means = ratings.groupby("userId")["rating"].mean()
    centered_ratings = ratings["rating"].values - ratings["userId"].map(user_means).values

    matrix = csr_matrix(
        (centered_ratings, (row, col)),
        shape=(len(user_ids), len(movie_ids)),
    )

    density = matrix.nnz / max(1, matrix.shape[0] * matrix.shape[1])
    print(f"   matrix: {matrix.shape[0]:,} users x {matrix.shape[1]:,} movies")
    print(f"   sparsity: {100 * (1 - density):.2f}%")
    return matrix, idx_to_movie


def train_svd(matrix: csr_matrix, dimensions: int) -> np.ndarray:
    """Run SVD and return normalized movie vectors."""
    if dimensions >= min(matrix.shape):
        dimensions = max(1, min(matrix.shape) - 1)

    print(f"Running SVD with {dimensions} latent dimensions...")
    _, sigma, vt = svds(matrix.astype(float), k=dimensions)
    movie_vectors = vt.T * sigma
    norms = np.linalg.norm(movie_vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return movie_vectors / norms


def map_to_tmdb(movie_vectors: np.ndarray, idx_to_movie: dict[int, int], links: pd.DataFrame) -> dict[str, list[float]]:
    """Map MovieLens movie IDs to TMDB IDs."""
    print("Mapping MovieLens IDs to TMDB IDs...")
    ml_to_tmdb: dict[int, int] = {}

    for _, row in links.iterrows():
        movie_id = row.get("movieId")
        tmdb_id = row.get("tmdbId")
        if pd.notna(movie_id) and pd.notna(tmdb_id):
            ml_to_tmdb[int(movie_id)] = int(tmdb_id)

    mapped: dict[str, list[float]] = {}
    for idx, movie_id in idx_to_movie.items():
        tmdb_id = ml_to_tmdb.get(int(movie_id))
        if tmdb_id:
            mapped[str(tmdb_id)] = movie_vectors[idx].tolist()

    print(f"   mapped movies: {len(mapped):,}")
    print(f"   unmapped movies: {len(idx_to_movie) - len(mapped):,}")
    return mapped


def save_vectors(vectors: dict[str, list[float]], output_file: Path) -> None:
    """Save collaborative vectors as JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(vectors, file)

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Saved {len(vectors):,} vectors to {output_file}")
    print(f"File size: {file_size:.2f} MB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train MovieLens collaborative filtering vectors.")
    parser.add_argument("--data_path", default="./movielens/ml-latest-small/", help="MovieLens folder with ratings.csv, movies.csv, and links.csv.")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file path.")
    parser.add_argument("--dim", type=int, default=LATENT_DIM, help="Latent dimension for SVD.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_path = Path(args.data_path)
    output_file = Path(args.output)

    print("LumiTrace collaborative vector training")
    print("=" * 42)
    ratings, _, links = load_movielens_data(data_path)
    filtered = filter_data(ratings)
    matrix, idx_to_movie = build_user_item_matrix(filtered)
    movie_vectors = train_svd(matrix, args.dim)
    mapped_vectors = map_to_tmdb(movie_vectors, idx_to_movie, links)
    save_vectors(mapped_vectors, output_file)
    print("Training complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
