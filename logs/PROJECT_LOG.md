# PROJECT LOG — yt-dlp Download Manager

## 2026-05-25 — Legacy project normalization

### Trigger

Олег определил проект как личный инструмент и поручил привести существующий репозиторий к Project Execution OS.

### Verified Before Change

- Repository: `oleg3479881328-code/Yt-Dlp-Download-Manager`.
- Visibility: private.
- Default branch: `master`.
- Existing application components inspected: FastAPI web dashboard (веб-панель), SQLite persistence (локальное хранение состояния), download worker (обработчик загрузок), Chrome extension (расширение Chrome), native messaging host (локальный мост) and local transcription (локальная транскрибация).
- Before normalization, canonical project-state files required for recoverable compact operation were absent.

### Decision

- Use `compact mode` (компактный режим).
- Treat the repository as a personal local utility, not a public or commercial product.
- Preserve the existing web-dashboard and extension/native-host execution paths as an accepted personal-use compromise.

### Committed Artifacts Created

- `PROJECT_ENTRYPOINT.md`
- `PROJECT_STATE.md`
- `PROJECT_RULES.md`
- `workflow-runs/0001-legacy-normalization/06_REVIEW.md`
- `workflow-runs/0001-legacy-normalization/07_RESULT.md`
- `workflow-runs/0001-legacy-normalization/08_KNOWLEDGE_EXTRACT.md`
- `logs/PROJECT_LOG.md`

### Review Outcome

`accept with warnings`

### Open Risk

`RISK-001` remains `suspected`: web audio download (загрузка аудио через веб-панель) may store a pre-conversion output path rather than the final MP3 path after FFmpeg post-processing (постобработки).

---

## 2026-05-25 — Animated Subtitle Video Maker scope decision

### Trigger

Олег уточнил целевую функцию: проект должен уметь накладывать анимированные субтитры на собственные ролики, включая karaoke highlighting (караоке-подсветку слов), настройку цвета, появления, последовательности и положения текста на экране.

### Researched Direction

Определено готовое направление реализации:

- `yt-dlp` — получение существующих субтитров источника;
- `stable-ts` / `faster-whisper` — распознавание речи и word-level timing (временные метки отдельных слов);
- `Remotion` + `@remotion/captions` — preview/rendering (предпросмотр/отрисовка) и экспорт видео с анимированными субтитрами.

### Owner Decision

Выбран вариант `A`: добавить `Animated Subtitle Video Maker` (модуль создания роликов с анимированными субтитрами) внутрь текущего проекта, а не создавать отдельный проект.

### Committed State Changes

- Расширена цель в `PROJECT_ENTRYPOINT.md`.
- Обновлено текущее состояние в `PROJECT_STATE.md`.
- Обновлены правила и MVP-boundary (граница минимально рабочей версии) в `PROJECT_RULES.md`.
- Создан результат решения: `workflow-runs/0002-animated-subtitle-module/07_RESULT.md`.

### State Separation

- Scope decision (решение о границах): committed (зафиксировано).
- Implementation (реализация): not started (не начата).
- Validation (проверка работы): not performed (не проводилась).

---

## 2026-05-25 — Phase 1 Codex execution handoff prepared

### Goal

Передать Codex узкую и проверяемую реализацию первого MVP модуля анимированных субтитров без изменения существующего downloader application (приложения-загрузчика).

### Research And Design Decision

Поскольку существующая web dashboard (веб-панель) реализована на FastAPI + обычном HTML/JavaScript, а `Remotion` требует React/Node video-rendering layer (слой отрисовки видео на React/Node), первый MVP изолируется в новой папке:

- `subtitle_studio/`

Phase 1 ограничен rendering proof (доказательством отрисовки):

- локальный ролик пользователя;
- подготовленный JSON с word-level timing (временными метками отдельных слов);
- один `KaraokePresetV1`;
- preview (предпросмотр);
- экспорт MP4 с burned-in animated subtitles (вшитыми анимированными субтитрами).

