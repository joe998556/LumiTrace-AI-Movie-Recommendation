"""Deterministic recommender eval harness.

Runs every taste profile through the live BERT service on BOTH paths
(collection = favorites, prompt = zero-shot text) and scores the output
against the profile rubric. Prints a scorecard and writes per-profile JSON
artifacts to tools/eval/out/ for agent spot-checks.

Usage:
    python tools/eval/run_eval.py            # both paths
    python tools/eval/run_eval.py --path collection
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOG = HERE / "catalog.json"
PROFILES = HERE / "profiles.json"
OUT = HERE / "out"
SEARCH_URL = "http://127.0.0.1:5001/search"

GN = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
      99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
      27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "SciFi",
      10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"}


def names(ids):
    return [GN.get(int(g), str(g)) for g in ids]


def load_catalog():
    data = json.load(CATALOG.open(encoding="utf-8"))
    return {c["id"]: c for c in data}


def call_search(payload):
    r = requests.post(SEARCH_URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def result_year(m):
    rd = str(m.get("release_date") or "")[:4]
    return int(rd) if rd.isdigit() else 0


def score_list(results, profile, penalize_leak=True):
    n = len(results)
    expected = set(profile.get("expected_genres", []))
    redflags = set(profile.get("red_flag_genres", []))
    if not n:
        return {"n": 0, "score": 0, "coherence": 0, "red_flag_rate": 0, "dups": 0,
                "leak": 0, "bad_quality": 0, "distinct_genres": 0, "top_dominance": 0,
                "distinct_langs": 0, "lang_share": None, "era_share": None}

    seeds = set(profile.get("seed_ids", []))
    coh = redf = 0
    genre_counts = {}
    langs = {}
    ids_seen = {}
    titles_seen = {}
    bad_quality = leak = obscure = 0
    lang_hits = era_hits = 0
    lang_hint = profile.get("lang_hint")
    max_year = profile.get("max_year")

    for m in results:
        g = set(int(x) for x in m.get("genre_ids", []) if str(x).isdigit())
        if g & expected:
            coh += 1
        if g & redflags:
            redf += 1
        for x in g:
            genre_counts[x] = genre_counts.get(x, 0) + 1
        lg = (m.get("original_language") or "").lower()[:2]
        langs[lg] = langs.get(lg, 0) + 1
        mid = m.get("id")
        ids_seen[mid] = ids_seen.get(mid, 0) + 1
        t = (m.get("title") or "").strip().lower()
        titles_seen[t] = titles_seen.get(t, 0) + 1
        vc = int(m.get("vote_count") or 0)
        if vc < 20 or not m.get("poster_path"):
            bad_quality += 1
        if vc < 200:
            obscure += 1
        if mid in seeds:
            leak += 1
        if lang_hint and lg == lang_hint:
            lang_hits += 1
        y = result_year(m)
        if max_year and y and y <= max_year:
            era_hits += 1

    dups = sum(v - 1 for v in ids_seen.values() if v > 1) + \
        sum(v - 1 for v in titles_seen.values() if v > 1)
    coherence = coh / n
    red_flag_rate = redf / n
    top_dominance = max(genre_counts.values()) / n if genre_counts else 0
    lang_share = (lang_hits / n) if lang_hint else None
    era_share = (era_hits / n) if max_year else None

    # Composite 0-100
    score = coherence * 100
    score -= red_flag_rate * 40
    score -= dups * 5
    if penalize_leak:
        score -= leak * 10
    score -= bad_quality * 5
    score -= (obscure / n) * 15
    if lang_share is not None:
        need = profile.get("min_lang_share", 0.4)
        if lang_share < need:
            score -= (need - lang_share) * 60
    if era_share is not None:
        need = profile.get("min_era_share", 0.4)
        if era_share < need:
            score -= (need - era_share) * 60
    # diversity: punish if a single genre dominates almost everything
    if top_dominance > 0.85 and len(expected) > 1:
        score -= (top_dominance - 0.85) * 60
    score = max(0, min(100, round(score)))

    return {"n": n, "score": score, "coherence": round(coherence, 2),
            "red_flag_rate": round(red_flag_rate, 2), "dups": dups, "leak": leak,
            "obscure_rate": round(obscure / n, 2),
            "bad_quality": bad_quality, "distinct_genres": len(genre_counts),
            "top_dominance": round(top_dominance, 2), "distinct_langs": len(langs),
            "lang_share": None if lang_share is None else round(lang_share, 2),
            "era_share": None if era_share is None else round(era_share, 2)}


def artifact_rows(results):
    rows = []
    for i, m in enumerate(results, 1):
        rows.append({
            "rank": i, "id": m.get("id"), "title": m.get("title"),
            "year": result_year(m), "lang": (m.get("original_language") or "")[:2],
            "genres": names(m.get("genre_ids", [])),
            "score": m.get("score"), "semantic": m.get("semantic_score"),
            "svd": m.get("svd_score"), "genome": m.get("genome_score"),
            "off_profile_penalty": m.get("off_profile_penalty"),
        })
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", choices=["collection", "prompt", "both"], default="both")
    ap.add_argument("--top-k", type=int, default=18)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    cat = load_catalog()
    profiles = json.load(PROFILES.open(encoding="utf-8"))

    paths = ["collection", "prompt"] if args.path == "both" else [args.path]
    print(f"{'profile':18s} {'path':11s} {'n':>2} {'score':>5} {'coher':>5} {'redflag':>7} "
          f"{'dup':>3} {'leak':>4} {'divG':>4} {'dom':>4} {'extra'}")
    print("-" * 92)
    summary = {}
    for p in profiles:
        rec = {"label": p["label"], "prompt": p["prompt"],
               "expected_genres": names(p.get("expected_genres", [])),
               "red_flag_genres": names(p.get("red_flag_genres", [])),
               "notes": p.get("notes", ""), "results": {}}
        for path in paths:
            if path == "collection":
                seeds = [s for s in p["seed_ids"] if s in cat]
                payload = {
                    "user_movie_ids": seeds,
                    "exclude_ids": seeds,
                    "user_genre_ids": [cat[s]["genre_ids"] for s in seeds],
                    "user_vote_counts": [8] * len(seeds),
                    "user_release_years": [cat[s]["year"] for s in seeds if cat[s]["year"]],
                    "top_k": args.top_k,
                }
            else:
                payload = {"overviews": [p["prompt"]], "top_k": args.top_k}
            try:
                resp = call_search(payload)
                results = resp.get("results", [])
            except Exception as exc:
                print(f"{p['key']:18s} {path:11s} ERROR {exc}")
                continue
            m = score_list(results, p, penalize_leak=(path == "collection"))
            extra = f"obsc={m['obscure_rate']} "
            if m["lang_share"] is not None:
                extra += f"lang%={m['lang_share']} "
            if m["era_share"] is not None:
                extra += f"era%={m['era_share']} "
            print(f"{p['key']:18s} {path:11s} {m['n']:>2} {m['score']:>5} {m['coherence']:>5} "
                  f"{m['red_flag_rate']:>7} {m['dups']:>3} {m['leak']:>4} {m['distinct_genres']:>4} "
                  f"{m['top_dominance']:>4} {extra}")
            rec["results"][path] = {"metrics": m, "rows": artifact_rows(results)}
            summary.setdefault(path, []).append(m["score"])
        (OUT / f"{p['key']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-" * 92)
    for path, scores in summary.items():
        print(f"AVG {path:11s} {round(sum(scores)/len(scores),1)}  (per-profile: {scores})")


if __name__ == "__main__":
    raise SystemExit(main())
