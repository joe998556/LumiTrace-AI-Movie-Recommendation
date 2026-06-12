"""Local setup checker for LumiTrace.

This script intentionally prints only presence/absence checks. It never prints
API key values, private service URLs, database rows, or generated vector data.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def mark(ok: bool) -> str:
    return "OK" if ok else "MISSING"


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def env_present(name: str) -> bool:
    return bool(os.getenv(name))


def main() -> int:
    checks: list[tuple[str, bool, str]] = [
        ("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0]),
        ("requirements.txt", exists("requirements.txt"), "dependency list"),
        (".env.example", exists(".env.example"), "safe env template"),
        ("app.py", exists("app.py"), "Flask backend"),
        ("ai_engine/bert_service.py", exists("ai_engine/bert_service.py"), "BERT service"),
        ("ai_engine/generate_vectors.py", exists("ai_engine/generate_vectors.py"), "vector builder"),
        ("TMDB_API_KEY", env_present("TMDB_API_KEY"), "env var presence only"),
        ("RAPID_API_KEY", env_present("RAPID_API_KEY"), "env var presence only"),
        ("REMOTE_SEARCH_URL", env_present("REMOTE_SEARCH_URL"), "env var presence only"),
        ("movie_vectors.json", exists("movie_vectors.json"), "optional generated index"),
        ("final_boss_vectors.json", exists("final_boss_vectors.json"), "optional hybrid index"),
    ]

    print("LumiTrace setup check")
    print("=" * 22)
    for label, ok, note in checks:
        print(f"{mark(ok):8} {label:28} {note}")

    required_ok = all(ok for _, ok, _ in checks[:6])
    if not required_ok:
        print("\nRequired project files are missing.")
        return 1

    print("\nRequired project files look ready.")
    if not exists("movie_vectors.json") and not exists("final_boss_vectors.json"):
        print("Recommendation service will need a generated vector file before it can return candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
