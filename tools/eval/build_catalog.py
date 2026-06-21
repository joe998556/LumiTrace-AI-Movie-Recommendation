"""Build a compact catalog (id/title/genres/year/lang/votes) from the big
vector file so the eval harness can resolve seed titles to real corpus IDs.

Usage: python tools/eval/build_catalog.py
Writes tools/eval/catalog.json (small).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "final_boss_vectors.json"
OUT = Path(__file__).resolve().parent / "catalog.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {SRC} ...")
    with SRC.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data):,} records")
    catalog = []
    for o in data:
        v = o.get("bert_vector") or o.get("vector")
        if not isinstance(v, list) or not v:
            continue
        mid = int(o.get("id", 0) or 0)
        if not mid:
            continue
        rd = str(o.get("release_date") or "")[:4]
        catalog.append(
            {
                "id": mid,
                "title": o.get("title") or o.get("name") or "?",
                "genre_ids": [int(g) for g in (o.get("genre_ids") or []) if str(g).isdigit()],
                "year": int(rd) if rd.isdigit() else 0,
                "lang": (o.get("original_language") or "").lower()[:2],
                "vote_average": float(o.get("vote_average") or 0),
                "vote_count": int(o.get("vote_count") or 0),
                "has_poster": bool(o.get("poster_path")),
                "has_svd": isinstance(o.get("svd_vector"), list),
                "has_genome": isinstance(o.get("genome_vector"), list),
            }
        )
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False)
    print(f"Wrote {len(catalog):,} entries to {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
