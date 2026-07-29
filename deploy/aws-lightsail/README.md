# VIDEO MIX Review Portal — AWS without a custom domain

## Result

This deployment creates a permanently available review portal on Amazon AWS.

Olga receives one client HTTPS link such as:

```text
https://xxxxxxxxxxxx.cloudfront.net/?token=<client-token>
```

The owner receives a separate admin HTTPS link:

```text
https://xxxxxxxxxxxx.cloudfront.net/admin?token=<admin-token>
```

No registered domain is required for this first release.

## Architecture

```text
Phone / browser
      |
      | HTTPS, AWS-generated cloudfront.net address
      v
Amazon Lightsail Distribution
      |
      | HTTP origin connection
      v
Amazon Lightsail Ubuntu instance
      |
      +-- nginx :80
      +-- FastAPI review portal :8770
      +-- /srv/video-review-portal/media
      +-- /srv/video-review-portal/data/review_portal.db
      +-- /srv/video-review-portal/data/audio
```

The distribution is configured to:

- use the AWS default HTTPS certificate and technical domain;
- forward query strings, including the client/admin token;
- forward `GET`, `HEAD`, `OPTIONS`, `PUT`, `PATCH`, `POST`, and `DELETE` because the portal uses `POST` for comments and `PATCH` for statuses;
- use zero cache TTL for the dynamic portal;
- keep the current single-page video-card UX unchanged.

## Why this contour

The current portal is intentionally a simple FastAPI + SQLite application. A Lightsail instance gives it a persistent disk and a continuously running process. The AWS distribution gives the public HTTPS address needed for phone microphone access without requiring a domain.

This pass does not move the application to an ephemeral container filesystem.

## Prerequisites

On the owner's Windows computer:

1. AWS account with permission to create Lightsail instances, static IPs, and distributions.
2. AWS CLI v2 installed and configured.
3. PowerShell 7.
4. OpenSSH Client (`ssh` and `scp`).
5. `tar`, included with current Windows 11 installations.

Verify AWS access:

```powershell
aws sts get-caller-identity
```

## Deploy

From the repository root:

```powershell
pwsh .\deploy\aws-lightsail\deploy.ps1
```

Defaults:

- origin region: `us-east-2`;
- availability zone: `us-east-2a`;
- instance bundle: `nano_3_0`;
- newest active Ubuntu blueprint detected automatically;
- least expensive active distribution bundle detected automatically;
- random independent client and admin tokens generated automatically;
- repository branch: `feature/review-portal-aws` during review.

The script creates:

- Lightsail Ubuntu instance;
- static IP;
- port 80 origin access;
- systemd service for FastAPI;
- nginx reverse proxy;
- Lightsail distribution with an AWS HTTPS address;
- local `deployment-output.json` containing the two final links and tokens.

Example with explicit names and AWS profile:

```powershell
pwsh .\deploy\aws-lightsail\deploy.ps1 `
  -Profile default `
  -Region us-east-2 `
  -InstanceName olga-review-portal `
  -StaticIpName olga-review-portal-ip `
  -DistributionName olga-review-portal-web
```

## Upload finished videos

```powershell
pwsh .\deploy\aws-lightsail\upload-videos.ps1 `
  -SourceDir "C:\VIDEO MIX\Ready for Olga"
```

By default, the server media folder is replaced with the selected local folder.

To keep existing files and add or overwrite only matching names:

```powershell
pwsh .\deploy\aws-lightsail\upload-videos.ps1 `
  -SourceDir "C:\VIDEO MIX\Ready for Olga" `
  -KeepExisting
```

The portal scans its media directory on each video-list request, so an application restart is not required after upload.

## Validate

```powershell
pwsh .\deploy\aws-lightsail\validate.ps1
```

Automated validation checks:

- client page returns HTTP 200;
- admin page returns HTTP 200;
- health endpoint is healthy.

Required manual phone gate:

1. Open the client link on Olga's phone.
2. Play a video directly in the main-page card.
3. Pause and press the pin button.
4. Type a comment.
5. Grant microphone permission and record a voice comment.
6. Submit.
7. Open the admin link.
8. Confirm text, timecode, and voice playback.
9. Change the status and reload the page.

The system is not owner-validated until this real phone gate passes.

## Server diagnostics

Connect with the Lightsail browser SSH terminal or an SSH client, then use:

```bash
sudo systemctl status video-review-portal --no-pager
sudo journalctl -u video-review-portal -n 200 --no-pager
sudo nginx -t
curl http://127.0.0.1/health
cat /var/log/video-review-portal-bootstrap.log
```

Runtime locations:

```text
Application: /opt/video-review-portal
Videos:      /srv/video-review-portal/media
Database:    /srv/video-review-portal/data/review_portal.db
Voice notes: /srv/video-review-portal/data/audio
Secrets:     /etc/video-review-portal.env
```

## Security rules

- Share only the client link with Olga.
- Never share the admin link or `deployment-output.json`.
- Client and admin tokens are different by default.
- Both pages remain protected even if someone discovers the technical AWS domain.
- The origin IP still requires a valid token; the final user-facing link must use HTTPS through the distribution.
- Rotate tokens by editing `/etc/video-review-portal.env` and restarting the service.

```bash
sudo nano /etc/video-review-portal.env
sudo systemctl restart video-review-portal
```

## Persistence and backup boundary

The Lightsail instance disk is persistent across ordinary application restarts and instance reboots. It is still a single-server MVP.

Before production dependence, add scheduled instance snapshots or an object-storage backup of:

```text
/srv/video-review-portal/data
/srv/video-review-portal/media
```

A later scale pass can move videos and voice files to object storage and comments to a managed database. That is not required for the first validated Olga workflow.

## Custom domain later

After the workflow is accepted, a registered domain can be connected without changing the application UX. For example:

```text
https://review.olgapolo.com
```

The first release intentionally uses the generated AWS HTTPS address so domain registration does not block testing.
