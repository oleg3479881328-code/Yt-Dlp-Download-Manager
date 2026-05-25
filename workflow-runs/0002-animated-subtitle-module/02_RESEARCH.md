# 02 RESEARCH — Animated Subtitle Video Maker MVP

## Date

2026-05-25

## Research Goal

Найти готовую основу для личного локального модуля, который накладывает на собственные видео пользователя animated karaoke subtitles (анимированные караоке-субтитры) с подсветкой произносимого слова и экспортом готового MP4.

## Existing Project Evidence

Подтверждено в текущем репозитории:

- существующая web dashboard (веб-панель) реализована на FastAPI + обычном HTML/JavaScript (`app/templates/index.html`, `app/static/app.js`), а не на React;
- текущая транскрибация уже использует `faster-whisper` внутри `native_host/ytdlp_host.py`;
- существующий scope (границы проекта) — личный локальный инструмент, не публичный продукт.

## Confirmed External Findings

### 1. Remotion supports TikTok-style captions and word highlighting

Official source:
- https://www.remotion.dev/docs/captions/create-tiktok-style-captions
- https://www.remotion.dev/docs/captions/displaying

Confirmed capabilities:

- `@remotion/captions` provides `createTikTokStyleCaptions()`;
- it groups timed caption tokens into pages commonly used in TikTok-style videos;
- `combineTokensWithinMilliseconds` controls whether more words stay together or animation approaches word-by-word behavior;
- returned page tokens contain `fromMs` and `toMs`, which are sufficient to identify and style the currently spoken word;
- official display example changes the active word color and identifies animations and text stroke as supported customization directions.

### 2. Remotion Player supports preview inside an application

Official source:
- https://www.remotion.dev/docs/player

Confirmed capability:

- `@remotion/player` provides an embeddable preview surface for a Remotion composition.

### 3. stable-ts can use faster-whisper and produce word timestamps

Official repository source:
- https://github.com/jianfch/stable-ts

Confirmed capabilities:

- installation supports `stable-ts[fw]` for Faster-Whisper integration;
- `load_faster_whisper()` uses a `faster_whisper.WhisperModel` instance;
- `word_timestamps` defaults to `True` and includes timestamps for individual words;
- output includes SRT/VTT/ASS options, while structured word timing can feed a rendering layer.

### 4. yt-dlp can obtain available subtitle files before local generation

Official repository source:
- https://github.com/yt-dlp/yt-dlp

Confirmed capabilities:

- `--write-subs` writes available subtitle files;
- `--write-auto-subs` writes automatically generated subtitle files;
- `--list-subs` lists available subtitles;
- `--sub-format` and `--sub-langs` control format and language.

## Architecture Conclusion

Do not force Remotion into the current FastAPI HTML/JavaScript dashboard in the first implementation. That would combine a new React/Node video-rendering stack with the old UI before the core video-output scenario is validated.

Use a new isolated module in the same repository:

```text
subtitle_studio/
  Remotion + React + TypeScript local application
```

The module can later be connected to the Python backend after it proves one successful local karaoke render.

## MVP Recommendation

Phase 1 should validate rendering only:

- local user video input;
- imported `captions.json` in Remotion `Caption[]` word-timing format;
- one built-in karaoke preset;
- preview through Remotion Player or Studio;
- exported MP4 with burned-in animated subtitles.

Speech-to-word-timing integration with `stable-ts` is a planned next phase, not part of the first rendering proof. This keeps the first build small and testable while preserving the approved direction.

## Risks

- Adding Node/React/Remotion creates a second technology stack beside Python; this is acceptable only if kept isolated under `subtitle_studio/`.
- If automatic transcription is bundled into the first implementation, failures will not reveal whether the problem is transcription or video rendering.
- Text styling options must not expand beyond one preset before a successful exported video is validated.

## One Next Action

Hand the bounded Phase 1 rendering MVP to Codex through `05_IMPLEMENTATION_HANDOFF_PACKET.md`.
