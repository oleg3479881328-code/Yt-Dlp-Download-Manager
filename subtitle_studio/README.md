# Subtitle Studio

Phase 1 MVP for the `Animated Subtitle Video Maker` module. This Remotion project renders one vertical MP4 with burned-in karaoke subtitles using prepared timed caption JSON.

## Scope

This module only proves the rendering workflow:

- local video input;
- prepared word-timed caption JSON;
- one built-in preset: `KaraokePresetV1`;
- local preview in Remotion Studio;
- MP4 export with burned-in subtitles.

It does **not** implement transcription, `stable-ts`, `faster-whisper`, `yt-dlp` subtitle import, multiple presets, or editor UI.

## Files

- `src/KaraokeVideo.tsx` - the only composition used for preview and render.
- `src/KaraokePresetV1.ts` - isolated visual constants for the one allowed preset.
- `public/samples/captions.json` - documented example caption input with word timings.
- `public/local-assets/` - ignored folder for your local input video.

## Install

```powershell
cd subtitle_studio
npm install
```

## Local Input

1. Put your local test video here:

```text
subtitle_studio/public/local-assets/validation-input.mp4
```

2. Replace the sample captions if needed:

```text
subtitle_studio/public/samples/captions.json
```

The caption file must be a JSON array in Remotion `Caption[]` shape:

```json
[
  {
    "text": "Hello",
    "startMs": 0,
    "endMs": 400,
    "timestampMs": 200,
    "confidence": 0.99
  },
  {
    "text": " world",
    "startMs": 400,
    "endMs": 900,
    "timestampMs": 650,
    "confidence": 0.99
  }
]
```

Important:

- keep whitespace before words after the first token, for example `" world"`;
- this module expects prepared timings only.

## Preview

```powershell
npm run dev
```

Then open the `KaraokeVideo` composition in Remotion Studio.

## Export MP4

```powershell
npm run render:sample
```

Output:

```text
subtitle_studio/out/karaoke-preview.mp4
```

## Checks

Type + lint + bundle:

```powershell
npm run lint
npm run build
```

## Notes

- The composition is portrait by default: `1080x1920`.
- The video is shown with a blurred background layer plus a contained foreground layer to preserve aspect ratio.
- `KaraokePresetV1` is the only preset in this phase.
