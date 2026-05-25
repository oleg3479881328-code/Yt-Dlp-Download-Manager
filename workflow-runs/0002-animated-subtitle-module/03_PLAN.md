# 03 PLAN — Animated Subtitle Video Maker Phase 1 MVP

## Date

2026-05-25

## Goal

Доказать минимальный пользовательский результат: собственный локальный ролик можно превратить в новый MP4 с вшитыми караоке-субтитрами и предпросмотром до экспорта.

## MVP Principle

Не смешивать в первом implementation run (цикле реализации) два независимых риска:

1. speech-to-text timing generation (создание текста и таймингов из речи);
2. animated video rendering (отрисовка видео с анимированными субтитрами).

Phase 1 проверяет только второй риск на готовых входных данных `captions.json`.

## Chosen Implementation Slice

Создать изолированный модуль внутри существующего repository (репозитория):

```text
subtitle_studio/
```

Технологический стек модуля:

- `Remotion` — video rendering framework (платформа отрисовки видео);
- `React` + `TypeScript` — слой композиции и параметров пресета;
- `@remotion/captions` — timed captions utilities (утилиты субтитров с таймингами);
- Remotion preview surface (поверхность предпросмотра) and local render command (локальная команда экспорта).

## Phase 1 User Flow

```text
sample/local MP4 video
        +
caption timing JSON
        ↓
open subtitle_studio preview
        ↓
see one karaoke preset with current-word highlighting
        ↓
render MP4
        ↓
confirm exported video contains burned-in animated subtitles
```

## Required MVP Capabilities

1. One Remotion composition for a vertical social-video shape by default (`1080x1920`), with input video fitting safely inside the canvas.
2. Video source and caption data are passed through composition props (параметры композиции), not hardcoded in rendering logic.
3. Caption input accepts a documented sample `captions.json` using Remotion timed caption data sufficient for per-word activation.
4. One `KaraokePresetV1` style only:
   - text placed near lower center in a safe zone;
   - non-active text visible;
   - active spoken word highlighted with a contrasting color and a simple scale/pop effect;
   - text remains readable using stroke or shadow.
5. Preview works locally.
6. A local render/export command generates an MP4 with subtitles embedded into the image.
7. A short README explains setup, preview, replacing sample assets and exporting.

## Explicitly Out Of Scope For Phase 1

- automatic transcription or `stable-ts` integration;
- downloading captions through `yt-dlp`;
- multiple visual presets;
- an editor for color, position or animations;
- integration into the existing FastAPI dashboard;
- integration into Chrome extension or native host;
- batch processing;
- subtitle translation;
- speaker detection;
- cloud services;
- production installer.

## Repository Safety Boundaries

- All new code must remain under `subtitle_studio/`, except a necessary `.gitignore` addition for Node dependencies and rendered output.
- Existing `app/`, `chrome_extension/`, and `native_host/` application behavior must not be modified in Phase 1.
- Sample video binaries and generated MP4 outputs must not be committed.
- Provide a tiny sample caption JSON and instructions for the user to place a local test video file himself.

## Acceptance Gate

Phase 1 becomes `validated` (проверенным) only when execution evidence shows:

- dependencies install successfully;
- preview opens with a real local video and the sample captions;
- the active word visibly changes during playback;
- one MP4 render succeeds;
- the rendered MP4 visibly contains burned-in karaoke highlighting;
- Codex returns an execution report listing files changed and checks performed.

## Follow-Up Only After Validation

After successful Phase 1 render, prepare Phase 2 for:

- local `stable-ts` / `faster-whisper` generation of word-level timing;
- conversion of timing output into the caption JSON consumed by `subtitle_studio/`.

## One Next Action

Execute `05_IMPLEMENTATION_HANDOFF_PACKET.md` through Codex in VS Code.
