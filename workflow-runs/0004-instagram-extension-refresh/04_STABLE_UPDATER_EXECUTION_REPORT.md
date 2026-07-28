# Quick Downloader Stable Updater — Execution Report

## Status

`review-ready`

## GitHub Issue

- `#70 Add stable one-command updater for Quick Downloader`

## Owner Requirement

Reuse the proven TikTok Research Sorter pattern:

- one fixed local extension path
- one first-install command
- one update command for all later versions
- GitHub as the update source

## Stable Layout

```text
%LOCALAPPDATA%\QuickDownloader
├── extension
├── native_host
├── installer
├── config
├── dist_v2
├── INSTALL_QUICK_DOWNLOADER.cmd
├── UPDATE_QUICK_DOWNLOADER.cmd
└── REGISTER_QUICK_DOWNLOADER.cmd
```

Chrome loads the unpacked extension from:

```text
%LOCALAPPDATA%\QuickDownloader\extension
```

## Implemented Flow

### First Install

`INSTALL_QUICK_DOWNLOADER.cmd`:

1. finds Python 3
2. downloads the current `master` archive from GitHub
3. validates required extension/native-host/updater files
4. installs application files into the stable directory
5. builds the native host
6. opens the stable extension folder and `chrome://extensions`
7. accepts and saves the Chrome extension ID
8. registers the native messaging host

### Future Update

`UPDATE_QUICK_DOWNLOADER.cmd`:

1. downloads and validates the current `master`
2. atomically refreshes the application trees
3. preserves the saved extension ID and generated native-host manifest
4. leaves configuration, downloads, logs, virtual environment and unrelated local files untouched
5. rebuilds the native host with rollback protection
6. re-registers the host using the saved extension ID
7. opens `chrome://extensions` for the unpacked-extension reload

`REGISTER_QUICK_DOWNLOADER.cmd` is a recovery helper if Chrome's extension ID
was not entered during the first install.

## Safety

- ZIP paths are checked before extraction.
- The archive must contain exactly one complete Quick Downloader source tree.
- Replacement is staged and previous application targets are restored on copy failure.
- The previous built native host is restored if rebuild fails.
- Stable configuration, downloads and logs are outside replacement targets.

## Validation

- `22` focused tests passed.
- Ruff passed.
- updater source compiled successfully.
- current repository package passed updater validation.
- first install and repeated update passed in an isolated staging directory.
- saved ID, generated native-host registration, downloads and configuration preservation are covered by tests.
- `git diff --check` passed.

## Logged Validation Interruptions

1. The prior temporary pytest dependency directory had already been cleaned.
   A new isolated `/tmp/quick_downloader_test_deps` directory was installed and
   the full test set passed.
2. The sandbox rejected an attempted cleanup of a dedicated `/tmp` validation
   directory because recursive removal is restricted. No real files were changed.
   Validation was repeated in a new `mktemp` directory without deletion and passed.
3. A documentation search command used unescaped Markdown backticks, so the shell
   tried to execute `20` as a command. No files were changed. The search was rerun
   with a single-quoted pattern and completed normally.
4. GitHub CLI installation initially hit an ownership-preservation restriction
   during archive extraction. The checksum-verified archive was extracted with
   `--no-same-owner`, and GitHub CLI `2.96.0` launched successfully.
5. The container has no browser for GitHub device authentication. The official
   device-login URL and one-time code were provided to the owner; publication waits
   for that authorization.
6. The default GitHub CLI and Git configuration locations under `/root` were
   read-only. Authentication and Git credential configuration were redirected to
   dedicated writable `/tmp` paths; authenticated access for
   `oleg3479881328-code` then passed.

## Windows Review Target

1. Run `INSTALL_QUICK_DOWNLOADER.cmd`.
2. Load `%LOCALAPPDATA%\QuickDownloader\extension` once in Chrome.
3. Paste the extension ID into the installer prompt.
4. Run `%LOCALAPPDATA%\QuickDownloader\UPDATE_QUICK_DOWNLOADER.cmd`.
5. Confirm native-host rebuild/registration completes.
6. Reload Quick Downloader on `chrome://extensions` if required.
7. Validate Issue `#69`: right-click download starts immediately and the completed-file folder opens.
