# VIDEO MIX Review Portal — Implementation Report

## Owner decision

Build a client review page where videos are immediately playable on the main page. Do not require opening a separate video details page.

Under each video provide:

- written feedback;
- a pin that captures the current playback time;
- microphone recording;
- one submit action.

## Implemented branch

```text
feature/video-review-portal
```

Tracked by Issue `#72`.

## Implemented scope

### Client page

- all discovered MP4, MOV, WebM and M4V videos are displayed as playable cards on one page;
- no second-level video page exists;
- video files load lazily as the client scrolls;
- starting one video pauses the others;
- each card includes a text field;
- the pin captures the current player time in milliseconds;
- browser MediaRecorder captures an original voice comment;
- text, optional timecode and optional voice recording are submitted together;
- microphone availability is explained when the page is not running on HTTPS or localhost.

### Operator page

- comments appear in reverse chronological order;
- every item includes the source video name, author, written feedback and optional timecode;
- original voice comments are playable inline;
- statuses: `new`, `in_progress`, `done`, `dismissed`;
- status filtering and updates are available.

### Backend and storage

- standalone FastAPI module inside the existing repository;
- source videos remain in the selected local media folder;
- SQLite stores comments and workflow status;
- original voice recordings stay in local data storage;
- local paths are never returned by the public video-list API;
- video IDs are stable hashes of relative paths;
- symlink/path escape candidates outside the media root are ignored;
- optional client and admin shared-secret tokens;
- security headers and a 15 MB voice-recording limit;
- media is served inline for browser playback rather than as download attachments.

### Windows entrypoint

```powershell
.\start_review_portal.ps1 -MediaDir "C:\path\to\ready_reels"
```

Default binding is loopback. `-Lan` is an explicit local-network test mode.

## Local validation performed

```text
python -m pytest -q
5 passed

python -m compileall -q review_portal tests
passed

node --check review_portal/static/app.js
passed

node --check review_portal/static/admin.js
passed
```

Tests cover:

- access-token boundary;
- video discovery;
- inline video streaming;
- text feedback with timecode;
- voice-file persistence and inline playback;
- operator status changes;
- rejection of empty feedback.

Ruff was not available in the isolated execution environment, so repository CI or the normal project environment must run the canonical Ruff check.

## Not yet validated

- real Windows Chrome microphone permission;
- real MP4 seek/range behavior with production files;
- full mobile visual smoke;
- public HTTPS access from Olga's phone;
- reverse proxy, domain and production authentication.

## Explicitly deferred

- automatic speech-to-text;
- automatic conversion of feedback into edit-plan operations;
- automatic VIDEO MIX rebuild;
- public deployment;
- account system.

## Next action

Run the branch on the owner's Windows machine with several real rendered Reels. Validate one complete scenario:

```text
open main page
→ play a video in place
→ pause at a specific moment
→ pin the timecode
→ type feedback
→ record voice
→ submit
→ open /admin
→ play the voice recording
→ change status to in_progress
```
