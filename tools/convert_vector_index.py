"""Convert a legacy LumiTrace JSON vector file into the serving index format."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.index_format import load_index, write_matrix_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert movie_vectors.json to a compact LumiTrace index directory."
    )
    parser.add_argument("source", help="Legacy JSON file, manifest, or index directory.")
    parser.add_argument("--output", default="movie_index", help="Output index directory.")
    parser.add_argument("--model", default="", help="Embedding model used to build legacy vectors.")
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--archive", help="Optional ZIP path for remote deployment.")
    return parser.parse_args()


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def create_archive(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in sorted(source.iterdir()):
            if item.is_file():
                archive.write(item, arcname=item.name)
    temporary.replace(destination)
    digest = hashlib.sha256()
    with destination.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    output = Path(args.output)
    if not source.is_absolute():
        source = ROOT / source
    if not output.is_absolute():
        output = ROOT / output

    print(f"Loading {source}...")
    loaded = load_index(source)
    model = args.model or str(loaded.manifest.get("model") or "")
    if not model:
        raise SystemExit("The source does not record its embedding model; pass --model explicitly.")
    if source.resolve() == output.resolve() and loaded.manifest.get("format") == "lumitrace-vector-index":
        manifest_path = loaded.source
    else:
        manifest_path = write_matrix_index(
            loaded.movies,
            loaded.vectors,
            output,
            model=model,
            dtype=args.dtype,
        )
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    print(f"Created {manifest_path}")
    print(f"Movies: {manifest['count']:,}")
    print(f"Dimensions: {manifest['dimension']:,}")
    print(f"Storage dtype: {manifest['dtype']}")
    print(f"Index size: {directory_size(output) / (1024 * 1024):.1f} MB")
    if args.archive:
        archive = Path(args.archive)
        if not archive.is_absolute():
            archive = ROOT / archive
        checksum = create_archive(output, archive)
        print(f"Archive: {archive}")
        print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
