from __future__ import annotations

import base64
import binascii
import hashlib
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}
MAX_AUDIO_BYTES = 15 * 1024 * 1024
COMMENT_STATUSES = {"new", "in_progress", "done", "dismissed"}
TokenQuery = Annotated[str | None, Query()]
TokenHeader = Annotated[str | None, Header(alias="X-Review-Token")]


@dataclass(frozen=True)
class PortalSettings:
    media_dir: Path
    data_dir: Path
    review_token: str
    admin_token: str

    @classmethod
    def from_environment(cls) -> PortalSettings:
        media_dir = Path(
            os.getenv("REVIEW_PORTAL_MEDIA_DIR", str(REPO_ROOT / "review_portal_media"))
        ).expanduser()
        data_dir = Path(
            os.getenv("REVIEW_PORTAL_DATA_DIR", str(REPO_ROOT / "data" / "review_portal"))
        ).expanduser()
        review_token = os.getenv("REVIEW_PORTAL_TOKEN", "").strip()
        admin_token = os.getenv("REVIEW_PORTAL_ADMIN_TOKEN", review_token).strip()
        return cls(
            media_dir=media_dir.resolve(),
            data_dir=data_dir.resolve(),
            review_token=review_token,
            admin_token=admin_token,
        )


class CommentCreateRequest(BaseModel):
    video_id: str = Field(min_length=1, max_length=128)
    text: str = Field(default="", max_length=5000)
    timecode_ms: int | None = Field(default=None, ge=0)
    audio_base64: str | None = None
    audio_mime: str | None = Field(default=None, max_length=100)
    author: str = Field(default="Ольга", min_length=1, max_length=100)


class CommentStatusRequest(BaseModel):
    status: Literal["new", "in_progress", "done", "dismissed"]


class ReviewStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.audio_dir = data_dir / "audio"
        self.db_path = data_dir / "review_portal.db"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_comments (
                    id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    video_name TEXT NOT NULL,
                    author TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    timecode_ms INTEGER,
                    audio_path TEXT,
                    audio_mime TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_comments_created_at "
                "ON review_comments(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_comments_video_id "
                "ON review_comments(video_id)"
            )

    def create_comment(
        self,
        *,
        comment_id: str,
        video_id: str,
        video_name: str,
        author: str,
        text: str,
        timecode_ms: int | None,
        audio_path: str | None,
        audio_mime: str | None,
    ) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO review_comments (
                    id, video_id, video_name, author, text, timecode_ms,
                    audio_path, audio_mime, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
                """,
                (
                    comment_id,
                    video_id,
                    video_name,
                    author,
                    text,
                    timecode_ms,
                    audio_path,
                    audio_mime,
                    now,
                    now,
                ),
            )
        return self.get_comment(comment_id)

    def get_comment(self, comment_id: str) -> dict[str, object]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM review_comments WHERE id = ?", (comment_id,)
            ).fetchone()
        if row is None:
            raise KeyError(comment_id)
        return dict(row)

    def list_comments(self, status: str | None = None) -> list[dict[str, object]]:
        if status and status not in COMMENT_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        query = "SELECT * FROM review_comments"
        params: tuple[object, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_status(self, comment_id: str, status: str) -> dict[str, object]:
        if status not in COMMENT_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE review_comments SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, comment_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(comment_id)
        return self.get_comment(comment_id)


def _stable_video_id(relative_path: str) -> str:
    return hashlib.sha256(relative_path.casefold().encode("utf-8")).hexdigest()[:24]


def _display_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip() or path.name


def _scan_videos(media_dir: Path) -> list[dict[str, object]]:
    media_dir.mkdir(parents=True, exist_ok=True)
    videos: list[dict[str, object]] = []
    for path in media_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
            continue
        resolved = path.resolve()
        if media_dir not in resolved.parents:
            continue
        relative_path = resolved.relative_to(media_dir).as_posix()
        stat = resolved.stat()
        videos.append(
            {
                "video_id": _stable_video_id(relative_path),
                "title": _display_title(resolved),
                "filename": resolved.name,
                "relative_path": relative_path,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "path": resolved,
            }
        )
    videos.sort(key=lambda item: str(item["relative_path"]).casefold())
    return videos


def _video_lookup(media_dir: Path) -> dict[str, dict[str, object]]:
    return {str(video["video_id"]): video for video in _scan_videos(media_dir)}


def _extract_token(*, query_token: str | None, header_token: str | None) -> str:
    return (header_token or query_token or "").strip()


def _require_token(provided: str, expected: str) -> None:
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing review portal token")


def _audio_extension(mime_type: str | None) -> str:
    normalized = (mime_type or "").split(";", 1)[0].strip().lower()
    return {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
    }.get(normalized, ".bin")


def _decode_audio(raw_base64: str) -> bytes:
    value = raw_base64.strip()
    if value.startswith("data:"):
        _, _, value = value.partition(",")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Voice recording is not valid base64") from exc
    if not decoded:
        raise HTTPException(status_code=400, detail="Voice recording is empty")
    if len(decoded) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Voice recording is too large")
    return decoded


def create_app(
    *,
    media_dir: Path | None = None,
    data_dir: Path | None = None,
    review_token: str | None = None,
    admin_token: str | None = None,
) -> FastAPI:
    environment = PortalSettings.from_environment()
    settings = PortalSettings(
        media_dir=(media_dir or environment.media_dir).resolve(),
        data_dir=(data_dir or environment.data_dir).resolve(),
        review_token=environment.review_token if review_token is None else review_token,
        admin_token=environment.admin_token if admin_token is None else admin_token,
    )
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    store = ReviewStore(settings.data_dir)

    application = FastAPI(title="VIDEO MIX Review Portal")
    application.state.portal_settings = settings
    application.state.review_store = store
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="review-static")

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @application.get("/", response_class=HTMLResponse)
    async def review_page(
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> HTMLResponse:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.review_token,
        )
        return HTMLResponse((TEMPLATES_DIR / "index.html").read_text(encoding="utf-8"))

    @application.get("/admin", response_class=HTMLResponse)
    async def admin_page(
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> HTMLResponse:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.admin_token,
        )
        return HTMLResponse((TEMPLATES_DIR / "admin.html").read_text(encoding="utf-8"))

    @application.get("/api/review/videos")
    async def list_videos(
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> dict[str, object]:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.review_token,
        )
        public_videos = []
        for video in _scan_videos(settings.media_dir):
            public_videos.append({key: value for key, value in video.items() if key != "path"})
        return {"videos": public_videos, "count": len(public_videos)}

    @application.get("/api/review/videos/{video_id}/stream")
    async def stream_video(
        video_id: str,
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> FileResponse:
        provided = _extract_token(query_token=token, header_token=x_review_token)
        if settings.review_token and provided not in {settings.review_token, settings.admin_token}:
            raise HTTPException(status_code=401, detail="Invalid or missing review portal token")
        video = _video_lookup(settings.media_dir).get(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(
            path=Path(str(video["path"])),
            media_type="video/mp4" if str(video["filename"]).lower().endswith(".mp4") else None,
        )

    @application.post("/api/review/comments")
    async def create_comment(
        payload: CommentCreateRequest,
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> dict[str, object]:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.review_token,
        )
        video = _video_lookup(settings.media_dir).get(payload.video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video not found")

        normalized_text = payload.text.strip()
        if not normalized_text and not payload.audio_base64:
            raise HTTPException(status_code=400, detail="Add a written or voice comment")

        comment_id = str(uuid.uuid4())
        audio_relative_path: str | None = None
        audio_bytes: bytes | None = None
        if payload.audio_base64:
            audio_bytes = _decode_audio(payload.audio_base64)
            extension = _audio_extension(payload.audio_mime)
            audio_filename = f"{comment_id}{extension}"
            audio_path = (store.audio_dir / audio_filename).resolve()
            if store.audio_dir.resolve() not in audio_path.parents:
                raise HTTPException(status_code=400, detail="Invalid audio path")
            audio_path.write_bytes(audio_bytes)
            audio_relative_path = audio_path.relative_to(settings.data_dir).as_posix()

        try:
            comment = store.create_comment(
                comment_id=comment_id,
                video_id=payload.video_id,
                video_name=str(video["filename"]),
                author=payload.author.strip(),
                text=normalized_text,
                timecode_ms=payload.timecode_ms,
                audio_path=audio_relative_path,
                audio_mime=payload.audio_mime if audio_bytes else None,
            )
        except Exception:
            if audio_relative_path:
                (settings.data_dir / audio_relative_path).unlink(missing_ok=True)
            raise
        return {"ok": True, "comment": comment}

    @application.get("/api/admin/comments")
    async def admin_comments(
        status: str | None = Query(default=None),
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> dict[str, object]:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.admin_token,
        )
        try:
            comments = store.list_comments(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"comments": comments, "count": len(comments)}

    @application.get("/api/admin/comments/{comment_id}/audio")
    async def admin_comment_audio(
        comment_id: str,
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> FileResponse:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.admin_token,
        )
        try:
            comment = store.get_comment(comment_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Comment not found") from exc
        relative_audio_path = comment.get("audio_path")
        if not relative_audio_path:
            raise HTTPException(status_code=404, detail="Comment has no voice recording")
        audio_path = (settings.data_dir / str(relative_audio_path)).resolve()
        if settings.data_dir not in audio_path.parents or not audio_path.is_file():
            raise HTTPException(status_code=404, detail="Voice recording not found")
        return FileResponse(
            audio_path,
            filename=audio_path.name,
            media_type=str(comment.get("audio_mime") or "application/octet-stream"),
        )

    @application.patch("/api/admin/comments/{comment_id}/status")
    async def update_comment_status(
        comment_id: str,
        payload: CommentStatusRequest,
        token: TokenQuery = None,
        x_review_token: TokenHeader = None,
    ) -> dict[str, object]:
        _require_token(
            _extract_token(query_token=token, header_token=x_review_token),
            settings.admin_token,
        )
        try:
            comment = store.update_status(comment_id, payload.status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Comment not found") from exc
        return {"ok": True, "comment": comment}

    @application.get("/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "media_dir": str(settings.media_dir),
            "video_count": len(_scan_videos(settings.media_dir)),
        }

    return application


app = create_app()
