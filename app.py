"""LumiTrace public demo backend.

The clone-and-run path stays intentionally small:

- serve the static web app
- proxy TMDB requests using a user-provided API key header or .env fallback
- optionally proxy the local/remote semantic recommender service
- optionally proxy Streaming Availability when RAPID_API_KEY is configured
- expose a public-safe health endpoint

Favorites and public-demo recommendations are stored in the browser via
localStorage. Generated vector indexes stay local and are ignored by Git.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


load_dotenv()

ROOT = Path(__file__).resolve().parent


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
RAPID_API_KEY = os.getenv("RAPID_API_KEY", "")
REMOTE_SEARCH_URL = os.getenv("REMOTE_SEARCH_URL", "")
REMOTE_SEARCH_TOKEN = os.getenv("REMOTE_SEARCH_TOKEN", "")
# Browser-provided BERT URLs are unsafe for a public proxy. Keep the operator's
# configured service locked by default; a private self-host can opt out.
LOCK_REMOTE_SEARCH_URL = os.getenv("LOCK_REMOTE_SEARCH_URL", "true").lower() == "true"
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"
LOCAL_VECTOR_FILE = os.getenv("LUMITRACE_VECTOR_FILE", "").strip()
if not LOCAL_VECTOR_FILE:
    if (ROOT / "movie_index").exists():
        LOCAL_VECTOR_FILE = "movie_index"
    elif (ROOT / "movie_vectors.json").exists():
        LOCAL_VECTOR_FILE = "movie_vectors.json"
    elif (ROOT / "demo_index").exists():
        LOCAL_VECTOR_FILE = "demo_index"
if LOCAL_VECTOR_FILE:
    configured_index = Path(LOCAL_VECTOR_FILE)
    if not configured_index.is_absolute():
        configured_index = ROOT / configured_index
    if not configured_index.exists() or (configured_index.is_dir() and not (configured_index / "manifest.json").exists()):
        LOCAL_VECTOR_FILE = ""
LOCAL_DEVICE = os.getenv("LUMITRACE_DEVICE", "auto")
LOCAL_TEXT_SEARCH = os.getenv("LUMITRACE_TEXT_SEARCH", "auto").lower()
LOCAL_MODEL = os.getenv("LUMITRACE_MODEL", "")
PRELOAD_LOCAL_INDEX = os.getenv("LUMITRACE_PRELOAD_INDEX", "false").lower() == "true"
PREFER_LOCAL_INDEX = os.getenv("LUMITRACE_PREFER_LOCAL_INDEX", "false").lower() == "true"
ALLOW_CLIENT_LLM = os.getenv("LUMITRACE_ALLOW_CLIENT_LLM", "false").lower() == "true"
ALLOWED_ORIGINS = [
    value.strip()
    for value in os.getenv("LUMITRACE_ALLOWED_ORIGINS", "").split(",")
    if value.strip()
]
TRUST_PROXY_HEADERS = os.getenv("LUMITRACE_TRUST_PROXY_HEADERS", "false").lower() == "true"
RECOMMEND_RATE_LIMIT = max(0, env_int("LUMITRACE_RECOMMEND_PER_MINUTE", 30))
TMDB_RATE_LIMIT = max(0, env_int("LUMITRACE_TMDB_PER_MINUTE", 120))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
if ALLOWED_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})

RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}
RATE_LOCK = threading.Lock()
LOCAL_ENGINE_LOCK = threading.Lock()
LOCAL_ENGINE: Any = None
LOCAL_ENGINE_ERROR = ""

if not SSL_VERIFY:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def client_address() -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", "").split(",", 1)[0]
        if forwarded.strip():
            return forwarded.strip()[:64]
    return str(request.remote_addr or "unknown")[:64]


def enforce_rate_limit(scope: str, limit: int):
    if limit <= 0:
        return None
    now = time.monotonic()
    key = (scope, client_address())
    with RATE_LOCK:
        recent = [timestamp for timestamp in RATE_BUCKETS.get(key, []) if now - timestamp < 60.0]
        if len(recent) >= limit:
            retry_after = max(1, int(60 - (now - recent[0])))
            response = jsonify({"error": "rate limit exceeded", "retry_after": retry_after})
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            RATE_BUCKETS[key] = recent
            return response
        recent.append(now)
        RATE_BUCKETS[key] = recent
        if len(RATE_BUCKETS) > 10000:
            stale = [bucket_key for bucket_key, values in RATE_BUCKETS.items() if not values or now - values[-1] >= 60.0]
            for bucket_key in stale:
                RATE_BUCKETS.pop(bucket_key, None)
    return None


def get_local_engine():
    """Lazy-load the in-process vector engine for a one-container deployment."""
    global LOCAL_ENGINE, LOCAL_ENGINE_ERROR
    if LOCAL_ENGINE is not None:
        return LOCAL_ENGINE
    if not LOCAL_VECTOR_FILE:
        return None
    with LOCAL_ENGINE_LOCK:
        if LOCAL_ENGINE is not None:
            return LOCAL_ENGINE
        try:
            from ai_engine import bert_service

            bert_service.initialize(
                LOCAL_VECTOR_FILE,
                device_name=LOCAL_DEVICE,
                model_name=LOCAL_MODEL,
                text_search=LOCAL_TEXT_SEARCH,
            )
            LOCAL_ENGINE = bert_service
            LOCAL_ENGINE_ERROR = ""
        except (OSError, RuntimeError, ValueError) as exc:
            LOCAL_ENGINE_ERROR = str(exc)[:240]
            logger.error("Local recommendation index failed to initialize: %s", exc)
            return None
    return LOCAL_ENGINE


@app.after_request
def public_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.errorhandler(413)
def payload_too_large(_error):
    return jsonify({"error": "request body too large"}), 413


def get_tmdb_key() -> str:
    """Resolve a TMDB key without exposing it in logs or responses."""
    return (
        request.headers.get("X-TMDB-API-Key")
        or TMDB_API_KEY
    )


def clamp_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def clamp_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def clean_int_list(values: Any, limit: int = 50) -> list[int]:
    if not isinstance(values, list):
        return []
    cleaned: list[int] = []
    for value in values[:limit]:
        try:
            cleaned.append(int(value))
        except (TypeError, ValueError):
            continue
    return cleaned


def clean_nested_int_list(values: Any, limit: int = 50) -> list[list[int]]:
    if not isinstance(values, list):
        return []
    return [clean_int_list(item, limit=20) for item in values[:limit]]


def clean_items(values: Any, limit: int = 100) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for value in values[:limit]:
        if not isinstance(value, dict):
            continue
        try:
            movie_id = int(value.get("tmdb_id", value.get("id")))
        except (TypeError, ValueError):
            continue
        if movie_id <= 0 or movie_id in seen:
            continue
        seen.add(movie_id)
        result.append(
            {
                "tmdb_id": movie_id,
                "rating": clamp_float(value.get("rating"), default=5.0, low=1.0, high=10.0),
                "genre_ids": clean_int_list(value.get("genre_ids"), limit=20),
            }
        )
    return result


def clean_float_list(values: Any, limit: int = 50) -> list[float]:
    if not isinstance(values, list):
        return []
    cleaned: list[float] = []
    for value in values[:limit]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        cleaned.append(max(1.0, min(10.0, number)))
    return cleaned


def clean_year_list(values: Any, limit: int = 100) -> list[int]:
    if not isinstance(values, list):
        return []
    cleaned: list[int] = []
    for value in values[:limit]:
        try:
            year = int(str(value)[:4])
        except (TypeError, ValueError):
            continue
        if 1888 <= year <= 2100:
            cleaned.append(year)
    return cleaned


def clean_language_list(values: Any, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values[:limit]:
        code = str(value or "").strip().lower().split("-")[0]
        if len(code) == 2 and code.isalpha() and code not in cleaned:
            cleaned.append(code)
    return cleaned


def clean_text_list(values: Any, limit: int = 20, max_len: int = 2000) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values[:limit]:
        if isinstance(value, str) and value.strip():
            cleaned.append(value.strip()[:max_len])
    return cleaned


def clean_llm_config(data: Any) -> dict[str, str] | None:
    """Extract a user-provided, bring-your-own LLM narrator config.

    The browser stores its own OpenAI-compatible endpoint/key/model so the
    open-source clone never ships a baked-in LLM. We only forward it when an
    api_url is present; the BERT service ignores it otherwise.
    """
    if not ALLOW_CLIENT_LLM or not isinstance(data, dict):
        return None
    config = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    api_url = str(config.get("api_url") or "").strip()
    if not api_url.lower().startswith(("http://", "https://")):
        return None
    cleaned = {
        "api_url": api_url[:300],
        "api_key": str(config.get("api_key") or "").strip()[:400],
        "model": str(config.get("model") or "").strip()[:120],
    }
    return cleaned


def resolve_search_target(data: Any) -> str:
    """Pick the BERT search target: a validated browser override or the .env value.

    LOCK_REMOTE_SEARCH_URL defaults to true. A private self-host may opt out,
    but public deployments should never proxy browser-selected addresses.
    """
    if LOCK_REMOTE_SEARCH_URL:
        return REMOTE_SEARCH_URL
    override = ""
    if isinstance(data, dict):
        override = str(data.get("remote_search_url") or "").strip()
    if override.lower().startswith(("http://", "https://")):
        return override[:400]
    return REMOTE_SEARCH_URL


@app.route("/api/health")
def health_check():
    """Return public-safe backend readiness information."""
    return jsonify(
        {
            "status": "ok",
            "service": "LumiTrace public demo backend",
            "mode": "public-demo",
            "integrations": {
                "tmdb_env_key": bool(TMDB_API_KEY),
                "tmdb_user_key_header": bool(request.headers.get("X-TMDB-API-Key")),
                "omdb_key": bool(OMDB_API_KEY),
                "semantic_search": bool(REMOTE_SEARCH_URL or LOCAL_VECTOR_FILE),
                "semantic_mode": (
                    "local-index"
                    if LOCAL_VECTOR_FILE and (PREFER_LOCAL_INDEX or not REMOTE_SEARCH_URL)
                    else ("remote" if REMOTE_SEARCH_URL else "metadata-only")
                ),
                "local_index_loaded": LOCAL_ENGINE is not None,
                "local_index_error": bool(LOCAL_ENGINE_ERROR),
                "text_search": LOCAL_TEXT_SEARCH if LOCAL_VECTOR_FILE else "unavailable",
                "client_llm": ALLOW_CLIENT_LLM,
                "remote_search_locked": LOCK_REMOTE_SEARCH_URL,
                "semantic_search_auth": bool(REMOTE_SEARCH_TOKEN),
                "rapidapi_streaming": bool(RAPID_API_KEY),
            },
        }
    )


@app.route("/api/tmdb/<path:endpoint>", methods=["GET"])
def tmdb_proxy(endpoint):
    """Proxy TMDB requests with a user-provided key or .env fallback."""
    limited = enforce_rate_limit("tmdb", TMDB_RATE_LIMIT)
    if limited:
        return limited
    tmdb_key = get_tmdb_key()
    if not tmdb_key:
        return jsonify({"error": "TMDB API key is required"}), 400

    params = dict(request.args)
    params["api_key"] = tmdb_key

    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/{endpoint}",
            params=params,
            timeout=10,
            verify=SSL_VERIFY,
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        logger.warning("TMDB proxy request failed: %s", exc)
        return jsonify({"error": "TMDB request failed"}), 502


@app.route("/api/omdb/<path:imdb_id>", methods=["GET"])
def omdb_proxy(imdb_id):
    """Proxy OMDB requests to fetch IMDB ratings."""
    if not OMDB_API_KEY:
        return jsonify({"error": "OMDB_API_KEY is not configured"}), 503

    try:
        response = requests.get(
            "http://www.omdbapi.com/",
            params={"i": imdb_id, "apikey": OMDB_API_KEY},
            timeout=8,
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        logger.warning("OMDB proxy request failed: %s", exc)
        return jsonify({"error": "OMDB request failed"}), 502


@app.route("/api/recommendations", methods=["POST"])
@app.route("/api/semantic-recommendations", methods=["POST"])
def semantic_recommendations():
    """Run or forward a sanitized recommendation request."""
    limited = enforce_rate_limit("recommend", RECOMMEND_RATE_LIMIT)
    if limited:
        return limited
    data = request.get_json(silent=True) or {}

    payload = {
        "items": clean_items(data.get("items"), limit=100),
        "overviews": clean_text_list(data.get("overviews")),
        "exclude_ids": clean_int_list(data.get("exclude_ids"), limit=100),
        # Watched IDs align browser taste records with the local BERT index.
        "user_movie_ids": clean_int_list(data.get("user_movie_ids"), limit=200),
        "user_genre_ids": clean_nested_int_list(data.get("user_genre_ids"), limit=100),
        "user_vote_counts": clean_float_list(data.get("user_vote_counts"), limit=100),
        "user_release_years": clean_year_list(data.get("user_release_years"), limit=100),
        "playlist_genre_ids": clean_int_list(data.get("playlist_genre_ids"), limit=24),
        "preferred_languages": clean_language_list(data.get("preferred_languages"), limit=12),
        "diversity": clamp_float(data.get("diversity"), default=0.55, low=0.0, high=1.0),
        "top_k": clamp_int(data.get("top_k"), default=18, low=1, high=30),
    }

    # Optional bring-your-own LLM narrator config from the browser Settings page.
    llm_config = clean_llm_config(data)
    if llm_config:
        payload["llm"] = llm_config

    if not payload["overviews"] and not payload["user_movie_ids"] and not payload["items"]:
        return jsonify({"error": "At least one rated movie item, user_movie_ids, or overview is required"}), 400

    # A one-container demo can use its local index directly. Existing remote
    # gateways remain supported, with an explicit preference switch when both
    # are configured.
    search_target = resolve_search_target(data)
    use_local_engine = bool(LOCAL_VECTOR_FILE) and (PREFER_LOCAL_INDEX or not search_target)
    if use_local_engine:
        engine = get_local_engine()
        if engine is None:
            fallback = "semantic service is not configured"
            if LOCAL_VECTOR_FILE and LOCAL_ENGINE_ERROR:
                fallback = "local recommendation index could not be loaded"
            if not search_target:
                return jsonify({"results": [], "fallback": fallback})
            logger.info("%s; falling back to the configured remote service.", fallback)
        else:
            if payload["overviews"] and LOCAL_TEXT_SEARCH == "disabled" and not payload["items"] and not payload["user_movie_ids"]:
                return jsonify({"error": "free-text search is disabled; rate at least one movie"}), 409
            try:
                results, profile = engine.recommend(payload)
            except engine.TextSearchDisabled as exc:
                return jsonify({"error": str(exc)}), 409
            return jsonify(
                {
                    "results": results,
                    "taste_profile": profile,
                    "llm": {"enabled": bool(payload.get("llm"))},
                }
            )
    if not search_target:
        return jsonify({"results": [], "fallback": "semantic service is not configured"})

    try:
        request_options: dict[str, Any] = {}
        if REMOTE_SEARCH_TOKEN:
            request_options["headers"] = {"X-LumiTrace-Gateway": REMOTE_SEARCH_TOKEN}
        response = requests.post(search_target, json=payload, timeout=30, verify=SSL_VERIFY, **request_options)
        if not response.ok:
            logger.info("Semantic recommendation service returned %s; using metadata fallback.", response.status_code)
            return jsonify({"results": [], "fallback": "semantic service returned an error"})
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        logger.info("Semantic recommendation service unavailable; using metadata fallback: %s", exc)
        return jsonify({"results": [], "fallback": "semantic service unavailable"})


@app.route("/api/streaming/<path:show_id>", methods=["GET"])
def streaming_proxy(show_id):
    """Optional proxy for Streaming Availability API."""
    if not RAPID_API_KEY:
        return jsonify({"error": "RAPID_API_KEY is not configured"}), 503

    try:
        response = requests.get(
            f"https://streaming-availability.p.rapidapi.com/shows/{show_id}",
            headers={
                "x-rapidapi-key": RAPID_API_KEY,
                "x-rapidapi-host": "streaming-availability.p.rapidapi.com",
            },
            timeout=10,
            verify=SSL_VERIFY,
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        logger.warning("Streaming proxy request failed: %s", exc)
        return jsonify({"error": "Streaming API request failed"}), 502


@app.route("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    # Never serve secrets, the favorites DB, server source, or dotfiles.
    lowered = path.lower()
    base = os.path.basename(lowered)
    if base.startswith(".") or lowered.endswith((".db", ".sqlite", ".sqlite3", ".py", ".env")):
        return jsonify({"error": "not found"}), 404
    return send_from_directory(ROOT, path)


if PRELOAD_LOCAL_INDEX and LOCAL_VECTOR_FILE and (PREFER_LOCAL_INDEX or not REMOTE_SEARCH_URL):
    get_local_engine()


if __name__ == "__main__":
    logger.info("Starting LumiTrace public demo backend...")
    logger.info("TMDB env key configured: %s", bool(TMDB_API_KEY))
    logger.info("Semantic search configured: %s", bool(REMOTE_SEARCH_URL))
    logger.info("Local vector index configured: %s", bool(LOCAL_VECTOR_FILE))
    logger.info("RapidAPI streaming configured: %s", bool(RAPID_API_KEY))
    logger.info("SSL verify: %s", SSL_VERIFY)
    app.run(
        host=os.getenv("LUMITRACE_HOST", "0.0.0.0"),
        port=env_int("PORT", env_int("LUMITRACE_PORT", 8080)),
        debug=False,
        use_reloader=False,
    )
