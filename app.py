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
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


load_dotenv()

ROOT = Path(__file__).resolve().parent
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
RAPID_API_KEY = os.getenv("RAPID_API_KEY", "")
REMOTE_SEARCH_URL = os.getenv("REMOTE_SEARCH_URL", "")
# When true, ignore any browser-provided BERT URL override and force the .env
# REMOTE_SEARCH_URL. Leave false for self-hosting (the open-source default lets
# users point at their own BERT service from the Settings page); set true for
# any public/multi-tenant deployment to avoid server-side request forgery.
LOCK_REMOTE_SEARCH_URL = os.getenv("LOCK_REMOTE_SEARCH_URL", "false").lower() == "true"
SSL_VERIFY = os.getenv("SSL_VERIFY", "false").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

if not SSL_VERIFY:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_tmdb_key() -> str:
    """Resolve a TMDB key without exposing it in logs or responses."""
    return (
        request.headers.get("X-TMDB-API-Key")
        or request.args.get("tmdb_api_key")
        or TMDB_API_KEY
    )


def clamp_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
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
    if not isinstance(data, dict):
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

    The override is opt-in for self-hosting; LOCK_REMOTE_SEARCH_URL forces the
    .env value so a public deployment cannot be coerced into forwarding requests
    to arbitrary hosts.
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
                "semantic_search": bool(REMOTE_SEARCH_URL),
                "rapidapi_streaming": bool(RAPID_API_KEY),
            },
        }
    )


@app.route("/api/tmdb/<path:endpoint>", methods=["GET"])
def tmdb_proxy(endpoint):
    """Proxy TMDB requests with a user-provided key or .env fallback."""
    tmdb_key = get_tmdb_key()
    if not tmdb_key:
        return jsonify({"error": "TMDB API key is required"}), 400

    params = dict(request.args)
    params.pop("tmdb_api_key", None)
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


@app.route("/api/semantic-recommendations", methods=["POST"])
def semantic_recommendations():
    """Forward a sanitized recommendation request to the optional BERT service."""
    data = request.get_json(silent=True) or {}

    # Target can come from the browser Settings page (self-host) or fall back to
    # the operator's .env. The override field is never forwarded to the service.
    search_target = resolve_search_target(data)
    if not search_target:
        return jsonify({"results": [], "fallback": "semantic service is not configured"})

    payload = {
        "overviews": clean_text_list(data.get("overviews")),
        "exclude_ids": clean_int_list(data.get("exclude_ids"), limit=100),
        # Watched TMDB ids align the browser-local favorites with the optional
        # BERT service's MovieLens SVD/Genome item-vector taste centers.
        "user_movie_ids": clean_int_list(data.get("user_movie_ids"), limit=200),
        "user_genre_ids": clean_nested_int_list(data.get("user_genre_ids"), limit=100),
        "user_vote_counts": clean_float_list(data.get("user_vote_counts"), limit=100),
        "user_release_years": clean_year_list(data.get("user_release_years"), limit=100),
        "playlist_genre_ids": clean_int_list(data.get("playlist_genre_ids"), limit=24),
        "preferred_languages": clean_language_list(data.get("preferred_languages"), limit=12),
        "top_k": clamp_int(data.get("top_k"), default=18, low=1, high=30),
    }

    # Optional bring-your-own LLM narrator config from the browser Settings page.
    llm_config = clean_llm_config(data)
    if llm_config:
        payload["llm"] = llm_config

    if not payload["overviews"] and not payload["user_movie_ids"]:
        return jsonify({"error": "At least one movie overview or user_movie_ids is required"}), 400

    try:
        response = requests.post(
            search_target,
            json=payload,
            timeout=30,
            verify=SSL_VERIFY,
        )
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
    return send_from_directory(ROOT, path)


if __name__ == "__main__":
    logger.info("Starting LumiTrace public demo backend...")
    logger.info("TMDB env key configured: %s", bool(TMDB_API_KEY))
    logger.info("Semantic search configured: %s", bool(REMOTE_SEARCH_URL))
    logger.info("RapidAPI streaming configured: %s", bool(RAPID_API_KEY))
    logger.info("SSL verify: %s", SSL_VERIFY)
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
