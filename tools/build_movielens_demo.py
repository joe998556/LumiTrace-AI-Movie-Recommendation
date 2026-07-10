"""Build the redistributable LumiTrace demo index from MovieLens Latest Small."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.index_format import write_index  # noqa: E402


DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATASET_MD5 = "31a303aabbc519bd33d025e44d6c2570"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GENRE_IDS = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Children": 10751,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Fantasy": 14,
    "Film-Noir": 80,
    "Horror": 27,
    "Musical": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Thriller": 53,
    "War": 10752,
    "Western": 37,
}


def display_title(value: str) -> str:
    title = re.sub(r"\s*\(\d{4}\)$", "", value.strip()).strip()
    match = re.match(r"^(.*),\s+(The|A|An)$", title)
    return f"{match.group(2)} {match.group(1)}" if match else title


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the bundled MovieLens semantic demo index.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--minimum-ratings", type=int, default=20)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", default="demo_index")
    parser.add_argument("--cache", default="scratch/ml-latest-small.zip")
    return parser.parse_args()


def download_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        print(f"Downloading {DATASET_URL}")
        with requests.get(DATASET_URL, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            temporary = path.with_suffix(path.suffix + ".tmp")
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            temporary.replace(path)
    digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
    if digest != DATASET_MD5:
        raise RuntimeError(f"MovieLens checksum mismatch: expected {DATASET_MD5}, received {digest}")


def csv_rows(archive: zipfile.ZipFile, name: str):
    with archive.open(f"ml-latest-small/{name}") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        yield from csv.DictReader(text)


def load_movies(path: Path, limit: int, minimum_ratings: int) -> tuple[list[dict[str, Any]], list[str]]:
    with zipfile.ZipFile(path) as archive:
        movies = {int(row["movieId"]): row for row in csv_rows(archive, "movies.csv")}
        links = {
            int(row["movieId"]): int(float(row["tmdbId"]))
            for row in csv_rows(archive, "links.csv")
            if row.get("tmdbId")
        }
        rating_sum: dict[int, float] = defaultdict(float)
        rating_count: Counter[int] = Counter()
        for row in csv_rows(archive, "ratings.csv"):
            movie_id = int(row["movieId"])
            rating_sum[movie_id] += float(row["rating"])
            rating_count[movie_id] += 1
        tags: dict[int, Counter[str]] = defaultdict(Counter)
        for row in csv_rows(archive, "tags.csv"):
            tag = " ".join(str(row.get("tag") or "").strip().split())[:80]
            if tag:
                tags[int(row["movieId"])][tag] += 1

    selected = [
        movie_id
        for movie_id, count in rating_count.most_common()
        if count >= minimum_ratings and movie_id in movies and movie_id in links
    ][: max(1, limit)]
    records: list[dict[str, Any]] = []
    texts: list[str] = []
    for movie_id in selected:
        row = movies[movie_id]
        raw_title = row["title"].strip()
        year_match = re.search(r"\((\d{4})\)$", raw_title)
        year = year_match.group(1) if year_match else ""
        title = display_title(raw_title)
        genres = [value for value in row.get("genres", "").split("|") if value and value != "(no genres listed)"]
        top_tags = [value for value, _count in tags[movie_id].most_common(12)]
        texts.append(
            ". ".join(
                part
                for part in (
                    f"Title: {title}",
                    f"Genres: {', '.join(genres)}" if genres else "",
                    f"Community tags: {', '.join(top_tags)}" if top_tags else "",
                )
                if part
            )
        )
        records.append(
            {
                "id": links[movie_id],
                "title": title,
                "overview": "",
                "poster_path": "",
                "release_date": f"{year}-01-01" if year else "",
                "vote_average": round((rating_sum[movie_id] / rating_count[movie_id]) * 2, 3),
                "vote_count": rating_count[movie_id],
                "genre_ids": [GENRE_IDS[genre] for genre in genres if genre in GENRE_IDS],
                "original_language": "",
                "embedding_text_mode": "movielens-title-genres-tags",
            }
        )
    return records, texts


def embed(texts: list[str], model_name: str, device_name: str, batch_size: int) -> list[list[float]]:
    import torch
    import torch.nn.functional as functional
    from transformers import AutoModel, AutoTokenizer

    device = torch.device("cuda" if device_name == "auto" and torch.cuda.is_available() else ("cpu" if device_name == "auto" else device_name))
    print(f"Loading {model_name} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()
    rows: list[list[float]] = []
    for start in range(0, len(texts), max(1, batch_size)):
        batch = texts[start : start + max(1, batch_size)]
        tokens = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
        tokens = {key: value.to(device) for key, value in tokens.items()}
        with torch.no_grad():
            hidden = model(**tokens).last_hidden_state
        mask = tokens["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        rows.extend(functional.normalize(pooled, p=2, dim=1).cpu().tolist())
        print(f"Embedded {min(start + len(batch), len(texts)):,}/{len(texts):,}")
    return rows


def main() -> int:
    args = parse_args()
    cache = Path(args.cache)
    output = Path(args.output)
    if not cache.is_absolute():
        cache = ROOT / cache
    if not output.is_absolute():
        output = ROOT / output
    download_dataset(cache)
    records, texts = load_movies(cache, args.limit, args.minimum_ratings)
    vectors = embed(texts, args.model, args.device, args.batch_size)
    for record, vector in zip(records, vectors):
        record["vector"] = vector
    manifest = write_index(records, output, model=args.model, dtype="float16")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data.update(
        {
            "dataset": "MovieLens Latest Small",
            "dataset_url": DATASET_URL,
            "dataset_md5": DATASET_MD5,
            "data_license": "MOVIELENS_README.txt",
            "data_notice": "../DATA_LICENSE.md",
        }
    )
    manifest.write_text(json.dumps(manifest_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with zipfile.ZipFile(cache) as archive:
        license_text = archive.read("ml-latest-small/README.txt")
    (output / "MOVIELENS_README.txt").write_bytes(license_text)
    print(f"Created {manifest} with {len(records):,} movies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
