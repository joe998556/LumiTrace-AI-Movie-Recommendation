"""BERT semantic recommendation service for LumiTrace.

Run this service after generating `movie_vectors.json` with:

    python tools/bootstrap_recommender.py --preset small
    python ai_engine/bert_service.py

The public Flask app can call this service through `REMOTE_SEARCH_URL`, for
example:

    REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_VECTOR_FILES = ("final_boss_vectors.json", "movie_vectors.json")

GENRE_HINTS = {
    9648: ("mystery", "suspense", "twist", "whodunit", "detective", "\u61f8\u7591", "\u63a8\u7406", "\u53cd\u8f49"),
    53: ("thriller", "tense", "psychological", "\u9a5a\u609a", "\u7dca\u5f35"),
    80: ("crime", "noir", "heist", "criminal", "\u72af\u7f6a", "\u9ed1\u8272\u96fb\u5f71"),
    18: ("drama", "melancholy", "slow burn", "slow-burn", "intimate", "\u5287\u60c5", "\u6162\u7bc0\u594f"),
    10749: ("romance", "romantic", "love", "\u611b\u60c5", "\u6d6a\u6f2b"),
    878: ("sci-fi", "science fiction", "space", "future", "\u79d1\u5e7b", "\u592a\u7a7a"),
    27: ("horror", "scary", "haunted", "\u6050\u6016", "\u9b3c"),
    35: ("comedy", "funny", "light", "\u559c\u5287", "\u8f15\u9b06"),
    16: ("animation", "animated", "\u52d5\u756b"),
    99: ("documentary", "documentary-style", "\u7d00\u9304\u7247"),
    14: ("fantasy", "magical", "myth", "\u5947\u5e7b", "\u9b54\u6cd5"),
    28: ("action", "action-packed", "gunfight", "car chase", "explosion", "stunt", "\u52d5\u4f5c", "\u69cd\u6230", "\u8ffd\u8eca", "\u7206\u7834", "\u7279\u6280", "\u723d\u7247", "\u814e\u4e0a\u817a\u7d20"),
    12: ("adventure", "quest", "expedition", "\u5192\u96aa", "\u5c0b\u5bf6"),
    10752: ("war", "wartime", "battlefield", "soldier", "\u6230\u722d", "\u6230\u5834", "\u4e8c\u6230", "\u8ecd\u4e8b"),
    36: ("history", "historical", "period piece", "epic", "\u6b77\u53f2", "\u53f2\u8a69", "\u53e4\u88dd"),
    10751: ("family", "wholesome", "kids", "\u95d4\u5bb6", "\u89aa\u5b50", "\u5bb6\u5ead\u96fb\u5f71"),
    10402: ("music", "musical", "song and dance", "\u97f3\u6a02", "\u6b4c\u821e"),
    37: ("western", "cowboy", "\u897f\u90e8"),
}

LANGUAGE_HINTS = {
    "fr": ("french", "france", "paris", "\u6cd5\u570b", "\u6cd5\u8a9e"),
    "de": ("german", "germany", "berlin", "\u5fb7\u570b", "\u5fb7\u8a9e"),
    "es": ("spanish", "spain", "\u897f\u73ed\u7259", "\u897f\u8a9e"),
    "it": ("italian", "italy", "\u7fa9\u5927\u5229", "\u7fa9\u8a9e"),
    "ja": ("japanese", "japan", "\u65e5\u672c", "\u65e5\u8a9e"),
    "ko": ("korean", "korea", "\u97d3\u570b", "\u97d3\u8a9e"),
    "zh": ("chinese", "taiwan", "hong kong", "mandarin", "\u4e2d\u6587", "\u83ef\u8a9e", "\u53f0\u7063", "\u9999\u6e2f"),
    "en": ("english", "british", "american", "\u82f1\u8a9e", "\u7f8e\u570b", "\u82f1\u570b"),
}

EUROPEAN_LANGUAGE_CODES = ("fr", "de", "es", "it", "da", "sv", "no", "nl", "pl", "pt", "fi", "is", "tr")


def build_parser(default_vectors: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LumiTrace BERT semantic recommendation service.")
    parser.add_argument("--vectors", default=default_vectors, help="Path to movie_vectors.json.")
    parser.add_argument("--model", default=os.getenv("LUMITRACE_MODEL", DEFAULT_MODEL), help="Hugging Face model name.")
    parser.add_argument("--host", default=os.getenv("BERT_HOST", "127.0.0.1"), help="Service host.")
    parser.add_argument("--port", type=int, default=int(os.getenv("BERT_PORT", "5001")), help="Service port.")
    parser.add_argument("--device", default=os.getenv("LUMITRACE_DEVICE", "auto"), help="auto, cpu, cuda, or cuda:0.")
    return parser


if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
    build_parser(str(ROOT / "movie_vectors.json")).parse_args()
    raise SystemExit(0)

try:
    from dotenv import load_dotenv
    from flask import Flask, jsonify, request
    from flask_cors import CORS
except ImportError as exc:
    raise SystemExit("Missing web dependencies. Run `pip install -r requirements.txt` first.") from exc


app = Flask(__name__)
CORS(app)
logging.basicConfig(level=os.getenv("LUMITRACE_LOG_LEVEL", "INFO").upper(), format="%(levelname)s: %(message)s")
logger = logging.getLogger("lumitrace.bert")

BERT_GATEWAY_TOKEN: str = ""


@app.before_request
def check_gateway_token():
    """If BERT_GATEWAY_TOKEN is set, require X-LumiTrace-Gateway header on POST endpoints."""
    if not BERT_GATEWAY_TOKEN:
        return
    if request.method != "POST":
        return
    header = request.headers.get("X-LumiTrace-Gateway", "")
    if header != BERT_GATEWAY_TOKEN:
        return jsonify({"error": "Forbidden: invalid or missing gateway token"}), 403

TOKENIZER: Any = None
MODEL: Any = None
DEVICE: Any = None
MODEL_NAME = DEFAULT_MODEL
VECTOR_PATH: Path | None = None
MOVIES: list[dict[str, Any]] = []
VECTOR_TENSOR: torch.Tensor | None = None
SVD_TENSOR: torch.Tensor | None = None
GENOME_TENSOR: torch.Tensor | None = None
MOVIE_ID_TO_INDEX: dict[int, int] = {}


def first_existing_vector_file() -> Path:
    configured = os.getenv("LUMITRACE_VECTOR_FILE")
    candidates = [configured] if configured else []
    candidates.extend(DEFAULT_VECTOR_FILES)

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            return path
    return ROOT / "movie_vectors.json"


def resolve_device(requested: str | None = None) -> torch.device:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    if requested and requested != "auto":
        return torch.device(requested)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model(model_name: str, device: torch.device) -> None:
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Missing dependency: transformers. Run `pip install -r requirements.txt` first.") from exc

    global TOKENIZER, MODEL, MODEL_NAME, DEVICE
    MODEL_NAME = model_name
    DEVICE = device
    print(f"Loading embedding model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")
    TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
    MODEL = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    MODEL.eval()


def vector_from_movie(movie: dict[str, Any]) -> list[float] | None:
    vector = movie.get("vector") or movie.get("bert_vector")
    if not isinstance(vector, list) or not vector:
        return None
    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        return None


def clean_movie(movie: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        "id": int(movie.get("id", 0)),
        "title": movie.get("title") or movie.get("name") or "Untitled",
        "overview": movie.get("overview") or "",
        "poster_path": movie.get("poster_path"),
        "release_date": movie.get("release_date") or "",
        "original_language": movie.get("original_language") or "",
        "vote_average": float(movie.get("vote_average") or 0),
        "vote_count": int(movie.get("vote_count") or 0),
        "genre_ids": movie.get("genre_ids") or [],
    }
    for optional_key in ("director", "cast", "collection_name"):
        if movie.get(optional_key):
            cleaned[optional_key] = movie[optional_key]
    return cleaned


def optional_vector_from_movie(movie: dict[str, Any], key: str) -> list[float] | None:
    vector = movie.get(key)
    if not isinstance(vector, list) or not vector:
        return None
    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        return None


def pad_or_zero_vector(vector: list[float] | None, size: int) -> list[float]:
    if not vector:
        return [0.0] * size
    if len(vector) >= size:
        return vector[:size]
    return vector + ([0.0] * (size - len(vector)))


def load_vector_index(path: Path) -> bool:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    global VECTOR_PATH, MOVIES, VECTOR_TENSOR, SVD_TENSOR, GENOME_TENSOR, MOVIE_ID_TO_INDEX

    if not path.exists():
        VECTOR_PATH = path
        MOVIES = []
        VECTOR_TENSOR = None
        SVD_TENSOR = None
        GENOME_TENSOR = None
        MOVIE_ID_TO_INDEX = {}
        print(f"Vector file not found: {path}")
        return False

    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, list):
        raise ValueError("Vector file must be a JSON list of movie records.")

    movies: list[dict[str, Any]] = []
    vectors: list[list[float]] = []
    svd_vectors: list[list[float] | None] = []
    genome_vectors: list[list[float] | None] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        vector = vector_from_movie(item)
        if not vector:
            continue
        movie = clean_movie(item)
        if not movie["id"] or not movie["overview"]:
            continue
        movies.append(movie)
        vectors.append(vector)
        svd_vectors.append(optional_vector_from_movie(item, "svd_vector"))
        genome_vectors.append(optional_vector_from_movie(item, "genome_vector"))

    if not vectors:
        VECTOR_PATH = path
        MOVIES = []
        VECTOR_TENSOR = None
        SVD_TENSOR = None
        GENOME_TENSOR = None
        MOVIE_ID_TO_INDEX = {}
        print(f"No usable vectors found in {path}")
        return False

    tensor = torch.tensor(vectors, dtype=torch.float32, device=DEVICE)
    VECTOR_TENSOR = F.normalize(tensor, p=2, dim=1).contiguous()
    svd_size = max((len(vector) for vector in svd_vectors if vector), default=0)
    genome_size = max((len(vector) for vector in genome_vectors if vector), default=0)
    SVD_TENSOR = None
    GENOME_TENSOR = None
    if svd_size:
        svd_tensor = torch.tensor(
            [pad_or_zero_vector(vector, svd_size) for vector in svd_vectors],
            dtype=torch.float32,
            device=DEVICE,
        )
        SVD_TENSOR = F.normalize(svd_tensor, p=2, dim=1).contiguous()
    if genome_size:
        genome_tensor = torch.tensor(
            [pad_or_zero_vector(vector, genome_size) for vector in genome_vectors],
            dtype=torch.float32,
            device=DEVICE,
        )
        GENOME_TENSOR = F.normalize(genome_tensor, p=2, dim=1).contiguous()
    VECTOR_PATH = path
    MOVIES = movies
    MOVIE_ID_TO_INDEX = {movie["id"]: index for index, movie in enumerate(MOVIES)}
    print(f"Loaded {len(MOVIES):,} movie vectors from {path}")
    if SVD_TENSOR is not None or GENOME_TENSOR is not None:
        svd_count = sum(1 for vector in svd_vectors if vector)
        genome_count = sum(1 for vector in genome_vectors if vector)
        print(f"Loaded hybrid vectors: SVD {svd_count:,}, Genome {genome_count:,}")
    return True


def embed_texts(texts: list[str]) -> torch.Tensor:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    if TOKENIZER is None or MODEL is None or DEVICE is None:
        raise RuntimeError("Embedding model is not loaded.")

    encoded = TOKENIZER(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    )
    encoded = {key: value.to(DEVICE) for key, value in encoded.items()}

    with torch.no_grad():
        output = MODEL(**encoded)

    hidden = output.last_hidden_state
    mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
    return F.normalize(pooled, p=2, dim=1)


def flatten_genres(values: Any) -> set[int]:
    genres: set[int] = set()
    if not isinstance(values, list):
        return genres
    for item in values:
        if isinstance(item, list):
            source = item
        else:
            source = [item]
        for value in source:
            try:
                genres.add(int(value))
            except (TypeError, ValueError):
                continue
    return genres


def clean_language_code(value: Any) -> str | None:
    code = str(value or "").strip().lower()
    if not code:
        return None
    code = code.split("-")[0]
    if len(code) != 2 or not code.isalpha():
        return None
    return code


def clean_language_list(values: Any, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values[:limit]:
        code = clean_language_code(value)
        if code and code not in cleaned:
            cleaned.append(code)
    return cleaned


def clean_flat_int_list(values: Any, limit: int = 24) -> list[int]:
    if not isinstance(values, list):
        return []
    cleaned: list[int] = []
    for value in values[:limit]:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number not in cleaned:
            cleaned.append(number)
    return cleaned


def infer_context_filters(texts: list[str]) -> tuple[list[int], list[str]]:
    """Infer lightweight genre/language filters from a zero-shot playlist prompt."""
    prompt = " ".join(texts).lower()
    inferred_genres: list[int] = []
    inferred_languages: list[str] = []

    for genre_id, hints in GENRE_HINTS.items():
        if any(hint in prompt for hint in hints):
            inferred_genres.append(genre_id)

    for language, hints in LANGUAGE_HINTS.items():
        if any(hint in prompt for hint in hints):
            inferred_languages.append(language)

    if any(hint in prompt for hint in ("european", "europe", "歐洲", "欧洲")):
        for language in EUROPEAN_LANGUAGE_CODES:
            if language not in inferred_languages:
                inferred_languages.append(language)

    return inferred_genres, inferred_languages


def infer_year_window(texts: list[str]) -> tuple[int | None, int | None]:
    """Infer a release-year window from an era-flavoured prompt.

    Release year is metadata the embedding cannot perceive, so "1970 年以前的
    經典老片" needs an explicit year filter. Returns (min_year, max_year), either
    of which may be None.
    """
    prompt = " ".join(texts).lower()
    min_year: int | None = None
    max_year: int | None = None

    def tighten_max(year: int) -> None:
        nonlocal max_year
        max_year = year if max_year is None else min(max_year, year)

    def raise_min(year: int) -> None:
        nonlocal min_year
        min_year = year if min_year is None else max(min_year, year)

    # "before 1970" / "1970 年以前" / "pre-1970"
    for m in re.finditer(r"(?:before|pre-?)\s*(\d{4})", prompt):
        tighten_max(int(m.group(1)) - 1)
    for m in re.finditer(r"(\d{4})\s*年?(?:代)?\s*(?:以前|之前|前)", prompt):
        tighten_max(int(m.group(1)) - 1)
    # "after 1990" / "1990 年以後" / "post-1990"
    for m in re.finditer(r"(?:after|since|post-?)\s*(\d{4})", prompt):
        raise_min(int(m.group(1)) + 1)
    for m in re.finditer(r"(\d{4})\s*年?(?:代)?\s*(?:以後|之後|以来|起|後)", prompt):
        raise_min(int(m.group(1)) + 1)
    # bare decade "1960年代" / "1960s" -> [1960, 1969]
    for m in re.finditer(r"(\d{3}0)\s*(?:年代|s)\b", prompt):
        decade = int(m.group(1))
        if 1880 <= decade <= 2030:
            raise_min(decade)
            tighten_max(decade + 9)

    # Soft era cues without explicit years.
    if any(cue in prompt for cue in ("黑白", "black and white", "black-and-white", "默片", "silent film")):
        tighten_max(1965)
    if any(cue in prompt for cue in ("黃金年代", "黄金年代", "golden age")):
        tighten_max(1965)

    # Sanity: ignore impossible windows.
    if min_year and max_year and min_year > max_year:
        return None, None
    if max_year is not None and max_year < 1888:
        max_year = None
    return min_year, max_year


def build_genre_weights(user_genre_ids: list[list[int]], user_ratings: list[float]) -> dict[int, float]:
    """Build genre weights from user ratings.

    Each watched movie contributes +1 base weight per genre, plus (rating - 5) delta.
    Ratings default to 5 (neutral) when missing.
    Final weights are clamped to >= 0.
    """
    weights: dict[int, float] = {}
    for genres, rating in zip(user_genre_ids, user_ratings):
        delta = rating - 5  # -4 to +5
        for genre_id in genres:
            try:
                gid = int(genre_id)
            except (TypeError, ValueError):
                continue
            weights[gid] = weights.get(gid, 0) + 1 + delta
    # Clamp to >= 0
    return {gid: max(0.0, w) for gid, w in weights.items()}


def score_metadata(movie: dict[str, Any], genre_weights: dict[int, float]) -> float:
    """Score a movie based on genre overlap with user's rating-weighted genre profile."""
    movie_genres = {int(genre) for genre in movie.get("genre_ids", []) if str(genre).isdigit()}

    # Genre score: sum of matching genre weights, capped
    genre_score = 0.0
    for gid in movie_genres:
        genre_score += genre_weights.get(gid, 0.0)
    genre_score = min(0.25, genre_score * 0.02)

    # TMDB rating bonus (small influence)
    rating_score = max(0.0, min(0.05, (float(movie.get("vote_average") or 0) - 5.0) * 0.01))

    return genre_score + rating_score


