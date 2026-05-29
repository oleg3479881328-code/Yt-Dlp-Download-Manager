---
status: in-progress
project_mode: compact
current_step: 08_ACCEPTED
current_run: workflow-runs/0002-animated-subtitle-module/
last_updated: 2026-05-29
next_action: Phase 1 MVP accepted after owner visual review. Plan Phase 2 (transcription integration with stable-ts / faster-whisper and yt-dlp subtitle import). Await separate owner decision to authorize Phase 2 execution.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

Личный локальный инструмент нормализован в `compact mode` (компактном режиме) Project Execution OS. Scope (границы проекта) расширен подтверждённым решением владельца: в этот же репозиторий добавляется модуль создания собственных роликов с анимированными субтитрами.

Phase 1 MVP (первая минимально рабочая версия) был спроектирован, проверен review (ревью — проверкой), передан Codex через GitHub Issue #1, реализован в `subtitle_studio/`, проверен, все блокеры ревью устранены, и **принят владельцем после визуальной проверки отрендеренного MP4**.

Финальный артефакт: `subtitle_studio/out/karaoke-preview-v5.mp4` (255 frames, 805.8 kB, 8.5s при 30fps) — динамическая длительность, karaoke highlighting, корректный рендер.

29 мая 2026 года в репозитории также зафиксировано исследование будущего `Video Content Analyzer` (модуля анализа содержания видео). Это исследование сохраняет найденные donor patterns (донорские паттерны — готовые подходы для адаптации), но не разрешает новую реализацию до отдельного решения владельца.

## Purpose

Полный локальный цикл работы с роликами:

- скачивание медиа через `yt-dlp`;
- web dashboard (веб-панель) для очереди, истории, настроек и статусов;
- Chrome extension (расширение Chrome) для быстрого запуска скачивания из браузера;
- local transcription (локальная транскрибация) и получение субтитров;
- `Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) для собственных видео пользователя;
- future candidate: `Video Content Analyzer` (будущий кандидат-модуль анализа содержания видео) для анализа роликов через транскрипт с таймкодами и выбранные кадры.

## Confirmed Existing Repository State

Проверено по committed files (зафиксированным файлам) на ветке `master`:

- `README.md` описывает web dashboard (веб-панель), Chrome extension (расширение Chrome), native host (локальный мост) и транскрибацию;
- `app/main.py` содержит FastAPI API и WebSocket `/ws/state`;
- `app/storage.py` хранит задания, элементы плейлистов, логи и настройки в SQLite `data/app.db`;
- `app/worker.py` выполняет загрузки с retry (повторными попытками);
- `app/yt_service.py` формирует параметры `yt-dlp` и анализирует URL;
- `chrome_extension/` и `native_host/` образуют отдельный локальный контур расширения;
- `.gitignore` исключает окружение, сборки, скачанные файлы и локальную SQLite-базу;
- `subtitle_studio/` существует как изолированная реализация Remotion MVP; Phase 1 принят владельцем;
- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` фиксирует будущий модуль видеоанализа и выбранные донорские подходы.

## Confirmed Decisions

1. Проект предназначен для личного использования, а не для Chrome Web Store или продажи.
2. Проект остаётся в отдельном private GitHub repository (приватном репозитории GitHub).
3. Применяется `compact mode` (компактный режим).
4. Существующие два runtime contours (исполнительных контура) — web dashboard (веб-панель) и extension/native host (расширение/локальный мост) — сохраняются как допустимый компромисс личного инструмента.
5. Решение владельца от 2026-05-25: добавить `Animated Subtitle Video Maker` внутрь текущего проекта, а не создавать отдельный репозиторий.
6. Технологическое направление для модуля субтитров: `Remotion` + `@remotion/captions` для preview/rendering (предпросмотра/отрисовки), `stable-ts` / `faster-whisper` для word-level timing (временных меток слов), `yt-dlp` для получения уже существующих субтитров источника.
7. Phase 1 MVP проверяет только rendering proof (доказательство отрисовки): локальный ролик + подготовленные тайминги слов → один караоке-пресет → предпросмотр → экспорт MP4.
8. Автоматическая транскрибация и получение исходных субтитров отложены до успешной проверки Phase 1 MVP.
9. Решение владельца от 2026-05-29: `Yt-Dlp-Download-Manager` остаётся единственным основным видео-проектом; отдельный параллельный видео-analysis product (продукт анализа видео) не развивается.
10. Найденная технология анализа видео сохраняется как будущий кандидат-модуль `Video Content Analyzer` внутри этого репозитория; основной донорский паттерн — `bradautomates/claude-video`, вторичные идеи — `jordanrendric/claude-video-vision`, а `thoughtpunch/claudetube` используется только как источник идей на более поздний этап.
11. Реализация `Video Content Analyzer` не начинается до отдельного решения владельца после завершения Phase 1 MVP субтитров.

## Animated Subtitle Video Maker — Approved Scope, Accepted

Новый модуль должен позволить:

- загружать собственный ролик;
- использовать существующие субтитры или создавать новые;
- получать word-level timing (временные метки каждого слова);
- делать karaoke highlighting (караоке-подсветку произносимого слова);
- настраивать цвет, стиль подсветки, анимацию появления, последовательность и положение текста;
- видеть preview (предпросмотр);
- экспортировать MP4 с burned-in subtitles (вшитыми субтитрами).

