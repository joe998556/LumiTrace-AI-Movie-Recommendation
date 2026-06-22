"""Objective held-out validation using real MovieLens user ratings.

Protocol (per user, chronological leave-out):
  - take the user's highly-rated movies (>= MIN_RATING) that exist in our index
    and are actually recommendable (vote_count>=20, has poster)
  - split chronologically: earlier = input favorites, later = held-out targets
  - query /search with user_movie_ids = input (exclude_ids = input)
  - measure whether held-out targets appear in the top-K recommendations

Reports recall@K, precision@K, NDCG@K, hit-rate over a sample of users.

Caveat: the SVD/genome item vectors were trained on MovieLens, so there is mild
optimism here; the held-out split per user still measures ranking generalization.

Usage: python tools/eval/heldout_movielens.py [--users 200] [--top-k 50] [--min-rating 4.0]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ML = ROOT / "movielens" / "ml-latest-small"
CATALOG = HERE / "catalog.json"
SEARCH_URL = "http://127.0.0.1:5001/search"


def load_recommendable_tmdb_ids() -> set[int]:
    cat = json.load(CATALOG.open(encoding="utf-8"))
    ok = set()
    for c in cat:
        if c.get("vote_count", 0) >= 20 and c.get("has_poster"):
            ok.add(int(c["id"]))
    return ok


def load_links() -> dict[int, int]:
    m = {}
    with (ML / "links.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row.get("tmdbId") or ""
            if t.strip().isdigit():
                m[int(row["movieId"])] = int(t)
    return m


def load_user_likes(min_rating: float, movie_to_tmdb: dict[int, int],
                    recommendable: set[int]) -> dict[int, list[tuple[float, int]]]:
    """userId -> chronological list of (timestamp, tmdbId) for liked, in-index, recommendable movies."""
    likes: dict[int, list[tuple[float, int]]] = defaultdict(list)
    with (ML / "ratings.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if float(row["rating"]) < min_rating:
                continue
            tmdb = movie_to_tmdb.get(int(row["movieId"]))
            if tmdb is None or tmdb not in recommendable:
                continue
            likes[int(row["userId"])].append((float(row["timestamp"]), tmdb))
    for u in likes:
        likes[u].sort()  # chronological
    return likes


def search(input_ids: list[int], top_k: int) -> list[int]:
    payload = {"user_movie_ids": input_ids, "exclude_ids": input_ids, "top_k": top_k}
    r = requests.post(SEARCH_URL, json=payload, timeout=60)
    r.raise_for_status()
    return [int(m["id"]) for m in r.json().get("results", []) if m.get("id") is not None]


def ndcg_at_k(recs: list[int], targets: set[int], k: int) -> float:
    dcg = 0.0
    for i, mid in enumerate(recs[:k]):
        if mid in targets:
            dcg += 1.0 / math.log2(i + 2)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(targets), k)))
    return dcg / ideal if ideal > 0 else 0.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=200)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--min-rating", type=float, default=4.0)
    ap.add_argument("--min-likes", type=int, default=8)
    ap.add_argument("--holdout-frac", type=float, default=0.4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    recommendable = load_recommendable_tmdb_ids()
    movie_to_tmdb = load_links()
    likes = load_user_likes(args.min_rating, movie_to_tmdb, recommendable)

    eligible = [u for u, lst in likes.items() if len(lst) >= args.min_likes]
    random.seed(args.seed)
    random.shuffle(eligible)
    sample = eligible[: args.users]
    print(f"eligible users: {len(eligible)} | evaluating: {len(sample)} | top_k={args.top_k} "
          f"| min_rating={args.min_rating} | min_likes={args.min_likes}")

    rec_sum = prec_sum = ndcg_sum = hit_sum = 0.0
    n = 0
    for u in sample:
        lst = likes[u]
        # dedupe tmdb preserving chronological order
        seen = set()
        ordered = []
        for _, t in lst:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        if len(ordered) < args.min_likes:
            continue
        n_hold = max(2, int(round(len(ordered) * args.holdout_frac)))
        inp = ordered[:-n_hold][:200]
        targets = set(ordered[-n_hold:])
        if not inp or not targets:
            continue
        try:
            recs = search(inp, args.top_k)
        except Exception as exc:
            print("  search error:", exc)
            continue
        hits = sum(1 for m in recs if m in targets)
        rec_sum += hits / len(targets)
        prec_sum += hits / args.top_k
        ndcg_sum += ndcg_at_k(recs, targets, args.top_k)
        hit_sum += 1.0 if hits > 0 else 0.0
        n += 1

    if not n:
        print("no users evaluated")
        return 1
    print(f"\nusers evaluated: {n}")
    print(f"recall@{args.top_k}:   {rec_sum/n:.4f}")
    print(f"precision@{args.top_k}:{prec_sum/n:.4f}")
    print(f"NDCG@{args.top_k}:     {ndcg_sum/n:.4f}")
    print(f"hit-rate@{args.top_k}: {hit_sum/n:.4f}  (>=1 held-out movie surfaced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
