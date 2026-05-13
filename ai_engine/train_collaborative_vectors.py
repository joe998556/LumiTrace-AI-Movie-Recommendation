"""
Train Collaborative Filtering Vectors using MovieLens Dataset
This script uses SVD to generate latent vectors for movies based on user ratings.

Prerequisites:
1. Download MovieLens dataset (ml-25m or ml-latest-small) from https://grouplens.org/datasets/movielens/
2. Extract to a folder (e.g., ./movielens/)
3. Required files: ratings.csv, movies.csv, links.csv

Usage:
    python train_collaborative_vectors.py --data_path ./movielens/ml-latest-small/
"""

import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
import json
import argparse
import os

# ============================================
# Configuration
# ============================================
LATENT_DIM = 64  # SVD 維度 (越高越精確，但也越慢)
MIN_RATINGS_PER_MOVIE = 50  # 至少要有這麼多人評分才納入
MIN_RATINGS_PER_USER = 20   # 至少要評這麼多部電影的用戶才納入
OUTPUT_FILE = "collaborative_vectors.json"


def load_movielens_data(data_path: str):
    """載入 MovieLens 資料集"""
    print("📂 載入 MovieLens 資料集...")
    
    # 載入評分資料
    ratings_file = os.path.join(data_path, "ratings.csv")
    ratings = pd.read_csv(ratings_file)
    print(f"   - ratings.csv: {len(ratings):,} 筆評分")
    
    # 載入電影資料
    movies_file = os.path.join(data_path, "movies.csv")
    movies = pd.read_csv(movies_file)
    print(f"   - movies.csv: {len(movies):,} 部電影")
    
    # 載入 ID 映射 (MovieLens ID -> TMDB ID)
    links_file = os.path.join(data_path, "links.csv")
    links = pd.read_csv(links_file)
    print(f"   - links.csv: {len(links):,} 筆映射")
    
    return ratings, movies, links


def filter_data(ratings: pd.DataFrame):
    """過濾低品質資料"""
    print("\n🔍 過濾低品質資料...")
    
    original_count = len(ratings)
    
    # 計算每部電影的評分數
    movie_counts = ratings.groupby('movieId').size()
    valid_movies = movie_counts[movie_counts >= MIN_RATINGS_PER_MOVIE].index
    
    # 計算每個用戶的評分數
    user_counts = ratings.groupby('userId').size()
    valid_users = user_counts[user_counts >= MIN_RATINGS_PER_USER].index
    
    # 過濾
    ratings_filtered = ratings[
        (ratings['movieId'].isin(valid_movies)) & 
        (ratings['userId'].isin(valid_users))
    ]
    
    print(f"   - 原始評分: {original_count:,}")
    print(f"   - 過濾後: {len(ratings_filtered):,}")
    print(f"   - 有效電影數: {len(valid_movies):,}")
    print(f"   - 有效用戶數: {len(valid_users):,}")
    
    return ratings_filtered


def build_user_item_matrix(ratings: pd.DataFrame):
    """建立 User-Item 稀疏矩陣"""
    print("\n🔢 建立 User-Item 矩陣...")
    
    # 建立 ID 映射 (原始 ID -> 連續索引)
    user_ids = ratings['userId'].unique()
    movie_ids = ratings['movieId'].unique()
    
    user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
    movie_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
    idx_to_movie = {idx: mid for mid, idx in movie_to_idx.items()}
    
    # 建立稀疏矩陣
    row = ratings['userId'].map(user_to_idx)
    col = ratings['movieId'].map(movie_to_idx)
    data = ratings['rating'].values
    
    # 中心化 (減去每個用戶的平均評分，消除評分偏差)
    user_means = ratings.groupby('userId')['rating'].mean()
    data_centered = data - ratings['userId'].map(user_means).values
    
    matrix = csr_matrix(
        (data_centered, (row, col)),
        shape=(len(user_ids), len(movie_ids))
    )
    
    print(f"   - 矩陣大小: {matrix.shape[0]:,} users x {matrix.shape[1]:,} movies")
    print(f"   - 稀疏度: {100 * (1 - matrix.nnz / (matrix.shape[0] * matrix.shape[1])):.2f}%")
    
    return matrix, idx_to_movie, movie_to_idx


