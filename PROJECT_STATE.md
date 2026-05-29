---
status: in-progress
project_mode: compact
current_step: 06_REVIEW_BLOCKED
current_run: workflow-runs/0002-animated-subtitle-module/
last_updated: 2026-05-29
next_action: Codex must fix the outstanding Phase 1 review blockers in GitHub Issue #1 and return the required Execution Report.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

Личный локальный инструмент нормализован в `compact mode` (компактном режиме) Project Execution OS. Scope (границы проекта) расширен подтверждённым решением владельца: в этот же репозиторий добавляется модуль создания собственных роликов с анимированными субтитрами.

Phase 1 MVP (первая минимально рабочая версия) был спроектирован, проверен review (ревью — проверкой), передан Codex через GitHub Issue #1 и частично реализован в `subtitle_studio/`. Реализация не принята: review обнаружил блокирующий дефект длительности композиции и отсутствие корректного `EXECUTION REPORT` (отчёта о выполнении).

29 мая 2026 года в репозитории также зафиксировано исследование будущего `Video Content Analyzer` (модуля анализа содержания видео). Это исследование сохраняет найденные donor patterns (донорские паттерны — готовые подходы для адаптации), но не разрешает новую реализацию до закрытия текущего Phase 1 MVP.

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
- `subtitle_studio/` существует как изолированная реализация Remotion MVP, но её принятие заблокировано ревью;
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
9. Решение владельца от 2026-05-29: `Yt-Dlp-Download-Manager` остаётся единственным основным видео-проектом; `Video-Combine-Analyzer` не развивается как параллельный продукт.
10. Найденная технология анализа видео сохраняется как будущий кандидат-модуль `Video Content Analyzer` внутри этого репозитория; основной донорский паттерн — `bradautomates/claude-video`, вторичные идеи — `jordanrendric/claude-video-vision`, а `thoughtpunch/claudetube` используется только как источник идей на более поздний этап.
11. Реализация `Video Content Analyzer` не начинается до отдельного решения владельца после закрытия активных блокеров Phase 1 субтитров.

## Animated Subtitle Video Maker — Approved Scope, Blocked Validation

Новый модуль должен позволить:

- загружать собственный ролик;
- использовать существующие субтитры или создавать новые;
- получать word-level timing (временные метки каждого слова);
- делать karaoke highlighting (караоке-подсветку произносимого слова);
- настраивать цвет, стиль подсветки, анимацию появления, последовательность и положение текста;
- видеть preview (предпросмотр);
- экспортировать MP4 с burned-in subtitles (вшитыми субтитрами).

Current implementation state (текущий статус реализации): code present in `subtitle_studio/`, but not accepted.

Active review blockers (активные блокеры ревью):

- `subtitle_studio/src/Root.tsx` uses fixed `durationInFrames={240}` at `fps={30}`, truncating content longer than 8 seconds;
- README claim about a blurred background must be implemented or corrected;
- validation must use content longer than 8 seconds;
- Codex must post the required structured `EXECUTION REPORT` with actual evidence.

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
- GitHub transport issue (задача-переносчик GitHub): `#1 Implement Phase 1 Animated Subtitle Video Maker MVP`
- Current review state (текущее состояние ревью): `changes requested`; Phase 1 not accepted.

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

### RISK-004 — Duplicate video-analysis repository direction

Отдельный репозиторий `Video-Combine-Analyzer` мог создать конкурирующее направление рядом с основным видео-проектом.

Status (статус): resolved by owner decision (устранено решением владельца): знания перенесены в этот проект, отдельное развитие не требуется.

## Latest Result

Зафиксировано исследование технологии AI-assisted video analysis (ИИ-анализа видео) и решение владельца сохранить её как будущий модуль в основном проекте, не создавая параллельный продукт. Приоритет реализации не изменён: текущий Phase 1 MVP модуля анимированных субтитров остаётся заблокированным до устранения замечаний ревью.

## Current Next Action

Codex должен исправить блокеры в GitHub Issue #1, проверить MP4 на материале длиннее 8 секунд и вернуть обязательный `EXECUTION REPORT` (отчёт о выполнении) до утверждения любых следующих работ.