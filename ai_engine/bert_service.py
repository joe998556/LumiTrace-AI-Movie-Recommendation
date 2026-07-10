"""LumiTrace Lite BERT semantic recommendation service.

The public service deliberately has one retrieval path: normalized BERT movie
vectors plus transparent local preference signals.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import os
import re
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = os.getenv("LUMITRACE_MODEL", "BAAI/bge-m3")
DEFAULT_VECTORS = os.getenv("LUMITRACE_VECTOR_FILE", "movie_vectors.json")
DEFAULT_DEVICE = os.getenv("LUMITRACE_DEVICE", "auto")
GATEWAY_TOKEN = ""
ALLOW_PRIVATE_LLM = os.getenv("LUMITRACE_ALLOW_PRIVATE_LLM", "false").lower() == "true"

app = Flask(__name__)
logger = logging.getLogger("lumitrace.bert")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

MODEL: Any = None
TOKENIZER: Any = None
DEVICE: Any = None
MOVIES: list[dict[str, Any]] = []
VECTOR_TENSOR: Any = None
INDEX_BY_ID: dict[int, int] = {}
VECTOR_PATH: Path | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LumiTrace Lite BERT service.")
    parser.add_argument("--host", default=os.getenv("BERT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BERT_PORT", "5001")))
    parser.add_argument("--vectors", default=DEFAULT_VECTORS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=DEFAULT_DEVICE, choices=("auto", "cpu", "cuda"))
    return parser


def require_gateway_token() -> bool:
    if not GATEWAY_TOKEN:
        return True
    supplied = request.headers.get("X-LumiTrace-Gateway", "")
    return supplied == GATEWAY_TOKEN


def protected(handler):
    def wrapped(*args: Any, **kwargs: Any):
        if not require_gateway_token():
            return jsonify({"error": "gateway token required"}), 403
        return handler(*args, **kwargs)

    wrapped.__name__ = handler.__name__
    return wrapped


def resolve_device(name: str):
    import torch

    if name == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available.")
        return torch.device("cuda")
    if name == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model(model_name: str, device: Any) -> None:
    global MODEL, TOKENIZER, DEVICE
    from transformers import AutoModel, AutoTokenizer

    logger.info("Loading embedding model %s on %s", model_name, device)
    TOKENIZER = AutoTokenizer.from_pretrained(model_name)
    MODEL = AutoModel.from_pretrained(model_name).to(device)
    MODEL.eval()
    DEVICE = device


def normalize_rows(tensor: Any) -> Any:
    import torch.nn.functional as functional

    return functional.normalize(tensor, p=2, dim=1)


def embed_texts(texts: list[str]) -> Any:
    """Embed text with mean pooling and return L2-normalized rows."""
    import torch

    cleaned = [text.strip()[:4000] for text in texts if isinstance(text, str) and text.strip()]
    if not cleaned:
        return torch.empty((0, 0), device=DEVICE)

    rows: list[Any] = []
    batch_size = 8 if DEVICE and DEVICE.type == "cuda" else 4
    for start in range(0, len(cleaned), batch_size):
        batch = cleaned[start : start + batch_size]
        tokens = TOKENIZER(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
        tokens = {key: value.to(DEVICE) for key, value in tokens.items()}
        with torch.no_grad():
            outputs = MODEL(**tokens).last_hidden_state
        mask = tokens["attention_mask"].unsqueeze(-1).expand(outputs.size()).float()
        pooled = (outputs * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        rows.append(pooled)
    return normalize_rows(torch.cat(rows, dim=0))


def integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_vector_index(path: Path) -> None:
    """Load a single BERT vector file into one normalized tensor."""
    global MOVIES, VECTOR_TENSOR, INDEX_BY_ID, VECTOR_PATH
    import torch

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if isinstance(raw, dict):
        raw = raw.get("movies") or raw.get("items") or []
    if not isinstance(raw, list):
        raise RuntimeError("Vector file must contain a list of movie records.")

    movies: list[dict[str, Any]] = []
    vectors: list[list[float]] = []
    dimension = 0
    for item in raw:
        if not isinstance(item, dict):
            continue
        vector = item.get("vector") or item.get("embedding") or item.get("bert_vector")
        movie_id = integer(item.get("id"))
        if movie_id is None or not isinstance(vector, list) or not vector:
            continue
        try:
            parsed = [float(value) for value in vector]
        except (TypeError, ValueError):
            continue
        if dimension == 0:
            dimension = len(parsed)
        if len(parsed) != dimension:
            continue
        movies.append(
            {
                "id": movie_id,
                "title": str(item.get("title") or item.get("name") or "Untitled"),
                "overview": str(item.get("overview") or ""),
                "poster_path": item.get("poster_path") or "",
                "release_date": item.get("release_date") or "",
                "vote_average": number(item.get("vote_average")),
                "vote_count": number(item.get("vote_count")),
                "genre_ids": [value for value in (item.get("genre_ids") or []) if integer(value) is not None],
                "original_language": str(item.get("original_language") or "").lower(),
                "collection_id": integer(item.get("collection_id")),
            }
        )
        vectors.append(parsed)

    if not movies:
        raise RuntimeError("No valid BERT vectors were found in the vector file.")

    configured_dimension = integer(getattr(getattr(MODEL, "config", None), "hidden_size", None))
    if configured_dimension and dimension != configured_dimension:
        raise RuntimeError(
            f"Vector dimension {dimension} does not match model dimension {configured_dimension}. "
            "Rebuild the index with tools/bootstrap_recommender.py using the same --model value."
        )

    tensor = torch.tensor(vectors, dtype=torch.float32, device=DEVICE)
    MOVIES = movies
    VECTOR_TENSOR = normalize_rows(tensor).contiguous()
    INDEX_BY_ID = {movie["id"]: index for index, movie in enumerate(MOVIES)}
    VECTOR_PATH = path
    logger.info("Loaded %s movie vectors with %s dimensions", len(MOVIES), dimension)


def clean_ints(values: Any, limit: int = 100) -> list[int]:
    if not isinstance(values, list):
        return []
    result: list[int] = []
    for value in values[:limit]:
        parsed = integer(value)
        if parsed is not None:
            result.append(parsed)
    return result


def clean_nested_ints(values: Any, limit: int = 100) -> list[list[int]]:
    if not isinstance(values, list):
        return []
    return [clean_ints(value, limit=30) for value in values[:limit]]


def clean_ratings(values: Any, target_length: int) -> list[float]:
    raw = values if isinstance(values, list) else []
    result = [max(1.0, min(10.0, number(value, 5.0))) for value in raw[:target_length]]
    return result + [5.0] * max(0, target_length - len(result))


def clean_texts(values: Any, limit: int = 20) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip()[:4000] for value in values[:limit] if isinstance(value, str) and value.strip()]


def clean_languages(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    result: set[str] = set()
    for value in values[:12]:
        code = str(value or "").lower().strip().split("-")[0]
        if len(code) == 2 and code.isalpha():
            result.add(code)
    return result


def weighted_genres(rows: list[list[int]], ratings: list[float]) -> dict[int, float]:
    weights: dict[int, float] = {}
    for genres, rating in zip(rows, ratings):
        if rating <= 5:
            continue
        strength = max(0.2, rating / 5.0)
        for genre in genres:
            weights[genre] = weights.get(genre, 0.0) + strength
    return weights


def profile_vectors(data: dict[str, Any]) -> tuple[Any | None, Any | None, list[dict[str, Any]], list[dict[str, Any]], list[float]]:
    """Return positive and negative taste matrices plus explainable seed records."""
    import torch

    ids = clean_ints(data.get("user_movie_ids"), limit=100)
    ratings = clean_ratings(data.get("user_vote_counts"), len(ids))
    positive_rows: list[Any] = []
    negative_rows: list[Any] = []
    positives: list[dict[str, Any]] = []
    negatives: list[dict[str, Any]] = []
    positive_weights: list[float] = []

    for movie_id, rating in zip(ids, ratings):
        index = INDEX_BY_ID.get(movie_id)
        if index is None:
            continue
        seed = {"title": MOVIES[index]["title"], "rating": rating, "index": index}
        if rating > 5.0:
            positive_rows.append(VECTOR_TENSOR[index])
            positive_weights.append(max(0.1, rating / 5.0))
            positives.append(seed)
        elif rating < 5.0:
            negative_rows.append(VECTOR_TENSOR[index])
            negatives.append(seed)

    texts = clean_texts(data.get("overviews"))
    if texts:
        text_rows = embed_texts(texts)
        if text_rows.numel():
            positive_rows.extend(text_rows)
            positive_weights.extend([1.0] * len(text_rows))
            positives.extend({"title": "your scene prompt", "rating": 5.0, "index": None} for _ in range(len(text_rows)))

    if not positive_rows:
        return None, None, positives, negatives, ratings

    positive_matrix = torch.stack(positive_rows)
    weights = torch.tensor(positive_weights, dtype=torch.float32, device=DEVICE).unsqueeze(1)
    positive_center = normalize_rows((positive_matrix * weights).sum(dim=0, keepdim=True))
    negative_matrix = torch.stack(negative_rows) if negative_rows else None
    return positive_center, negative_matrix, positives, negatives, ratings


def metadata_fallback(excluded: set[int], top_k: int) -> list[dict[str, Any]]:
    ordered = sorted(MOVIES, key=lambda movie: (movie["vote_average"], movie["vote_count"]), reverse=True)
    results: list[dict[str, Any]] = []
    for movie in ordered:
        if movie["id"] in excluded or not movie["poster_path"]:
            continue
        results.append(
            {
                **movie,
                "score": round(movie["vote_average"] / 10, 4),
                "semantic_score": 0.0,
                "negative_penalty": 0.0,
                "evidence": {
                    "kind": "metadata_fallback",
                    "similar_to": [],
                    "matched_genre_ids": [],
                    "rating_weight": None,
                    "avoids_disliked": False,
                    "disliked_titles": [],
                },
            }
        )
        if len(results) >= top_k:
            break
    return results


def diversity_rerank(candidates: list[dict[str, Any]], top_k: int, diversity: float) -> list[dict[str, Any]]:
    """Apply a tiny, deterministic diversity adjustment to an already short list."""
    selected: list[dict[str, Any]] = []
    genre_counts: dict[int, int] = {}
    language_counts: dict[str, int] = {}
    collection_counts: dict[int, int] = {}
    remaining = list(candidates)
    strength = max(0.0, min(1.0, diversity))
    while remaining and len(selected) < top_k:
        best_index = 0
        best_score = float("-inf")
        for index, movie in enumerate(remaining):
            duplicate = sum(genre_counts.get(genre, 0) for genre in movie["genre_ids"])
            language = movie.get("original_language") or ""
            collection = movie.get("collection_id")
            penalty = duplicate * 0.018 * strength
            penalty += max(0, language_counts.get(language, 0) - 1) * 0.012 * strength
            if collection:
                penalty += collection_counts.get(collection, 0) * 0.08 * strength
            score = number(movie.get("score")) - penalty
            if score > best_score:
                best_score = score
                best_index = index
        chosen = remaining.pop(best_index)
        chosen["diversity_penalty"] = round(max(0.0, number(chosen.get("score")) - best_score), 4)
        selected.append(chosen)
        for genre in chosen["genre_ids"]:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        language = chosen.get("original_language") or ""
        language_counts[language] = language_counts.get(language, 0) + 1
        if chosen.get("collection_id"):
            collection = chosen["collection_id"]
            collection_counts[collection] = collection_counts.get(collection, 0) + 1
    return selected


def normalize_llm_url(raw_url: Any) -> str | None:
    value = str(raw_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return None
    if not ALLOW_PRIVATE_LLM and not is_public_host(hostname, parsed.port):
        logger.info("LLM narrator target rejected because it is not a public host")
        return None
    return value if value.endswith("/chat/completions") else f"{value}/chat/completions"


def is_public_host(hostname: str, port: int | None) -> bool:
    """Reject loopback, link-local, and private LLM targets in public mode."""
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return False
    try:
        addresses = {entry[4][0].split("%", 1)[0] for entry in socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        return False
    if not addresses:
        return False
    try:
        return all(ipaddress.ip_address(address).is_global for address in addresses)
    except ValueError:
        return False


def llm_reasons(config: Any, candidates: list[dict[str, Any]]) -> dict[int, str]:
    """Ask a user-provided compatible LLM to narrate existing evidence only."""
    if not isinstance(config, dict) or not candidates:
        return {}
    url = normalize_llm_url(config.get("api_url"))
    model = str(config.get("model") or "").strip()
    if not url or not model:
        return {}
    evidence = []
    for movie in candidates[:10]:
        proof = movie.get("evidence") or {}
        evidence.append(
            {
                "id": movie["id"],
                "title": movie["title"],
                "similar_to": proof.get("similar_to", []),
                "matched_genres": proof.get("matched_genre_ids", []),
                "rating_weight": proof.get("rating_weight"),
                "avoids_disliked": proof.get("avoids_disliked", False),
            }
        )
    prompt = (
        "Write spoiler-free recommendation reasons from the evidence only. "
        "Never invent plot details. Return JSON: {\"reasons\": {\"movie id\": \"short reason\"}}.\n"
        + json.dumps(evidence, ensure_ascii=False)
    )
    headers = {"Content-Type": "application/json"}
    api_key = str(config.get("api_key") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.post(
            url,
            headers=headers,
            json={
                "model": model,
                "temperature": 0.2,
                "max_tokens": 450,
                "messages": [
                    {"role": "system", "content": "You are a concise spoiler-free movie recommender."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=18,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", str(content), re.DOTALL)
        parsed = json.loads(match.group(0) if match else content)
        reasons = parsed.get("reasons", {}) if isinstance(parsed, dict) else {}
        return {int(key): str(value)[:240] for key, value in reasons.items() if integer(key) is not None and isinstance(value, str)}
    except (requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.info("LLM narration unavailable: %s", type(exc).__name__)
        return {}


def recommend(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import torch

    top_k = max(1, min(30, integer(data.get("top_k")) or 12))
    excluded = set(clean_ints(data.get("exclude_ids"), limit=250))
    preferred_languages = clean_languages(data.get("preferred_languages"))
    playlist_genres = set(clean_ints(data.get("playlist_genre_ids"), limit=20))
    genres = clean_nested_ints(data.get("user_genre_ids"), limit=100)
    diversity = max(0.0, min(1.0, number(data.get("diversity"), 0.55)))
    positive_center, negative_matrix, positives, negatives, ratings = profile_vectors(data)
    if positive_center is None:
        return metadata_fallback(excluded, top_k), {"mode": "metadata_fallback", "seed_count": 0}

    semantic_scores = torch.mm(VECTOR_TENSOR, positive_center.T).squeeze(1)
    negative_penalty = torch.zeros(len(MOVIES), device=DEVICE)
    if negative_matrix is not None:
        negative_similarity = torch.mm(VECTOR_TENSOR, negative_matrix.T)
        negative_penalty = ((negative_similarity.max(dim=1).values - 0.52) / 0.48).clamp(0.0, 1.0)

    genre_weights = weighted_genres(genres, ratings)
    pool_size = min(len(MOVIES), max(180, top_k * 24))
    _, positions = torch.topk(semantic_scores, k=pool_size)
    seed_matrix = torch.stack([VECTOR_TENSOR[item["index"]] for item in positives if item["index"] is not None]) if any(item["index"] is not None for item in positives) else None

    candidates: list[dict[str, Any]] = []
    for position in positions.detach().cpu().tolist():
        movie = MOVIES[position]
        if movie["id"] in excluded or not movie["poster_path"]:
            continue
        movie_genres = movie["genre_ids"]
        if playlist_genres and not playlist_genres.intersection(movie_genres):
            continue
        language_bonus = 0.018 if preferred_languages and movie["original_language"] in preferred_languages else 0.0
        genre_bonus = min(0.05, sum(genre_weights.get(genre, 0.0) for genre in movie_genres) * 0.008)
        penalty = float(negative_penalty[position].item())
        semantic = float(semantic_scores[position].item())
        score = semantic * (1 - penalty * 0.75) + language_bonus + genre_bonus
        similar_to: list[str] = []
        if seed_matrix is not None:
            seed_scores = torch.mm(VECTOR_TENSOR[position : position + 1], seed_matrix.T).squeeze(0)
            top_seed_count = min(2, len(seed_scores))
            for seed_position in torch.topk(seed_scores, k=top_seed_count).indices.detach().cpu().tolist():
                similar_to.append(positives[seed_position]["title"])
        matched_genres = [genre for genre in movie_genres if genre_weights.get(genre, 0.0) > 0]
        candidates.append(
            {
                **movie,
                "score": round(score, 4),
                "semantic_score": round(semantic, 4),
                "negative_penalty": round(penalty, 4),
                "evidence": {
                    "kind": "semantic",
                    "similar_to": similar_to,
                    "matched_genre_ids": matched_genres,
                    "rating_weight": round(max((item["rating"] for item in positives), default=5.0), 1),
                    "avoids_disliked": penalty >= 0.08,
                    "disliked_titles": [item["title"] for item in negatives[:2]],
                },
            }
        )
    if not candidates:
        candidates = metadata_fallback(excluded, top_k)
    candidates.sort(key=lambda movie: number(movie.get("score")), reverse=True)
    results = diversity_rerank(candidates, top_k, diversity)
    reasons = llm_reasons(data.get("llm"), results)
    for movie in results:
        if movie["id"] in reasons:
            movie["llm_reason"] = reasons[movie["id"]]
    return results, {
        "mode": "semantic",
        "seed_count": len(positives),
        "negative_seed_count": len(negatives),
        "diversity": round(diversity, 2),
    }


@app.get("/status")
def status():
    return jsonify(
        {
            "status": "online" if VECTOR_TENSOR is not None else "starting",
            "model": DEFAULT_MODEL,
            "device": str(DEVICE) if DEVICE is not None else "unknown",
            "movie_count": len(MOVIES),
            "vector_file": str(VECTOR_PATH) if VECTOR_PATH else None,
            "index_loaded": VECTOR_TENSOR is not None,
            "engine": "lite_bert",
        }
    )


@app.post("/embed")
@protected
def embed():
    data = request.get_json(silent=True) or {}
    texts = clean_texts(data.get("texts"), limit=20)
    if not texts:
        return jsonify({"error": "texts is required"}), 400
    vectors = embed_texts(texts).detach().cpu().tolist()
    return jsonify({"vectors": vectors})


@app.post("/search")
@protected
def search():
    if VECTOR_TENSOR is None:
        return jsonify({"error": "vector index is not loaded"}), 503
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    if not clean_texts(data.get("overviews")) and not clean_ints(data.get("user_movie_ids")):
        return jsonify({"error": "provide overviews or user_movie_ids"}), 400
    results, profile = recommend(data)
    return jsonify({"results": results, "taste_profile": profile, "llm": {"enabled": bool(data.get("llm"))}})


@app.post("/reload")
@protected
def reload_index():
    if VECTOR_PATH is None:
        return jsonify({"error": "no vector path configured"}), 503
    load_vector_index(VECTOR_PATH)
    return jsonify({"ok": True, "movie_count": len(MOVIES)})


def main() -> int:
    global ALLOW_PRIVATE_LLM, GATEWAY_TOKEN, DEFAULT_MODEL
    load_dotenv(ROOT / ".env")
    args = build_parser().parse_args()
    GATEWAY_TOKEN = os.getenv("BERT_GATEWAY_TOKEN", "")
    ALLOW_PRIVATE_LLM = os.getenv("LUMITRACE_ALLOW_PRIVATE_LLM", "false").lower() == "true"
    DEFAULT_MODEL = args.model
    device = resolve_device(args.device)
    load_model(args.model, device)
    vector_path = Path(args.vectors)
    if not vector_path.is_absolute():
        vector_path = ROOT / vector_path
    load_vector_index(vector_path)
    logger.info("Starting Lite BERT service on http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
