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

import json
import logging
import os
import sqlite3
import time
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
REMOTE_SEARCH_TOKEN = os.getenv("REMOTE_SEARCH_TOKEN", "")
# Browser-provided BERT URLs are unsafe for a public proxy. Keep the operator's
# configured service locked by default; a private self-host can opt out.
LOCK_REMOTE_SEARCH_URL = os.getenv("LOCK_REMOTE_SEARCH_URL", "true").lower() == "true"
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"

# Cross-reinstall favorites sync. Keyed by a client-computed SHA-256 of the
# user's TMDB key (the raw key is never sent here or stored). Local-first demo
# storage; a single SQLite file is plenty at this scale.
FAVORITES_DB = os.getenv("FAVORITES_DB", str(Path(__file__).resolve().parent / "lumitrace_favorites.db"))
MAX_FAVORITES_BYTES = 512 * 1024

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
                "semantic_search": bool(REMOTE_SEARCH_URL),
                "remote_search_locked": LOCK_REMOTE_SEARCH_URL,
                "semantic_search_auth": bool(REMOTE_SEARCH_TOKEN),
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

    if not payload["overviews"] and not payload["user_movie_ids"]:
        return jsonify({"error": "At least one movie overview or user_movie_ids is required"}), 400

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


def favorites_db() -> sqlite3.Connection:
    conn = sqlite3.connect(FAVORITES_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS favorites ("
        "sync_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at INTEGER NOT NULL)"
    )
    return conn


def valid_sync_id(value: Any) -> bool:
    """A sync id must look like a SHA-256 hex digest (64 lowercase hex chars)."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


@app.route("/api/favorites", methods=["GET", "POST"])
def favorites_sync():
    """Store/retrieve a user's favorites blob keyed by hash(TMDB key).

    The client sends X-Sync-Id = SHA-256(tmdb_key); the raw key never reaches
    this endpoint. The payload is an opaque JSON blob (favorites + ratings).
    """
    sync_id = (request.headers.get("X-Sync-Id") or "").strip().lower()
    if not valid_sync_id(sync_id):
        return jsonify({"error": "A valid X-Sync-Id (sha-256 hex) is required"}), 400

    if request.method == "GET":
        try:
            conn = favorites_db()
            row = conn.execute(
                "SELECT payload, updated_at FROM favorites WHERE sync_id = ?", (sync_id,)
            ).fetchone()
            conn.close()
        except sqlite3.Error as exc:
            logger.warning("favorites read failed: %s", exc)
            return jsonify({"error": "favorites store unavailable"}), 503
        if not row:
            return jsonify({"payload": None})
        try:
            payload = json.loads(row[0])
        except json.JSONDecodeError:
            payload = None
        return jsonify({"payload": payload, "updated_at": row[1]})

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "A JSON object body is required"}), 400
    payload_text = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    if len(payload_text.encode("utf-8")) > MAX_FAVORITES_BYTES:
        return jsonify({"error": "favorites payload too large"}), 413
    now = int(time.time())
    try:
        conn = favorites_db()
        conn.execute(
            "INSERT INTO favorites (sync_id, payload, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(sync_id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
            (sync_id, payload_text, now),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as exc:
        logger.warning("favorites write failed: %s", exc)
        return jsonify({"error": "favorites store unavailable"}), 503
    return jsonify({"ok": True, "updated_at": now})


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


if __name__ == "__main__":
    logger.info("Starting LumiTrace public demo backend...")
    logger.info("TMDB env key configured: %s", bool(TMDB_API_KEY))
    logger.info("Semantic search configured: %s", bool(REMOTE_SEARCH_URL))
    logger.info("RapidAPI streaming configured: %s", bool(RAPID_API_KEY))
    logger.info("SSL verify: %s", SSL_VERIFY)
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
