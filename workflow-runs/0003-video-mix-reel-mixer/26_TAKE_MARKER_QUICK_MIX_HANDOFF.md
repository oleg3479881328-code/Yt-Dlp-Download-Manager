# VIDEO MIX take marker Quick Mix handoff

## Goal

Allow one exported vertical source video to contain multiple machine-readable takes separated by a technical full-frame magenta card.

## Marker

- Name: `VM_TAKE_BREAK_V1`
- Color: `#ff00ff`
- Recommended duration: 0.3-0.5 seconds
- Transition style: hard cut / no transition

## Implementation summary

- The planning pipeline tries `TakeMarkerSegmenter` before fixed-interval fallback.
- Quick Mix expands marker-separated video takes into separate internal usable sources.
- Quick Mix offsets rendered source starts so generated clips skip the magenta marker cards.
- Quick Mix reports `quick_mix_source_count` and `detected_take_count` for validation.

## Owner test target

The owner can export a single vertical video from Google Vids with magenta cards between takes, put it in the source folder, and run Quick Mix. The expected behavior is that VIDEO MIX treats each detected take as a separate internal source instead of mixing the whole file as one long video.
