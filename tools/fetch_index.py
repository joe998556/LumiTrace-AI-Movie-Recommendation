"""Download and verify a packaged LumiTrace vector index."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.index_format import MANIFEST_NAME, close_index, load_index  # noqa: E402


MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024


def download(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    received = 0
    with requests.get(url, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                received += len(chunk)
                if received > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError("Index download exceeds the 2 GB safety limit")
                digest.update(chunk)
                handle.write(chunk)
    return digest.hexdigest()


def safe_extract(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            mode = member.external_attr >> 16
            if member_path.is_absolute() or ".." in member_path.parts or stat.S_ISLNK(mode):
                raise RuntimeError("Index archive contains an unsafe path")
        archive.extractall(destination)


def locate_index(root: Path) -> Path:
    direct = root / MANIFEST_NAME
    if direct.exists():
        return root
    manifests = list(root.glob(f"*/{MANIFEST_NAME}"))
    if len(manifests) != 1:
        raise RuntimeError("Index archive must contain exactly one manifest.json")
    return manifests[0].parent


def fetch_index(url: str, checksum: str, output: Path) -> Path:
    output = output.resolve()
    manifest = output / MANIFEST_NAME
    if manifest.exists():
        loaded = load_index(output)
        close_index(loaded)
        print(f"Using existing vector index: {output}")
        return output
    if output.exists():
        if output.is_dir() and not any(output.iterdir()):
            output.rmdir()
        else:
            raise RuntimeError(f"Output directory exists without a valid manifest: {output}")
    expected = checksum.strip().lower()
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise RuntimeError("A valid LUMITRACE_INDEX_SHA256 is required for remote indexes")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lumitrace-index-", dir=output.parent) as temporary_name:
        temporary = Path(temporary_name)
        archive = temporary / "index.zip"
        actual = download(url, archive)
        if actual != expected:
            raise RuntimeError(f"Index checksum mismatch: expected {expected}, received {actual}")
        extracted = temporary / "extracted"
        extracted.mkdir()
        safe_extract(archive, extracted)
        source = locate_index(extracted)
        loaded = load_index(source)
        close_index(loaded)
        shutil.move(str(source), str(output))
    print(f"Downloaded and verified vector index: {output}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a verified LumiTrace index archive.")
    parser.add_argument("--url", default=os.getenv("LUMITRACE_INDEX_URL", ""))
    parser.add_argument("--sha256", default=os.getenv("LUMITRACE_INDEX_SHA256", ""))
    parser.add_argument("--output", default=os.getenv("LUMITRACE_VECTOR_FILE", "movie_index"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.url:
        print("No remote index URL configured; continuing without a downloaded index.")
        return 0
    fetch_index(args.url, args.sha256, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
