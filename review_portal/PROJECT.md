# VIDEO MIX Review Portal

## Purpose

Client-facing review surface for rendered videos.

The client opens one page and sees playable video previews immediately. Under every video they can:

- type a comment;
- pin the current playback moment;
- record a voice comment;
- submit all selected feedback as one revision item.

There is no second-level video details page.

## Local runtime

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

## Optional local access tokens

```powershell
.\start_review_portal.ps1 `
  -MediaDir "C:\path\to\ready_reels" `
  -Token "client-secret" `
  -AdminToken "owner-secret"
```

The launcher opens the client page with the token in the URL. Open the operator page with the admin token.

## AWS runtime path

The approved first public-hosting contour is:

```text
Olga phone
  -> AWS-generated HTTPS cloudfront.net link
  -> Amazon Lightsail Distribution
  -> Lightsail Ubuntu instance
  -> nginx + FastAPI
  -> persistent instance media, SQLite and voice-note storage
```

A registered domain is not required for the first release.

Deployment artifacts:

```text
deploy/aws-lightsail/deploy.ps1
deploy/aws-lightsail/bootstrap.sh
deploy/aws-lightsail/upload-videos.ps1
deploy/aws-lightsail/update-app.ps1
deploy/aws-lightsail/validate.ps1
deploy/aws-lightsail/remove-deployment.ps1
deploy/aws-lightsail/README.md
```

Deployment command:

```powershell
pwsh .\deploy\aws-lightsail\deploy.ps1
```

This is committed deployment capability, not yet owner-validated AWS state. Real AWS resource creation and phone microphone smoke require the owner's configured AWS account.

## Storage

Local mode:

- source videos stay in the selected media directory;
- comments are stored in `data/review_portal/review_portal.db`;
- original voice recordings are stored in `data/review_portal/audio/`.

AWS MVP mode:

- source videos are stored on the persistent Lightsail instance disk;
- comments remain in SQLite on the persistent instance disk;
- original voice recordings remain on the persistent instance disk;
- scheduled snapshots or an object-storage backup are required before production dependence.

Media, database, voice files, deployment tokens and private keys must never be committed to GitHub.

## Security boundary

- default local host is `127.0.0.1`;
- `-Lan` explicitly binds to `0.0.0.0` for local-network testing;
- remote microphone access uses the AWS HTTPS distribution link;
- client and admin links use different shared-secret tokens;
- nginx and Uvicorn public access logs are disabled because tokens are carried in URLs;
- the public health endpoint does not expose internal filesystem paths;
- token access is an MVP shared-secret boundary, not a full account system.

## Current MVP boundary

Implemented application scope:

- immediate playable preview cards on the main page;
- lazy video loading;
- only one playing video at a time;
- text feedback;
- optional pinned timecode;
- browser microphone recording;
- SQLite persistence;
- original audio persistence;
- operator queue and status updates.

Implemented AWS deployment scope:

- automatic instance, static IP and distribution creation;
- AWS-generated HTTPS technical link;
- automated video upload;
- automated application updates;
- automated HTTP validation;
- explicit deployment cleanup;
- focused deployment safety tests.

Not included yet:

- automatic speech transcription;
- automatic conversion into VIDEO MIX edit commands;
- automatic video rebuilding;
- account-based authentication;
- custom domain;
- managed object/database storage.

## Next action

Run repository CI for the AWS deployment branch. Then use the owner's configured AWS account to create the real Lightsail contour, upload real MP4 files, and validate playback, timecode pinning, microphone recording, admin audio playback and status persistence on a real phone.
