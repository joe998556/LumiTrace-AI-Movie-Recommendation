"""
🔥 FINAL BOSS ENGINE v2.0 🔥
The Ultimate Hybrid Recommendation System

Supports SEPARATE data sources:
- MovieLens 32M (ratings.csv, links.csv) → SVD 品味向量
- Tag Genome 2021 → Genome DNA 向量
- BERT vectors (movie_vectors.json) → 語意向量

Usage:
    python final_boss_engine.py --ratings_path ./ml-32m/ --genome_path ./genome-2021/ --bert_file movie_vectors.json
"""

import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import json
import os
import argparse
import glob

# ============================================
# Configuration
# ============================================
LATENT_DIM = 64
MIN_RATINGS_PER_MOVIE = 100
OUTPUT_FILE = "final_boss_vectors.json"


def find_file(directory: str, patterns: list) -> str:
    """在目錄中搜尋符合 pattern 的檔案"""
    for pattern in patterns:
        matches = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def load_links(data_path: str) -> tuple:
    """載入 MovieLens ID -> TMDB ID 映射"""
    print("\n📂 [1/5] 載入 ID 映射 (links.csv)...")
    
    links_file = find_file(data_path, ["links.csv"])
    if not links_file:
        print(f"   ❌ 找不到 links.csv in {data_path}")
        return {}, {}
    
    print(f"   找到: {links_file}")
    links = pd.read_csv(links_file)
    
    ml_to_tmdb = {}
    tmdb_to_ml = {}
    
    for _, row in links.iterrows():
        ml_id = int(row['movieId'])
        tmdb_id = row.get('tmdbId')
        if pd.notna(tmdb_id):
            tmdb_id = int(tmdb_id)
            ml_to_tmdb[ml_id] = tmdb_id
            tmdb_to_ml[tmdb_id] = ml_id
    
    print(f"   ✅ 成功映射: {len(ml_to_tmdb):,} 部電影")
    return ml_to_tmdb, tmdb_to_ml


def train_svd_vectors(data_path: str, ml_to_tmdb: dict) -> dict:
    """訓練 SVD 品味向量"""
    print("\n🧮 [2/5] 訓練 SVD 品味向量 (ratings.csv)...")
    
    ratings_file = find_file(data_path, ["ratings.csv"])
    if not ratings_file:
        print(f"   ❌ 找不到 ratings.csv in {data_path}")
        return {}
    
    print(f"   找到: {ratings_file}")
    print("   載入中 (這可能需要幾分鐘)...")
    ratings = pd.read_csv(ratings_file)
    print(f"   原始評分: {len(ratings):,} 筆")
    
    # 過濾
    movie_counts = ratings.groupby('movieId').size()
    valid_movies = movie_counts[movie_counts >= MIN_RATINGS_PER_MOVIE].index
    ratings_filtered = ratings[ratings['movieId'].isin(valid_movies)]
    print(f"   過濾後: {len(ratings_filtered):,} 筆 ({len(valid_movies):,} 部電影)")
    
    # ID 映射
    user_ids = ratings_filtered['userId'].unique()
    movie_ids = ratings_filtered['movieId'].unique()
    
    user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
    movie_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
    idx_to_movie = {idx: mid for mid, idx in movie_to_idx.items()}
    
    # 稀疏矩陣
    print("   建立 User-Item 矩陣...")
    row = ratings_filtered['userId'].map(user_to_idx)
    col = ratings_filtered['movieId'].map(movie_to_idx)
    
    user_means = ratings_filtered.groupby('userId')['rating'].mean()
    data = ratings_filtered['rating'].values - ratings_filtered['userId'].map(user_means).values
    
    matrix = csr_matrix(
        (data, (row, col)),
        shape=(len(user_ids), len(movie_ids))
    )
    print(f"   矩陣大小: {matrix.shape[0]:,} users x {matrix.shape[1]:,} movies")
    
    # SVD
    print(f"   執行 SVD (k={LATENT_DIM})...")
    U, sigma, Vt = svds(matrix.astype(float), k=LATENT_DIM)
    movie_vectors = normalize(Vt.T * sigma, norm='l2', axis=1)
    
    # 映射到 TMDB
    svd_vectors = {}
    for idx, ml_id in idx_to_movie.items():
        if ml_id in ml_to_tmdb:
            tmdb_id = ml_to_tmdb[ml_id]
            svd_vectors[tmdb_id] = movie_vectors[idx].tolist()
    
    print(f"   ✅ SVD 向量完成: {len(svd_vectors):,} 部電影")
    return svd_vectors


