# Quick Downloader One-Click Context Menu — Execution Report

## Status

`review-ready`

## GitHub Issue

- `#69 Make context-menu download one-click and open folder on completion`

## Owner Requirement

`Right-click -> Скачать через yt-dlp -> immediate download -> automatically open the completed file folder.`

No extension page and no second Start action are allowed in this path.

## Root Cause

`chrome_extension/background.js` treated the saved `Full` mode as an instruction to open `app.html` from the context menu. That inserted a second manual Start action.

## Changes

- context menu now always starts a download immediately
- saved Mini/Full context-menu branching removed
- obsolete Work mode selector removed from popup and settings
- Full manual controls remain available through the toolbar popup
- context-menu jobs send `openFolderOnComplete=true`
- native runner opens the output folder only after successful download/post-processing
- failures do not open the output folder
- non-HTTP sources such as Instagram `blob:` video URLs are skipped in favor of the real page URL
- extension version raised to `0.2.1`

## Validation

- `13` focused tests passed
- Ruff passed
- background, popup and options JavaScript syntax checks passed
- manifest JSON validation passed
- `git diff --check` passed

Focused coverage confirms:

- context handler does not call `chrome.tabs.create`
- context handler queues the download
- context jobs carry the folder-open flag
- `blob:` is not selected as a yt-dlp source URL
- folder opening requires the explicit flag

## Logged Check Correction

The first Ruff pass reported one import-order formatting error in the new test. `ruff --fix` corrected the import block. The complete test and lint suite then passed.

## Windows Review Target

1. Reload extension `0.2.1` and rebuild the native host.
2. Right-click the Instagram page or video.
3. Choose `Скачать через yt-dlp`.
4. Confirm no extension page opens.
5. Wait for completion.
6. Confirm the output folder opens automatically.

## Follow-Up

Stable install and one-command update delivery are tracked in GitHub Issue `#70`
and `04_STABLE_UPDATER_EXECUTION_REPORT.md`.
