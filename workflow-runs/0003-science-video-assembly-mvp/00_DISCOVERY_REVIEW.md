# Science Video Assembly MVP — Discovery Review

- Date: 2026-06-20
- Repository: `oleg3479881328-code/Yt-Dlp-Download-Manager`
- Status: planning / execution-prep
- Owner intent: automate creation of educational / science-popular videos with AI assistance.

## Purpose

Capture the confirmed reuse-first review before any implementation task is handed to Codex or another executor.

The target is not a blind YouTube scraper. The target is a rights-aware AI-assisted video assembly pipeline:

```text
topic / script
-> visual beats
-> allowed source search
-> candidate ranking
-> human approval
-> clip timeline JSON
-> ffmpeg / Remotion preview render
-> source ledger
```

## Internal Reuse Findings

### Primary project

`Yt-Dlp-Download-Manager` remains the correct home for this work.

Confirmed existing capabilities from current project state and entrypoint:

- local Windows video tool;
- `yt-dlp` media download workflow;
- FastAPI dashboard;
- Chrome extension and native messaging host;
- optional local transcription into `SRT + TXT`;
- accepted `Animated Subtitle Video Maker` Phase 1;
- future candidate `Video Content Analyzer` based on transcript plus selected frames.

Do not create a separate competing repository for this work unless the owner explicitly reverses this decision.

### Reusable internal modules / patterns

1. `Video Content Analyzer` research
   - Use for: understanding candidate videos through transcript + sampled frames.
   - Donor pattern already selected: `bradautomates/claude-video`.
   - Secondary donor ideas: `jordanrendric/claude-video-vision`.
   - Later ideas only: `thoughtpunch/claudetube`.

2. `Animated Subtitle Video Maker`
   - Use for: preview/render layer, burned-in captions, possible Remotion template reuse.
   - Do not disturb its accepted Phase 1 artifact.

3. `QuizLight` video learning flow
   - Reuse conceptually: transcript line -> context window -> sense block -> scene start/end -> replay.
   - Do not import QuizLight product scope.

4. Project Execution OS video blocks
   - `VIDEO_PIPELINES.md`: reusable video production chains.
   - `AI_VIDEO_STACKS.md`: script/TTS/manual edit, transcript clip suggestions, AI visuals, localization.
   - `YT_DLP_AND_FFMPEG.md`: deterministic media processing and rights-aware import.

## External Ready-Made Solution Review

No single ready-made product fully covers:

```text
topic -> 10-minute science script -> find exact reusable external footage -> cut -> assemble -> source ledger
```

Existing SaaS products cover pieces:

- Pictory / InVideo / Kapwing / Descript: useful for script-to-video, stock or AI visuals, captions, B-roll assistance.
- OpusClip: useful for long-video-to-shorts, not for new science script assembled from many external sources.
- Twelve Labs / VideoDB: promising APIs for semantic video search and video moment retrieval, but require a separate spike.
- Shotstack: possible cloud render API, but Remotion/ffmpeg is better aligned with the existing local project.

## Official External Facts Checked

### DeepSeek API

Official docs checked on 2026-06-20:

- Base URL: `https://api.deepseek.com`.
- Current models page lists `deepseek-v4-flash` and `deepseek-v4-pro`.
- Model details page lists 1M context length and JSON Output / Tool Calls support.
- JSON Output requires `response_format: {'type': 'json_object'}` and the prompt must include the word `json` plus a sample JSON format.
- Function Calling / Tool Calls mean the model returns a function call; the application must execute the actual function. The model does not execute tools itself.

Sources:

- https://api-docs.deepseek.com/quick_start/pricing
- https://api-docs.deepseek.com/guides/json_mode
- https://api-docs.deepseek.com/guides/function_calling

### Pexels API

Official docs checked on 2026-06-20:

- API requires an Authorization header with a Pexels API key.
- Video search endpoint: `GET https://api.pexels.com/v1/videos/search`.
- Search accepts a `query` parameter and supports broad or specific searches.

Source:

- https://www.pexels.com/api/documentation/

### Pixabay API

Official docs checked on 2026-06-20:

- Video search endpoint: `GET https://pixabay.com/api/videos/`.
- `key` is required.
- `q` is a URL-encoded search term.
- Supports filters such as `video_type`, `category`, `min_width`, `min_height`, `safesearch`, `order`, `page`, and `per_page`.
- API returns video URLs in multiple sizes.

Source:

- https://pixabay.com/api/docs/

### YouTube Terms Boundary

Official YouTube Terms checked on 2026-06-20.

Important constraint:

- You may view/listen through the service and show videos through the embeddable player.
- Restrictions include not downloading, reproducing, modifying, distributing, or otherwise using Service/Content except as expressly authorized by the Service or with prior written permission from YouTube and rights holders.
- Restrictions also include not accessing the Service using automated means such as robots, botnets or scrapers, except narrow allowed cases or prior written permission.

Therefore, MVP-1 must not be specified as automatic YouTube downloading / ripping / republishing.

Source:

- https://www.youtube.com/static?template=terms

## Correct Product Framing

Wrong framing:

```text
Automatically scrape YouTube, cut pieces, and publish a new video.
```

Correct framing:

```text
AI-assisted rights-aware science video assembly from allowed sources, with source ledger, human approval, and optional YouTube analysis/reference/embedding only where permitted.
```

## MVP Boundary

MVP-1 should use:

- user-provided short script or generated script;
- DeepSeek-backed visual beat extraction;
- Pexels / Pixabay video search adapters;
- manual review and approval of candidates;
- timeline JSON;
- local preview render through ffmpeg or Remotion;
- source ledger.

MVP-1 should not include:

- automatic YouTube downloading for publication;
- broad SaaS platform build;
- user accounts;
- marketplace/collaboration;
- direct monetization features;
- fully automated publishing;
- bypassing rights checks.

## Decision

Proceed with a bounded planning and prototype handoff for `Science Video Assembly MVP` inside this repository.