def score_context_filters(
    movie: dict[str, Any],
    playlist_genre_ids: set[int],
    preferred_languages: set[str],
) -> float:
    score = 0.0
    movie_genres = {int(genre) for genre in movie.get("genre_ids", []) if str(genre).isdigit()}
    if playlist_genre_ids:
        overlap = len(movie_genres.intersection(playlist_genre_ids))
        score += min(0.18, overlap * 0.06)

    language = clean_language_code(movie.get("original_language"))
    if language and language in preferred_languages:
        score += 0.08

    return score


def clamp_rating(value: Any) -> float:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return 5.0
    return max(1.0, min(10.0, rating))


def ensure_2d_tensor(tensor: Any) -> Any:
    if tensor.dim() == 1:
        return tensor.unsqueeze(0)
    return tensor


def build_taste_centers(embeddings: Any, weights: Any, max_centers: int = 3) -> Any:
    """Build one or more taste centers so mixed tastes do not collapse into one average."""
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    embeddings = ensure_2d_tensor(embeddings)
    if embeddings.size(0) < 5:
        weighted = embeddings * weights.unsqueeze(1)
        return ensure_2d_tensor(F.normalize(weighted.sum(dim=0, keepdim=True), p=2, dim=1))

    center_count = min(max_centers, 2 if embeddings.size(0) < 9 else 3, embeddings.size(0))
    first_index = int(torch.argmax(weights).item())
    selected = {first_index}
    centers = [embeddings[first_index]]

    for _ in range(1, center_count):
        similarities = torch.stack([torch.mv(embeddings, center) for center in centers], dim=1)
        distance = 1.0 - similarities.max(dim=1).values
        selection_score = distance * weights
        for index in selected:
            selection_score[index] = -1.0
        next_index = int(torch.argmax(selection_score).item())
        selected.add(next_index)
        centers.append(embeddings[next_index])

    centers_tensor = F.normalize(torch.stack(centers), p=2, dim=1)
    for _ in range(4):
        assignments = torch.mm(embeddings, centers_tensor.T).argmax(dim=1)
        next_centers = []
        for center_index in range(center_count):
            mask = assignments == center_index
            if bool(mask.any()):
                cluster_embeddings = embeddings[mask]
                cluster_weights = weights[mask]
                center = (cluster_embeddings * cluster_weights.unsqueeze(1)).sum(dim=0, keepdim=True)
                next_centers.append(F.normalize(center, p=2, dim=1).squeeze(0))
            else:
                next_centers.append(centers_tensor[center_index])
        centers_tensor = F.normalize(torch.stack(next_centers), p=2, dim=1)

    return centers_tensor


