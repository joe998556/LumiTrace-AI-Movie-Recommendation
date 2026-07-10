from __future__ import annotations

import pytest

import app as app_module
from ai_engine import bert_service as bert_service_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "FAVORITES_DB", str(tmp_path / "favorites.db"))
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def test_health(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    data = health.get_json()
    assert data["status"] == "ok"
    assert data["mode"] == "public-demo"
    assert "tmdb_env_key" in data["integrations"]
    assert data["integrations"]["remote_search_locked"] is True


def test_static_route_does_not_serve_private_files(client):
    assert client.get("/.env").status_code == 404
    assert client.get("/app.py").status_code == 404
    assert client.get("/lumitrace_favorites.db").status_code == 404


def test_favorites_sync_round_trip(client):
    sync_id = "a" * 64
    payload = {
        "favorites": [
            {"id": 329865, "title": "Arrival", "rating": 9.0},
        ],
        "updated_at": 123,
    }

    write = client.post("/api/favorites", headers={"X-Sync-Id": sync_id}, json=payload)
    assert write.status_code == 200
    assert write.get_json()["ok"] is True

    read = client.get("/api/favorites", headers={"X-Sync-Id": sync_id})
    assert read.status_code == 200
    assert read.get_json()["payload"] == payload


def test_favorites_rejects_invalid_sync_id(client):
    response = client.get("/api/favorites", headers={"X-Sync-Id": "not-a-sha"})
    assert response.status_code == 400


def test_tiny_semantic_proxy_sanitizes_payload(client, monkeypatch):
    captured = {}

    class FakeResponse:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"results": [{"id": 1, "title": "Synthetic Match"}]}

    def fake_post(url, json=None, timeout=None, verify=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        captured["verify"] = verify
        return FakeResponse()

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module, "LOCK_REMOTE_SEARCH_URL", False)
    monkeypatch.setattr(app_module, "REMOTE_SEARCH_URL", "")

    payload = {
        "remote_search_url": "http://127.0.0.1:5001/search",
        "overviews": ["Quiet philosophical science fiction."],
        "exclude_ids": ["329865", "bad"],
        "user_movie_ids": ["329865", 157336, "oops"],
        "user_genre_ids": [[878, "18", "bad"], "skip"],
        "user_vote_counts": [12, 0, 8.5, "bad"],
        "user_release_years": ["2016-11-11", "nope", 2014],
        "playlist_genre_ids": [9648, "53"],
        "preferred_languages": ["EN-US", "de", "english", "de"],
        "llm": {
            "api_url": "https://api.openai.com/v1",
            "api_key": "user-owned-key",
            "model": "gpt-test",
        },
        "top_k": 999,
    }

    response = client.post("/api/semantic-recommendations", json=payload)
    assert response.status_code == 200
    assert response.get_json()["results"][0]["title"] == "Synthetic Match"

    forwarded = captured["json"]
    assert captured["url"] == "http://127.0.0.1:5001/search"
    assert forwarded["exclude_ids"] == [329865]
    assert forwarded["user_movie_ids"] == [329865, 157336]
    assert forwarded["user_genre_ids"] == [[878, 18], []]
    assert forwarded["user_vote_counts"] == [10.0, 1.0, 8.5]
    assert forwarded["user_release_years"] == [2016, 2014]
    assert forwarded["playlist_genre_ids"] == [9648, 53]
    assert forwarded["preferred_languages"] == ["en", "de"]
    assert forwarded["top_k"] == 30
    assert forwarded["llm"]["api_url"] == "https://api.openai.com/v1"
    assert forwarded["llm"]["model"] == "gpt-test"


def test_semantic_proxy_ignores_browser_target_when_locked(client, monkeypatch):
    captured = {}

    class FakeResponse:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"results": []}

    def fake_post(url, json=None, timeout=None, verify=None):
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module, "LOCK_REMOTE_SEARCH_URL", True)
    monkeypatch.setattr(app_module, "REMOTE_SEARCH_URL", "https://configured.example/search")

    response = client.post(
        "/api/semantic-recommendations",
        json={
            "remote_search_url": "http://127.0.0.1:5001/search",
            "overviews": ["A calm mystery."],
        },
    )

    assert response.status_code == 200
    assert captured["url"] == "https://configured.example/search"


def test_semantic_proxy_requires_signal(client, monkeypatch):
    monkeypatch.setattr(app_module, "LOCK_REMOTE_SEARCH_URL", True)
    monkeypatch.setattr(app_module, "REMOTE_SEARCH_URL", "https://configured.example/search")
    response = client.post(
        "/api/semantic-recommendations",
        json={"remote_search_url": "http://127.0.0.1:5001/search"},
    )
    assert response.status_code == 400


def test_neutral_rating_does_not_add_genre_weight():
    weights = bert_service_module.weighted_genres([[878], [18]], [5.0, 9.0])
    assert 878 not in weights
    assert weights[18] > 0


def test_private_llm_target_is_blocked_by_default(monkeypatch):
    monkeypatch.setattr(bert_service_module, "ALLOW_PRIVATE_LLM", False)
    assert bert_service_module.normalize_llm_url("http://127.0.0.1:11434/v1") is None
