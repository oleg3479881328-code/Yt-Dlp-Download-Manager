from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient

from review_portal.app import create_app


def make_client(tmp_path: Path) -> tuple[TestClient, Path, Path]:
    media_dir = tmp_path / "media"
    data_dir = tmp_path / "data"
    media_dir.mkdir()
    (media_dir / "01_babushka_v1.mp4").write_bytes(b"fake-mp4")
    (media_dir / "ignore.txt").write_text("ignore", encoding="utf-8")
    app = create_app(
        media_dir=media_dir,
        data_dir=data_dir,
        review_token="client-token",
        admin_token="admin-token",
    )
    return TestClient(app), media_dir, data_dir


def test_review_page_and_video_list_require_token(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path)

    assert client.get("/").status_code == 401
    page = client.get("/?token=client-token")
    assert page.status_code == 200
    assert "Видео на согласование" in page.text

    response = client.get("/api/review/videos", headers={"X-Review-Token": "client-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["videos"][0]["filename"] == "01_babushka_v1.mp4"
    assert "path" not in payload["videos"][0]


def test_text_comment_with_timecode_appears_in_admin_queue(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path)
    videos = client.get("/api/review/videos?token=client-token").json()["videos"]

    created = client.post(
        "/api/review/comments?token=client-token",
        json={
            "video_id": videos[0]["video_id"],
            "text": "Опустить текст ниже",
            "timecode_ms": 7420,
            "author": "Ольга",
        },
    )
    assert created.status_code == 200
    assert created.json()["comment"]["status"] == "new"

    admin = client.get("/api/admin/comments?token=admin-token")
    assert admin.status_code == 200
    comment = admin.json()["comments"][0]
    assert comment["text"] == "Опустить текст ниже"
    assert comment["timecode_ms"] == 7420
    assert comment["video_name"] == "01_babushka_v1.mp4"


def test_voice_comment_is_saved_and_playable_for_admin(tmp_path: Path) -> None:
    client, _, data_dir = make_client(tmp_path)
    video = client.get("/api/review/videos?token=client-token").json()["videos"][0]
    audio_bytes = b"small-webm-voice"

    created = client.post(
        "/api/review/comments?token=client-token",
        json={
            "video_id": video["video_id"],
            "text": "",
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/webm",
        },
    )
    assert created.status_code == 200
    comment = created.json()["comment"]
    assert comment["audio_path"].endswith(".webm")
    assert (data_dir / comment["audio_path"]).read_bytes() == audio_bytes

    audio = client.get(f"/api/admin/comments/{comment['id']}/audio?token=admin-token")
    assert audio.status_code == 200
    assert audio.content == audio_bytes


def test_admin_can_update_comment_status(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path)
    video = client.get("/api/review/videos?token=client-token").json()["videos"][0]
    comment_id = client.post(
        "/api/review/comments?token=client-token",
        json={"video_id": video["video_id"], "text": "Сделать музыку тише"},
    ).json()["comment"]["id"]

    updated = client.patch(
        f"/api/admin/comments/{comment_id}/status?token=admin-token",
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["comment"]["status"] == "in_progress"


def test_comment_requires_text_or_voice(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path)
    video = client.get("/api/review/videos?token=client-token").json()["videos"][0]
    response = client.post(
        "/api/review/comments?token=client-token",
        json={"video_id": video["video_id"], "text": ""},
    )
    assert response.status_code == 400
