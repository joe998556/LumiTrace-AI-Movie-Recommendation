"""
🔥 INFINITY MOVIE VECTOR GENERATOR (無限制版) 🔥
目標：抓取 TMDB 上的「所有」電影 (只要有人評分)

參數全開 (ALL)：
- 年份: 1900 - 2026
- 評分門檻: >= 1 (只要有人評分就抓)
- 頁數: 跑好跑滿 (每頁 20 部 x 500 頁 = 每個查詢 10,000 部)
- 策略: 使用多重排序組合來突破 10,000 部限制

預計產量：200,000+ 部
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
OUTPUT_FILE = "movie_vectors.json"  # 直接覆蓋或擴充主檔案
SAVE_INTERVAL = 1000  # 每 1000 部存檔一次

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

if os.path.exists(OUTPUT_FILE):
    try:
        print(f"📂 發現現有檔案 {OUTPUT_FILE}，正在載入...")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            vector_database = json.load(f)
        for m in vector_database:
            seen_ids.add(m['id'])
        print(f"✅ 已載入 {len(vector_database)} 部電影，將繼續擴充...")
    except Exception as e:
        print(f"⚠️ 載入失敗: {e}")

def save_db():
    print(f"\n💾 正在存檔... (總數: {len(vector_database):,})")
    temp_file = OUTPUT_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(vector_database, f, ensure_ascii=False)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    os.rename(temp_file, OUTPUT_FILE)
    filesize = os.path.getsize(OUTPUT_FILE) / (1024*1024)
    print(f"✅ 存檔完成 ({filesize:.2f} MB)")

def signal_handler(sig, frame):
    print("\n🛑 用戶中斷！正在最後存檔...")
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
        # 極限寬容: 只要有標題就抓
        if not title: continue
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

def fetch_with_params(params, desc):
    """通用抓取函式"""
    max_pages = 500
    total_added = 0
    
    # 自動重試機制
    for page in range(1, max_pages + 1):
        retries = 3
        while retries > 0:
            try:
                base = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&language=zh-TW&page={page}"
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{base}&{query}"
                
                res = requests.get(url, timeout=10)
                if res.status_code == 422: # 頁數超過限制
                    return total_added
                if not res.ok:
                    print(f"   ⚠️ API Error {res.status_code}, retrying...")
                    time.sleep(2)
                    retries -= 1
                    continue
                
                data = res.json()
                results = data.get('results', [])
                if not results: return total_added
                
                added = process_results(results)
                total_added += added
                
                # 進度顯示
                sys.stdout.write(f"\r   [{desc}] 頁 {page:<3} | 本次新增: {total_added:<5} | 總庫存: {len(vector_database):,}")
                sys.stdout.flush()
                
                if len(vector_database) % SAVE_INTERVAL == 0 and added > 0:
                    save_db()
                
                time.sleep(0.05) # 極速模式 (注意 Rate Limit)
                break
            except Exception as e:
                print(f"\n   ⚠️ Network Error: {e}")
                time.sleep(5)
                retries -= 1
    return total_added

# ==========================================
# 主流程
# ==========================================
print("=" * 60)
print("🚀 INFINITY GENERATOR 啟動 (全參數解鎖)")
print("🎯 目標: 掃描所有存在的電影 (1900-2026)")
print("=" * 60)

# 策略：按年份切分
# 對於每一年，我們使用多種排序方式來抓取不同的電影 (突破 10,000 部限制)
current_year = datetime.now().year + 1
years = list(range(current_year, 1900, -1))

sort_options = [
    ("vote_count.desc", "最多人評分"),
    ("popularity.desc", "最熱門"),
    ("revenue.desc", "最高票房"),
    ("vote_average.desc", "最高評價 (需>10評分)"),
    ("primary_release_date.desc", "最新上映"),
    ("primary_release_date.asc", "最早上映"),
]

for year in years:
    print(f"\n\n📅 正在地毯式掃描: {year} 年")
    
    for sort_by, label in sort_options:
        params = {
            "primary_release_year": year,
            "sort_by": sort_by,
            "vote_count.gte": 1  # 門檻極低
        }
        if "vote_average" in sort_by:
            params["vote_count.gte"] = 10 # 避免只有1人評分10分的
            
        fetch_with_params(params, f"{year} {label}")

print("\n" + "=" * 60)
save_db()
print("🏆 任務完成！")
