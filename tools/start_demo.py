"""Container entry point for the one-process public demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fetch_index import fetch_index


def main() -> int:
    index_url = os.getenv("LUMITRACE_INDEX_URL", "").strip()
    index_path = Path(os.getenv("LUMITRACE_VECTOR_FILE", "movie_index"))
    if index_url:
        fetch_index(index_url, os.getenv("LUMITRACE_INDEX_SHA256", ""), index_path)
        os.environ["LUMITRACE_VECTOR_FILE"] = str(index_path)

    port = os.getenv("PORT", "7860")
    workers = os.getenv("WEB_CONCURRENCY", "1")
    command = [
        "gunicorn",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        workers,
        "--threads",
        os.getenv("GUNICORN_THREADS", "4"),
        "--timeout",
        "180",
        "--access-logfile",
        "-",
        "app:app",
    ]
    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
