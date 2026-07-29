# 26 — AWS Review Portal Deployment Report

## Status

Committed implementation. Repository CI and real AWS/phone validation remain separate gates.

## Owner decision

Continue with Amazon AWS rather than GitHub Pages.

The first public release must not require a registered domain. Olga must receive one ordinary HTTPS link and use the existing single-page review UX from her phone.

## Implemented contour

```text
Olga phone
  -> AWS-generated cloudfront.net HTTPS link
  -> Amazon Lightsail Distribution
  -> Lightsail Ubuntu instance
  -> nginx reverse proxy
  -> FastAPI review portal
  -> persistent instance media + SQLite + voice-note storage
```

## Why an instance was selected

The accepted portal currently depends on:

- local MP4 files;
- SQLite comments and statuses;
- locally stored original voice recordings.

A Lightsail instance preserves this state on a persistent disk. The Lightsail Distribution adds the technical AWS HTTPS domain required for microphone access without forcing a custom-domain decision.

A later scale pass can migrate media to object storage and comments to a managed database. That migration is not required to validate Olga's first real workflow.

## Added artifacts

- `review_portal/aws_app.py`
  - public AWS entrypoint;
  - minimal health response without internal filesystem paths.
- `review_portal/requirements.txt`
  - isolated runtime dependencies for the portal.
- `deploy/aws-lightsail/bootstrap.sh`
  - Ubuntu provisioning;
  - systemd service;
  - nginx reverse proxy;
  - persistent runtime directories;
  - privacy-safe logging configuration.
- `deploy/aws-lightsail/deploy.ps1`
  - AWS credential check;
  - automatic Ubuntu and least-cost active bundle detection;
  - instance, static IP and Distribution creation;
  - independent random client/admin tokens;
  - dynamic HTTP method and query-string forwarding;
  - AWS HTTPS client/admin link output.
- `deploy/aws-lightsail/upload-videos.ps1`
  - upload a local folder of finished videos over SSH/SCP.
- `deploy/aws-lightsail/update-app.ps1`
  - update application code without replacing runtime data.
- `deploy/aws-lightsail/validate.ps1`
  - client, admin and health HTTP checks.
- `deploy/aws-lightsail/remove-deployment.ps1`
  - explicit cleanup for billable AWS resources.
- `deploy/aws-lightsail/README.md`
  - deploy, upload, update, validate, diagnose, secure and remove instructions.
- `tests/test_review_portal_aws_deployment.py`
  - privacy-safe health response;
  - access-log suppression;
  - query-token forwarding;
  - POST/PATCH method forwarding;
  - no-cache configuration;
  - secret/private-key ignore rules.

## Security decisions

- client and admin tokens are different;
- tokens are generated locally by the deployment helper;
- secret deployment output and PEM files are gitignored;
- nginx and Uvicorn access logs are disabled because tokens are carried in URLs;
- Referrer Policy from the application remains `no-referrer`;
- the public health route returns only `{ "ok": true }`;
- Distribution caching is disabled for the dynamic portal;
- query strings are forwarded because the token is part of the shared link;
- the origin still validates tokens even if its static IP is discovered.

## Source verification

Official AWS documentation confirms:

- Lightsail distributions receive a default HTTPS `cloudfront.net` domain;
- a custom certificate is needed only when a registered custom domain is connected;
- Lightsail Distribution can forward `POST` and `PATCH` when all supported methods are enabled;
- query strings can be forwarded to the origin.

## Validation completed in this pass

- branch changes are committed separately from the base review portal;
- deployment configuration is covered by focused repository tests;
- secrets and private key artifacts are excluded from GitHub;
- existing VIDEO MIX pipeline code was not changed.

## Not yet validated

- PowerShell scripts against the owner's real AWS credentials;
- actual instance and Distribution creation;
- actual AWS technical HTTPS link;
- real video upload;
- real phone inline playback;
- real phone microphone permission and recording;
- real admin voice playback and status persistence;
- AWS billing/resource cleanup behavior.

Do not describe the AWS deployment as live until these gates pass.

## Canonical next action

1. Review and pass GitHub CI for the AWS deployment PR.
2. On the owner's Windows machine, confirm `aws sts get-caller-identity` succeeds.
3. Run `deploy/aws-lightsail/deploy.ps1`.
4. Upload real MP4 files.
5. Run automated validation.
6. Run the real phone review scenario.
7. Either accept the deployment or remove it using the cleanup helper.