def train_genome_vectors(genome_path: str, ml_to_tmdb: dict) -> dict:
    """訓練 Genome DNA 向量 - 支援 Tag Genome 2021 格式"""
    print("\n🧬 [3/5] 訓練 Genome DNA 向量...")
    
    if not genome_path or not os.path.exists(genome_path):
        print(f"   ⚠️ Genome 路徑不存在: {genome_path}")
        return {}
    
    # 嘗試多種可能的檔案格式
    genome_files = [
        os.path.join(genome_path, "scores", "glmer.csv"),
        os.path.join(genome_path, "scores", "tagdl.csv"),
        os.path.join(genome_path, "genome-scores.csv"),
    ]
    
    genome_file = None
    for f in genome_files:
        if os.path.exists(f):
            genome_file = f
            break
    
    if not genome_file:
        # 最後嘗試遞迴搜尋
        csv_files = glob.glob(os.path.join(genome_path, "**", "*.csv"), recursive=True)
        for f in csv_files:
            if 'glmer' in f.lower() or 'tagdl' in f.lower() or 'genome' in f.lower():
                genome_file = f
                break
    
    if not genome_file:
        print(f"   ❌ 無法找到 Genome 資料")
        return {}
    
    print(f"   找到: {genome_file}")
    
    try:
        print("   載入中 (這可能需要幾分鐘)...")
        genome = pd.read_csv(genome_file)
        print(f"   欄位: {list(genome.columns)}")
        print(f"   資料筆數: {len(genome):,}")
        
        # 檢測格式
        cols = [c.lower() for c in genome.columns]
        
        if 'movieid' in cols and 'tagid' in cols and 'relevance' in cols:
            # 標準 MovieLens 25M 格式 (movieId, tagId, relevance)
            print("   格式: MovieLens 25M (movieId, tagId, relevance)")
            genome_matrix = genome.pivot(index='movieId', columns='tagId', values='relevance')
        
        elif 'item_id' in cols and 'tag' in cols and 'score' in cols:
            # Tag Genome 2021 格式 (tag, item_id, score)
            print("   格式: Tag Genome 2021 (tag, item_id, score)")
            print("   執行 Pivot 轉換...")
            genome_matrix = genome.pivot(index='item_id', columns='tag', values='score')
            print(f"   轉換完成: {genome_matrix.shape[0]:,} movies x {genome_matrix.shape[1]} tags")
        
        elif 'item' in cols and 'tag' in cols:
            # 另一種可能的 Genome 格式
            print("   格式: 變體格式 (item, tag, score)")
            score_col = 'score' if 'score' in cols else genome.columns[2]
            genome_matrix = genome.pivot(index='item', columns='tag', values=score_col)
        
        elif len(genome.columns) > 10:
            # 寬格式 (已經是 movie x tags 矩陣)
            print("   格式: 寬格式 (已經是矩陣)")
            id_col = genome.columns[0]
            genome_matrix = genome.set_index(id_col)
            genome_matrix = genome_matrix.select_dtypes(include=[np.number])
        
        else:
            print(f"   ❌ 無法識別的格式: {list(genome.columns)}")
            return {}
        
        genome_matrix = genome_matrix.fillna(0)
        print(f"   Genome 矩陣: {genome_matrix.shape[0]:,} movies x {genome_matrix.shape[1]} tags")
        
        if genome_matrix.shape[0] == 0:
            print("   ❌ 矩陣為空")
            return {}
        
        # PCA 降維
        n_components = min(LATENT_DIM, genome_matrix.shape[1])
        print(f"   執行 PCA (n_components={n_components})...")
        pca = PCA(n_components=n_components)
        genome_reduced = pca.fit_transform(genome_matrix.values)
        print(f"   解釋變異量: {sum(pca.explained_variance_ratio_)*100:.1f}%")
        
        # 正規化
        genome_reduced = normalize(genome_reduced, norm='l2', axis=1)
        
        # 映射到 TMDB ID
        genome_vectors = {}
        movie_ids = genome_matrix.index.tolist()
        
        mapped = 0
        for i, ml_id in enumerate(movie_ids):
            # 嘗試轉換為 int
            try:
                ml_id_int = int(ml_id)
            except:
                continue
            
            if ml_id_int in ml_to_tmdb:
                tmdb_id = ml_to_tmdb[ml_id_int]
                genome_vectors[tmdb_id] = genome_reduced[i].tolist()
                mapped += 1
        
        print(f"   ✅ Genome 向量完成: {mapped:,} 部電影 (共 {len(movie_ids):,})")
        return genome_vectors
        
    except Exception as e:
        print(f"   ❌ 處理 Genome 資料時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return {}


def load_bert_vectors(bert_file: str) -> dict:
    """載入 BERT 向量"""
    print("\n📖 [4/5] 載入 BERT 語意向量...")
    
    if not os.path.exists(bert_file):
        print(f"   ❌ 找不到 {bert_file}")
        return {}
    
    with open(bert_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    bert_vectors = {}
    for m in raw_data:
        tmdb_id = m['id']
        bert_vectors[tmdb_id] = {
            "vector": m['vector'],
            "title": m.get('title', ''),
            "overview": m.get('overview', ''),
            "poster_path": m.get('poster_path'),
            "vote_average": m.get('vote_average', 0),
            "vote_count": m.get('vote_count', 0),
            "genre_ids": m.get('genre_ids', [])
        }
    
    print(f"   ✅ BERT 向量載入: {len(bert_vectors):,} 部電影")
    return bert_vectors


def merge_and_save(svd_vectors: dict, genome_vectors: dict, bert_vectors: dict, output_file: str):
    """合併所有向量"""
    print("\n🔗 [5/5] 合併向量並儲存...")
    
    all_tmdb_ids = set(bert_vectors.keys())
    
    has_svd = sum(1 for tid in all_tmdb_ids if tid in svd_vectors)
    has_genome = sum(1 for tid in all_tmdb_ids if tid in genome_vectors)
    has_all = sum(1 for tid in all_tmdb_ids if tid in svd_vectors and tid in genome_vectors)
    
    print(f"\n   覆蓋率統計 (基於 {len(all_tmdb_ids)} 部 BERT 電影):")
    print(f"   - 有 SVD 向量: {has_svd:,} ({100*has_svd/len(all_tmdb_ids):.1f}%)")
    print(f"   - 有 Genome 向量: {has_genome:,} ({100*has_genome/len(all_tmdb_ids):.1f}%)")
    print(f"   - 三合一完整: {has_all:,} ({100*has_all/len(all_tmdb_ids):.1f}%)")
    
    final_data = []
    for tmdb_id, bert_data in bert_vectors.items():
        entry = {
            "id": tmdb_id,
            "title": bert_data.get('title', ''),
            "overview": bert_data.get('overview', ''),
            "poster_path": bert_data.get('poster_path'),
            "vote_average": bert_data.get('vote_average', 0),
            "vote_count": bert_data.get('vote_count', 0),
            "genre_ids": bert_data.get('genre_ids', []),
            "bert_vector": bert_data['vector'],
            "svd_vector": svd_vectors.get(tmdb_id),
            "genome_vector": genome_vectors.get(tmdb_id)
        }
        final_data.append(entry)
    
    print(f"\n   儲存到 {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False)
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   ✅ 檔案大小: {file_size:.2f} MB")
    
    return final_data


def main():
    parser = argparse.ArgumentParser(description="🔥 FINAL BOSS ENGINE v2.0 🔥")
    parser.add_argument(
        '--ratings_path', 
        type=str, 
        default='./ml-32m/',
        help='Path to MovieLens ratings dataset (contains ratings.csv, links.csv)'
    )
    parser.add_argument(
        '--genome_path', 
        type=str, 
        default='./genome-2021/',
        help='Path to Tag Genome dataset (contains genome-scores.csv or scores/)'
    )
    parser.add_argument(
        '--bert_file', 
        type=str, 
        default='movie_vectors.json',
        help='Path to BERT vectors'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default=OUTPUT_FILE,
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔥 FINAL BOSS ENGINE v2.0 - 終極混合推薦系統 🔥")
    print("=" * 60)
    print(f"   評分資料: {args.ratings_path}")
    print(f"   Genome資料: {args.genome_path}")
    print(f"   BERT向量: {args.bert_file}")
    print("=" * 60)
    
    # 1. 載入 ID 映射 (從 ratings 資料夾)
    ml_to_tmdb, tmdb_to_ml = load_links(args.ratings_path)
    
    if not ml_to_tmdb:
        print("❌ 無法載入 ID 映射，請確認 links.csv 路徑")
        return
    
    # 2. 訓練 SVD
    svd_vectors = train_svd_vectors(args.ratings_path, ml_to_tmdb)
    
    # 3. 訓練 Genome
    genome_vectors = train_genome_vectors(args.genome_path, ml_to_tmdb)
    
    # 4. 載入 BERT
    bert_vectors = load_bert_vectors(args.bert_file)
    
    if not bert_vectors:
        print("❌ 無法載入 BERT 向量，請先執行 generate_vectors.py")
        return
    
    # 5. 合併並儲存
    final_data = merge_and_save(svd_vectors, genome_vectors, bert_vectors, args.output)
    
    print("\n" + "=" * 60)
    print("🏆 FINAL BOSS ENGINE 訓練完成！")
    print("=" * 60)
    print(f"   輸出: {args.output}")
    print(f"   電影: {len(final_data):,}")
    print("=" * 60)


if __name__ == '__main__':
    main()
