"""
LumiTrace - Backend Server
All API keys loaded from .env file
"""
import os
import re
import json
import time
import math
import random
import logging
import sqlite3
from collections import Counter

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ==========================================
# Initialization
# ==========================================
load_dotenv()

app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Environment Variables (no more hardcoded keys!)
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '')
RAPID_API_KEY = os.getenv('RAPID_API_KEY', '')
REMOTE_SEARCH_URL = os.getenv('REMOTE_SEARCH_URL', '')
OLLAMA_URL = os.getenv('OLLAMA_URL', '')
SSL_VERIFY = os.getenv('SSL_VERIFY', 'false').lower() == 'true'

if not TMDB_API_KEY:
    logger.warning("TMDB_API_KEY not set in .env!")
if not RAPID_API_KEY:
    logger.warning("RAPID_API_KEY not set in .env!")

# Lazy import requests (to allow startup without it for testing)
import requests
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# Database
# ==========================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dev_v4.db')

def get_db():
    """Get database connection, stored in Flask g object for request lifecycle."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        region TEXT DEFAULT 'TW'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS favorite_movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        movie_id INTEGER,
        title TEXT,
        overview TEXT,
        genres TEXT,
        genre_ids TEXT,
        poster_path TEXT,
        vote_average REAL,
        vote_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, movie_id)
    )''')
    conn.commit()
    conn.close()
    logger.info("Database initialized.")

init_db()

# ==========================================
# BERT Remote Search
# ==========================================
def remote_search(overviews: list, top_k=10, exclude_ids=[], user_genre_ids=[], user_vote_counts=[]):
    """Call GPU Server for Max-Sim semantic search with Genre Constraints."""
    if not REMOTE_SEARCH_URL:
        logger.warning("REMOTE_SEARCH_URL not set; skipping semantic search.")
        return []

    try:
        payload = {
            "overviews": overviews,
            "top_k": top_k,
            "exclude_ids": exclude_ids,
            "user_genre_ids": user_genre_ids,
            "user_vote_counts": user_vote_counts
        }
        logger.info(f"Connecting to BERT Service at {REMOTE_SEARCH_URL}")
        res = requests.post(REMOTE_SEARCH_URL, json=payload, timeout=15, verify=SSL_VERIFY)
        if res.ok:
            return res.json().get("results", [])
        else:
            logger.warning(f"Remote Search Error: {res.status_code}")
    except Exception as e:
        logger.error(f"Remote Search Connection Failed: {e}", exc_info=True)
    return []


# ==========================================
# Frontend Proxy APIs (Security: hide API keys)
# ==========================================

@app.route('/api/tmdb/<path:endpoint>', methods=['GET'])
def tmdb_proxy(endpoint):
    """Proxy TMDB API requests so frontend never sees the API key."""
    try:
        params = dict(request.args)
        params['api_key'] = TMDB_API_KEY
        url = f"https://api.themoviedb.org/3/{endpoint}"
        res = requests.get(url, params=params, timeout=10)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error(f"TMDB Proxy Error: {e}", exc_info=True)
        return jsonify({"error": "TMDB request failed"}), 500


@app.route('/api/streaming/<path:show_id>', methods=['GET'])
def streaming_proxy(show_id):
    """Proxy Streaming Availability API requests."""
    try:
        url = f"https://streaming-availability.p.rapidapi.com/shows/{show_id}"
        headers = {
            'x-rapidapi-key': RAPID_API_KEY,
            'x-rapidapi-host': 'streaming-availability.p.rapidapi.com'
        }
        res = requests.get(url, headers=headers, timeout=10)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error(f"Streaming Proxy Error: {e}", exc_info=True)
        return jsonify({"error": "Streaming API request failed"}), 500


# ==========================================
# Recommendations
# ==========================================
def get_cosine_similarity_vector(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@app.route('/api/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    username = data.get('username')
    db = get_db()

    favorites = db.execute(
        "SELECT movie_id, title, overview, genre_ids, vote_count FROM favorite_movies WHERE username = ?",
        (username,)
    ).fetchall()

    if not favorites:
        return jsonify({"recommendations": [], "message": "請先收藏電影"})

    fav_count = len(favorites)
    if fav_count < 3:
        quality_tier = "初階"
        quality_note = f"💡 目前收藏 {fav_count} 部，建議收藏至少 5 部以獲得更精準的推薦"
    elif fav_count < 5:
        quality_tier = "基本"
        quality_note = f"📈 再收藏 {5 - fav_count} 部即可達到最佳推薦效果"
    else:
        quality_tier = "最佳"
        quality_note = ""

    fav_ids = [f['movie_id'] for f in favorites]
    recent_favs = list(favorites)[-10:]

    overviews = [f['overview'] for f in recent_favs if f['overview']]
    if not overviews:
        overviews = [f['title'] for f in recent_favs]

    user_genre_ids = []
    for f in recent_favs:
        try:
            gids = json.loads(f['genre_ids']) if f['genre_ids'] else []
            user_genre_ids.append(gids)
        except Exception:
            user_genre_ids.append([])

    user_vote_counts = [f['vote_count'] or 0 for f in recent_favs]

    candidates = remote_search(
        overviews,
        top_k=50,
        exclude_ids=fav_ids,
        user_genre_ids=user_genre_ids,
        user_vote_counts=user_vote_counts
    )

    if candidates:
        if len(candidates) > 10:
            try:
                import numpy as np
                weights = [max(c.get('score', 0.5) + 0.1, 0.1) for c in candidates]
                total_weight = sum(weights)
                probabilities = [w / total_weight for w in weights]
                indices = np.random.choice(
                    len(candidates),
                    size=min(10, len(candidates)),
                    replace=False,
                    p=probabilities
                )
                recs = [candidates[i] for i in indices]
            except ImportError:
                logger.warning("numpy not available, using simple random selection")
                recs = random.sample(candidates, min(10, len(candidates)))
        else:
            recs = candidates

        base_msg = f"AI 根據您的 {fav_count} 部收藏，透過 Max-Sim 語意分析推薦"
        if quality_note:
            full_msg = f"{base_msg} ({quality_tier}) | {quality_note}"
        else:
            full_msg = f"{base_msg} (推薦品質：{quality_tier})"

        return jsonify({
            "recommendations": recs,
            "message": full_msg,
            "quality_tier": quality_tier,
            "favorite_count": fav_count
        })

    return jsonify({"recommendations": [], "message": "推薦系統暫時忙碌中"})


# ==========================================
# Auth APIs
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (data['username'],)).fetchone()
    if user and check_password_hash(user['password'], data['password']):
        return jsonify({"username": user['username'], "region": user['region']})
    return jsonify({"message": "帳號或密碼錯誤"}), 401


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    try:
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (data['username'], generate_password_hash(data['password']))
        )
        db.commit()
        return jsonify({"message": "註冊成功"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "帳號已存在"}), 400
    except Exception as e:
        logger.error(f"Register Error: {e}", exc_info=True)
        return jsonify({"message": "註冊失敗"}), 400


# ==========================================
# Favorites APIs
# ==========================================
@app.route('/api/add_favorite', methods=['POST'])
def add_favorite():
    data = request.json
    db = get_db()
    try:
        genre_ids_json = json.dumps(data.get('genre_ids', []))
        db.execute(
            """INSERT INTO favorite_movies
               (username, movie_id, title, overview, poster_path, vote_average, genre_ids, vote_count)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                data['username'],
                data['movie_id'],
                data['title'],
                data.get('overview', ''),
                data.get('poster_path', ''),
                data.get('vote_average', 0),
                genre_ids_json,
                data.get('vote_count', 0)
            )
        )
        db.commit()
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "exists"}), 400
    except Exception as e:
        logger.error(f"Add Favorite Error: {e}", exc_info=True)
        return jsonify({"status": "error"}), 500


