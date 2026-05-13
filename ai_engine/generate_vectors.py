"""
🔥 ULTIMATE MOVIE VECTOR GENERATOR 🔥
抓取最大量的電影資料，包含各種類型、年份、語言

預計執行時間：2-4 小時
預計電影數量：30,000+ 部
"""

import json
import os
import torch
import requests
import time
from transformers import AutoTokenizer, AutoModel
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 設定
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is not set. Add it to .env or your shell environment.")
MODEL_NAME = "AventIQ-AI/bert-movie-recommendation-system"
OUTPUT_FILE = "movie_vectors.json"

# 初始化模型
print(f"正在載入模型 {MODEL_NAME} ...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用裝置: {device}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(device)
model.eval()

def get_emb(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        return model(**inputs).last_hidden_state.mean(dim=1).squeeze().tolist()

# 主流程
vector_database = []
seen_ids = set()
start_time = datetime.now()

def log_progress():
    elapsed = (datetime.now() - start_time).seconds
    rate = len(vector_database) / max(elapsed, 1) * 3600
    print(f"   📊 總數: {len(vector_database):,} | 已運行: {elapsed//60}分{elapsed%60}秒 | 速率: {rate:.0f}/小時")

def fetch_movies(endpoint, max_pages, desc=""):
    """抓取電影列表 API"""
    global vector_database
    print(f"\n📥 {desc or endpoint} ({max_pages} 頁)...")
    
    for page in range(1, max_pages + 1):
        try:
            url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={TMDB_API_KEY}&language=zh-TW&page={page}"
            res = requests.get(url, timeout=10)
            if not res.ok: continue
            process_movies(res.json().get('results', []))
            
            if page % 20 == 0:
                log_progress()
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

def fetch_discover(params, max_pages, desc=""):
    """使用 Discover API 進行進階搜尋"""
    global vector_database
    print(f"\n🔍 {desc} ({max_pages} 頁)...")
    
    for page in range(1, max_pages + 1):
        try:
            base = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&language=zh-TW&page={page}"
            url = base + "&" + "&".join(f"{k}={v}" for k, v in params.items())
            res = requests.get(url, timeout=10)
            if not res.ok: continue
            process_movies(res.json().get('results', []))
            
            if page % 20 == 0:
                log_progress()
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

def process_movies(movies):
    """處理電影列表"""
    global vector_database, seen_ids
    for m in movies:
        mid = m['id']
        if mid in seen_ids: continue
        
        title = m.get('title', '')
        overview = m.get('overview', '')
        if not overview or len(overview) < 10: continue
        
        seen_ids.add(mid)
        content = f"電影: {title}\n簡介: {overview}\n評分: {m.get('vote_average')}"
        vector = get_emb(content)
        
        vector_database.append({
            "id": mid,
            "title": title,
            "overview": overview,
            "poster_path": m.get('poster_path'),
            "vote_average": m.get('vote_average'),
            "vote_count": m.get('vote_count', 0),
            "genre_ids": m.get('genre_ids', []),
            "vector": vector
        })

print("=" * 70)
print("🔥 ULTIMATE MOVIE VECTOR GENERATOR - 終極電影向量生成器 🔥")
print("=" * 70)
print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================
# 1. 基礎電影 (熱門 & 高分)
# ============================================
fetch_movies("popular", 500, "🌟 熱門電影")
fetch_movies("top_rated", 200, "⭐ 高分電影")
fetch_movies("now_playing", 20, "🎬 現正上映")
fetch_movies("upcoming", 20, "📅 即將上映")

# ============================================
# 2. 按類型抓取 (使用 Discover API)
# ============================================
# TMDB Genre IDs:
# 28=Action, 12=Adventure, 16=Animation, 35=Comedy, 80=Crime,
# 99=Documentary, 18=Drama, 10751=Family, 14=Fantasy, 36=History,
# 27=Horror, 10402=Music, 9648=Mystery, 10749=Romance, 878=Sci-Fi,
# 10770=TV Movie, 53=Thriller, 10752=War, 37=Western

genres = [
    (18, "Drama", 300),           # 劇情片 - 最重要！藝術電影在這
    (10749, "Romance", 200),      # 愛情片
    (28, "Action", 200),          # 動作片 - Marvel 在這
    (878, "Sci-Fi", 150),         # 科幻片
    (12, "Adventure", 150),       # 冒險片
    (35, "Comedy", 200),          # 喜劇
    (16, "Animation", 150),       # 動畫
    (27, "Horror", 100),          # 恐怖
    (53, "Thriller", 150),        # 驚悚
    (80, "Crime", 100),           # 犯罪
    (99, "Documentary", 100),     # 紀錄片
    (14, "Fantasy", 100),         # 奇幻
    (36, "History", 80),          # 歷史
    (10752, "War", 80),           # 戰爭
    (9648, "Mystery", 100),       # 懸疑
    (10402, "Music", 50),         # 音樂
    (37, "Western", 50),          # 西部
    (10751, "Family", 100),       # 家庭
]

for genre_id, genre_name, pages in genres:
    fetch_discover(
        {"with_genres": genre_id, "sort_by": "vote_average.desc", "vote_count.gte": 50},
        pages, f"🎭 {genre_name} (高分排序)"
    )
    fetch_discover(
        {"with_genres": genre_id, "sort_by": "popularity.desc"},
        pages // 2, f"🎭 {genre_name} (熱門排序)"
    )

# ============================================
# 3. 按年份抓取 (近年電影)
# ============================================
for year in range(2024, 2018, -1):  # 2024-2019
    fetch_discover(
        {"primary_release_year": year, "sort_by": "vote_average.desc", "vote_count.gte": 100},
        50, f"📅 {year} 年度佳片"
    )

# ============================================
# 4. 按語言/地區抓取 (國際電影)
# ============================================
languages = [
    ("ko", "韓國電影", 100),
    ("ja", "日本電影", 100),
    ("fr", "法國電影", 80),
    ("de", "德國電影", 50),
    ("es", "西班牙電影", 50),
    ("it", "義大利電影", 50),
    ("zh", "華語電影", 100),
    ("hi", "印度電影", 80),
    ("th", "泰國電影", 30),
]

for lang_code, lang_name, pages in languages:
    fetch_discover(
        {"with_original_language": lang_code, "sort_by": "vote_average.desc", "vote_count.gte": 50},
        pages, f"🌍 {lang_name}"
    )

# ============================================
# 5. 特殊搜尋 (影展得獎作品風格)
# ============================================
# 高評分 + 低投票 = 獨立電影/藝術電影
fetch_discover(
    {"vote_average.gte": 7.5, "vote_count.gte": 100, "vote_count.lte": 5000, "sort_by": "vote_average.desc"},
    200, "🏆 高評價獨立電影"
)

# 經典老電影 (1950-1990)
for decade_start in [1950, 1960, 1970, 1980]:
    fetch_discover(
        {"primary_release_date.gte": f"{decade_start}-01-01", 
         "primary_release_date.lte": f"{decade_start+9}-12-31",
         "sort_by": "vote_average.desc", "vote_count.gte": 200},
        50, f"🎞️ {decade_start}s 經典電影"
    )

# ============================================
# 儲存結果
# ============================================
end_time = datetime.now()
elapsed = (end_time - start_time).seconds

print("\n" + "=" * 70)
print(f"💾 正在寫入檔案 {OUTPUT_FILE} ...")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(vector_database, f, ensure_ascii=False)

import os
file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)

print("=" * 70)
print("🏆 ULTIMATE MOVIE VECTOR GENERATOR 完成！")
print("=" * 70)
print(f"   📊 總電影數: {len(vector_database):,} 部")
print(f"   💾 檔案大小: {file_size:.2f} MB")
print(f"   ⏱️ 執行時間: {elapsed//3600}時{(elapsed%3600)//60}分{elapsed%60}秒")
print(f"   📅 完成時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print("\n下一步:")
print(f"   1. python final_boss_engine.py --ratings_path C:\\ma\\ml-32m --genome_path C:\\ma\\movie_dataset_public_final --bert_file {OUTPUT_FILE}")
print(f"   2. python bert_service.py")
print("=" * 70)
