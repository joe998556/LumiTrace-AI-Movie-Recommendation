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
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "AventIQ-AI/bert-movie-recommendation-system"
DEFAULT_VECTOR_FILES = ("final_boss_vectors.json", "movie_vectors.json")


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
    return {
        "id": int(movie.get("id", 0)),
        "title": movie.get("title") or movie.get("name") or "Untitled",
        "overview": movie.get("overview") or "",
        "poster_path": movie.get("poster_path"),
        "release_date": movie.get("release_date") or "",
        "vote_average": float(movie.get("vote_average") or 0),
        "vote_count": int(movie.get("vote_count") or 0),
        "genre_ids": movie.get("genre_ids") or [],
    }


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
    VECTOR_TENSOR = F.normalize(tensor, p=2, dim=1)
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


def build_genre_weights(user_genre_ids: list[list[int]], user_ratings: list[int]) -> dict[int, float]:
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
        return jsonify({"error": "Vector index is not loaded", "results": []}), 503

    data = request.get_json(silent=True) or {}
    overviews = data.get("overviews")
    if not overviews and data.get("text"):
        overviews = [data.get("text")]
    if not isinstance(overviews, list):
        overviews = []
    texts = [str(text).strip() for text in overviews if str(text).strip()]
    if not texts:
        return jsonify({"error": "overviews or text is required", "results": []}), 400

    top_k = max(1, min(50, int(data.get("top_k") or 10)))
    exclude_ids = {int(value) for value in data.get("exclude_ids", []) if str(value).isdigit()}
    user_genre_ids = data.get("user_genre_ids", [])
    if not isinstance(user_genre_ids, list):
        user_genre_ids = []

    # Parse user ratings (1-10), default to 5 for missing/invalid
    raw_ratings = data.get("user_vote_counts", [])
    if not isinstance(raw_ratings, list):
        raw_ratings = []
    user_ratings: list[int] = []
    for val in raw_ratings:
        try:
            r = int(val)
            user_ratings.append(max(1, min(10, r)))
        except (TypeError, ValueError):
            user_ratings.append(5)
    # Pad to match user_genre_ids length
    while len(user_ratings) < len(user_genre_ids):
        user_ratings.append(5)

    # Build rating-weighted genre profile
    genre_weights = build_genre_weights(user_genre_ids, user_ratings)

    # Build rating-weighted user embeddings
    raw_embeddings = embed_texts(texts)  # shape: (n_texts, dim)

    if len(user_ratings) >= len(texts):
        # Use ratings as weights for semantic embedding
        weights = torch.tensor(
            [max(0.1, r / 5.0) for r in user_ratings[:len(texts)]],
            dtype=torch.float32,
            device=DEVICE,
        )
        # Weighted average of embeddings
        weighted = raw_embeddings * weights.unsqueeze(1)
        user_embedding = F.normalize(weighted.sum(dim=0, keepdim=True), p=2, dim=1)
    else:
        # Fallback: simple average
        user_embedding = F.normalize(raw_embeddings.mean(dim=0, keepdim=True), p=2, dim=1)

    # Semantic scores: cosine similarity
    semantic_scores = torch.mm(VECTOR_TENSOR, user_embedding.T).squeeze(1).detach().cpu().tolist()

    candidates: list[dict[str, Any]] = []
    for movie, sem_score in zip(MOVIES, semantic_scores):
        if movie["id"] in exclude_ids:
            continue
        if not movie.get("poster_path"):
            continue
        if movie.get("vote_count", 0) < 20:
            continue

        meta_score = score_metadata(movie, genre_weights)
        final = float(sem_score) + meta_score
        candidates.append(
            {
                **movie,
                "semantic_score": round(float(sem_score), 4),
                "metadata_score": round(meta_score, 4),
                "score": round(final, 4),
            }
        )

    candidates.sort(key=lambda m: m["score"], reverse=True)
    return jsonify({"results": candidates[:top_k]})


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