def clean_user_movie_ids(values: Any, limit: int = 200) -> list[int]:
    if not isinstance(values, list):
        return []
    movie_ids: list[int] = []
    for value in values[:limit]:
        try:
            movie_id = int(value)
        except (TypeError, ValueError):
            movie_id = 0
        movie_ids.append(movie_id)
    return movie_ids


def item_vector_scores(
    item_tensor: Any,
    user_movie_ids: list[int],
    user_ratings: list[float],
) -> tuple[Any, Any, int]:
    """Return MovieLens-style positive scores and negative penalties.

    The tensor is aligned with MOVIES. User movie IDs point to watched movies in
    the same index. Ratings >= 5 become positive taste centers; ratings < 5 are
    conservative post-ranking penalties.
    """
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    zero = torch.zeros(len(MOVIES), dtype=torch.float32, device=DEVICE)
    if item_tensor is None or not user_movie_ids:
        return zero, zero, 0

    positive_rows: list[int] = []
    positive_weights: list[float] = []
    negative_rows: list[int] = []
    negative_strengths: list[float] = []
    for movie_id, rating in zip(user_movie_ids, user_ratings):
        row = MOVIE_ID_TO_INDEX.get(movie_id)
        if row is None:
            continue
        vector_norm = float(item_tensor[row].abs().sum().detach().cpu().item())
        if vector_norm <= 0:
            continue
        if rating >= 5.0:
            positive_rows.append(row)
            positive_weights.append(max(0.1, rating / 5.0))
        else:
            negative_rows.append(row)
            negative_strengths.append((5.0 - rating) / 4.0)

    scores = zero
    center_count = 0
    if positive_rows:
        rows_tensor = torch.tensor(positive_rows, dtype=torch.long, device=DEVICE)
        positive_vectors = ensure_2d_tensor(item_tensor[rows_tensor])
        weights = torch.tensor(positive_weights, dtype=torch.float32, device=DEVICE)
        centers = ensure_2d_tensor(build_taste_centers(positive_vectors, weights))
        center_count = int(centers.size(0))
        scores = torch.mm(item_tensor, centers.T).max(dim=1).values.clamp(min=0.0)

    penalty = zero
    if negative_rows:
        rows_tensor = torch.tensor(negative_rows, dtype=torch.long, device=DEVICE)
        negative_vectors = ensure_2d_tensor(item_tensor[rows_tensor])
        strengths = torch.tensor(negative_strengths, dtype=torch.float32, device=DEVICE).clamp(0.0, 1.0)
        similarity = torch.mm(item_tensor, negative_vectors.T)
        penalty_curve = ((similarity - 0.55) / 0.45).clamp(0.0, 1.0)
        penalty = (penalty_curve * strengths.unsqueeze(0)).max(dim=1).values

    return scores, penalty, center_count


def movie_release_year(movie: dict[str, Any]) -> int | None:
    release = str(movie.get("release_date") or "").strip()
    if len(release) < 4 or not release[:4].isdigit():
        return None
    year = int(release[:4])
    if year < 1888 or year > 2100:
        return None
    return year


def clean_year_list(values: Any, limit: int = 100) -> list[int]:
    if not isinstance(values, list):
        return []
    years: list[int] = []
    for value in values[:limit]:
        try:
            year = int(str(value)[:4])
        except (TypeError, ValueError):
            continue
        if 1888 <= year <= 2100:
            years.append(year)
    return years


def score_year_affinity(movie: dict[str, Any], user_years: list[int]) -> float:
    if not user_years:
        return 0.0
    year = movie_release_year(movie)
    if year is None:
        return 0.0
    center_year = sum(user_years) / len(user_years)
    distance = abs(year - center_year)
    return max(0.0, 0.04 * (1.0 - min(distance, 40.0) / 40.0))


