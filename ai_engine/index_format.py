"""Portable, safe vector-index storage for LumiTrace.

The legacy JSON format is intentionally supported for migration, but it is a
poor serving format: float arrays become hundreds of megabytes of text and the
whole document must be parsed before the service can start. The v1 format keeps
metadata as JSON and vectors as a NumPy array without using pickle.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


FORMAT_NAME = "lumitrace-vector-index"
FORMAT_VERSION = 1
MANIFEST_NAME = "manifest.json"
MOVIES_NAME = "movies.json"
VECTORS_NAME = "vectors.npy"

MOVIE_FIELDS = (
    "id",
    "title",
    "overview",
    "poster_path",
    "release_date",
    "vote_average",
    "vote_count",
    "genre_ids",
    "original_language",
    "collection_id",
    "embedding_text_mode",
)


@dataclass(frozen=True)
class LoadedIndex:
    movies: list[dict[str, Any]]
    vectors: np.ndarray
    manifest: dict[str, Any]
    source: Path


def close_index(index: LoadedIndex) -> None:
    """Release a memory-mapped vector file when a caller has copied its data."""
    memory_map = getattr(index.vectors, "_mmap", None)
    if memory_map is not None:
        memory_map.close()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_movie(item: dict[str, Any]) -> dict[str, Any] | None:
    movie_id = _integer(item.get("id"))
    if movie_id is None:
        return None
    genres = []
    for value in item.get("genre_ids") or []:
        parsed = _integer(value)
        if parsed is not None:
            genres.append(parsed)
    return {
        "id": movie_id,
        "title": str(item.get("title") or item.get("name") or "Untitled"),
        "overview": str(item.get("overview") or ""),
        "poster_path": str(item.get("poster_path") or ""),
        "release_date": str(item.get("release_date") or ""),
        "vote_average": _number(item.get("vote_average")),
        "vote_count": _number(item.get("vote_count")),
        "genre_ids": genres,
        "original_language": str(item.get("original_language") or "").lower(),
        "collection_id": _integer(item.get("collection_id")),
        "embedding_text_mode": str(item.get("embedding_text_mode") or "rich"),
    }


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporary, path)


def _atomic_numpy(path: Path, value: np.ndarray) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, value, allow_pickle=False)
    os.replace(temporary, path)


def write_matrix_index(
    movies: list[dict[str, Any]],
    vectors: np.ndarray,
    output_dir: Path,
    *,
    model: str,
    dtype: str = "float16",
) -> Path:
    """Write aligned movie metadata and a numeric matrix without Python lists."""
    if dtype not in {"float16", "float32"}:
        raise ValueError("dtype must be float16 or float32")
    normalized_movies = [movie for item in movies if (movie := normalize_movie(item))]
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != len(normalized_movies) or not matrix.shape[1]:
        raise ValueError("Movie metadata and vector matrix are not aligned")
    if not np.isfinite(matrix).all():
        raise ValueError("Vector matrix contains non-finite values")
    ids = [movie["id"] for movie in normalized_movies]
    if len(ids) != len(set(ids)):
        raise ValueError("Movie metadata contains duplicate IDs")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms <= 1e-12):
        raise ValueError("Vector matrix contains a zero row")
    matrix = (matrix / norms).astype(dtype, copy=False)

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "model": model,
        "count": len(normalized_movies),
        "dimension": int(matrix.shape[1]),
        "dtype": str(matrix.dtype),
        "normalized": True,
        "movies": MOVIES_NAME,
        "vectors": VECTORS_NAME,
    }
    _atomic_numpy(output_dir / VECTORS_NAME, matrix)
    _atomic_json(output_dir / MOVIES_NAME, normalized_movies)
    _atomic_json(output_dir / MANIFEST_NAME, manifest)
    return output_dir / MANIFEST_NAME


def write_index(
    records: Iterable[dict[str, Any]],
    output_dir: Path,
    *,
    model: str,
    dtype: str = "float16",
) -> Path:
    """Write records to a v1 index directory and return its manifest path."""
    if dtype not in {"float16", "float32"}:
        raise ValueError("dtype must be float16 or float32")

    movies: list[dict[str, Any]] = []
    rows: list[np.ndarray] = []
    seen_ids: set[int] = set()
    dimension = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        movie = normalize_movie(record)
        vector = record.get("vector") or record.get("embedding") or record.get("bert_vector")
        if movie is None or not isinstance(vector, (list, tuple, np.ndarray)):
            continue
        row = np.asarray(vector, dtype=np.float32)
        if row.ndim != 1 or not row.size or not np.isfinite(row).all():
            continue
        if dimension == 0:
            dimension = int(row.size)
        if row.size != dimension:
            continue
        if movie["id"] in seen_ids:
            continue
        seen_ids.add(movie["id"])
        movies.append(movie)
        rows.append(row)

    if not movies:
        raise ValueError("No valid movie vectors were provided")

    return write_matrix_index(movies, np.stack(rows), output_dir, model=model, dtype=dtype)


def _safe_child(parent: Path, value: Any) -> Path:
    name = str(value or "").strip()
    if not name or Path(name).is_absolute():
        raise ValueError("Index manifest contains an invalid file name")
    child = (parent / name).resolve()
    if parent.resolve() not in child.parents:
        raise ValueError("Index manifest path escapes its directory")
    return child


def _load_manifest(path: Path, manifest: dict[str, Any]) -> LoadedIndex:
    if manifest.get("format") != FORMAT_NAME or int(manifest.get("version", 0)) != FORMAT_VERSION:
        raise ValueError("Unsupported LumiTrace vector-index format")

    parent = path.parent.resolve()
    movies_path = _safe_child(parent, manifest.get("movies"))
    vectors_path = _safe_child(parent, manifest.get("vectors"))
    with movies_path.open("r", encoding="utf-8") as handle:
        raw_movies = json.load(handle)
    if not isinstance(raw_movies, list):
        raise ValueError("Index movie metadata must be a list")

    movies = [movie for item in raw_movies if isinstance(item, dict) if (movie := normalize_movie(item))]
    vectors = np.load(vectors_path, mmap_mode="r", allow_pickle=False)
    if vectors.ndim != 2 or vectors.dtype not in {np.dtype("float16"), np.dtype("float32")}:
        raise ValueError("Index vectors must be a two-dimensional float16 or float32 array")
    expected_count = int(manifest.get("count", -1))
    expected_dimension = int(manifest.get("dimension", -1))
    if len(movies) != vectors.shape[0] or len(movies) != expected_count:
        raise ValueError("Index movie and vector counts do not match")
    if vectors.shape[1] != expected_dimension:
        raise ValueError("Index vector dimension does not match its manifest")
    ids = [movie["id"] for movie in movies]
    if len(ids) != len(set(ids)):
        raise ValueError("Index contains duplicate movie IDs")
    return LoadedIndex(movies=movies, vectors=vectors, manifest=manifest, source=path)


def _load_legacy(path: Path, raw: Any) -> LoadedIndex:
    if isinstance(raw, dict):
        raw = raw.get("movies") or raw.get("items") or []
    if not isinstance(raw, list):
        raise ValueError("Legacy vector file must contain a list of movie records")

    movies: list[dict[str, Any]] = []
    rows: list[np.ndarray] = []
    dimension = 0
    seen_ids: set[int] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        movie = normalize_movie(item)
        vector = item.get("vector") or item.get("embedding") or item.get("bert_vector")
        if movie is None or not isinstance(vector, list) or not vector or movie["id"] in seen_ids:
            continue
        try:
            row = np.asarray(vector, dtype=np.float32)
        except (TypeError, ValueError):
            continue
        if row.ndim != 1 or not np.isfinite(row).all():
            continue
        if dimension == 0:
            dimension = int(row.size)
        if row.size != dimension:
            continue
        seen_ids.add(movie["id"])
        movies.append(movie)
        rows.append(row)
    if not movies:
        raise ValueError("No valid vectors were found in the legacy JSON file")
    vectors = np.stack(rows)
    return LoadedIndex(
        movies=movies,
        vectors=vectors,
        manifest={
            "format": "legacy-json",
            "version": 0,
            "model": "",
            "count": len(movies),
            "dimension": dimension,
            "dtype": "float32",
            "normalized": False,
        },
        source=path,
    )


def load_index(path: Path) -> LoadedIndex:
    """Load either a v1 index directory/manifest or a legacy JSON index."""
    path = path.resolve()
    if path.is_dir():
        path = path / MANIFEST_NAME
    if not path.exists():
        raise FileNotFoundError(path)
    if path.name == MANIFEST_NAME:
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if not isinstance(manifest, dict):
            raise ValueError("Index manifest must be a JSON object")
        return _load_manifest(path, manifest)

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if isinstance(raw, dict) and raw.get("format") == FORMAT_NAME:
        return _load_manifest(path, raw)
    return _load_legacy(path, raw)


def records_from_index(index: LoadedIndex) -> list[dict[str, Any]]:
    """Rebuild record dictionaries for an interrupted bootstrap run."""
    return [
        {**movie, "vector": np.asarray(index.vectors[position], dtype=np.float32).tolist()}
        for position, movie in enumerate(index.movies)
    ]
