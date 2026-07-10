from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from ai_engine import bert_service
from ai_engine.index_format import load_index, write_index
from tools.fetch_index import safe_extract


ROOT = Path(__file__).resolve().parents[1]


def sample_records():
    return [
        {
            "id": 1,
            "title": "Seed",
            "poster_path": "/seed.jpg",
            "vote_average": 8.0,
            "vote_count": 1000,
            "genre_ids": [878],
            "vector": [1.0, 0.0],
        },
        {
            "id": 2,
            "title": "Close Match",
            "poster_path": "/match.jpg",
            "vote_average": 7.8,
            "vote_count": 900,
            "genre_ids": [878],
            "vector": [0.99, 0.1],
        },
        {
            "id": 3,
            "title": "Different Taste",
            "poster_path": "/different.jpg",
            "vote_average": 7.5,
            "vote_count": 800,
            "genre_ids": [35],
            "vector": [0.0, 1.0],
        },
    ]


def test_compact_index_round_trip(tmp_path):
    manifest_path = write_index(
        sample_records(),
        tmp_path / "movie_index",
        model="test/tiny-model",
        dtype="float16",
    )
    loaded = load_index(manifest_path.parent)

    assert loaded.manifest["format"] == "lumitrace-vector-index"
    assert loaded.manifest["count"] == 3
    assert loaded.vectors.shape == (3, 2)
    assert loaded.vectors.dtype == np.float16
    assert [movie["id"] for movie in loaded.movies] == [1, 2, 3]
    with manifest_path.open("r", encoding="utf-8") as handle:
        assert json.load(handle)["model"] == "test/tiny-model"


def test_bundled_demo_index_is_loadable_and_attributed():
    loaded = load_index(ROOT / "demo_index")

    assert loaded.manifest["count"] == 1000
    assert loaded.manifest["dimension"] == 384
    assert loaded.manifest["model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert loaded.manifest["dataset"] == "MovieLens Latest Small"
    assert loaded.manifest["data_license"] == "MOVIELENS_README.txt"
    assert loaded.vectors.shape == (1000, 384)
    assert (ROOT / "demo_index" / loaded.manifest["data_license"]).is_file()


def test_id_rating_recommendation_does_not_load_text_model(tmp_path, monkeypatch):
    index_dir = tmp_path / "movie_index"
    write_index(sample_records(), index_dir, model="test/tiny-model", dtype="float16")
    for name, value in {
        "MODEL": None,
        "TOKENIZER": None,
        "DEVICE": None,
        "VECTOR_TENSOR": None,
        "MOVIES": [],
        "INDEX_BY_ID": {},
        "INDEX_INFO": {},
        "VECTOR_PATH": None,
        "GATEWAY_TOKEN": "",
    }.items():
        monkeypatch.setattr(bert_service, name, value)

    bert_service.initialize(
        index_dir,
        device_name="cpu",
        text_search="disabled",
    )
    client = bert_service.app.test_client()
    response = client.post(
        "/v1/recommend",
        json={
            "items": [{"tmdb_id": 1, "rating": 9, "genre_ids": [878]}],
            "exclude_ids": [1],
            "top_k": 2,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["results"][0]["id"] == 2
    assert data["taste_profile"]["mode"] == "precomputed_vector"
    assert bert_service.MODEL is None

    text_only = client.post("/v1/recommend", json={"overviews": ["quiet science fiction"]})
    assert text_only.status_code == 409
    assert client.post("/reload").status_code == 403
    assert client.post("/embed", json={"texts": ["test"]}).status_code == 403


def test_index_archive_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "not allowed")
    with pytest.raises(RuntimeError, match="unsafe path"):
        safe_extract(archive_path, tmp_path / "output")
