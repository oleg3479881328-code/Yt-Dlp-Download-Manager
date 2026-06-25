# Codex Handoff: Approved Pencil Horse SVG Draw-on

## Goal

Animate the owner-approved horse drawing as a pencil/whiteboard draw-on video.

This package contains the approved visual asset. Do not invent a new horse drawing from words.

## Files

- `approved-reference.png`
  - Exact owner-approved reference image.
  - Use only for visual comparison.
  - Do **not** render it as a static pop-in.

- `approved-reference-horse-only.png`
  - Same reference with the human hand/pencil area removed as much as practical.
  - Use only for visual comparison if useful.

- `approved-drawing.svg`
  - Machine-readable grouped SVG/path version.
  - This is the source of truth for the renderer.
  - It has groups:
    - `construction`
    - `outline`
    - `head_details`
    - `mane_tail`
    - `inner_structure`
    - `hatching`
    - `ground_shadow`

- `pencil-horse-scenes.json`
  - Timeline and render instructions.
  - The renderer should use this file to decide the draw-on order and timings.

## Required renderer behavior

1. Load `approved-drawing.svg` or otherwise ingest its grouped paths.
2. Reveal paths using `strokeDasharray` / `strokeDashoffset` or an equivalent local SVG path-length draw-on approach.
3. Preserve the group order:
   1. construction
   2. outline
   3. head_details
   4. mane_tail
   5. inner_structure
   6. hatching
   7. ground_shadow
4. Render vertical MP4: `1080x1920`.
5. Use output path:
   `whiteboard_studio/out/pencil-horse-demo.mp4`

## Important visual rule

The PNG is the approved look. The SVG is the animatable source. The output should feel like the approved pencil horse sketch being drawn progressively, not like the previous childish doodle.

## Out of scope

Do not implement:
- automatic PNG/JPG tracing;
- editor UI;
- dashboard integration;
- TTS;
- subtitles;
- cloud rendering;
- SaaS tools;
- hand tracking.

## Validation

Run:

```powershell
cd whiteboard_studio
npm install
npm run lint
npm run build
npm run render:sample
npm run render:horse
```

Then run ffprobe on:

```text
whiteboard_studio/out/pencil-horse-demo.mp4
```

Report:

- branch;
- PR link;
- commit SHA;
- validation results;
- MP4 width / height / fps / duration / file size;
- artifact status;
- ready for owner visual review: yes/no.