Транскрибация, получение субтитров через `yt-dlp`, несколько пресетов и интеграция с существующей веб-панелью отложены до подтверждённого первого экспорта.

### Committed Artifacts

- `workflow-runs/0002-animated-subtitle-module/02_RESEARCH.md`
- `workflow-runs/0002-animated-subtitle-module/03_PLAN.md`
- `workflow-runs/0002-animated-subtitle-module/05_IMPLEMENTATION_HANDOFF_PACKET.md`
- `workflow-runs/0002-animated-subtitle-module/06_REVIEW.md`
- Updated `PROJECT_STATE.md`

### Coordination Surface

Создан GitHub Issue `#1 Implement Phase 1 Animated Subtitle Video Maker MVP` как канал передачи задачи Codex. Issue указывает Codex читать канонический пакет и запрещает выход за утверждённый scope (границы задачи).

### Review Outcome

`accept for execution with warnings`

### State Separation

- Research and plan (исследование и план): committed (зафиксированы).
- Handoff packet (пакет реализации): committed and reviewed (зафиксирован и проверен).
- GitHub transport issue (задача-переносчик GitHub): created (создана).
- Code implementation (реализация кода): not executed yet (ещё не выполнена).
- MP4 render validation (проверка экспорта MP4): not performed yet (ещё не выполнена).

### Current Next Action

Codex выполняет GitHub Issue #1 по пакету `workflow-runs/0002-animated-subtitle-module/05_IMPLEMENTATION_HANDOFF_PACKET.md` и возвращает обязательный `EXECUTION REPORT` (отчёт о выполнении).

---

## 2026-05-29 — Cleanup of legacy parallel video-analysis naming

### Trigger

Олег попросил добить cleanup старого параллельного направления видеоанализа перед возвратом к `subtitle_studio`.

### Verified Before Change

- В репозитории не обнаружено отдельного рабочего модуля или кода старого направления.
- Остались только документационные упоминания прежнего отдельного `Video-Combine-Analyzer` как исторического имени.
- Каноническое направление уже подтверждено: будущая возможность анализа видео хранится только как `Video Content Analyzer` внутри этого репозитория.

### Committed Cleanup

- Упоминания старого параллельного имени ослаблены в `PROJECT_ENTRYPOINT.md`, `PROJECT_STATE.md` и `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md`.
- Формулировки приведены к единому правилу: не развивать отдельный параллельный продукт, а хранить знания как будущий внутренний модуль.

### Validation

- Проверено поиском по репозиторию: рабочих файлов, модулей или активных execution artifacts (артефактов исполнения) для старого отдельного направления нет.
- Cleanup носит документационный характер; рабочий код приложения и `subtitle_studio/` не изменялись.

### Current Next Action

Вернуться к блокерам `subtitle_studio` Phase 1 MVP и продолжить их исправление с проверкой рендера длиннее 8 секунд.

---

## 2026-05-29 — Handoff-readiness sync for repository-local recovery

### Trigger

Олег попросил проверить, находится ли проект в состоянии, при котором любой ИИ сможет подхватить работу без потери контекста, и привести репозиторий к такому состоянию.

### Verified Before Change

- `PROJECT_ENTRYPOINT.md` и `PROJECT_STATE.md` уже указывали правильный текущий фокус: блокеры `subtitle_studio` Phase 1 MVP.
- `PROJECT_RULES.md` отставал по полю `Current Next Action` и всё ещё ссылался на уже выполненный этап подготовки handoff packet.
- `docs/README.md` был stale (устаревшим) и ссылался на абсолютные пути вне текущего репозитория.

### Committed Cleanup

- `PROJECT_RULES.md` синхронизирован с фактическим current state (текущим состоянием).
- `docs/README.md` обновлён как self-contained repository index (самодостаточный индекс репозитория) с локальными ссылками и порядком чтения для handoff.