@app.route('/api/remove_favorite', methods=['POST'])
def remove_favorite():
    data = request.json
    db = get_db()
    db.execute("DELETE FROM favorite_movies WHERE username = ? AND movie_id = ?",
               (data['username'], data['movie_id']))
    db.commit()
    return jsonify({"status": "ok"})


@app.route('/api/get_favorites', methods=['GET'])
def get_favorites():
    u = request.args.get('username')
    db = get_db()
    favs = db.execute(
        "SELECT * FROM favorite_movies WHERE username = ? ORDER BY created_at DESC", (u,)
    ).fetchall()
    return jsonify([dict(row) for row in favs])


# ==========================================
# Watch Providers Helper
# ==========================================
def get_watch_providers(movie_id):
    """Query watch providers for a movie in Taiwan."""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
        res = requests.get(url, params={"api_key": TMDB_API_KEY}, timeout=5)
        if res.ok:
            data = res.json()
            tw_providers = data.get('results', {}).get('TW', {})
            flatrate = tw_providers.get('flatrate', [])
            if flatrate:
                return ", ".join([p['provider_name'] for p in flatrate])
    except Exception as e:
        logger.warning(f"Watch Provider Error: {e}")
    return "未知"


# ==========================================
# AI Chat Proxy (RAG + Ollama)
# ==========================================
@app.route('/api/agent_query', methods=['POST'])
def chat_proxy():
    data = request.json  # <-- FIXED: was missing this line in the original

    if not OLLAMA_URL:
        return jsonify({"message": {"content": "AI chat service is not configured."}}), 503

    user_message = ""
    if data.get("messages"):
        user_message = data["messages"][-1].get("content", "")

    # RAG: Semantic search for related movies
    rag_context = ""
    semantic_results = remote_search([user_message], top_k=5)

    if semantic_results:
        movie_info_list = []
        for m in semantic_results:
            providers = get_watch_providers(m['id'])
            info = f"- 《{m['title']}》 (評分:{m['vote_average']})\n  簡介: {m['overview'][:100]}...\n  📺 線上觀看: {providers}"
            movie_info_list.append(info)

        movie_info = "\n".join(movie_info_list)
        rag_context = f"""
        【資料庫中有這些相關電影 (Max-Sim Search Result)】(請優先從這裡參考回答)：
        {movie_info}

        👉 請在回答中明確告訴使用者這些電影可以在哪個平台 (Netflix, Disney+ 等) 觀看。如果顯示「未知」，則不用特別提及。
        """
        logger.info(f"RAG hit: found {len(semantic_results)} related movies")

    try:
        messages = data.get("messages", [])
        system_content = f"""你是一位專業電影 AI 助手。

        {rag_context}

        請根據使用者的問題進行回答。如果資料庫中有相關電影，請優先推薦，並說明理由。
        若資料庫中沒有相關資訊，你可以用你原本的知識回答，但請保持禮貌與專業。
        """

        system_prompt = {"role": "system", "content": system_content}
        messages_clean = [m for m in messages if m['role'] != 'system']
        messages_with_system = [system_prompt] + messages_clean

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": data.get("model", "llama3.1:8b"),
                "messages": messages_with_system,
                "stream": False,
                "options": {"temperature": 0.3}
            },
            headers={"Content-Type": "application/json"},
            timeout=60,
            verify=SSL_VERIFY
        )
        return jsonify(response.json())

    except Exception as e:
        logger.error(f"Chat Proxy Error: {e}", exc_info=True)
        return jsonify({"message": {"content": "AI 連線異常，請稍後再試。"}})



# ==========================================
# Static Files & Frontend
# ==========================================
@app.route('/')
def index():
    """Serve the main index.html file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve other static files (js, css, html)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, path)

# ==========================================
# Entry Point
# ==========================================
if __name__ == '__main__':
    logger.info("Starting LumiTrace Backend...")
    logger.info(f"TMDB Key: {'***' + TMDB_API_KEY[-4:] if TMDB_API_KEY else 'NOT SET'}")
    logger.info(f"BERT Service: {REMOTE_SEARCH_URL}")
    logger.info(f"SSL Verify: {SSL_VERIFY}")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
