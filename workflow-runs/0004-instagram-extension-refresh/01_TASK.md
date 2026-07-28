# Instagram Extension Refresh — Execution Task

## Authorization

- Owner request: update the existing downloader extension so Instagram works in the current environment.
- GitHub coordination issue: `#68`
- Repository: `oleg3479881328-code/Yt-Dlp-Download-Manager`

## Reproduction URL

`https://www.instagram.com/reels/DbOG_7gox2Q/`

## Scope

- `chrome_extension/`
- `native_host/`
- current `yt-dlp` dependency pin
- focused tests
- Project Execution OS state and logs

## Acceptance Criteria

1. Public Instagram Reel analysis uses current `yt-dlp`.
2. The download path produces MP4 with audio through FFmpeg.
3. The standalone `yt-dlp.exe` can update from the extension.
4. Automatic update checks are rate-limited.
5. Browser cookies are an explicit optional fallback and remain disabled by default.
6. Existing playlist behavior outside Instagram is preserved.
7. The exact reproduction URL passes a live smoke test.

## Boundaries

- Do not change VIDEO MIX.
- Do not store cookies, downloaded media or local update state in GitHub.
- Do not add DRM bypassing.
- Keep this a personal local Windows tool.
