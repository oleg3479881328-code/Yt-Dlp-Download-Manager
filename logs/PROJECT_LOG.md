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
