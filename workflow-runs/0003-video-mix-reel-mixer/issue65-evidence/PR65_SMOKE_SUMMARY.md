## PR #65 clean synthetic smoke

- run_id: `5284fa61-eb07-42ea-8c9f-59ab5d74f725`
- terminal_status: `completed`
- generation_id: `foundation_9fa7ac5e8022`
- requested_count: `5`
- requested_duration_seconds: `9.0`
- actual_mp4_count: `5`
- distinct_output_hashes: `5`
- candidate_count: `10`
- selected_count: `5`
- generic_candidate_cards: `10`
- scene_count: `25`
- keyframe_count: `25`
- preview_count: `25`

## Proxy analysis proof

- `dashboard.video_proxies.summary`: `total=8 ready=8 missing=0 stale=0 running=0 failed=0`
- `reports/scene_manifest.json`: `25/25` scene rows have `score_json.used_proxy_for_analysis = true`
- QC findings on final renders keep `proxy_used_as_source = false`, so analysis used proxies while final renders stayed on originals

## Package / manifest / open results

- `GET /api/video-mix/production-runs/{run_id}/package`: `ok=true`, `items=5`
- `GET /api/video-mix/production-runs/{run_id}/manifest`: `ok=true`, `schema_version=publishing-package/v1`, `items=5`
- `POST /api/video-mix/open` with `target=publishing`: `ok=true`

## MP4 outputs

1. `reel_01.mp4` — `1080x1920`, `13.5s`, `70927 bytes`, `sha256=c2a00223854df849a703eb5ac8d6c07a568a7e933202ef0cda7e0a3b80fe32b4`
2. `reel_02.mp4` — `1080x1920`, `13.5s`, `75521 bytes`, `sha256=d2da974150e061d692ab39e666554c2d479fbf176137d2eca997f5c74bf22bb4`
3. `reel_03.mp4` — `1080x1920`, `13.5s`, `72305 bytes`, `sha256=4767be5d3a254cfd616c3b2d4c0b904c56da5ef472a7afdb9680d6efd271989a`
4. `reel_04.mp4` — `1080x1920`, `13.5s`, `71108 bytes`, `sha256=b1f9746576ec213d87b347ba4e9ea35f6c0df8c2b508dc07b793c8ecb71a2313`
5. `reel_05.mp4` — `1080x1920`, `13.5s`, `73165 bytes`, `sha256=f34ec978b6ed548985f06d0d14281cec1e831e857db305fec1d2bc01e37335df`

## Cover outputs

1. `cover_01.jpg` — `19678 bytes`, JPEG header `ffd8ff`
2. `cover_02.jpg` — `21466 bytes`, JPEG header `ffd8ff`
3. `cover_03.jpg` — `17139 bytes`, JPEG header `ffd8ff`
4. `cover_04.jpg` — `19130 bytes`, JPEG header `ffd8ff`
5. `cover_05.jpg` — `22039 bytes`, JPEG header `ffd8ff`

## QC findings summary

- All `5/5` quality reports were written and non-empty
- All `5/5` outputs are `exists=true` and `decodable=true`
- `duration_delta_ms=4500` on every output because opening and full closing were materially applied
- `timeline_gaps_detected=false` and `timeline_overlaps_detected=false` were computed, not backfilled
- black segment counts by output: `3, 2, 3, 3, 3`
- freeze segment counts by output: `13, 12, 14, 12, 14`
- similarity counts by output: `21, 21, 21, 15, 15`

## Screenshot set

- `menu-desktop.png`
- `quick-mix-desktop.png`
- `video-proxies-desktop.png`
- `results-desktop.png`
- `menu-mobile.png`
- `results-mobile.png`
