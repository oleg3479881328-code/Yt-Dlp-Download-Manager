# Whiteboard Studio

Phase 1 MVP for a local whiteboard-style explainer renderer inside `Yt-Dlp-Download-Manager`.

This module renders one vertical MP4 from a JSON scene specification. It reuses the accepted Remotion direction from `subtitle_studio/`, but stays fully isolated from the downloader, extension, native host, and `subtitle_studio`.

Phase 2 adds a path-based pencil/sketch draw-on mode for more complex outlines, starting with a horse demo.

## Scope

This module proves a narrow rendering workflow:

- JSON scene spec input;
- whiteboard / sketch explainer visuals;
- timed draw-on reveal for primary shapes;
- timed path/SVG draw-on reveal for ordered sketch strokes;
- local preview in Remotion Studio;
- local MP4 export.

It does **not** include TTS, cloud rendering, editor UI, dashboard integration, or external APIs.

## Existing Solution Reuse

- Reused the same Remotion package/tooling pattern already accepted in `subtitle_studio/`.
- Checked `roughjs` as the lightest local sketch-look layer and used it for hand-drawn SVG paths.
- Avoided heavier editor SDKs because Phase 1 only needs a render proof.

## Files

- `src/Root.tsx` - registers the composition and computes duration from the JSON file.
- `src/WhiteboardVideo.tsx` - composition shell, scene sequencing, and chapter card.
- `src/WhiteboardScene.tsx` - scene-level layout and timing.
- `src/renderers/SketchElement.tsx` - sketch element renderer with draw-on animation.
- `public/samples/sky-blue-scenes.json` - sample topic: `Почему небо голубое?`
- `public/samples/pencil-horse/` - approved SVG + JSON package plus precompiled render-scene JSON for the pencil horse draw-on scene.

## Install

```powershell
cd whiteboard_studio
npm install
```

## Preview

```powershell
npm run dev
```

Open the `WhiteboardVideo` composition in Remotion Studio.

## Render Sample MP4

```powershell
npm run render:sample
```

Output:

```text
whiteboard_studio/out/sky-blue-demo.mp4
```

## Render Pencil Horse Demo

```powershell
npm run render:horse
```

Output:

```text
whiteboard_studio/out/pencil-horse-demo.mp4
```

## Scene Spec Shape

The sample JSON uses this high-level structure:

```json
{
  "meta": {
    "title": "Почему небо голубое?",
    "fps": 30,
    "width": 1080,
    "height": 1920
  },
  "scenes": [
    {
      "id": "scene-01",
      "title": "Солнце посылает белый свет",
      "durationSec": 8,
      "caption": "Белый свет содержит волны разных цветов.",
      "elements": []
    }
  ]
}
```

Element types used in Phase 1:

- `line`
- `arrow`
- `circle`
- `wave`
- `dots`
- `text`

Additional Phase 2 types:

- `strokePath`
- `pathGroup`

Each drawable element supports relative timing through `startSec` and `durationSec`.

`strokePath` renders one SVG path string with timed stroke reveal.

`pathGroup` renders an ordered list of SVG subpaths so one object can appear in multiple passes such as outline, details, and hatching.

The approved horse demo is compiled from `approved-drawing.svg` + `pencil-horse-scenes.json` into `pencil-horse-render-scenes.json`, and the render uses that precompiled scene spec directly.

## Checks

```powershell
npm run lint
npm run build
```

## Known Limitations

- The draw-on effect is deliberately simple and driven by SVG stroke reveal.
- The whiteboard style is optimized for a single demo topic, not a general-purpose animation editor.
- Text layout is manual in the JSON spec.
- The horse sample depends on the owner-approved grouped SVG package; automatic image tracing is intentionally not implemented here.
