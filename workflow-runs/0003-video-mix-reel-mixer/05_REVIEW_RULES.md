# 05_REVIEW_RULES — VIDEO MIX

Date: 2026-06-26
Status: planning

## Purpose

This file defines the minimum review and scoring rules for VIDEO MIX.

## Review Gate

Candidates must be reviewed before export.

Flow:

```text
generated -> previewed -> approved or rejected -> exported only if approved
```

## Clip Score

Each clip gets a 0-100 score.

Use simple signals first:

- image clarity;
- brightness;
- motion stability;
- duration fit;
- vertical format fit;
- duplicate penalty;
- template fit.

## Candidate Score

Each candidate Reel gets a 0-100 score.

Use simple signals first:

- average clip quality;
- template fit;
- duration fit;
- variety;
- repeated-source penalty.

## Duplicate Rule

Avoid candidates that reuse the same source too much.

## Pilot Pack Priorities

The first wedding pilot should prefer details, emotional shots, venue shots, preparation shots, backstage process and party energy.

It should penalize blurry, dark, repeated or unclear shots.

## Review UI Minimum

Show:

- candidate id;
- template name;
- duration;
- score;
- preview;
- warnings;
- approve, reject and regenerate actions.

## Export Rule

Only approved candidates should be exported.

Output naming pattern:

```text
{project_name}_{pack_id}_{template_id}_{candidate_id}.mp4
```

## Validation Metrics

Future implementation should report input count, clip count, candidate count, approved count, exported count and render failures.