### Validation

- Канонические project-state artifacts (артефакты состояния проекта) теперь согласованы по текущему next action.
- Индекс документации больше не зависит от внешней папки и может использоваться другим ИИ прямо из этого репозитория.
- Рабочий код приложения и `subtitle_studio/` не изменялись.

### Remaining Limitation

- Для полной durable handoff readiness (устойчивой готовности к передаче) эти изменения ещё должны быть зафиксированы в Git commit, иначе источник истины зависит от текущего локального worktree.

### Current Next Action

Исправить блокеры `subtitle_studio` Phase 1 MVP, подтвердить рендер длиннее 8 секунд и вернуть обязательный `EXECUTION REPORT`.

---

## 2026-05-29 — Added repository-local AI entrypoint

### Trigger

Олег попросил сделать схему, при которой можно просто передать папку репозитория другому ИИ, а он сам понял, с чего начинать.

### Verified Before Change

- Репозиторий уже содержал канонические project-state artifacts (артефакты состояния проекта), но не имел стандартного локального `AGENTS.md`.
- `README.md` не давал явного указания ИИ начинать с `PROJECT_ENTRYPOINT.md`.

### Committed Cleanup

- Добавлен корневой `AGENTS.md` как repository-local AI entrypoint (локальная точка входа для ИИ).
- В `README.md` добавлен короткий раздел `AI Start`, направляющий агента к `PROJECT_ENTRYPOINT.md`.

### Validation

- Теперь репозиторий содержит явную AI-readable entry layer (слой входа, читаемый ИИ) даже без внешнего чата или дополнительных инструкций.
- Канонический current task (текущая задача) и read order (порядок чтения) дублированы в стандартной корневой точке входа.

### Current Next Action

Исправить блокеры `subtitle_studio` Phase 1 MVP, подтвердить рендер длиннее 8 секунд и вернуть обязательный `EXECUTION REPORT`.

---

## 2026-05-29 — Phase 1 MVP review blockers resolved

### Trigger

Codex завершил выполнение GitHub Issue #1. Review обнаружил блокирующие дефекты: фиксированная длительность композиции (8 секунд), неточность в README и отсутствие EXECUTION REPORT.

### Verified Before Change

- `subtitle_studio/src/Root.tsx` использовал фиксированное `durationInFrames={240}` при `fps={30}`, что обрезало контент длиннее 8 секунд.
- `subtitle_studio/README.md` содержал неверное утверждение о "blurred background layer".
- `subtitle_studio/.gitignore` не исключал директорию `build/`.
- `workflow-runs/0002-animated-subtitle-module/` не содержал EXECUTION REPORT.

### Changes Made

1. **`subtitle_studio/src/Root.tsx`** — заменён фиксированный `durationInFrames={240}` на динамическое вычисление через `calculateMetadata`. Функция читает `captions.json`, вычисляет `maxEndMs` из caption timing data, добавляет 500ms буфер и конвертирует в frames при 30fps. Fallback: 240 frames (8s) при ошибке чтения.

2. **`subtitle_studio/README.md`** — исправлено неверное утверждение: "blurred background layer" заменено на "contained foreground layer plus overlay gradient". Добавлено примечание о динамической длительности композиции.

3. **`subtitle_studio/.gitignore`** — добавлена строка `build` для исключения директории сборки Remotion.

4. **`workflow-runs/0002-animated-subtitle-module/08_EXECUTION_REPORT.md`** — создан полный structured execution report со статусом `completed`, списком изменённых файлов, выполненными командами, результатами валидации и статусом блокеров.

### Commands Run

