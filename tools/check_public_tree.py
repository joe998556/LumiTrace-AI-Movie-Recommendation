"""Fail CI when private or generated artifacts enter the public repository."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES = ("paper/", "research/")
FORBIDDEN_SUFFIXES = (
    ".apk",
    ".aab",
    ".db",
    ".jks",
    ".keystore",
    ".npy",
    ".npz",
    ".p12",
    ".pem",
    ".pth",
    ".pt",
    ".sqlite",
    ".sqlite3",
)
FORBIDDEN_NAMES = {".env", "movie_vectors.json"}
FORBIDDEN_TEXT = (
    "ai-blockchain.ncue.edu.tw",
    "120.107.",
    "DvSpr-",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
)
NONEMPTY_SECRET = re.compile(
    r"(?mi)^(?:TMDB_API_KEY|REMOTE_SEARCH_TOKEN|BERT_GATEWAY_TOKEN|OPENAI_API_KEY)=(?!$|YOUR_|<)[^\s#]+"
)


def repository_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted({value for value in result.stdout.decode("utf-8").split("\0") if value})


def main() -> int:
    failures: list[str] = []
    for relative in repository_files():
        normalized = relative.replace("\\", "/")
        lowered = normalized.lower()
        name = Path(normalized).name.lower()
        allowed_demo_vector = lowered == "demo_index/vectors.npy"
        if name in FORBIDDEN_NAMES or lowered.startswith(FORBIDDEN_PREFIXES) or (lowered.endswith(FORBIDDEN_SUFFIXES) and not allowed_demo_vector):
            failures.append(f"forbidden public artifact: {normalized}")
            continue
        path = ROOT / relative
        if normalized == "tools/check_public_tree.py":
            continue
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for marker in FORBIDDEN_TEXT:
            if marker.lower() in text.lower():
                failures.append(f"private marker {marker!r} in {normalized}")
        if NONEMPTY_SECRET.search(text):
            failures.append(f"non-empty secret assignment in {normalized}")

    if failures:
        print("Public-tree check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Public-tree check passed for {len(repository_files())} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
