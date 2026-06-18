"""One-command TMDB data downloader and BERT vector builder for LumiTrace.

This script intentionally never writes API keys to disk. It reads TMDB_API_KEY
from the current environment/.env or asks for it interactively.
"""

from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
TMDB_BASE_URL = "https://api.themoviedb.org/3"
DEFAULT_MODEL = "AventIQ-AI/bert-movie-recommendation-system"
DEFAULT_OUTPUT = ROOT / "movie_vectors.json"


@dataclass(frozen=True)
class Preset:
    name: str
    target: int
    note: str


PRESETS: dict[str, Preset] = {
    "demo": Preset("demo", 200, "quick smoke test, laptop friendly"),
    "small": Preset("small", 1000, "good first real index"),
    "medium": Preset("medium", 5000, "better coverage, GPU recommended"),
    "large": Preset("large", 15000, "wide coverage, long run"),
    "xlarge": Preset("xlarge", 30000, "very large local index, overnight/GPU run"),
}

GENRE_IDS = [
    28,
    12,
    16,
    35,
    80,
    99,
    18,
    10751,
    14,
    36,
    27,
    10402,
    9648,
    10749,
    878,
    10770,
    53,
    10752,
    37,
]

GENRE_NAMES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

LANGUAGES = ["en", "zh", "ja", "ko", "fr", "de", "es", "it", "hi", "th"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download TMDB movie data and build LumiTrace BERT vectors."
    )
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Data size preset.")
    parser.add_argument("--limit", type=int, help="Override the target number of unique movies.")
    parser.add_argument("--tmdb-key", help="TMDB API key. If omitted, TMDB_API_KEY or interactive input is used.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON file.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face embedding model.")
    parser.add_argument("--language", default="en-US", help="TMDB response language.")
    parser.add_argument("--batch-size", type=int, default=16, help="Embedding batch size.")
    parser.add_argument("--sleep", type=float, default=0.12, help="Delay between TMDB API requests.")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:0.")
    parser.add_argument("--overwrite", action="store_true", help="Rebuild vectors even if output already exists.")
    return parser.parse_args()


def choose_preset(name: str | None) -> Preset:
    if name:
        return PRESETS[name]

    if not os.isatty(0):
        return PRESETS["small"]

    print("Choose a LumiTrace data preset:")
    for index, preset in enumerate(PRESETS.values(), start=1):
        print(f"  {index}. {preset.name:7} ~{preset.target:,} movies - {preset.note}")

    answer = input("Preset [small]: ").strip().lower()
    if not answer:
        return PRESETS["small"]
    if answer.isdigit():
        presets = list(PRESETS.values())
        number = int(answer)
        if 1 <= number <= len(presets):
            return presets[number - 1]
    if answer in PRESETS:
        return PRESETS[answer]
    raise SystemExit(f"Unknown preset: {answer}")


def resolve_tmdb_key(cli_key: str | None) -> str:
    key = (cli_key or os.getenv("TMDB_API_KEY") or "").strip()
    if key:
        return key
    if not os.isatty(0):
        raise SystemExit("TMDB_API_KEY is required in non-interactive mode.")
    key = getpass.getpass("TMDB API key (hidden, not saved): ").strip()
    if not key:
        raise SystemExit("TMDB API key is required.")
    return key