```powershell
# Install dependencies
cd subtitle_studio
npm install --legacy-peer-deps

# TypeScript check (passed)
npx tsc --noEmit

# ESLint check (passed, only TS version warning)
npx eslint src

# Remotion bundle (passed)
npx remotion bundle

# Generate test video (10 seconds, 1080x1920, blue background)
ffmpeg -f lavfi -i color=c=blue:s=1080x1920:d=10 -f lavfi -i anullsrc=r=44100:cl=mono ^
  -c:v libx264 -preset ultrafast -crf 28 -c:a aac -shortest -y ^
  public/local-assets/validation-input.mp4

# First render (240 frames — default fallback)
npx remotion render KaraokeVideo out/karaoke-preview.mp4

# Second render after calculateMetadata fix (255 frames — computed from captions)
npx remotion render KaraokeVideo out/karaoke-preview-v2.mp4
```

### Validation Results

- ✅ TypeScript compilation: no errors
- ✅ ESLint: no errors (only TS version compatibility warning, non-blocking)
- ✅ Remotion bundle: successful
- ✅ Render with default duration: 240 frames (8s) — MP4 produced (782.6 kB)
- ✅ Render with dynamic duration: 255 frames (8.5s) — MP4 produced (805.5 kB)
- ✅ Duration is no longer fixed at 8 seconds: `calculateMetadata` reads captions.json and computes `durationInFrames` dynamically
- ✅ Test video (10s, 1080x1920) generated and used as input

### Blockers Resolved

- **BLOCKER-001 (EXECUTION REPORT)**: RESOLVED — `08_EXECUTION_REPORT.md` создан.
- **BLOCKER-002 (фиксированная длительность)**: RESOLVED — `calculateMetadata` динамически вычисляет длительность. Рендер: 255 frames вместо 240.
- **NOTE-001 (README)**: RESOLVED — документация исправлена.

### State Separation

- Review blockers (блокеры ревью): resolved (устранены).
- Implementation (реализация): completed (завершена).
- Validation (проверка): completed (завершена).
- Visual verification (визуальная проверка): pending (ожидает владельца).

### Current Next Action

Владелец должен визуально проверить отрендеренный MP4 (`subtitle_studio/out/karaoke-preview-v2.mp4`), чтобы подтвердить корректную работу karaoke highlighting. После визуального подтверждения Phase 1 MVP может быть принят, и можно планировать Phase 2 (интеграция транскрибации).

---

## 2026-05-29 — Phase 1 MVP accepted after owner visual review

### Trigger

Олег провёл визуальную проверку финального артефакта `karaoke-preview-v5.mp4` (255 frames, 805.8 kB, 8.5s при 30fps). Phase 1 MVP принят.

### Verified Before Change

- `subtitle_studio/src/Root.tsx` — calculateMetadata использует staticFile() + fetch() для загрузки captions.json в render mode (не fs.readFileSync, не fetch к localhost:3000). Remotion render mode запускает код в headless Chrome, где fs.readFileSync недоступен. staticFile() работает в render mode — Remotion сам скачивает файлы из public/ и раздаёт их.
- `subtitle_studio/render-props.json` — создан для передачи captions через --props флаг Remotion.
- `PROJECT_STATE.md` — обновлён: current_step: 08_ACCEPTED, статус accepted after owner visual review.
- `PROJECT_ENTRYPOINT.md` — обновлён: Canonical Next Action — Phase 1 MVP принят, планировать Phase 2.
- `PROJECT_RULES.md` — обновлён: Current Next Action — Phase 1 MVP принят, планировать Phase 2.

### Owner Visual Review

- Проверен файл: `subtitle_studio/out/karaoke-preview-v5.mp4`
- Результат: принят (accepted)
- Финальный артефакт: 255 frames, 805.8 kB, 8.5s при 30fps

### State Separation

- Phase 1 MVP implementation: completed and accepted (завершена и принята).
- Visual verification: completed and accepted (завершена и принята).
- Phase 2 (transcription integration): not started (не начата).

### Current Next Action

Phase 1 MVP принят. Планировать Phase 2 (интеграция транскрибации через stable-ts / faster-whisper). Ожидание отдельного решения владельца о начале Phase 2.