def off_profile_genre_penalty(
    movie_genres: set[int],
    genre_weights: dict[int, float],
    strength: float = 0.10,
) -> float:
    """Dampen candidates dominated by genres the user barely engages with.

    A genre that appears in only ONE favorite (e.g. War/History from a single
    WWII title) collapses the whole result set toward that setting through
    collaborative co-occurrence. We penalize a candidate in proportion to how
    many of its genres sit BELOW 25% of the user's strongest genre weight.

    The penalty is skipped unless the profile has a clear dominant genre
    (max weight >= 2, i.e. shared by at least two favorites), so single-genre
    zero-shot prompts are unaffected.
    """
    if not movie_genres or not genre_weights or strength <= 0:
        return 0.0
    max_weight = max(genre_weights.values(), default=0.0)
    if max_weight < 2.0:
        return 0.0
    threshold = 0.25 * max_weight
    off_profile = sum(1 for gid in movie_genres if genre_weights.get(gid, 0.0) < threshold)
    return strength * (off_profile / len(movie_genres))


def movie_quality_score(movie: dict[str, Any]) -> float:
    vote_average = max(0.0, min(10.0, float(movie.get("vote_average") or 0))) / 10.0
    vote_count = max(0, int(movie.get("vote_count") or 0))
    popularity = min(1.0, math.log1p(vote_count) / math.log1p(10000))
    return vote_average * 0.7 + popularity * 0.3


def fallback_recommendations(top_k: int, exclude_ids: set[int]) -> list[dict[str, Any]]:
    logger.info("No taste profile found, falling back to metadata-quality movies.")
    candidates: list[dict[str, Any]] = []
    for movie in MOVIES:
        if movie["id"] in exclude_ids:
            continue
        if not movie.get("poster_path"):
            continue
        if movie.get("vote_count", 0) < 20:
            continue
        score = movie_quality_score(movie)
        candidates.append(
            {
                **movie,
                "semantic_score": 0.0,
                "adjusted_semantic_score": round(score, 4),
                "negative_penalty": 0.0,
                "penalty_multiplier": 1.0,
                "metadata_score": round(score, 4),
                "score": round(score, 4),
                "fallback_reason": "metadata_cold_start",
            }
        )
    candidates.sort(key=lambda m: m["score"], reverse=True)
    return candidates[:top_k]


