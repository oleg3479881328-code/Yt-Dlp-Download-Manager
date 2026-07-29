# VIDEO MIX Review Portal

## Purpose

Client-facing review surface for rendered videos.

The client opens one page and sees playable video previews immediately. Under every video they can:

- type a comment;
- pin the current playback moment;
- record a voice comment;
- submit all selected feedback as one revision item.

There is no second-level video details page.

## Runtime

```powershell
.\start_review_portal.ps1 -MediaDir "C:\path\to\ready_reels"
```

Client page:

```text
http://127.0.0.1:8770/
```

Operator page:

```text
http://127.0.0.1:8770/admin
```

## Optional access tokens

```powershell
.\start_review_portal.ps1 `
  -MediaDir "C:\path\to\ready_reels" `
  -Token "client-secret" `
  -AdminToken "owner-secret"
```

The launcher opens the client page with the token in the URL. Open the operator page with the admin token.

## Storage

- source videos stay in the selected media directory;
- comments are stored in `data/review_portal/review_portal.db`;
- original voice recordings are stored in `data/review_portal/audio/`;
- media, database and voice files must never be committed to GitHub.

## Security boundary

- default host is `127.0.0.1`;
- `-Lan` explicitly binds to `0.0.0.0` for local-network testing;
- remote microphone access requires HTTPS;
- public deployment, domain and reverse proxy are a separate validated step;
- token access is an MVP shared-secret boundary, not a full account system.

## Current MVP boundary

Implemented scope:

- immediate playable preview cards on the main page;
- lazy video loading;
- only one playing video at a time;
- text feedback;
- optional pinned timecode;
- browser microphone recording;
- SQLite persistence;
- original audio persistence;
- operator queue and status updates.

Not included yet:

- automatic speech transcription;
- automatic conversion into VIDEO MIX edit commands;
- automatic video rebuilding;
- public hosting and production authentication.

## Next action

Run the local smoke scenario on Windows with real MP4 files and Chrome, then validate microphone permission, timecode capture, audio playback and operator status updates.
