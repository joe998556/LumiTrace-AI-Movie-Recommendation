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
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "AventIQ-AI/bert-movie-recommendation-system"
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


def load_vector_index(path: Path) -> bool:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Missing dependency: torch. Run `pip install -r requirements.txt` first.") from exc

    global VECTOR_PATH, MOVIES, VECTOR_TENSOR

    if not path.exists():
        VECTOR_PATH = path
        MOVIES = []
        VECTOR_TENSOR = None
        print(f"Vector file not found: {path}")
        return False

    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, list):
        raise ValueError("Vector file must be a JSON list of movie records.")

    movies: list[dict[str, Any]] = []
    vectors: list[list[float]] = []
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

    if not vectors:
        VECTOR_PATH = path
        MOVIES = []
        VECTOR_TENSOR = None
        print(f"No usable vectors found in {path}")
        return False

    tensor = torch.tensor(vectors, dtype=torch.float32, device=DEVICE)
    VECTOR_TENSOR = F.normalize(tensor, p=2, dim=1).contiguous()
    VECTOR_PATH = path
    MOVIES = movies
    print(f"Loaded {len(MOVIES):,} movie vectors from {path}")
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


@app.route("/status", methods=["GET"])
def status():
    return jsonify(
        {
            "status": "online",
            "model": MODEL_NAME,
            "device": str(DEVICE),
            "movie_count": len(MOVIES),
            "index_loaded": VECTOR_TENSOR is not None,
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
    inferred_genres, inferred_languages = infer_context_filters(texts)
    playlist_genre_ids.update(inferred_genres)
    preferred_languages.update(inferred_languages)

    # Parse user ratings (1.0-10.0), default to 5 for missing/invalid.
    raw_ratings = data.get("user_vote_counts", [])
    if not isinstance(raw_ratings, list):
        raw_ratings = []
    user_ratings: list[float] = []
    for val in raw_ratings:
        user_ratings.append(clamp_rating(val))
    # Pad to match all taste inputs.
    while len(user_ratings) < max(len(user_genre_ids), len(texts)):
        user_ratings.append(5.0)
    user_release_years = clean_year_list(data.get("user_release_years"), limit=100)

    # Build rating-weighted genre profile
    genre_weights = build_genre_weights(user_genre_ids, user_ratings)

    if not texts:
        return jsonify({"results": fallback_recommendations(top_k, exclude_ids), "fallback": "metadata_cold_start"})

    # Build rating-weighted user embeddings. Low-rated movies are not
    # subtracted as negative vectors; they are used later as a post-ranking
    # penalty against candidates that are too similar to disliked items.
    raw_embeddings = ensure_2d_tensor(embed_texts(texts))  # shape: (n_texts, dim)
    if raw_embeddings.dim() != 2 or raw_embeddings.size(1) != VECTOR_TENSOR.size(1):
        logger.error(
            "Embedding dimension mismatch: embedding=%s index=%s",
            tuple(raw_embeddings.shape),
            tuple(VECTOR_TENSOR.shape),
        )
        return jsonify({"error": "Embedding dimension does not match vector index", "results": []}), 500
    semantic_ratings = user_ratings[:len(texts)]
    positive_indices = [index for index, rating in enumerate(semantic_ratings) if rating >= 5.0]
    negative_indices = [index for index, rating in enumerate(semantic_ratings) if rating < 5.0]
    taste_profile_mode = "metadata_fallback"
    taste_center_count = 0

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
        semantic_scores_tensor = center_scores.max(dim=1).values
        shortlist_scores = semantic_scores_tensor
    else:
        logger.info("Only low-rated taste inputs were provided; using metadata shortlist plus negative penalties.")
        semantic_scores_tensor = torch.zeros(len(MOVIES), dtype=torch.float32, device=DEVICE)
        shortlist_scores = torch.tensor(
            [movie_quality_score(movie) for movie in MOVIES],
            dtype=torch.float32,
            device=DEVICE,
        )

    # First shortlist from the positive taste signal or metadata fallback.
    has_context_filters = bool(playlist_genre_ids or preferred_languages)
    pool_size = min(len(MOVIES), max(top_k * 80, 1000 if has_context_filters else 300))
    _, top_indices_tensor = torch.topk(shortlist_scores, k=pool_size)
    top_indices = top_indices_tensor.detach().cpu().tolist()

    shortlist_semantic_scores = semantic_scores_tensor[top_indices_tensor]
    shortlist_base_scores = shortlist_scores[top_indices_tensor]
    shortlist_penalty = torch.zeros_like(shortlist_base_scores)
    if negative_indices:
        negative_embeddings = ensure_2d_tensor(raw_embeddings[negative_indices])
        shortlist_vectors = VECTOR_TENSOR[top_indices_tensor]
        negative_similarity = torch.mm(shortlist_vectors, negative_embeddings.T)
        dislike_strength = torch.tensor(
            [(5.0 - semantic_ratings[index]) / 4.0 for index in negative_indices],
            dtype=torch.float32,
            device=DEVICE,
        ).clamp(0.0, 1.0)
        penalty_curve = ((negative_similarity - 0.55) / 0.45).clamp(0.0, 1.0)
        shortlist_penalty = (penalty_curve * dislike_strength.unsqueeze(0)).max(dim=1).values

    shortlist_multiplier = 1.0 - (shortlist_penalty * 0.8)
    shortlist_adjusted_scores = shortlist_base_scores * shortlist_multiplier

    semantic_scores = shortlist_semantic_scores.detach().cpu().tolist()
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
        language = clean_language_code(movie.get("original_language"))
        if apply_context_filters and preferred_languages and language and language not in preferred_languages:
            return

        meta_score = score_metadata(movie, genre_weights)
        context_score = score_context_filters(movie, playlist_genre_ids, preferred_languages)
        year_score = score_year_affinity(movie, user_release_years)
        final = float(adjusted_scores[shortlist_position]) + meta_score + context_score + year_score
        candidates.append(
            {
                **movie,
                "semantic_score": round(float(semantic_scores[shortlist_position]), 4),
                "adjusted_semantic_score": round(float(adjusted_scores[shortlist_position]), 4),
                "negative_penalty": round(float(penalties[shortlist_position]), 4),
                "penalty_multiplier": round(float(multipliers[shortlist_position]), 4),
                "metadata_score": round(meta_score, 4),
                "context_score": round(context_score, 4),
                "year_score": round(year_score, 4),
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
                "release_year_count": len(user_release_years),
            },
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