def diversity_rerank(candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Greedy top-k rerank with small penalties for repeated language, genre, and collection."""
    selected: list[dict[str, Any]] = []
    remaining = sorted(candidates, key=lambda movie: movie["score"], reverse=True)
    genre_counts: dict[int, int] = {}
    language_counts: dict[str, int] = {}
    collection_counts: dict[str, int] = {}

    while remaining and len(selected) < top_k:
        best_index = 0
        best_score = float("-inf")
        for index, movie in enumerate(remaining[: max(30, top_k * 4)]):
            movie_genres = {int(genre) for genre in movie.get("genre_ids", []) if str(genre).isdigit()}
            language = clean_language_code(movie.get("original_language")) or ""
            collection = str(movie.get("collection_name") or "").strip().lower()
            penalty = 0.0
            penalty += sum(max(0, genre_counts.get(genre, 0) - 1) * 0.025 for genre in movie_genres)
            if language:
                penalty += max(0, language_counts.get(language, 0) - 2) * 0.02
            if collection:
                penalty += collection_counts.get(collection, 0) * 0.08
            diversified_score = float(movie["score"]) - min(0.18, penalty)
            if diversified_score > best_score:
                best_score = diversified_score
                best_index = index

        movie = remaining.pop(best_index)
        movie["diversified_score"] = round(best_score, 4)
        selected.append(movie)
        for genre in movie.get("genre_ids", []):
            try:
                genre_id = int(genre)
            except (TypeError, ValueError):
                continue
            genre_counts[genre_id] = genre_counts.get(genre_id, 0) + 1
        language = clean_language_code(movie.get("original_language"))
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1
        collection = str(movie.get("collection_name") or "").strip().lower()
        if collection:
            collection_counts[collection] = collection_counts.get(collection, 0) + 1

    return selected


QUERY_GENRE_NAMES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}


def query_template_text(prompt: str, genre_ids: list[int] | None = None, *, fill_unknown: bool = True) -> str:
    """Wrap a raw user prompt into the same rich-text template used for corpus vectors.

    This ensures query and corpus embeddings live in the same semantic space.
    """
    genre_names = [QUERY_GENRE_NAMES.get(gid, str(gid)) for gid in (genre_ids or []) if str(gid).isdigit()]
    if fill_unknown:
        # Variant (a): all fields present, unknown where missing.
        parts = [
            f"Title: unknown",
            f"Genres: {', '.join(genre_names) if genre_names else 'unknown'}",
            f"Original language: unknown",
            f"Release year: unknown",
            f"Audience rating: unknown",
            f"Plot and atmosphere: {prompt}",
        ]
    else:
        # Variant (b): omit fields that are unknown.
        parts = []
        if genre_names:
            parts.append(f"Genres: {', '.join(genre_names)}")
        parts.append(f"Plot and atmosphere: {prompt}")
    return "\n".join(parts)


_PRIVATE_NETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def normalize_llm_url(raw_url: str | None) -> str | None:
    """Normalize an OpenAI-compatible chat completions URL.

    Returns the full /chat/completions URL, or None if the input is invalid.
    HTTP is only allowed for private/local networks; public hosts must use HTTPS.
    """
    if not raw_url:
        return None
    url = raw_url.strip()
    if not url:
        return None

    # If it already ends with /chat/completions, accept as-is.
    if url.rstrip("/").endswith("/chat/completions"):
        parsed = urlparse(url)
    elif url.rstrip("/").endswith("/v1"):
        url = url.rstrip("/") + "/chat/completions"
        parsed = urlparse(url)
    else:
        # Treat as base URL — append /v1/chat/completions
        url = url.rstrip("/") + "/v1/chat/completions"
        parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    hostname = parsed.hostname or ""
    if parsed.scheme == "http":
        # Only allow localhost / private IPs over plain HTTP.
        try:
            ip = ipaddress.ip_address(hostname)
            is_private = any(ip in net for net in _PRIVATE_NETS)
        except ValueError:
            is_private = hostname in ("localhost", "127.0.0.1")
        if not is_private:
            logger.warning("LLM URL rejected: HTTP not allowed for public host %s", hostname)
            return None

    return url


def _extract_json_block(text: str) -> dict | None:
    """Try to parse JSON from LLM output, stripping markdown fences if needed."""
    text = text.strip()
    # Strip ```json ... ``` fences
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: grab first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: repair truncated JSON by closing open braces/brackets
    if start != -1:
        snippet = text[start:]
        # Remove trailing incomplete entries
        snippet = re.sub(r',\s*"[^"]*":\s*"[^"]*$', "", snippet)
        snippet = re.sub(r',\s*"[^"]*":\s*\[?[^\]}]*$', "", snippet)
        # Close open brackets/braces
        open_braces = snippet.count("{") - snippet.count("}")
        open_brackets = snippet.count("[") - snippet.count("]")
        snippet += "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        try:
            return json.loads(snippet)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


# ---------------------------------------------------------------------------
# Query expansion — improve recall for short / ambiguous queries
# ---------------------------------------------------------------------------

_QUERY_EXPANSIONS: dict[str, list[str]] = {
    # Chinese YA / campus
    "校園": ["campus", "high school", "teen", "coming-of-age", "young adult", "student life"],
    "YA": ["young adult", "teen", "high school", "coming-of-age", "adolescent"],
    "青春": ["youth", "teen", "coming-of-age", "young adult", "adolescent"],
    "校园": ["campus", "high school", "teen", "coming-of-age", "young adult"],
    # English YA / campus
    "campus": ["high school", "university", "student", "dorm", "classroom"],
    "teen": ["high school", "adolescent", "young adult", "coming-of-age"],
    "young adult": ["teen", "high school", "coming-of-age", "adolescent"],
    "coming-of-age": ["teen", "growing up", "adolescent", "youth", "first love"],
    "high school": ["campus", "teen", "prom", "graduation", "student"],
    # Horror / thriller (negative signal — helps model distinguish)
    "恐怖": ["horror", "scary", "slasher", "supernatural"],
    "horror": ["scary", "slasher", "supernatural", "haunted"],
    # Romance / comedy
    "戀愛": ["romance", "love story", "romantic", "dating"],
    "romance": ["love", "romantic", "dating", "relationship"],
    "喜劇": ["comedy", "funny", "humorous", "lighthearted"],
    "comedy": ["funny", "humorous", "lighthearted", "hilarious"],
}


_COLLECTION_ANALYSIS_SYSTEM = (
    "You are a movie taste analyst. Given a user's favorite movies, extract "
    "the DEEPER themes, tone, and psychological patterns — NOT surface-level genre tags.\n\n"
    "Critical rules:\n"
    "- If only ONE movie has a special setting (war, sci-fi, historical), do NOT "
    "drift the entire analysis toward that setting. Instead, extract the HUMAN "
    "core underneath it (e.g., moral dilemmas, institutional critique, trauma).\n"
    "- Prioritize: human nature dilemmas, psychological tension, moral conflict, "
    "emotional trauma, dialogue-driven intensity, social critique, dark realism.\n"
    "- Output ONLY 8-15 comma-separated lowercase English feature tags. "
    "No explanations, no movie titles."
)


def _llm_analyze_collection(
    movie_ids: list[int],
    api_url: str,
    api_key: str,
    model: str,
) -> str | None:
    """Analyze a user's movie collection via LLM to extract deep taste features.

    Returns a feature tag string on success, None on failure.
    """
    try:
        import requests as _requests
    except ImportError:
        return None

    url = normalize_llm_url(api_url)
    if not url:
        return None

    # Build compact movie list from the index.
    movie_lines = []
    for mid in movie_ids[:15]:
        idx = MOVIE_ID_TO_INDEX.get(mid)
        if idx is None:
            continue
        m = MOVIES[idx]
        genre_str = ",".join(str(g) for g in m.get("genre_ids", []))
        movie_lines.append(f'{m["title"]}({m.get("release_date","")[:4]},genres:[{genre_str}])')

    if not movie_lines:
        return None

    movies_str = " | ".join(movie_lines)
    user_msg = (
        f"User's favorite movies: {movies_str}\n\n"
        "Extract the deeper themes, tone, and psychological patterns as "
        "8-15 comma-separated English feature tags."
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _COLLECTION_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 2500,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        resp = _requests.post(url, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            reasoning = data["choices"][0]["message"].get("reasoning_content") or ""
            for line in reversed(reasoning.strip().splitlines()):
                line = line.strip().strip('"\'')
                if "," in line and len(line) < 300:
                    content = line
                    break
        if "high risk" in content.lower() or "rejected" in content.lower():
            logger.debug("Collection analysis blocked by safety filter")
            return None
        if content:
            return content.strip('"\'')
    except Exception as exc:
        logger.debug("Collection analysis failed: %s", exc)
    return None


def _rule_based_expand(text: str, max_extra_terms: int = 6) -> str:
    """Append relevant genre/synonym terms using keyword matching."""
    text_lower = text.lower()
    extra: list[str] = []
    seen: set[str] = set()

    for keyword, expansions in _QUERY_EXPANSIONS.items():
        if keyword.lower() in text_lower:
            for term in expansions:
                if term.lower() not in seen and term.lower() not in text_lower:
                    extra.append(term)
                    seen.add(term.lower())
                if len(extra) >= max_extra_terms:
                    break
        if len(extra) >= max_extra_terms:
            break

    if extra:
        return f"{text}. Related: {', '.join(extra)}"
    return text


_LLM_EXPAND_SYSTEM = (
    "You are a movie intent parser. Given a user query in any language, "
    "output 8-15 concise English feature tags that describe the movie type "
    "the user wants. Include: genre, mood/tone, setting, themes, visual style, "
    "target audience. Output ONLY a comma-separated list of lowercase English "
    "tags. No explanations, no movie titles, no numbering.\n\n"
    "Examples:\n"
    "Input: 想看校園YA片\n"
    "Output: young adult, high school, campus, teen comedy, coming-of-age, "
    "romantic comedy, lighthearted, friendship, social dynamics, prom, graduation\n\n"
    "Input: 那種很中二、主角突然拿到超能力的爽片\n"
    "Output: superpower, action, fantasy, overpowered protagonist, shounen, "
    "anime-style, escapist, power fantasy, supernatural ability\n\n"
    "Input: 看完會很emo的深夜療癒電影\n"
    "Output: emotional, healing, melancholy, slice of life, contemplative, "
    "bittersweet, introspective, quiet drama, therapeutic, late night mood\n\n"
    "Input: a dark crime thriller with detective investigation\n"
    "Output: crime, thriller, detective, noir, investigation, suspense, "
    "dark atmosphere, murder mystery, psychological tension"
)


def _llm_expand_query(text: str, api_url: str, api_key: str, model: str) -> str | None:
    """Call an LLM to expand a query into English feature tags.

    Returns the expanded text on success, None on failure.
    """
    try:
        import requests as _requests
    except ImportError:
        return None

    url = normalize_llm_url(api_url)
    if not url:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _LLM_EXPAND_SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "max_tokens": 250,
    }

    try:
        resp = _requests.post(url, json=body, headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        # Some reasoning models put output in reasoning_content when content is empty.
        if not content:
            reasoning = data["choices"][0]["message"].get("reasoning_content") or ""
            if reasoning and "," in reasoning:
                # Extract the last line that looks like a tag list
                for line in reversed(reasoning.strip().splitlines()):
                    line = line.strip().strip('"\'')
                    if "," in line and len(line) < 300:
                        content = line
                        break
        # Handle safety filter rejections
        if "high risk" in content.lower() or "rejected" in content.lower():
            logger.debug("LLM expansion blocked by safety filter; falling back.")
            return None
        # Clean up: remove numbering, bullet points, quotes
        content = content.strip('"\'')
        if content:
            return f"{text}. Features: {content}"
    except Exception as exc:
        logger.debug("LLM query expansion failed: %s", exc)
    return None


def expand_query(
    text: str,
    *,
    max_extra_terms: int = 6,
    llm_api_url: str = "",
    llm_api_key: str = "",
    llm_model: str = "",
) -> str:
    """Expand a query for better recall.

    Tries LLM dynamic expansion first (if credentials provided),
    falls back to rule-based keyword matching.
    """
    # Try LLM expansion first
    if llm_api_url and llm_api_key and llm_model:
        expanded = _llm_expand_query(text, llm_api_url, llm_api_key, llm_model)
        if expanded:
            return expanded
        logger.debug("LLM expansion returned nothing; falling back to rule-based.")

    # Fallback: rule-based
    return _rule_based_expand(text, max_extra_terms)


# ---------------------------------------------------------------------------
# Genre hard filtering — whitelist / blacklist
# ---------------------------------------------------------------------------

def genre_filter_check(
    movie_genres: set[int],
    whitelist: set[int],
    blacklist: set[int],
) -> bool:
    """Return True if the movie passes genre filters.

    - blacklist: if ANY movie genre is in blacklist → reject
    - whitelist: if whitelist is non-empty and movie has ZERO overlap → reject
    """
    if blacklist and not movie_genres.isdisjoint(blacklist):
        return False
    if whitelist and movie_genres.isdisjoint(whitelist):
        return False
    return True


def _call_llm_narrator(
    *,
    api_url: str,
    api_key: str,
    model: str,
    prompt_texts: list[str],
    taste_profile: dict[str, Any],
    playlist: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Call an OpenAI-compatible chat completions API to narrate results.

    Returns a dict with keys ``title``, ``summary``, ``reasons`` on success,
    or None on any failure.  Never raises.
    """
    try:
        import requests as _requests
    except ImportError:
        logger.warning("requests library not installed; skipping LLM narration.")
        return None

    url = normalize_llm_url(api_url)
    if not url:
        logger.warning("Invalid or rejected LLM API URL: %s", api_url)
        return None

    # Build compact movie list for the LLM (top 12 max).
    movies_for_llm = []
    for movie in ranked_candidates[:12]:
        movies_for_llm.append(
            {
                "id": movie.get("id"),
                "title": movie.get("title", ""),
                "overview": (movie.get("overview") or "")[:300],
                "genre_ids": movie.get("genre_ids", []),
                "release_date": movie.get("release_date", ""),
                "original_language": movie.get("original_language", ""),
                "score": movie.get("score"),
                "semantic_score": movie.get("semantic_score"),
                "svd_score": movie.get("svd_score"),
                "genome_score": movie.get("genome_score"),
                "context_score": movie.get("context_score"),
            }
        )

    # Build a compact prompt to minimize reasoning overhead for reasoning models.
    # A shorter prompt = fewer reasoning tokens = more room for actual output.
    movie_lines = []
    for m in movies_for_llm[:10]:
        genre_str = ",".join(str(g) for g in m.get("genre_ids", []))
        movie_lines.append(f'{m["title"]}(id:{m["id"]},genres:[{genre_str}],score:{m.get("score",0):.2f})')
    movies_compact = " | ".join(movie_lines)

    user_payload = (
        f'User query: {json.dumps(prompt_texts, ensure_ascii=False)}\n'
        f'Movies (ranked): {movies_compact}\n\n'
        'Output JSON only. Use ONLY the movies above. Do NOT invent titles.\n'
        '{"title":"playlist name","summary":"one sentence","reasons":[{"id":N,"reason":"why"}]}'
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": user_payload},
        ],
        "temperature": 0.3,
        "max_tokens": 2500,
    }

    try:
        resp = _requests.post(url, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("LLM API call failed: %s", exc)
        return None

    # Extract content from choices[0].message.content
    content = ""
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        logger.warning("LLM response missing choices[0].message.content")
        return None

    # Fallback: reasoning models may put JSON in reasoning_content
    if not content:
        reasoning = data["choices"][0]["message"].get("reasoning_content") or ""
        if reasoning:
            parsed = _extract_json_block(reasoning)
            if parsed:
                return _narrator_from_parsed(parsed, ranked_candidates)
        logger.warning("LLM narrator returned empty content")
        return None

    parsed = _extract_json_block(content)
    if not isinstance(parsed, dict):
        logger.warning("LLM response was not valid JSON: %s", content[:200])
        return None

    return _narrator_from_parsed(parsed, ranked_candidates)


def _narrator_from_parsed(
    parsed: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract title, summary, reasons from a parsed LLM JSON response."""
    title = str(parsed.get("title") or "").strip()
    summary = str(parsed.get("summary") or "").strip()
    reasons_raw = parsed.get("reasons")
    reasons_by_id: dict[int, str] = {}
    if isinstance(reasons_raw, list):
        for entry in reasons_raw:
            if isinstance(entry, dict):
                try:
                    mid = int(entry.get("id"))
                except (TypeError, ValueError):
                    continue
                reason = str(entry.get("reason") or "").strip()
                if mid and reason:
                    reasons_by_id[mid] = reason

    return {"title": title, "summary": summary, "reasons_by_id": reasons_by_id}


@app.route("/status", methods=["GET"])
def status():
    return jsonify(
        {
            "status": "online",
            "model": MODEL_NAME,
            "device": str(DEVICE),
            "movie_count": len(MOVIES),
            "index_loaded": VECTOR_TENSOR is not None,
            "hybrid": {
                "svd_loaded": SVD_TENSOR is not None,
                "genome_loaded": GENOME_TENSOR is not None,
            },
        }
    )


@app.route("/embed", methods=["POST"])
def embed():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    vector = embed_texts([text])[0].detach().cpu().tolist()
    return jsonify({"vector": vector})


@app.route("/reload_db", methods=["POST"])
def reload_db():
    data = request.get_json(silent=True) or {}
    requested = data.get("path")
    path = Path(requested) if requested else (VECTOR_PATH or first_existing_vector_file())
    if not path.is_absolute():
        path = ROOT / path
    ok = load_vector_index(path)
    return jsonify({"status": "ok" if ok else "missing", "movie_count": len(MOVIES)})


@app.route("/search", methods=["POST"])
def search():
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    if VECTOR_TENSOR is None:
        logger.warning("Search requested before vector index was loaded.")
        return jsonify({"error": "Vector index is not loaded", "results": []}), 503
    if not MOVIES:
        logger.warning("Search requested with an empty movie index.")
        return jsonify({"error": "Vector index is empty", "results": []}), 503
    if VECTOR_TENSOR.dim() != 2:
        logger.error("Vector index has invalid tensor shape: %s", tuple(VECTOR_TENSOR.shape))
        return jsonify({"error": "Vector index must be a 2D tensor", "results": []}), 500

    data = request.get_json(silent=True) or {}
    try:
        top_k = max(1, min(50, int(data.get("top_k") or 10)))
    except (TypeError, ValueError):
        top_k = 10
    exclude_ids = {int(value) for value in data.get("exclude_ids", []) if str(value).isdigit()}
    genre_whitelist = set(clean_flat_int_list(data.get("genre_whitelist") or []))
    genre_blacklist = set(clean_flat_int_list(data.get("genre_blacklist") or []))
    user_movie_ids = clean_user_movie_ids(data.get("user_movie_ids", []), limit=200)
    user_genre_ids = data.get("user_genre_ids", [])
    if not isinstance(user_genre_ids, list):
        user_genre_ids = []
    playlist_genre_ids = set(
        clean_flat_int_list(
            data.get("playlist_genre_ids")
            or data.get("required_genre_ids")
            or data.get("filter_genre_ids")
            or []
        )
    )
    preferred_languages = set(
        clean_language_list(
            data.get("preferred_languages")
            or data.get("playlist_languages")
            or data.get("languages")
            or []
        )
    )

    overviews = data.get("overviews")
    if not overviews and data.get("text"):
        overviews = [data.get("text")]
    if not isinstance(overviews, list):
        overviews = []
    texts = [str(text).strip() for text in overviews if str(text).strip()]

    # Extract LLM config (shared by expansion, collection analysis, narrator).
    _llm_cfg = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    _exp_api_url = data.get("llm_api_url") or _llm_cfg.get("api_url") or ""
    _exp_api_key = data.get("llm_api_key") or _llm_cfg.get("api_key") or ""
    _exp_model = data.get("llm_model") or _llm_cfg.get("model") or ""

    # Collection-based taste analysis: when user_movie_ids is provided without
    # text queries, analyze the collection's themes via LLM to generate feature
    # tags for embedding.
    if not texts and user_movie_ids and _exp_api_url and _exp_api_key and _exp_model:
        collection_tags = _llm_analyze_collection(
            user_movie_ids, _exp_api_url, _exp_api_key, _exp_model
        )
        if collection_tags:
            texts = [collection_tags]

    # Expand short queries with relevant synonyms for better recall.
    expanded_texts = [
        expand_query(t, llm_api_url=_exp_api_url, llm_api_key=_exp_api_key, llm_model=_exp_model)
        for t in texts
    ]
    inferred_genres, inferred_languages = infer_context_filters(texts)
    playlist_genre_ids.update(inferred_genres)
    preferred_languages.update(inferred_languages)
    era_min_year, era_max_year = infer_year_window(texts)

    # Parse user ratings (1.0-10.0), default to 5 for missing/invalid.
    raw_ratings = data.get("user_vote_counts", [])
    if not isinstance(raw_ratings, list):
        raw_ratings = []
    user_ratings: list[float] = []
    for val in raw_ratings:
        user_ratings.append(clamp_rating(val))
    # Pad to match all taste inputs.
    while len(user_ratings) < max(len(user_genre_ids), len(texts), len(user_movie_ids)):
        user_ratings.append(5.0)
    user_release_years = clean_year_list(data.get("user_release_years"), limit=100)

    # Soft language affinity from the collection: if the favorites lean toward a
    # non-English language, gently boost candidates in that language. This is a
    # bonus only (never a hard filter), so an English speaker who loves Korean
    # thrillers still gets English neighbors, just with Korean cinema surfaced.
    collection_languages: set[str] = set()
    if user_movie_ids:
        lang_counts: dict[str, int] = {}
        resolved = 0
        for mid in user_movie_ids:
            row = MOVIE_ID_TO_INDEX.get(mid)
            if row is None:
                continue
            resolved += 1
            code = clean_language_code(MOVIES[row].get("original_language"))
            if code:
                lang_counts[code] = lang_counts.get(code, 0) + 1
        if resolved >= 2 and lang_counts:
            top_lang, top_n = max(lang_counts.items(), key=lambda kv: kv[1])
            if top_lang != "en" and top_n >= max(2, 0.4 * resolved):
                collection_languages.add(top_lang)

    # Build rating-weighted genre profile
    genre_weights = build_genre_weights(user_genre_ids, user_ratings)

    svd_scores_tensor, svd_penalty_tensor, svd_center_count = item_vector_scores(
        SVD_TENSOR,
        user_movie_ids,
        user_ratings[: len(user_movie_ids)],
    )
    genome_scores_tensor, genome_penalty_tensor, genome_center_count = item_vector_scores(
        GENOME_TENSOR,
        user_movie_ids,
        user_ratings[: len(user_movie_ids)],
    )
    has_item_signal = bool(svd_center_count or genome_center_count)

    # BERT semantic scores from user_movie_ids (collection-based recommendation).
    # This runs when user_movie_ids is provided, even without text queries.
    bert_scores_tensor, bert_penalty_tensor, bert_center_count = item_vector_scores(
        VECTOR_TENSOR,
        user_movie_ids,
        user_ratings[: len(user_movie_ids)],
    )

    # Build rating-weighted user embeddings. Low-rated movies are not
    # subtracted as negative vectors; they are used later as a post-ranking
    # penalty against candidates that are too similar to disliked items.
    raw_embeddings = None
    semantic_ratings = user_ratings[:len(texts)]
    positive_indices = [index for index, rating in enumerate(semantic_ratings) if rating >= 5.0]
    negative_indices = [index for index, rating in enumerate(semantic_ratings) if rating < 5.0]
    taste_profile_mode = "metadata_fallback"
    taste_center_count = 0
    semantic_scores_tensor = torch.zeros(len(MOVIES), dtype=torch.float32, device=DEVICE)
    semantic_penalty_tensor = torch.zeros(len(MOVIES), dtype=torch.float32, device=DEVICE)

    if texts:
        # Apply the same rich-text template used for corpus vectors so that
        # query and corpus embeddings live in the same semantic space.
        embedding_texts = [
            query_template_text(t, sorted(playlist_genre_ids), fill_unknown=True)
            for t in expanded_texts
        ]
        raw_embeddings = ensure_2d_tensor(embed_texts(embedding_texts))  # shape: (n_texts, dim)
        if raw_embeddings.dim() != 2 or raw_embeddings.size(1) != VECTOR_TENSOR.size(1):
            logger.error(
                "Embedding dimension mismatch: embedding=%s index=%s",
                tuple(raw_embeddings.shape),
                tuple(VECTOR_TENSOR.shape),
            )
            return jsonify({"error": "Embedding dimension does not match vector index", "results": []}), 500

        if positive_indices:
            selected_embeddings = ensure_2d_tensor(raw_embeddings[positive_indices])
            weights = torch.tensor(
                [max(0.1, semantic_ratings[index] / 5.0) for index in positive_indices],
                dtype=torch.float32,
                device=DEVICE,
            )
            taste_centers = ensure_2d_tensor(build_taste_centers(selected_embeddings, weights))
            taste_center_count = int(taste_centers.size(0))
            taste_profile_mode = "multi_center" if taste_center_count > 1 else "single_center"
            center_scores = torch.mm(VECTOR_TENSOR, taste_centers.T)
            semantic_scores_tensor = center_scores.max(dim=1).values.clamp(min=0.0)
        elif negative_indices:
            logger.info("Only low-rated semantic taste inputs were provided; using hybrid metadata shortlist plus penalties.")

        if negative_indices:
            negative_embeddings = ensure_2d_tensor(raw_embeddings[negative_indices])
            negative_similarity = torch.mm(VECTOR_TENSOR, negative_embeddings.T)
            dislike_strength = torch.tensor(
                [(5.0 - semantic_ratings[index]) / 4.0 for index in negative_indices],
                dtype=torch.float32,
                device=DEVICE,
            ).clamp(0.0, 1.0)
            penalty_curve = ((negative_similarity - 0.55) / 0.45).clamp(0.0, 1.0)
            semantic_penalty_tensor = (penalty_curve * dislike_strength.unsqueeze(0)).max(dim=1).values

    # When no text query but user_movie_ids provided, use BERT collection scores.
    has_bert_item_signal = bool(bert_center_count) and not texts
    if has_bert_item_signal:
        semantic_scores_tensor = bert_scores_tensor
        semantic_penalty_tensor = bert_penalty_tensor
        taste_profile_mode = "collection_center"
        taste_center_count = bert_center_count

    has_any_signal = bool(texts) or has_item_signal or has_bert_item_signal
    if not has_any_signal:
        return jsonify({"results": fallback_recommendations(top_k, exclude_ids), "fallback": "metadata_cold_start"})

    metadata_scores_tensor = torch.tensor(
        [movie_quality_score(movie) for movie in MOVIES],
        dtype=torch.float32,
        device=DEVICE,
    )
    # Scoring weights: BERT semantic gets 58% when available, SVD 16%, Genome 26%.
    semantic_weight = 0.58 if (texts or has_bert_item_signal) else 0.0
    genome_weight = 0.26 if (has_item_signal or has_bert_item_signal) else 0.0
    svd_weight = 0.16 if (has_item_signal or has_bert_item_signal) else 0.0
    active_weight = semantic_weight + genome_weight + svd_weight
    if active_weight <= 0:
        active_weight = 1.0
    shortlist_scores = (
        (semantic_scores_tensor * semantic_weight)
        + (genome_scores_tensor * genome_weight)
        + (svd_scores_tensor * svd_weight)
    ) / active_weight
    # Text-only queries have no collaborative (SVD/genome) signal to act as a
    # quality prior, so a pure-semantic match lets obscure keyword hits outrank
    # canonical films. Lean harder on the metadata quality prior in that case.
    metadata_weight = 0.22 if (texts and not has_item_signal) else 0.08
    shortlist_scores = (shortlist_scores * (1.0 - metadata_weight)) + (metadata_scores_tensor * metadata_weight)

    # First shortlist from the positive taste signal or metadata fallback.
    has_era_filter = bool(era_min_year or era_max_year)
    has_context_filters = bool(playlist_genre_ids or preferred_languages or has_era_filter)
    # Release year is invisible to the embedding, so an era query needs the full
    # catalogue scanned (era-matching films rarely sit in the semantic top pool).
    if has_era_filter:
        pool_size = len(MOVIES)
    else:
        pool_size = min(len(MOVIES), max(top_k * 80, 1000 if has_context_filters else 300))
    _, top_indices_tensor = torch.topk(shortlist_scores, k=pool_size)
    top_indices = top_indices_tensor.detach().cpu().tolist()

    shortlist_semantic_scores = semantic_scores_tensor[top_indices_tensor]
    shortlist_base_scores = shortlist_scores[top_indices_tensor]
    shortlist_penalty = torch.stack(
        [
            semantic_penalty_tensor[top_indices_tensor],
            svd_penalty_tensor[top_indices_tensor],
            genome_penalty_tensor[top_indices_tensor],
        ],
        dim=1,
    ).max(dim=1).values

    shortlist_multiplier = 1.0 - (shortlist_penalty * 0.8)
    shortlist_adjusted_scores = shortlist_base_scores * shortlist_multiplier

    semantic_scores = shortlist_semantic_scores.detach().cpu().tolist()
    svd_scores = svd_scores_tensor[top_indices_tensor].detach().cpu().tolist()
    genome_scores = genome_scores_tensor[top_indices_tensor].detach().cpu().tolist()
    adjusted_scores = shortlist_adjusted_scores.detach().cpu().tolist()
    penalties = shortlist_penalty.detach().cpu().tolist()
    multipliers = shortlist_multiplier.detach().cpu().tolist()

    candidates: list[dict[str, Any]] = []
    relaxed_context_filters = False

    def add_candidate(index: int, shortlist_position: int, apply_context_filters: bool = True) -> None:
        movie = MOVIES[index]
        if movie["id"] in exclude_ids:
            return
        if not movie.get("poster_path"):
            return
        if movie.get("vote_count", 0) < 20:
            return
        movie_genres = {int(genre) for genre in movie.get("genre_ids", []) if str(genre).isdigit()}
        if apply_context_filters and playlist_genre_ids and movie_genres.isdisjoint(playlist_genre_ids):
            return
        # Genre hard filtering (whitelist/blacklist)
        if not genre_filter_check(movie_genres, genre_whitelist, genre_blacklist):
            return
        language = clean_language_code(movie.get("original_language"))
        if apply_context_filters and preferred_languages and language and language not in preferred_languages:
            return
        if apply_context_filters and has_era_filter:
            movie_year = movie_release_year(movie)
            if movie_year is None:
                return
            if era_min_year and movie_year < era_min_year:
                return
            if era_max_year and movie_year > era_max_year:
                return

        meta_score = score_metadata(movie, genre_weights)
        context_score = score_context_filters(movie, playlist_genre_ids, preferred_languages)
        year_score = score_year_affinity(movie, user_release_years)
        # Only dampen on the collection/favorites path, where genre_weights reflect
        # a genuine multi-title profile. Zero-shot text prompts have a synthetic
        # single-genre profile and must not be penalized.
        off_profile_penalty = 0.0 if texts else off_profile_genre_penalty(movie_genres, genre_weights)
        collection_lang_bonus = 0.10 if (language and language in collection_languages) else 0.0
        final = (
            float(adjusted_scores[shortlist_position])
            + meta_score
            + context_score
            + year_score
            + collection_lang_bonus
            - off_profile_penalty
        )
        candidates.append(
            {
                **movie,
                "semantic_score": round(float(semantic_scores[shortlist_position]), 4),
                "svd_score": round(float(svd_scores[shortlist_position]), 4),
                "genome_score": round(float(genome_scores[shortlist_position]), 4),
                "adjusted_semantic_score": round(float(adjusted_scores[shortlist_position]), 4),
                "negative_penalty": round(float(penalties[shortlist_position]), 4),
                "penalty_multiplier": round(float(multipliers[shortlist_position]), 4),
                "metadata_score": round(meta_score, 4),
                "context_score": round(context_score, 4),
                "year_score": round(year_score, 4),
                "off_profile_penalty": round(off_profile_penalty, 4),
                "collection_lang_bonus": round(collection_lang_bonus, 4),
                "score": round(final, 4),
                "playlist_genre_match": sorted(movie_genres.intersection(playlist_genre_ids)),
                "playlist_language_match": bool(language and language in preferred_languages),
            }
        )

    for position, movie_index in enumerate(top_indices):
        add_candidate(movie_index, position)

    if not candidates and has_context_filters:
        relaxed_context_filters = True
        for position, movie_index in enumerate(top_indices):
            add_candidate(movie_index, position, apply_context_filters=False)

    candidates.sort(key=lambda m: m["score"], reverse=True)
    ranked_candidates = diversity_rerank(candidates, top_k)

    # --- LLM narrator (optional, graceful fallback) ---
    llm_block: dict[str, Any] = {"enabled": False}
    llm_cfg = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    llm_api_url = data.get("llm_api_url") or llm_cfg.get("api_url") or ""
    llm_api_key = data.get("llm_api_key") or llm_cfg.get("api_key") or ""
    llm_model = data.get("llm_model") or llm_cfg.get("model") or ""

    if llm_api_url and llm_api_key and llm_model:
        llm_block = {"enabled": True, "model": llm_model}
        # Strip original query from expanded text to avoid safety filters on
        # Chinese/sensitive keywords.  Keep only the English feature tags.
        narrator_texts = []
        for orig, expanded in zip(texts, expanded_texts):
            if ". Features: " in expanded:
                narrator_texts.append(expanded.split(". Features: ", 1)[1])
            elif ". Related: " in expanded:
                narrator_texts.append(expanded.split(". Related: ", 1)[1])
            else:
                narrator_texts.append(expanded)
        narration = _call_llm_narrator(
            api_url=llm_api_url,
            api_key=llm_api_key,
            model=llm_model,
            prompt_texts=narrator_texts,
            taste_profile={
                "mode": taste_profile_mode,
                "center_count": taste_center_count,
                "bert_center_count": bert_center_count,
                "svd_center_count": svd_center_count,
                "genome_center_count": genome_center_count,
                "release_year_count": len(user_release_years),
            },
            playlist={
                "mode": "zero_shot_semantic",
                "genre_ids": sorted(playlist_genre_ids),
                "preferred_languages": sorted(preferred_languages),
                "relaxed_context_filters": relaxed_context_filters,
            },
            ranked_candidates=ranked_candidates,
        )
        if narration:
            reasons_map = narration.get("reasons_by_id", {})
            for movie in ranked_candidates:
                reason = reasons_map.get(movie.get("id"))
                if reason:
                    movie["reason"] = reason
            llm_block["title"] = narration.get("title", "")
            llm_block["summary"] = narration.get("summary", "")
        else:
            llm_block["error"] = "LLM narration failed; results are unmodified"

    return jsonify(
        {
            "results": ranked_candidates,
            "playlist": {
                "mode": "zero_shot_semantic",
                "genre_ids": sorted(playlist_genre_ids),
                "preferred_languages": sorted(preferred_languages),
                "relaxed_context_filters": relaxed_context_filters,
            },
            "taste_profile": {
                "mode": taste_profile_mode,
                "center_count": taste_center_count,
                "bert_center_count": bert_center_count,
                "svd_center_count": svd_center_count,
                "genome_center_count": genome_center_count,
                "release_year_count": len(user_release_years),
            },
            "llm": llm_block,
        }
    )


def parse_args() -> argparse.Namespace:
    return build_parser(str(first_existing_vector_file())).parse_args()


def main() -> int:
    global BERT_GATEWAY_TOKEN
    load_dotenv(ROOT / ".env")
    BERT_GATEWAY_TOKEN = os.getenv("BERT_GATEWAY_TOKEN", "")
    args = parse_args()
    try:
        device = resolve_device(args.device)
        load_model(args.model, device)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    vector_path = Path(args.vectors)
    if not vector_path.is_absolute():
        vector_path = ROOT / vector_path
    try:
        load_vector_index(vector_path)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Starting service at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
