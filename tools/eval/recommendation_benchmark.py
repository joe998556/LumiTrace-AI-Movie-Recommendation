#!/usr/bin/env python3
"""
LumiTrace Recommendation Benchmark Evaluator

Runs a set of user profiles against the BERT recommendation service,
validates results, scores quality, and produces JSON/MD reports.

Usage:
    python tools/eval/recommendation_benchmark.py [--service-url URL] [--profiles PATH] [--output-dir DIR] [--round N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from thematic_sets import build_thematic_ids

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE_URL = "http://127.0.0.1:5001/search"
DEFAULT_PROFILES = ROOT / "tools" / "eval" / "recommendation_profiles.json"
DEFAULT_OUTPUT_DIR = ROOT / "tools" / "eval" / "results"
DEFAULT_VECTOR_FILE = ROOT / "final_boss_vectors.json"

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"


# ── Scoring Rubric ────────────────────────────────────────────────

def score_recommendation(
    rec: dict[str, Any],
    profile: dict[str, Any],
    vector_ids: set[int],
    thematic_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Score a single recommendation against a profile.

    Returns a dict with per-dimension scores and a total.
    """
    rec_id = rec.get("id", 0)
    rec_genres = set(rec.get("genre_ids", []))
    rec_lang = rec.get("original_language", "")
    rec_year = int(str(rec.get("release_date", ""))[:4]) if rec.get("release_date") else 0
    rec_score = rec.get("score", 0)

    fav_genres = set(profile.get("favorite_genres", []))
    fav_langs = set(profile.get("favorite_languages", []))
    fav_years = profile.get("favorite_years", [])
    avoid_genres = set(profile.get("avoid_genres", []))
    collected_ids = set(profile.get("collected_movie_ids", []))

    scores = {}

    # 1. Existence check (0 or 1)
    scores["exists"] = 1 if rec_id in vector_ids else 0

    # 2. Not already collected (0 or 1)
    scores["not_collected"] = 0 if rec_id in collected_ids else 1

    # 3. Genre relevance (0-2) — normalized so single-genre profiles aren't penalized
    if fav_genres and rec_genres:
        overlap = len(rec_genres & fav_genres)
        # Normalize: divide by expected overlap (min of fav_genres count and 2)
        # so single-genre profiles get full credit for matching their one genre
        expected = min(len(fav_genres), 2)
        if expected > 0:
            scores["genre_relevance"] = min(2.0, (overlap / expected) * 2.0)
        else:
            scores["genre_relevance"] = 0.0
    elif not fav_genres:
        scores["genre_relevance"] = 1.0
    else:
        scores["genre_relevance"] = 0.0

    # 4. Genre mismatch penalty (0 or -1)
    if avoid_genres and rec_genres & avoid_genres:
        scores["genre_mismatch"] = -1.0
    else:
        scores["genre_mismatch"] = 0.0

    # 5. Language match (0-1)
    if fav_langs:
        scores["language_match"] = 1.0 if rec_lang in fav_langs else 0.0
    else:
        scores["language_match"] = 0.5

    # 6. Year proximity (0-1)
    if fav_years and rec_year:
        avg_year = sum(fav_years) / len(fav_years)
        distance = abs(rec_year - avg_year)
        scores["year_proximity"] = max(0.0, 1.0 - min(distance, 40) / 40)
    else:
        scores["year_proximity"] = 0.5

    # 7. Score strength (0-1)
    scores["score_strength"] = min(1.0, max(0.0, rec_score))

    # 8. Thematic relevance (0-3) — bonus for curated thematic match or strong genre+lang
    if thematic_ids is not None and rec_id in thematic_ids:
        scores["thematic_relevance"] = 3.0
    elif fav_genres and rec_genres and fav_langs and rec_lang in fav_langs:
        # Strong genre+language match even if not in curated set
        overlap = len(rec_genres & fav_genres)
        if overlap >= 2:
            scores["thematic_relevance"] = 2.0
        elif overlap >= 1:
            scores["thematic_relevance"] = 1.0
        else:
            scores["thematic_relevance"] = 0.0
    elif fav_genres and rec_genres:
        overlap = len(rec_genres & fav_genres)
        if overlap >= 2:
            scores["thematic_relevance"] = 1.5
        elif overlap >= 1:
            scores["thematic_relevance"] = 0.5
        else:
            scores["thematic_relevance"] = 0.0
    else:
        scores["thematic_relevance"] = 0.0

    total = sum(scores.values())
    scores["total"] = round(total, 2)

    return scores


