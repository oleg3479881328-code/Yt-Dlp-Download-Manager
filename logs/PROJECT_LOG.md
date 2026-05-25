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

### Current Next Action

Подготовить `Implementation Handoff Packet` (пакет задания на реализацию) для Codex на Phase 1 MVP: собственный ролик → тайминги слов → один караоке-пресет → предпросмотр → экспорт MP4 с вшитыми субтитрами.
