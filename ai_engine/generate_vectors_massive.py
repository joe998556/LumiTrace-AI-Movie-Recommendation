"""
🔥 MASSIVE MOVIE VECTOR GENERATOR (怪獸級) 🔥
目標：抓取 10萬+ 部電影 (突破 TMDB API 限制)

策略：按年份地毯式搜索 (1950-2026)
儲存：支援中斷續傳 (Resume Support)
"""

import json
import torch
import requests
import time
import os
import signal
import sys
from transformers import AutoTokenizer, AutoModel
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==========================================
# 設定
# ==========================================
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is not set. Add it to .env or your shell environment.")
MODEL_NAME = "AventIQ-AI/bert-movie-recommendation-system"
OUTPUT_FILE = "movie_vectors.json"
SAVE_INTERVAL = 500  # 每抓 500 部存檔一次
MIN_VOTE_COUNT = 10  # 放寬門檻：只要 10 人評分就抓 (衝量用)

# ==========================================
# 初始化
# ==========================================
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

# ==========================================
# 資料庫管理
# ==========================================
vector_database = []
seen_ids = set()

# 嘗試載入現有檔案
if os.path.exists(OUTPUT_FILE):
    try:
        print(f"📂 發現現有檔案 {OUTPUT_FILE}，正在載入...")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            vector_database = json.load(f)
        for m in vector_database:
            seen_ids.add(m['id'])
        print(f"✅ 已載入 {len(vector_database)} 部電影，將繼續擴充...")
    except Exception as e:
        print(f"⚠️ 載入失敗: {e}，將建立新檔案")

start_time = datetime.now()

def save_db():
    """儲存資料庫"""
    print(f"\n💾 正在存檔... (目前總數: {len(vector_database)})")
    # 先寫入 temp 避免中斷壞檔
    temp_file = OUTPUT_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(vector_database, f, ensure_ascii=False)
    
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    os.rename(temp_file, OUTPUT_FILE)
    print("✅ 存檔完成")

# 處理 Ctrl+C
def signal_handler(sig, frame):
    print("\n🛑 接收到中斷訊號！正在最後存檔...")
    save_db()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# 抓取邏輯
# ==========================================
def process_results(movies):
    new_count = 0
    for m in movies:
        mid = m['id']
        if mid in seen_ids: continue
        
        title = m.get('title', '')
        overview = m.get('overview', '')
        
        # 即使簡介很短也抓 (用標題補)，為了衝量
        if not overview: overview = "無簡介"
        
        content = f"電影: {title}\n簡介: {overview}\n評分: {m.get('vote_average')}\n上映: {m.get('release_date')}"
        vector = get_emb(content)
        
        vector_database.append({
            "id": mid,
            "title": title,
            "overview": overview,
            "poster_path": m.get('poster_path'),
            "vote_average": m.get('vote_average'),
            "vote_count": m.get('vote_count', 0),
            "genre_ids": m.get('genre_ids', []),
            "release_date": m.get('release_date'),
            "vector": vector
        })
        seen_ids.add(mid)
        new_count += 1
    return new_count

def fetch_year(year):
    """抓取特定年份的所有電影"""
    print(f"\n📅 正在掃描年份: {year}")
    total_added = 0
    max_pages = 500 # TMDB 上限
    
    for page in range(1, max_pages + 1):
        try:
            url = (
                f"https://api.themoviedb.org/3/discover/movie?"
                f"api_key={TMDB_API_KEY}&language=zh-TW&page={page}"
                f"&primary_release_year={year}"
                f"&vote_count.gte={MIN_VOTE_COUNT}" # 門檻
                f"&sort_by=vote_count.desc" # 優先抓多人評分的
            )
            
            res = requests.get(url, timeout=10)
            if not res.ok: 
                print(f"   ❌ API Error on page {page}")
                break
                
            data = res.json()
            results = data.get('results', [])
            if not results: break # 沒資料了
            
            added = process_results(results)
            total_added += added
            
            # 進度顯示
            sys.stdout.write(f"\r   頁 {page:>3} | 新增: {added:>2} | {year}年總計: {total_added:>4} | 全局總數: {len(vector_database):,}")
            sys.stdout.flush()
            
            # 定期存檔
            if len(vector_database) % SAVE_INTERVAL == 0 and added > 0:
                save_db()
                print(f"\n📅 繼續掃描年份: {year}")

            time.sleep(0.1) # 避免 Rate Limit
            
            # 如果這頁沒滿20個，表示後面沒了
            if len(results) < 20: break
            
        except Exception as e:
            print(f"\n   ⚠️ Error: {e}")
            time.sleep(5)

# ==========================================
# 主程式
# ==========================================
print("=" * 60)
print("🚀 MASSIVE GENERATOR 啟動")
print(f"🎯 目標: 抓取 1950-2026 所有評分 > {MIN_VOTE_COUNT} 的電影")
print("=" * 60)

# 從今年往回抓
current_year = datetime.now().year + 1
target_years = list(range(current_year, 1950, -1)) # 2026 -> 1950

for year in target_years:
    fetch_year(year)

print("\n" + "=" * 60)
save_db()
print("🏆 全部完成！")
filesize = os.path.getsize(OUTPUT_FILE) / (1024*1024)
print(f"總電影數: {len(vector_database):,} 部")
print(f"檔案大小: {filesize:.2f} MB")