def resolve_device(name: str) -> torch.device:
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    if name != "auto":
        return torch.device(name)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def plan_sources(limit: int) -> Iterable[tuple[str, str, dict[str, Any], int]]:
    base_pages = min(500, max(3, math.ceil(limit / 160)))
    discover_pages = min(500, max(2, math.ceil(limit / 500)))
    year_pages = min(500, max(1, math.ceil(limit / 900)))
    language_pages = min(500, max(1, math.ceil(limit / 1200)))

    base_sources = [
        ("trending", "trending/movie/week", {}, base_pages),
        ("popular", "movie/popular", {}, base_pages),
        ("top_rated", "movie/top_rated", {}, base_pages),
        ("now_playing", "movie/now_playing", {}, max(1, base_pages // 3)),
        ("upcoming", "movie/upcoming", {}, max(1, base_pages // 3)),
    ]
    yield from base_sources

    for genre_id in GENRE_IDS:
        yield (
            f"genre_{genre_id}_popular",
            "discover/movie",
            {"with_genres": genre_id, "sort_by": "popularity.desc"},
            discover_pages,
        )
        yield (
            f"genre_{genre_id}_rated",
            "discover/movie",
            {"with_genres": genre_id, "sort_by": "vote_average.desc", "vote_count.gte": 50},
            discover_pages,
        )

    current_year = datetime.now().year
    for year in range(current_year, 1949, -1):
        yield (
            f"year_{year}",
            "discover/movie",
            {"primary_release_year": year, "sort_by": "vote_average.desc", "vote_count.gte": 50},
            year_pages,
        )

    for language in LANGUAGES:
        yield (
            f"language_{language}",
            "discover/movie",
            {"with_original_language": language, "sort_by": "vote_average.desc", "vote_count.gte": 50},
            language_pages,
        )


def fetch_page(
    session: requests.Session,
    key: str,
    endpoint: str,
    params: dict[str, Any],
    page: int,
    language: str,
) -> list[dict[str, Any]]:
    query = {
        "api_key": key,
        "language": language,
        "include_adult": "false",
        "page": page,
        **params,
    }
    response = session.get(f"{TMDB_BASE_URL}/{endpoint}", params=query, timeout=20)
    response.raise_for_status()
    return response.json().get("results", [])


def clean_string_list(values: Any, limit: int = 5) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values[:limit]:
        if isinstance(value, dict):
            text = str(value.get("name") or value.get("title") or "").strip()
        else:
            text = str(value or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def clean_collection_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "").strip()
    return str(value or "").strip()


def clean_movie(movie: dict[str, Any]) -> dict[str, Any] | None:
    overview = str(movie.get("overview") or "").strip()
    poster_path = movie.get("poster_path")
    if len(overview) < 20 or not poster_path:
        return None
    try:
        movie_id = int(movie.get("id"))
    except (TypeError, ValueError):
        return None
    cleaned = {
        "id": movie_id,
        "title": movie.get("title") or movie.get("name") or "Untitled",
        "overview": overview,
        "poster_path": poster_path,
        "release_date": movie.get("release_date") or "",
        "original_language": movie.get("original_language") or "",
        "vote_average": float(movie.get("vote_average") or 0),
        "vote_count": int(movie.get("vote_count") or 0),
        "genre_ids": movie.get("genre_ids") or [],
    }
    director = str(movie.get("director") or "").strip()
    cast = clean_string_list(movie.get("cast") or movie.get("actors") or [])
    collection = clean_collection_name(movie.get("collection_name") or movie.get("belongs_to_collection"))
    if director:
        cleaned["director"] = director
    if cast:
        cleaned["cast"] = cast
    if collection:
        cleaned["collection_name"] = collection
    return cleaned


def download_movies(key: str, limit: int, language: str, sleep_seconds: float) -> list[dict[str, Any]]:
    session = make_session()
    movies: dict[int, dict[str, Any]] = {}

    print(f"Downloading up to {limit:,} unique movies from TMDB...")
    for label, endpoint, params, pages in plan_sources(limit):
        if len(movies) >= limit:
            break
        for page in range(1, pages + 1):
            if len(movies) >= limit:
                break
            try:
                results = fetch_page(session, key, endpoint, params, page, language)
            except requests.RequestException as exc:
                print(f"[download] skipped {label} page {page}: {exc}")
                continue

            for raw_movie in results:
                movie = clean_movie(raw_movie)
                if movie and movie["id"] not in movies:
                    movies[movie["id"]] = movie
                    if len(movies) >= limit:
                        break

            if page == 1 or page % 10 == 0:
                print(f"[download] {len(movies):,}/{limit:,} movies collected ({label}, page {page})")
            time.sleep(max(0.0, sleep_seconds))

    return list(movies.values())[:limit]


def movie_text(movie: dict[str, Any]) -> str:
    genre_ids = [int(genre) for genre in movie.get("genre_ids", []) if str(genre).isdigit()]
    genre_names = [GENRE_NAMES.get(genre_id, str(genre_id)) for genre_id in genre_ids]
    release_year = str(movie.get("release_date") or "")[:4]
    director = str(movie.get("director") or "").strip()
    cast = clean_string_list(movie.get("cast") or [], limit=4)
    collection = str(movie.get("collection_name") or "").strip()
    parts = [
        f"Title: {movie['title']}",
        f"Genres: {', '.join(genre_names) if genre_names else 'unknown'}",
        f"Original language: {movie.get('original_language') or 'unknown'}",
        f"Release year: {release_year if release_year.isdigit() else 'unknown'}",
        f"Audience rating: {movie['vote_average']}",
    ]
    if director:
        parts.append(f"Director: {director}")
    if cast:
        parts.append(f"Cast: {', '.join(cast)}")
    if collection:
        parts.append(f"Series or collection: {collection}")
    parts.append(f"Plot and atmosphere: {movie['overview']}")
    return "\n".join(
        parts
    )


def load_existing_vectors(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    existing: dict[int, dict[str, Any]] = {}
    for item in data:
        if not isinstance(item, dict) or "vector" not in item:
            continue
        try:
            existing[int(item["id"])] = item
        except (TypeError, ValueError, KeyError):
            continue
    return existing


def save_vectors(path: Path, vectors: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(vectors, file, ensure_ascii=False)
    tmp_path.replace(path)


def embed_movies(
    movies: list[dict[str, Any]],
    existing: dict[int, dict[str, Any]],
    output: Path,
    model_name: str,
    device: torch.device,
    batch_size: int,
) -> list[dict[str, Any]]:
    try:
        import torch
        import torch.nn.functional as F
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Missing ML dependencies. Run `pip install -r requirements.txt` first.") from exc

    vectors: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    for movie in movies:
        existing_item = existing.get(movie["id"])
        if existing_item:
            vectors.append(existing_item)
        else:
            pending.append(movie)

    if not pending:
        print("All requested movies already have vectors.")
        return vectors

    print(f"Loading embedding model: {model_name}")
    print(f"Device: {device}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()

    print(f"Embedding {len(pending):,} new movies...")
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        texts = [movie_text(movie) for movie in batch]
        encoded = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}

        with torch.no_grad():
            output_state = model(**encoded)

        hidden = output_state.last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        embeddings = F.normalize(pooled, p=2, dim=1).detach().cpu().tolist()

        for movie, vector in zip(batch, embeddings):
            vectors.append({**movie, "vector": vector})

        completed = min(start + len(batch), len(pending))
        total_completed = len(vectors)
        print(f"[embed] {completed:,}/{len(pending):,} new movies embedded; {total_completed:,} total vectors")

        if total_completed % max(batch_size * 10, 100) == 0:
            save_vectors(output, vectors)

    return vectors


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()
    preset = choose_preset(args.preset)
    limit = max(1, args.limit or preset.target)
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    key = resolve_tmdb_key(args.tmdb_key)
    device = resolve_device(args.device)
    existing = {} if args.overwrite else load_existing_vectors(output)

    print("LumiTrace recommender bootstrap")
    print("=" * 34)
    print(f"Preset: {preset.name} ({preset.note})")
    print(f"Target movies: {limit:,}")
    print(f"Output: {output}")
    print("More movies usually improve coverage, but downloads and embeddings take longer.")

    movies = download_movies(key, limit, args.language, args.sleep)
    if not movies:
        raise SystemExit("No movies were downloaded. Check the TMDB API key and network access.")

    vectors = embed_movies(
        movies=movies,
        existing=existing,
        output=output,
        model_name=args.model,
        device=device,
        batch_size=max(1, args.batch_size),
    )
    save_vectors(output, vectors)

    size_mb = output.stat().st_size / (1024 * 1024)
    print("=" * 34)
    print(f"Done: {len(vectors):,} vectors saved")
    print(f"File size: {size_mb:.1f} MB")
    print("Next:")
    print("  python ai_engine/bert_service.py")
    print("  set REMOTE_SEARCH_URL=http://127.0.0.1:5001/search in .env to let the web app use BERT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