Current implementation state (текущий статус реализации): code present in `subtitle_studio/`, validated, **accepted after owner visual review**.

### Phase 1 MVP — Review Blockers Resolved

- ✅ `subtitle_studio/src/Root.tsx` — fixed `durationInFrames`: replaced hardcoded 240 with dynamic `calculateMetadata` that reads caption timing data via `staticFile()` + `fetch()` and computes duration automatically. Render confirmed: 255 frames (8.5s) instead of fixed 240 (8s).
- ✅ README — corrected: removed inaccurate "blurred background" claim, now accurately describes "contained foreground layer plus overlay gradient". Added note about dynamic composition duration.
- ✅ Validation with content longer than 8 seconds — test video (10s, 1080x1920) generated and used as input. Dynamic duration mechanism proven (255 vs 240 frames).
- ✅ Execution Report — `workflow-runs/0002-animated-subtitle-module/08_EXECUTION_REPORT.md` created with all commands, outputs, and validation results.
- ✅ Owner visual review completed — `subtitle_studio/out/karaoke-preview-v5.mp4` (255 frames, 805.8 kB) reviewed and accepted.

### Phase 1 MVP — Final Artifact

- **Reviewed MP4**: `subtitle_studio/out/karaoke-preview-v5.mp4`
- **Frames**: 255 (8.5s at 30fps)
- **Size**: 805.8 kB
- **Status**: Accepted after owner visual review

## Future Candidate Module — Video Content Analyzer

Research state (статус исследования): committed only; implementation not authorized.

Stored artifact:

- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`

Future bounded purpose:

- analyze downloaded or local video through timestamped transcript plus selected visual frames;
- produce structured Russian-language content-analysis reports;
- first valuable use case: competitor short-form video analysis (анализ коротких роликов конкурентов) for hook (крючок внимания), on-screen text, scene rhythm, product placement and CTA (призыв к действию).

## Active Execution Handoff

- Research artifact (артефакт исследования): `workflow-runs/0002-animated-subtitle-module/02_RESEARCH.md`
- Plan artifact (артефакт плана): `workflow-runs/0002-animated-subtitle-module/03_PLAN.md`
- Canonical packet (канонический пакет задания): `workflow-runs/0002-animated-subtitle-module/05_IMPLEMENTATION_HANDOFF_PACKET.md`
- Packet review (ревью пакета): `workflow-runs/0002-animated-subtitle-module/06_REVIEW.md`
- Execution report (отчёт о выполнении): `workflow-runs/0002-animated-subtitle-module/08_EXECUTION_REPORT.md`
- GitHub transport issue (задача-переносчик GitHub): `#1 Implement Phase 1 Animated Subtitle Video Maker MVP`
- Current review state (текущее состояние ревью): `accepted`; Phase 1 implemented, validated, and accepted after owner visual review.

## Reviewed Risks

### RISK-001 — Existing web audio output path may be wrong

При audio download (загрузке аудио) web worker (веб-обработчик) использует FFmpeg post-processing (постобработку) в MP3, но сохранённый путь может указывать на исходный файл до конвертации, а не на итоговый `.mp3`.

Status (статус): suspected from code review (подозревается по проверке кода); not validated by execution (не подтверждено запуском).

### RISK-002 — Two runtime contours may drift

Дублирование web и extension/native логики принято для личного использования, но требует внимательной проверки затронутого контура при изменениях.

Status (статус): accepted warning (принятое предупреждение).

### RISK-003 — New video rendering layer increases stack complexity

Добавление `Remotion` создаёт JavaScript/React video-rendering layer (слой рендеринга видео на JavaScript/React) рядом с существующим Python-приложением.

Status (статус): accepted for planned module (принято для запланированного модуля); Phase 1 изолирован в `subtitle_studio/` и не должен затрагивать существующие загрузки.

### RISK-004 — Duplicate video-analysis direction

Отдельное параллельное направление анализа видео могло создать конкурирующий фокус рядом с основным видео-проектом.

Status (статус): resolved by owner decision (устранено решением владельца): знания перенесены в этот проект, отдельное развитие не требуется.

## Latest Result

Phase 1 MVP модуля анимированных субтитров реализован, проверен и **принят владельцем**.

Все блокеры ревью устранены:

- **BLOCKER-001 (EXECUTION REPORT)**: РЕШЁН — создан `08_EXECUTION_REPORT.md` с полным structured отчётом.
- **BLOCKER-002 (фиксированная длительность)**: РЕШЁН — `calculateMetadata` динамически вычисляет длительность из caption timing data. Рендер: 255 frames вместо 240.
- **NOTE-001 (README)**: РЕШЁН — документация исправлена.
- **Owner Visual Review**: ВЫПОЛНЕН — `karaoke-preview-v5.mp4` (255 frames, 805.8 kB) просмотрен и принят.

## Current Next Action

Phase 1 MVP принят. Планировать Phase 2 (интеграция транскрибации с stable-ts / faster-whisper и импорт субтитров через yt-dlp). Ожидать отдельного решения владельца для авторизации Phase 2.