def score_profile(
    profile: dict[str, Any],
    results: list[dict[str, Any]],
    vector_ids: set[int],
    thematic_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Score all recommendations for a profile."""
    scored_recs = []
    for rec in results:
        rec_scores = score_recommendation(rec, profile, vector_ids, thematic_ids)
        scored_recs.append({
            "id": rec.get("id"),
            "title": rec.get("title"),
            "score": rec.get("score"),
            "original_language": rec.get("original_language"),
            "genre_ids": rec.get("genre_ids"),
            "scores": rec_scores,
        })

    # Aggregate metrics
    totals = [r["scores"]["total"] for r in scored_recs]
    exists_count = sum(1 for r in scored_recs if r["scores"]["exists"])
    not_collected_count = sum(1 for r in scored_recs if r["scores"]["not_collected"])
    genre_rels = [r["scores"]["genre_relevance"] for r in scored_recs]
    lang_matches = [r["scores"]["language_match"] for r in scored_recs]
    genre_mismatches = sum(1 for r in scored_recs if r["scores"]["genre_mismatch"] < 0)

    # Duplicate check
    rec_ids = [r["id"] for r in scored_recs]
    duplicates = len(rec_ids) - len(set(rec_ids))

    return {
        "profile_name": profile["name"],
        "recommendation_count": len(scored_recs),
        "avg_total_score": round(sum(totals) / len(totals), 2) if totals else 0,
        "min_total_score": round(min(totals), 2) if totals else 0,
        "max_total_score": round(max(totals), 2) if totals else 0,
        "existence_rate": round(exists_count / len(scored_recs), 2) if scored_recs else 0,
        "not_collected_rate": round(not_collected_count / len(scored_recs), 2) if scored_recs else 0,
        "avg_genre_relevance": round(sum(genre_rels) / len(genre_rels), 2) if genre_rels else 0,
        "avg_language_match": round(sum(lang_matches) / len(lang_matches), 2) if lang_matches else 0,
        "genre_mismatch_count": genre_mismatches,
        "duplicate_count": duplicates,
        "recommendations": scored_recs,
    }


# ── Profile Runner ────────────────────────────────────────────────

def run_profile(
    profile: dict[str, Any],
    service_url: str,
    vector_ids: set[int],
    top_k: int = 10,
    thematic_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Run a single profile through the recommendation service and score it."""
    payload = {
        "overviews": profile.get("overviews", []),
        "exclude_ids": list(set(profile.get("collected_movie_ids", []))),
        "user_movie_ids": profile.get("collected_movie_ids", []),
        "user_genre_ids": profile.get("user_genre_ids", []),
        "playlist_genre_ids": profile.get("favorite_genres", []),
        "preferred_languages": profile.get("favorite_languages", []),
        "genre_blacklist": profile.get("avoid_genres", []),
        "top_k": top_k,
    }

    try:
        resp = requests.post(service_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
    except Exception as e:
        return {
            "profile_name": profile["name"],
            "error": str(e),
            "recommendation_count": 0,
            "avg_total_score": 0,
            "recommendations": [],
        }

    return score_profile(profile, results, vector_ids, thematic_ids)


# ── Report Generation ─────────────────────────────────────────────

def generate_json_report(
    all_results: list[dict[str, Any]],
    round_num: int,
    output_dir: Path,
) -> Path:
    """Write JSON report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "profile_count": len(all_results),
        "avg_score": round(
            sum(r.get("avg_total_score", 0) for r in all_results) / len(all_results), 2
        ) if all_results else 0,
        "min_profile": min(all_results, key=lambda r: r.get("avg_total_score", 0)),
        "max_profile": max(all_results, key=lambda r: r.get("avg_total_score", 0)),
        "total_recommendations": sum(r.get("recommendation_count", 0) for r in all_results),
        "total_genre_mismatches": sum(r.get("genre_mismatch_count", 0) for r in all_results),
        "total_duplicates": sum(r.get("duplicate_count", 0) for r in all_results),
        "profiles": all_results,
    }

    path = output_dir / f"benchmark_round_{round_num}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return path


def generate_md_report(
    all_results: list[dict[str, Any]],
    round_num: int,
    output_dir: Path,
) -> Path:
    """Write Markdown report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    avg_score = round(
        sum(r.get("avg_total_score", 0) for r in all_results) / len(all_results), 2
    ) if all_results else 0

    lines = [
        f"# Recommendation Benchmark — Round {round_num}",
        f"",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Profiles tested:** {len(all_results)}",
        f"**Average score:** {avg_score}",
        f"",
        "## Summary Table",
        "",
        "| Profile | Recs | Avg Score | Genre Rel | Lang Match | Mismatches | Duplicates |",
        "|---------|------|-----------|-----------|------------|------------|------------|",
    ]

    for r in sorted(all_results, key=lambda x: x.get("avg_total_score", 0)):
        lines.append(
            f"| {r.get('profile_name', '?')} "
            f"| {r.get('recommendation_count', 0)} "
            f"| {r.get('avg_total_score', 0)} "
            f"| {r.get('avg_genre_relevance', 0)} "
            f"| {r.get('avg_language_match', 0)} "
            f"| {r.get('genre_mismatch_count', 0)} "
            f"| {r.get('duplicate_count', 0)} |"
        )

    lines.append("")
    lines.append("## Top 3 Best Profiles")
    for r in sorted(all_results, key=lambda x: x.get("avg_total_score", 0), reverse=True)[:3]:
        lines.append(f"### {r.get('profile_name', '?')} (avg={r.get('avg_total_score', 0)})")
        for rec in r.get("recommendations", [])[:3]:
            lines.append(f"  - {rec.get('title', '?')} (score={rec.get('scores', {}).get('total', 0)})")
        lines.append("")

    lines.append("## Top 3 Worst Profiles")
    for r in sorted(all_results, key=lambda x: x.get("avg_total_score", 0))[:3]:
        lines.append(f"### {r.get('profile_name', '?')} (avg={r.get('avg_total_score', 0)})")
        for rec in r.get("recommendations", [])[:3]:
            s = rec.get("scores", {})
            issues = []
            if not s.get("exists"): issues.append("NOT_IN_INDEX")
            if not s.get("not_collected"): issues.append("ALREADY_COLLECTED")
            if s.get("genre_mismatch", 0) < 0: issues.append("GENRE_MISMATCH")
            if s.get("language_match", 1) == 0: issues.append("LANG_MISMATCH")
            issue_str = f" [{', '.join(issues)}]" if issues else ""
            lines.append(f"  - {rec.get('title', '?')} (score={s.get('total', 0)}){issue_str}")
        lines.append("")

    path = output_dir / f"benchmark_round_{round_num}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def compare_rounds(output_dir: Path, round_a: int, round_b: int) -> dict[str, Any]:
    """Compare two benchmark rounds."""
    def load_round(r: int) -> dict | None:
        path = output_dir / f"benchmark_round_{r}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    a = load_round(round_a)
    b = load_round(round_b)
    if not a or not b:
        return {"error": "Could not load both rounds"}

    comparison = {
        "round_a": round_a,
        "round_b": round_b,
        "avg_score_a": a.get("avg_score", 0),
        "avg_score_b": b.get("avg_score", 0),
        "improvement": round(b.get("avg_score", 0) - a.get("avg_score", 0), 2),
        "mismatches_a": a.get("total_genre_mismatches", 0),
        "mismatches_b": b.get("total_genre_mismatches", 0),
        "duplicates_a": a.get("total_duplicates", 0),
        "duplicates_b": b.get("total_duplicates", 0),
    }

    # Per-profile comparison
    a_by_name = {p["profile_name"]: p for p in a.get("profiles", [])}
    b_by_name = {p["profile_name"]: p for p in b.get("profiles", [])}
    profile_changes = []
    for name in set(list(a_by_name.keys()) + list(b_by_name.keys())):
        sa = a_by_name.get(name, {}).get("avg_total_score", 0)
        sb = b_by_name.get(name, {}).get("avg_total_score", 0)
        profile_changes.append({
            "profile": name,
            "score_a": sa,
            "score_b": sb,
            "change": round(sb - sa, 2),
        })
    comparison["profile_changes"] = sorted(profile_changes, key=lambda x: x["change"])

    return comparison


# ── Main ──────────────────────────────────────────────────────────

def load_vector_ids(path: Path) -> set[int]:
    """Load movie IDs from the vector file."""
    with open(path, "r", encoding="utf-8") as f:
        movies = json.load(f)
    return {m["id"] for m in movies if isinstance(m, dict) and m.get("id")}


def main():
    parser = argparse.ArgumentParser(description="LumiTrace Recommendation Benchmark")
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--compare", type=int, nargs=2, metavar=("A", "B"))
    parser.add_argument("--vector-file", default=str(DEFAULT_VECTOR_FILE))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Compare mode
    if args.compare:
        comp = compare_rounds(output_dir, args.compare[0], args.compare[1])
        print(json.dumps(comp, ensure_ascii=False, indent=2))
        return

    # Load vector IDs for existence checks
    print(f"Loading vector index from {args.vector_file}...")
    vector_ids = load_vector_ids(Path(args.vector_file))
    print(f"Loaded {len(vector_ids):,} movie IDs")

    # Load profiles
    print(f"Loading profiles from {args.profiles}...")
    with open(args.profiles, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    print(f"Loaded {len(profiles)} profiles")

    # Build thematic sets
    print("Building thematic relevance sets...")
    with open(args.vector_file, "r", encoding="utf-8") as f:
        vector_movies = json.load(f)
    thematic_sets = build_thematic_ids(vector_movies)
    print(f"Built {len(thematic_sets)} thematic sets")

    # Run each profile
    all_results = []
    for i, profile in enumerate(profiles):
        print(f"  [{i+1}/{len(profiles)}] {profile['name']}... ", end="", flush=True)
        theme_ids = thematic_sets.get(profile["name"], set())
        result = run_profile(profile, args.service_url, vector_ids, top_k=args.top_k, thematic_ids=theme_ids)
        all_results.append(result)
        avg = result.get("avg_total_score", 0)
        count = result.get("recommendation_count", 0)
        print(f"avg={avg:.2f} ({count} recs)")
        time.sleep(0.1)

    # Generate reports
    json_path = generate_json_report(all_results, args.round, output_dir)
    md_path = generate_md_report(all_results, args.round, output_dir)

    # Print summary
    avg_score = round(
        sum(r.get("avg_total_score", 0) for r in all_results) / len(all_results), 2
    ) if all_results else 0
    total_mismatches = sum(r.get("genre_mismatch_count", 0) for r in all_results)
    total_duplicates = sum(r.get("duplicate_count", 0) for r in all_results)

    print(f"\n{'='*60}")
    print(f"Round {args.round} Summary")
    print(f"{'='*60}")
    print(f"  Profiles:        {len(all_results)}")
    print(f"  Avg score:       {avg_score}")
    print(f"  Mismatches:      {total_mismatches}")
    print(f"  Duplicates:      {total_duplicates}")
    print(f"  JSON report:     {json_path}")
    print(f"  Markdown report: {md_path}")


if __name__ == "__main__":
    main()
