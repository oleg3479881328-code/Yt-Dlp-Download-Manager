# Instagram Extension Refresh — Execution Report

## Status

`review-ready`

## GitHub Issue

- `#68 Fix Instagram downloads in Chrome extension for current yt-dlp`

## Root Cause

The extension used a fixed `C:\yt-dlp\yt-dlp.exe` path but did not inspect or update that executable. Site extractors can become stale when Instagram changes its responses.

The old command also forced the legacy `best` selector. The refreshed path maps that legacy setting to `bv*+ba/b`, allowing separate best video and audio streams to be merged by FFmpeg.

## Changes

- extension version raised to `0.2.0`
- automatic `yt-dlp` update check added, limited to once per 24 hours
- default update channel set to `nightly`
- manual `Обновить yt-dlp сейчас` action added
- tool diagnostics now report the installed `yt-dlp` version
- Instagram URLs use single-item mode
- downloads ignore unrelated global yt-dlp configuration
- MP4 merge/remux path made explicit
- optional `cookies-from-browser` setting added and disabled by default
- optional Chrome request impersonation added and disabled by default
- repository `yt-dlp` dependency updated to `2026.7.4`
- focused native-host tests added

## Validation

Automated:

- `9` focused tests passed
- Ruff passed
- Chrome extension JavaScript syntax checks passed
- manifest JSON validation passed

Live smoke:

- URL: `https://www.instagram.com/reels/DbOG_7gox2Q/`
- result: successful
- output container: MP4
- video: VP9, `1080x1920`
- audio: AAC
- duration: `9.172993s`
- size: `2,469,730` bytes

The live smoke used no cookies and no impersonation. Those options remain fallbacks for login/CAPTCHA/403 cases.

## Windows Review Steps

1. Rebuild the native host with `native_host\build_host.ps1`.
2. Reload the unpacked `chrome_extension` in `chrome://extensions`.
3. Re-register the native host if the extension id changed.
4. Open extension settings.
5. Click `Обновить yt-dlp сейчас`.
6. Keep `Cookies из браузера` set to `Не использовать` for the first test.
7. Download the reproduction URL.
8. Confirm the result is an MP4 with sound in `C:\yt-dlp\DOWNLOADS`.

## Known Boundary

The Windows packaged native host cannot be rebuilt or visually exercised in the Linux validation environment. Python command construction, extension scripts and the exact live Instagram download were validated.

## Follow-Up

The owner requested removal of the extra Start action from the context menu. See:

- GitHub Issue `#69`
- `03_ONE_CLICK_CONTEXT_MENU_EXECUTION_REPORT.md`
