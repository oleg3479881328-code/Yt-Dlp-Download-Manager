# VIDEO CONTENT ANALYZER — DONOR ASSESSMENT AND CAPTURED DECISION

## Capture Status

- Date captured: `2026-05-29`
- State: `committed research / future-module decision captured`
- Implementation state: `not approved for execution yet`
- Main project: `oleg3479881328-code/Yt-Dlp-Download-Manager`
- Temporary parallel direction discussed during research: a separate experimental video-analysis repository

## Why This Artifact Exists

A useful open-source pattern was found during discussion: AI-assisted analysis of public or local video by converting video into timestamped transcript plus selected frames that a multimodal model can inspect.

This must not be lost in chat, but it also must not create a competing main project. The owner's confirmed direction is:

- `Yt-Dlp-Download-Manager` remains the primary video project;
- the video-analysis capability is a possible future module inside this primary project;
- the former separate experimental direction is not a second product direction and is no longer required as a knowledge holder after this capture;
- no video-analysis implementation should interrupt the currently blocked `Animated Subtitle Video Maker` Phase 1 MVP.

## Confirmed Project Fit

The existing primary project already covers the necessary base capabilities:

- video/media download through `yt-dlp`;
- local web dashboard (локальная веб-панель);
- Chrome extension (расширение Chrome) and native host (локальный мост расширения к Windows);
- local transcription (локальная транскрибация) into subtitle/text files;
- planned/partially implemented animated subtitle creation.

Therefore, a future video-analysis feature belongs here as an additional bounded module, not as a separate product repository.

## Existing Solutions Checked

### 1. `bradautomates/claude-video` — selected primary donor pattern

Repository: `https://github.com/bradautomates/claude-video`

Verified capabilities from its README:

- accepts a supported public video URL or a local video path;
- downloads online video using `yt-dlp`;
- extracts timestamped JPEG frames using `ffmpeg`;
- uses duration-aware frame extraction with a hard ceiling of `2 fps` and `100 frames`;
- first attempts source captions, then falls back to Whisper through Groq or OpenAI when required;
- supports focused re-analysis through `--start` and `--end`;
- states installation as a Codex / generic skill (универсальный навык для Codex);
- license: MIT.

Important limitation:

- for videos longer than 10 minutes, the default 100-frame scan is sparse; it is useful for orientation but not proof that every visual event was captured.

Selected value:

- simplest donor for the core pipeline: `video -> transcript + timestamped frames -> model analysis`.

### 2. `jordanrendric/claude-video-vision` — selected secondary donor ideas

Repository: `https://github.com/jordanrendric/claude-video-vision`

Verified capabilities from its README:

- Claude Code plugin with MCP server (сервер инструментов по протоколу Model Context Protocol — протоколу подключения инструментов к модели);
- frame extraction through `ffmpeg`;
- audio backends: Gemini API, local Whisper (локальный Whisper) or OpenAI API;
- transcript provenance (происхождение транскрипта): manual YouTube subtitles, automatic captions or processed audio;
- configuration supports PNG for sharp UI/text frames and a cache lifetime;
- exposes focused video tools such as `video_watch`, `video_detail` and `video_info`;
- license: MIT.

Selected value:

- local transcription option;
- provenance labeling for transcript reliability;
- PNG/high-resolution mode for screen recordings, interfaces, diagrams and code.

### 3. `thoughtpunch/claudetube` — ideas only, not an MVP foundation

Repository: `https://github.com/thoughtpunch/claudetube`

Verified capabilities from its README:

- MCP server for multiple MCP-compatible clients;
- online video download through `yt-dlp`;
- local transcription through `faster-whisper`;
- cached content and frame extraction on demand;
- scene/moment-oriented tools and more than 40 exposed MCP tools;
- license: MIT.

Selected value:

- possible later ideas: cache-first repeated investigation, moment lookup and focused high-quality frames.

Rejected for current MVP basis:

- its tool surface and orchestration complexity are excessive for the next bounded addition to this project.

## Marketing Claims Corrected

The researched open-source pattern is useful, but the public framing must not be copied uncritically.

### Not native video intelligence

The model does not necessarily receive continuous native video. The donor pattern generally supplies:

- sampled frames;
- a transcript with timestamps;
- optional focused follow-up extractions.

That is strong for structure, captions, UI/screens, product placement, hooks and calls to action. It is weaker for fast motion or events between sampled frames.

### Not automatically fully local

- `claude-video` may send audio to Groq or OpenAI Whisper when source captions are unavailable.
- `claude-video-vision` can be local with Whisper, but it also supports cloud backends.
- fully local preparation does not mean fully local interpretation unless the analyzing model is also local.

### Speed claim not accepted as evidence

The statement that a 30-minute video is analyzed in under two minutes was not treated as a validated benchmark. Performance depends on captions availability, download speed, transcription backend, hardware, frame count, resolution and model latency.

## Captured Product Decision

### Primary-project rule

`Yt-Dlp-Download-Manager` remains the only primary video project. Do not develop a separate competing video-analysis system.

### Future candidate module

Proposed module name:

- `Video Content Analyzer` (модуль анализа содержания видео)

Purpose:

- analyze downloaded or local videos by combining transcript timing and selected visual frames;
- produce structured reports useful for content research and the owner's video-production workflow.

### Highest-value first use case

Competitor short-form content analysis (анализ коротких роликов конкурентов), especially for TikTok/YouTube-style material:

- opening hook (крючок внимания) in the first seconds;
- spoken opening and on-screen text;
- scene rhythm and visual structure;
- product appearance timing;
- call to action / CTA (призыв к действию);
- reusable ideas for the owner's own content.

## Bounded Future MVP Shape

Only after the active animated-subtitle MVP is accepted and a new implementation task is explicitly approved, the smallest useful video-analysis MVP should be:

1. accept an existing downloaded file or local video file;
2. reuse existing/local transcript capabilities where adequate;
3. extract timestamped frames with a bounded budget;
4. support a dense focused segment pass for important moments;
5. output one structured Russian-language analysis report with evidence timestamps;
6. avoid building a new standalone platform, database or broad MCP tool suite at the first stage.

## Reuse Decisions

| Candidate | Decision | Reason |
|---|---|---|
| `bradautomates/claude-video` | primary donor pattern | Smallest adequate frame-plus-transcript analysis pipeline and Codex-compatible skill packaging idea. |
| `jordanrendric/claude-video-vision` | secondary pattern source | Local Whisper, transcript provenance and high-quality UI frame handling. |
| `thoughtpunch/claudetube` | ideas only for later | Cache and focused retrieval are valuable, but its current surface is too large for MVP adoption. |
| Former separate experimental direction | not a primary project | Its useful knowledge is captured here; separate development would duplicate the primary video system. |

## Current Boundary And Next Action

This research does **not** authorize implementation of `Video Content Analyzer` yet.

Current project priority remains the active `Animated Subtitle Video Maker` Phase 1 MVP. It must first close the existing review blockers in GitHub Issue `#1`, specifically:

- remove the fixed 8-second composition duration limitation;
- align README claims with implemented rendering;
- validate export using content longer than 8 seconds;
- post the required Codex execution report with actual evidence.

After Phase 1 is accepted, the owner may decide whether to open a bounded implementation task for `Video Content Analyzer`.
