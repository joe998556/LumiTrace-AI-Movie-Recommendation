"""A/B test multilingual embedding models on a movie subset.

Usage:
    python tools/ab_test_multilingual.py --subset 800

Compares:
  - paraphrase-multilingual-mpnet-base-v2
  - BAAI/bge-m3

against the current bert-base-cased model on three eval prompts.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]

CURRENT_MODEL = "AventIQ-AI/bert-movie-recommendation-system"
CANDIDATES = [
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "BAAI/bge-m3",
]

EVAL_PROMPTS = [
    "想看校園YA片",
    "A coming-of-age high school teen campus story, young adult romance and friendship",
    "high school students, prom, bullying, first love, graduation, teen comedy",
]

GENRE_NAMES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}


def rich_text(movie: dict[str, Any]) -> str:
    genre_ids = [int(g) for g in movie.get("genre_ids", []) if str(g).isdigit()]
    genre_names = [GENRE_NAMES.get(gid, str(gid)) for gid in genre_ids]
    release_year = str(movie.get("release_date") or "")[:4]
    parts = [
        f"Title: {movie.get('title', 'unknown')}",
        f"Genres: {', '.join(genre_names) if genre_names else 'unknown'}",
        f"Original language: {movie.get('original_language') or 'unknown'}",
        f"Release year: {release_year if release_year.isdigit() else 'unknown'}",
        f"Audience rating: {movie.get('vote_average', 0)}",
        f"Plot and atmosphere: {movie.get('overview', '')}",
    ]
    return "\n".join(parts)


def query_template(prompt: str) -> str:
    return (
        f"Title: unknown\n"
        f"Genres: unknown\n"
        f"Original language: unknown\n"
        f"Release year: unknown\n"
        f"Audience rating: unknown\n"
        f"Plot and atmosphere: {prompt}"
    )


def load_subset(path: Path, n: int) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Prefer movies with posters and enough votes
    good = [m for m in data if m.get("poster_path") and m.get("vote_count", 0) >= 20]
    if len(good) >= n:
        return good[:n]
    return data[:n]


def embed_batch(texts: list[str], model, tokenizer, device, batch_size: int = 64) -> np.ndarray:
    all_vecs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512)
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            output = model(**encoded)
        hidden = output.last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        vecs = F.normalize(pooled, p=2, dim=1).cpu().numpy()
        all_vecs.append(vecs)
    return np.concatenate(all_vecs, axis=0)


def evaluate(
    corpus_vecs: np.ndarray,
    movies: list[dict[str, Any]],
    model_name: str,
    device: str,
) -> None:
    """Load model, embed queries, print top-10 for each eval prompt."""
    print(f"\n{'='*70}")
    print(f"Model: {model_name}")
    print(f"{'='*70}")

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()
    print(f"  Model load: {time.time()-t0:.1f}s")

    # Build corpus vectors
    t0 = time.time()
    corpus_texts = [rich_text(m) for m in movies]
    corpus_vecs_new = embed_batch(corpus_texts, model, tokenizer, device)
    print(f"  Corpus embed ({len(movies)} movies): {time.time()-t0:.1f}s")

    # Embed queries
    for pi, prompt in enumerate(EVAL_PROMPTS, 1):
        query_text = query_template(prompt)
        query_vec = embed_batch([query_text], model, tokenizer, device)  # (1, dim)

        # Cosine similarity
        sims = corpus_vecs_new @ query_vec.T  # (n_movies, 1)
        sims = sims.flatten()

        top_k = 10
        top_indices = np.argsort(sims)[::-1][:top_k]

        print(f"\n  Prompt {pi}: {prompt[:65]}")
        for rank, idx in enumerate(top_indices, 1):
            m = movies[idx]
            print(f"    {rank:2d}. {m['title'][:48]:48s}  sim={sims[idx]:.4f}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", type=int, default=800, help="Number of movies to test on")
    parser.add_argument("--data", default=str(ROOT / "final_boss_vectors.json"))
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    movies = load_subset(Path(args.data), args.subset)
    print(f"Loaded {len(movies)} movies for A/B test")

    # Also evaluate current model for baseline
    all_models = [CURRENT_MODEL] + CANDIDATES

    for model_name in all_models:
        evaluate(None, movies, model_name, device)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
