"""Re-embed existing movie_vectors.json with a new model.

Usage:
    python tools/reembed_vectors.py --model BAAI/bge-m3 --device cuda

Reads movie_vectors.json, re-embeds all movies using the specified model
with the same rich-text template, and writes back.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

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
    director = str(movie.get("director") or "").strip()
    cast = movie.get("cast") or []
    if isinstance(cast, list):
        cast = [str(c).strip() for c in cast[:4] if c]
    else:
        cast = []
    collection = str(movie.get("collection_name") or "").strip()
    parts = [
        f"Title: {movie.get('title', 'unknown')}",
        f"Genres: {', '.join(genre_names) if genre_names else 'unknown'}",
        f"Original language: {movie.get('original_language') or 'unknown'}",
        f"Release year: {release_year if release_year.isdigit() else 'unknown'}",
        f"Audience rating: {movie.get('vote_average', 0)}",
    ]
    if director:
        parts.append(f"Director: {director}")
    if cast:
        parts.append(f"Cast: {', '.join(cast)}")
    if collection:
        parts.append(f"Series or collection: {collection}")
    parts.append(f"Plot and atmosphere: {movie.get('overview', '')}")
    return "\n".join(parts)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Re-embed movie_vectors.json with a new model.")
    parser.add_argument("--model", default="BAAI/bge-m3", help="Hugging Face model name.")
    parser.add_argument("--input", default=str(ROOT / "movie_vectors.json"))
    parser.add_argument("--output", default=None, help="Output path (default: overwrite input)")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Device: {device}")

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    print(f"Loading vectors from {input_path}")
    with input_path.open("r", encoding="utf-8") as f:
        movies = json.load(f)
    print(f"Loaded {len(movies)} movies")

    print(f"Loading model: {args.model}")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModel.from_pretrained(args.model).to(device)
    model.eval()
    print(f"Model loaded in {time.time()-t0:.1f}s")

    texts = [rich_text(m) for m in movies]
    batch_size = args.batch_size
    total = len(texts)
    vectors = []

    print(f"Embedding {total} movies (batch_size={batch_size})...")
    t0 = time.time()
    for start in range(0, total, batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512)
        encoded = {k: v.to(device) for k, v in encoded.items()}
        with torch.no_grad():
            output = model(**encoded)
        hidden = output.last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        vecs = F.normalize(pooled, p=2, dim=1).detach().cpu().tolist()
        vectors.extend(vecs)
        done = min(start + batch_size, total)
        elapsed = time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        print(f"  [{done:,}/{total:,}] {elapsed:.0f}s elapsed, {eta:.0f}s remaining")

    # Write output
    for movie, vec in zip(movies, vectors):
        movie["vector"] = vec
        movie["embedding_text_mode"] = "rich"
        # Remove old bert_vector key if present (from final_boss format)
        movie.pop("bert_vector", None)
        movie.pop("svd_vector", None)
        movie.pop("genome_vector", None)

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False)
    tmp_path.replace(output_path)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nSaved to {output_path} ({size_mb:.1f} MB)")
    print(f"Total time: {time.time()-t0:.1f}s")
    print(f"Vector dim: {len(vectors[0])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
