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
RAPID_API_KEY = os.getenv("RAPID_API_KEY", "")
REMOTE_SEARCH_URL = os.getenv("REMOTE_SEARCH_URL", "")
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


def clean_text_list(values: Any, limit: int = 20, max_len: int = 2000) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values[:limit]:
        if isinstance(value, str) and value.strip():
            cleaned.append(value.strip()[:max_len])
    return cleaned


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


@app.route("/api/semantic-recommendations", methods=["POST"])
def semantic_recommendations():
    """Forward a sanitized recommendation request to the optional BERT service."""
    if not REMOTE_SEARCH_URL:
        return jsonify({"error": "Semantic recommendation service is not configured"}), 503

    data = request.get_json(silent=True) or {}
    payload = {
        "overviews": clean_text_list(data.get("overviews")),
        "exclude_ids": clean_int_list(data.get("exclude_ids"), limit=100),
        "user_genre_ids": clean_nested_int_list(data.get("user_genre_ids"), limit=100),
        "user_vote_counts": clean_int_list(data.get("user_vote_counts"), limit=100),
        "top_k": clamp_int(data.get("top_k"), default=18, low=1, high=30),
    }

    if not payload["overviews"]:
        return jsonify({"error": "At least one movie overview is required"}), 400

    try:
        response = requests.post(
            REMOTE_SEARCH_URL,
            json=payload,
            timeout=30,
            verify=SSL_VERIFY,
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        logger.warning("Semantic recommendation request failed: %s", exc)
        return jsonify({"error": "Semantic recommendation service request failed"}), 502


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
