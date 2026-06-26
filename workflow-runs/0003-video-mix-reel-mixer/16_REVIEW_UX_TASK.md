# 16_REVIEW_UX_TASK — VIDEO MIX

Date: 2026-06-26
Status: ready for executor

Task: VIDEO MIX Stage 1.1 — Review UX

Purpose:

Make it easier to review generated candidate Reels before export.

This is a narrow follow-up to the accepted Stage 1 baseline.

Do not rebuild the engine.
Do not add SaaS features.
Do not add posting automation.
Do not add AI tagging.
Do not add Remotion rendering.
Do not create a full dashboard.

Required starting point:

- PR #22 is already merged.
- `video_mix/` is the accepted Stage 1 baseline.
- `14_STAGE_1_EXECUTION_REPORT.md` is the Stage 1 proof.

Goal:

After `plan`, the user should have a simple local review surface that shows candidates clearly enough to approve or reject them.

Minimum acceptable output:

1. Add a CLI command or equivalent entrypoint for review output.
2. Generate a local static review artifact inside the work directory.
3. The artifact should show every candidate with useful metadata:
   - candidate id;
   - template id;
   - status;
   - score;
   - duration;
   - warnings;
   - source clips;
   - source filenames;
   - tags if present.
4. Include clear instructions on how to approve or reject a candidate using the existing CLI.
5. Do not commit generated review files.
6. Update `.gitignore` if needed.
7. Add or update tests.
8. Add an execution report.

Preferred implementation:

- Add `python -m video_mix.cli review <work_dir>`.
- Output `reports/review.html` or `reports/review.md`.
- HTML is preferred because it is easier for the owner to scan visually.
- Keep it local and static.

Optional if easy:

- Include small thumbnails if they can be generated safely and ignored by git.
- Include links to working clips if local browser access works.
- Include a simple score/category label.

Required report:

Create `workflow-runs/0003-video-mix-reel-mixer/17_REVIEW_UX_EXECUTION_REPORT.md`.

Report must include:

- files changed;
- commands run;
- validation result;
- review artifact path;
- whether thumbnails were added;
- limitations;
- next recommendation.

Validation:

Use synthetic local media if owner media is not available.
Do not commit media, clips, exports, thumbnails, or generated review pages.

Completion rule:

Open a PR and link it in the execution Issue.

First executor comment should be a start confirmation, not a question.

Final executor comment should include PR link, report path, validation summary, limitations, and next recommendation.