def train_svd(matrix: csr_matrix, k: int = LATENT_DIM):
    """執行 SVD 分解"""
    print(f"\n🧮 執行 SVD (k={k})...")
    
    # SVD 分解: matrix ≈ U @ S @ Vt
    # U: 用戶潛在向量 (n_users, k)
    # S: 奇異值
    # Vt: 電影潛在向量 (k, n_movies)
    U, sigma, Vt = svds(matrix.astype(float), k=k)
    
    # 將奇異值乘進去，得到更有意義的向量
    # 電影向量 = Vt.T @ diag(sigma)
    movie_vectors = Vt.T * sigma  # Shape: (n_movies, k)
    
    print(f"   - 用戶潛在向量: {U.shape}")
    print(f"   - 電影潛在向量: {movie_vectors.shape}")
    print(f"   - 前5個奇異值: {sigma[:5].round(2)}")
    
    return movie_vectors, U, sigma


def map_to_tmdb(movie_vectors: np.ndarray, idx_to_movie: dict, links: pd.DataFrame):
    """將 MovieLens ID 映射到 TMDB ID"""
    print("\n🔗 映射到 TMDB ID...")
    
    # 建立 MovieLens ID -> TMDB ID 的映射
    ml_to_tmdb = {}
    for _, row in links.iterrows():
        ml_id = row['movieId']
        tmdb_id = row.get('tmdbId')
        if pd.notna(tmdb_id):
            ml_to_tmdb[ml_id] = int(tmdb_id)
    
    # 映射向量
    result = {}
    mapped_count = 0
    
    for idx, ml_id in idx_to_movie.items():
        if ml_id in ml_to_tmdb:
            tmdb_id = ml_to_tmdb[ml_id]
            vector = movie_vectors[idx].tolist()
            result[str(tmdb_id)] = vector  # JSON key 必須是 string
            mapped_count += 1
    
    print(f"   - 成功映射: {mapped_count:,} 部電影")
    print(f"   - 映射失敗 (無 TMDB ID): {len(idx_to_movie) - mapped_count:,}")
    
    return result


def normalize_vectors(vectors_dict: dict):
    """L2 正規化向量 (方便計算 Cosine Similarity)"""
    print("\n📐 正規化向量...")
    
    result = {}
    for tmdb_id, vec in vectors_dict.items():
        vec_np = np.array(vec)
        norm = np.linalg.norm(vec_np)
        if norm > 0:
            result[tmdb_id] = (vec_np / norm).tolist()
        else:
            result[tmdb_id] = vec
    
    return result


def save_vectors(vectors: dict, output_file: str):
    """儲存向量到 JSON"""
    print(f"\n💾 儲存到 {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vectors, f)
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   - 檔案大小: {file_size:.2f} MB")
    print(f"   - 向量數量: {len(vectors):,}")


def main():
    parser = argparse.ArgumentParser(description="Train Collaborative Filtering Vectors")
    parser.add_argument(
        '--data_path', 
        type=str, 
        default='./movielens/ml-latest-small/',
        help='Path to MovieLens dataset folder'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default=OUTPUT_FILE,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--dim', 
        type=int, 
        default=LATENT_DIM,
        help='Latent dimension for SVD'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎬 Collaborative Filtering Vector Training")
    print("=" * 60)
    
    # 1. 載入資料
    ratings, movies, links = load_movielens_data(args.data_path)
    
    # 2. 過濾低品質資料
    ratings_filtered = filter_data(ratings)
    
    # 3. 建立 User-Item 矩陣
    matrix, idx_to_movie, movie_to_idx = build_user_item_matrix(ratings_filtered)
    
    # 4. SVD 分解
    movie_vectors, user_vectors, sigma = train_svd(matrix, k=args.dim)
    
    # 5. 映射到 TMDB ID
    vectors_dict = map_to_tmdb(movie_vectors, idx_to_movie, links)
    
    # 6. 正規化
    vectors_normalized = normalize_vectors(vectors_dict)
    
    # 7. 儲存
    save_vectors(vectors_normalized, args.output)
    
    print("\n" + "=" * 60)
    print("✅ 訓練完成！")
    print(f"   輸出檔案: {args.output}")
    print(f"   向量維度: {args.dim}")
    print(f"   電影數量: {len(vectors_normalized):,}")
    print("=" * 60)
    
    # 印出一些範例
    print("\n📌 範例向量 (前3部):")
    for i, (tmdb_id, vec) in enumerate(list(vectors_normalized.items())[:3]):
        print(f"   TMDB ID {tmdb_id}: [{vec[0]:.4f}, {vec[1]:.4f}, ..., {vec[-1]:.4f}]")


if __name__ == '__main__':
    main()
