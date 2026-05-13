"""
🔥 FINAL BOSS RECOMMENDATION SERVICE 🔥
The Ultimate Hybrid Recommendation API

Scoring Formula:
- Genome DNA (50%): Movie's soul/style
- SVD Taste (30%): Audience profile matching
- BERT Semantic (20%): Plot keyword backup
"""
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import os
import json
import math
from collections import Counter

# ============================================
# 初始化 Flask & Model
# ============================================
app = Flask(__name__)

MODEL_NAME = "AventIQ-AI/bert-movie-recommendation-system"
FINAL_BOSS_FILE = "final_boss_vectors.json"
LEGACY_BERT_FILE = "movie_vectors.json"

# Global Storage
MOVIE_DATA = []
BERT_TENSOR = None
SVD_TENSOR = None
GENOME_TENSOR = None
MOVIE_IDS = []
ID_TO_IDX = {}

# 權重配置
WEIGHTS = {
    "genome": 0.50,  # 風格基因 (最重要)
    "svd": 0.30,     # 品味受眾
    "bert": 0.20     # 語意輔助
}

# TMDB 類型映射
GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

BLOCKBUSTER_GENRES = {"Action", "Science Fiction", "Adventure", "Fantasy"}

print(f"正在載入模型 {MODEL_NAME} ...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用裝置: {device}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(device)
model.eval()

# ============================================
# 載入 Final Boss 向量資料庫
# ============================================
def load_final_boss_db():
    global MOVIE_DATA, BERT_TENSOR, SVD_TENSOR, GENOME_TENSOR, MOVIE_IDS, ID_TO_IDX
    
    # 優先使用 Final Boss 格式
    if os.path.exists(FINAL_BOSS_FILE):
        data_file = FINAL_BOSS_FILE
        is_final_boss = True
    elif os.path.exists(LEGACY_BERT_FILE):
        data_file = LEGACY_BERT_FILE
        is_final_boss = False
        print(f"⚠️ 使用舊版 BERT-only 格式 (建議執行 final_boss_engine.py 升級)")
    else:
        print("❌ 找不到向量資料庫!")
        return False
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        MOVIE_DATA = []
        bert_vectors = []
        svd_vectors = []
        genome_vectors = []
        MOVIE_IDS = []
        
        has_svd_count = 0
        has_genome_count = 0
        
        for m in raw_data:
            mid = m['id']
            MOVIE_IDS.append(mid)
            ID_TO_IDX[mid] = len(MOVIE_DATA)
            
            MOVIE_DATA.append({
                "id": mid,
                "title": m.get('title', ''),
                "overview": m.get('overview', ''),
                "poster_path": m.get('poster_path'),
                "vote_average": m.get('vote_average', 0),
                "vote_count": m.get('vote_count', 0),
                "genre_ids": m.get('genre_ids', [])
            })
            
            # BERT 向量
            if is_final_boss:
                bert_vec = m.get('bert_vector', [0] * 768)
            else:
                bert_vec = m.get('vector', [0] * 768)
            bert_vectors.append(bert_vec)
            
            # SVD 向量 (可能為 None)
            svd_vec = m.get('svd_vector')
            if svd_vec:
                svd_vectors.append(svd_vec)
                has_svd_count += 1
            else:
                svd_vectors.append([0] * 64)  # 填充零向量
            
            # Genome 向量 (可能為 None)
            genome_vec = m.get('genome_vector')
            if genome_vec:
                genome_vectors.append(genome_vec)
                has_genome_count += 1
            else:
                genome_vectors.append([0] * 64)  # 填充零向量
        
        # 轉為 Tensor
        BERT_TENSOR = torch.tensor(bert_vectors, dtype=torch.float32, device=device)
        BERT_TENSOR = F.normalize(BERT_TENSOR, p=2, dim=1)
        
        SVD_TENSOR = torch.tensor(svd_vectors, dtype=torch.float32, device=device)
        # 對於有值的才正規化
        svd_norms = SVD_TENSOR.norm(dim=1, keepdim=True)
        svd_norms = torch.where(svd_norms > 0, svd_norms, torch.ones_like(svd_norms))
        SVD_TENSOR = SVD_TENSOR / svd_norms
        
        GENOME_TENSOR = torch.tensor(genome_vectors, dtype=torch.float32, device=device)
        genome_norms = GENOME_TENSOR.norm(dim=1, keepdim=True)
        genome_norms = torch.where(genome_norms > 0, genome_norms, torch.ones_like(genome_norms))
        GENOME_TENSOR = GENOME_TENSOR / genome_norms
        
        print(f"✅ 資料庫已載入: {len(MOVIE_DATA)} 筆電影")
        print(f"   - BERT 向量: 100%")
        print(f"   - SVD 向量: {has_svd_count}/{len(MOVIE_DATA)} ({100*has_svd_count/len(MOVIE_DATA):.1f}%)")
        print(f"   - Genome 向量: {has_genome_count}/{len(MOVIE_DATA)} ({100*has_genome_count/len(MOVIE_DATA):.1f}%)")
        
        if has_genome_count > 0:
            print(f"🔥 FINAL BOSS MODE ACTIVATED!")
        
        return True
        
    except Exception as e:
        print(f"❌ 載入資料庫失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


load_final_boss_db()

# ============================================
# Helper Functions
# ============================================
def get_batch_embeddings(texts: list) -> torch.Tensor:
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return F.normalize(embeddings, p=2, dim=1)

def get_genre_names(gids):
    return {GENRE_MAP.get(g) for g in gids if GENRE_MAP.get(g)}

def compute_user_profile(fav_ids: set):
    """
    計算用戶的 SVD 和 Genome Profile
    = 收藏電影向量的平均
    """
    svd_vecs = []
    genome_vecs = []
    
    for fav_id in fav_ids:
        if fav_id in ID_TO_IDX:
            idx = ID_TO_IDX[fav_id]
            
            # SVD
            if SVD_TENSOR[idx].norm() > 0.1:  # 確保有有效向量
                svd_vecs.append(SVD_TENSOR[idx])
            
            # Genome
            if GENOME_TENSOR[idx].norm() > 0.1:
                genome_vecs.append(GENOME_TENSOR[idx])
    
    user_svd = None
    user_genome = None
    
    if svd_vecs:
        user_svd = torch.stack(svd_vecs).mean(dim=0)
        user_svd = F.normalize(user_svd.unsqueeze(0), p=2, dim=1)
    
    if genome_vecs:
        user_genome = torch.stack(genome_vecs).mean(dim=0)
        user_genome = F.normalize(user_genome.unsqueeze(0), p=2, dim=1)
    
    return user_svd, user_genome


# ============================================
# 核心搜尋邏輯 (Final Boss Scoring)
# ============================================
@app.route('/search', methods=['POST'])
def search():
    data = request.json
    overviews = data.get('overviews', [])
    top_k = data.get('top_k', 10)
    exclude_ids = set(data.get('exclude_ids', []))
    
    user_genre_ids = data.get('user_genre_ids', [])
    user_vote_counts = data.get('user_vote_counts', [])
    
    if not overviews and data.get('text'):
        overviews = [data.get('text')]
    
    if not overviews or BERT_TENSOR is None:
        return jsonify({"results": []})
    
    try:
        # ==================================================
        # 1. 分析用戶特徵 (Anti-Blockbuster Logic)
        # ==================================================
        user_seen_genres = set()
        for gids in user_genre_ids:
            user_seen_genres.update(get_genre_names(gids))
        
        valid_counts = [c for c in user_vote_counts if c > 0]
        user_avg_vote = sum(valid_counts) / len(valid_counts) if valid_counts else 1000
        is_indie_fan = user_avg_vote < 8000
        has_watched_blockbuster = bool(user_seen_genres & BLOCKBUSTER_GENRES)
        
        # 如果無類型資料，嘗試從收藏電影的標題推斷用戶偏好
        if len(user_seen_genres) == 0:
            # 檢查用戶收藏的電影是否包含大片關鍵字
            blockbuster_title_keywords = [
                'avenger', 'marvel', 'iron man', 'thor', 'spider', 'batman', 'superman',
                'fast', 'furious', 'star wars', 'transformers', 'x-men', 'deadpool',
                '復仇者', '雷神', '蜘蛛', '鋼鐵人', '蝙蝠俠', '超人', '玩命關頭',
                '死侍', '變形金剛', '驚奇', 'fantastic', 'captain america', '美國隊長'
            ]
            
            # 獲取用戶收藏電影的標題
            user_titles = []
            for fav_id in exclude_ids:
                if fav_id in ID_TO_IDX:
                    idx = ID_TO_IDX[fav_id]
                    if idx < len(MOVIE_DATA):
                        user_titles.append(MOVIE_DATA[idx]['title'].lower())
            
            # 檢查是否有大片
            user_likes_blockbusters = any(
                any(kw in title for kw in blockbuster_title_keywords)
                for title in user_titles
            )
            
            if user_likes_blockbusters:
                has_watched_blockbuster = True
                is_indie_fan = False
                print("🦸 用戶收藏包含大片，啟用「大片模式」")
            else:
                has_watched_blockbuster = False
                is_indie_fan = True
                print("🎬 用戶收藏偏文藝，啟用「保守模式」")
        
        # ==================================================
        # 2. 計算用戶 Profile (SVD + Genome)
        # ==================================================
        user_svd, user_genome = compute_user_profile(exclude_ids)
        
        mode = []
        if user_genome is not None:
            mode.append("Genome")
        if user_svd is not None:
            mode.append("SVD")
        mode.append("BERT")
        print(f"📊 使用模式: {' + '.join(mode)}")
        
        # ==================================================
        # 3. 計算各維度相似度
        # ==================================================
        # BERT 相似度
        user_bert = get_batch_embeddings(overviews)
        bert_sim = torch.mm(BERT_TENSOR, user_bert.T).max(dim=1)[0]
        
        # SVD 相似度
        if user_svd is not None:
            svd_sim = torch.mm(SVD_TENSOR, user_svd.T).squeeze()
        else:
            svd_sim = torch.zeros(len(MOVIE_DATA), device=device)
        
        # Genome 相似度
        if user_genome is not None:
            genome_sim = torch.mm(GENOME_TENSOR, user_genome.T).squeeze()
        else:
            genome_sim = torch.zeros(len(MOVIE_DATA), device=device)
        
        # ==================================================
        # 4. 計算最終分數 (Weighted Combination)
        # ==================================================
        # 動態調整權重 (如果某個向量不存在，重新分配權重)
        w_genome = WEIGHTS["genome"] if user_genome is not None else 0
        w_svd = WEIGHTS["svd"] if user_svd is not None else 0
        w_bert = WEIGHTS["bert"]
        
        # 正規化權重使總和為 1
        total_weight = w_genome + w_svd + w_bert
        if total_weight > 0:
            w_genome /= total_weight
            w_svd /= total_weight
            w_bert /= total_weight
        else:
            w_bert = 1.0
        
        # 計算加權分數
        final_scores = (
            genome_sim * w_genome +
            svd_sim * w_svd +
            bert_sim * w_bert
        )
        
        scores = final_scores.cpu().tolist()
        bert_scores_list = bert_sim.cpu().tolist()
        svd_scores_list = svd_sim.cpu().tolist()
        genome_scores_list = genome_sim.cpu().tolist()
        
        # ==================================================
        # 5. 過濾與懲罰
        # ==================================================
        candidates = []
        
        # 標題黑名單
        blockbuster_keywords = [
            'thor', 'avengers', 'fast', 'furious', '玩命關頭', '雷神',
            'spider-man', 'batman', 'superman', 'iron man', 'hulk',
            'transformers', 'star wars', 'avatar', 'jurassic', '侏羅紀',
            'marvel', 'dc', 'x-men', 'deadpool', 'flash', '閃電俠',
            '復仇者', '蜘蛛人', '蝙蝠俠', '超人', '鋼鐵人', '變形金剛'
        ]
        
        horror_keywords = [
            'freddy', 'nightmare', 'horror', 'halloween', 'saw',
            'conjuring', 'annabelle', 'insidious', 'scream', 'chucky',
            '驚魂', '恐怖', '凶宅', '厲陰', 'zombie', '殭屍'
        ]
        
        for idx, base_score in enumerate(scores):
            movie = MOVIE_DATA[idx]
            mid = movie['id']
            m_vote_avg = movie['vote_average']
            m_vote_count = movie['vote_count']
            m_title = movie['title'].lower()
            
            # 基本過濾
            if mid in exclude_ids: continue
            if m_vote_avg <= 0.1: continue
            if m_vote_count < 50: continue
            
            final_score = base_score
            penalties = []
            
            # 標題黑名單懲罰
            if is_indie_fan:
                if any(kw in m_title for kw in blockbuster_keywords):
                    final_score *= 0.2
                    penalties.append("Blockbuster Blacklist")
                
                if any(kw in m_title for kw in horror_keywords):
                    final_score *= 0.3
                    penalties.append("Horror Blacklist")
                
                # 投票數懲罰
                if m_vote_count > 50000:
                    final_score *= 0.5
                    penalties.append("Mega-Popular")
                elif m_vote_count > 20000:
                    final_score *= 0.7
                    penalties.append("Popular")
            
            # 類型懲罰
            m_genres = get_genre_names(movie['genre_ids'])
            if not has_watched_blockbuster and bool(m_genres & BLOCKBUSTER_GENRES):
                if base_score < 0.85:
                    final_score *= 0.4
                    penalties.append("Genre Mismatch")
            
            if final_score > 0.3:  # 最低門檻
                candidates.append({
                    "id": mid,
                    "title": movie['title'],
                    "overview": movie['overview'],
                    "poster_path": movie.get('poster_path'),
                    "vote_average": m_vote_avg,
                    "vote_count": m_vote_count,
                    "genre_ids": movie.get('genre_ids', []),
                    "score": round(final_score, 4),
                    "debug": {
                        "bert": round(bert_scores_list[idx], 3),
                        "svd": round(svd_scores_list[idx], 3),
                        "genome": round(genome_scores_list[idx], 3),
                        "penalties": penalties
                    }
                })
        
        # 排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        results = candidates[:top_k]
        
        # 清理 debug (生產環境可移除)
        # for r in results: del r['debug']
        
        return jsonify({"results": results})
    
    except Exception as e:
        print(f"Search Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================
# API Endpoints
# ============================================
@app.route('/embed', methods=['POST'])
def embed():
    try:
        text = request.json.get('text', '')
        vec = get_batch_embeddings([text])[0].cpu().tolist()
        return jsonify({"vector": vec})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/reload_db', methods=['POST'])
def reload_db():
    if load_final_boss_db():
        return jsonify({"status": "ok", "count": len(MOVIE_DATA)})
    return jsonify({"error": "Failed"}), 500


@app.route('/status', methods=['GET'])
def status():
    has_svd = SVD_TENSOR.norm(dim=1).gt(0.1).sum().item() if SVD_TENSOR is not None else 0
    has_genome = GENOME_TENSOR.norm(dim=1).gt(0.1).sum().item() if GENOME_TENSOR is not None else 0
    
    return jsonify({
        "status": "online",
        "device": device,
        "movie_count": len(MOVIE_DATA),
        "svd_coverage": has_svd,
        "genome_coverage": has_genome,
        "weights": WEIGHTS,
        "algorithm": "Final Boss Engine (Genome 50% + SVD 30% + BERT 20%)"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
