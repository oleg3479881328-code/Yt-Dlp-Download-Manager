from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, storage

client = TestClient(app)


def test_create_segment_job_stores_segment_metadata(monkeypatch) -> None:
    def fake_analyze(url: str) -> dict[str, object]:
        return {
            "url": url,
            "title": "Demo video",
            "type": "single",
            "extractor": "YouTube",
            "item_count": 1,
            "duration": 600,
            "entries": [],
            "thumbnail": None,
        }

    monkeypatch.setattr("app.main.analyze_url", fake_analyze)

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://example.com/watch?v=demo",
            "segment_start": "00:01:05",
            "segment_end": "00:01:35",
            "segment_label": "Hook",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    segment = payload["job"]["analysis_json"]["segment"]
    assert segment["start"] == 65
    assert segment["end"] == 95
    assert segment["duration"] == 30
    assert segment["label"] == "Hook"
    assert segment["section_expression"] == "*65-95"

    storage.remove_job(payload["job"]["id"])


def test_create_segment_job_rejects_invalid_range(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.analyze_url",
        lambda url: {
            "url": url,
            "title": "Demo video",
            "type": "single",
            "extractor": "YouTube",
            "item_count": 1,
            "duration": 600,
            "entries": [],
            "thumbnail": None,
        },
    )

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://example.com/watch?v=demo",
            "segment_start": "90",
            "segment_end": "60",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "end must be greater than start"


def test_create_segment_job_rejects_playlist_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.analyze_url",
        lambda url: {
            "url": url,
            "title": "Demo playlist",
            "type": "playlist",
            "extractor": "YouTube",
            "item_count": 2,
            "duration": None,
            "entries": [{"index": 1, "title": "One", "url": "https://example.com/1", "duration": 10}],
            "thumbnail": None,
        },
    )

    response = client.post(
        "/api/jobs",
        json={
            "url": "https://example.com/playlist",
            "segment_start": "00:00:10",
            "segment_duration": "30",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Segment download currently supports single videos only"
