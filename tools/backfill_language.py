"""Backfill original_language into final_boss_vectors.json from movie_vectors.json.

final_boss_vectors.json carries the BERT + SVD + genome vectors but lost the
original_language field; movie_vectors.json still has it. Both share the same
TMDB id set, so we join on id and write original_language back.

Usage: python tools/backfill_language.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "final_boss_vectors.json"
SOURCE = ROOT / "movie_vectors.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading language map from {SOURCE.name} ...")
    src = json.load(SOURCE.open(encoding="utf-8"))
    lang = {}
    for o in src:
        mid = int(o.get("id", 0) or 0)
        code = (o.get("original_language") or "").lower()[:2]
        if mid and code:
            lang[mid] = code
    del src
    print(f"  languages available: {len(lang):,}")

    print(f"Loading {TARGET.name} ...")
    data = json.load(TARGET.open(encoding="utf-8"))
    patched = already = missing = 0
    for o in data:
        mid = int(o.get("id", 0) or 0)
        if o.get("original_language"):
            already += 1
            continue
        code = lang.get(mid)
        if code:
            o["original_language"] = code
            patched += 1
        else:
            missing += 1
    print(f"  patched={patched:,} already={already:,} missing={missing:,}")

    if not patched:
        print("Nothing to patch; leaving file untouched.")
        return 0

    tmp = TARGET.with_suffix(TARGET.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(TARGET)
    print(f"Wrote {TARGET} ({TARGET.stat().st_size/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
