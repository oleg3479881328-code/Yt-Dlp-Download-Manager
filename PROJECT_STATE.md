---
status: in-progress
project_mode: compact
current_step: 09_SCIENCE_ASSEMBLY_MVP_DRAFT
current_run: workflow-runs/0003-science-video-assembly-mvp/
last_updated: 2026-06-20
next_action: Validate and harden PR #3 Science Video Assembly MVP draft scaffold. Keep it isolated. No automatic YouTube downloading for publication. Phase 2 transcription integration remains planned but is not the active task while PR #3 is open.
---

# PROJECT STATE — yt-dlp Download Manager

## Current Phase

Личный локальный инструмент остаётся в `compact mode` Project Execution OS.

Phase 1 `Animated Subtitle Video Maker` был реализован в `subtitle_studio/`, проверен и **принят владельцем после визуальной проверки**.

20 июня 2026 года владелец принял отдельное решение: подготовить и максимально продвинуть bounded MVP-направление `Science Video Assembly MVP` внутри этого репозитория. Это не отменяет Phase 2 transcription plan, но временно делает активной задачей PR `#3 EXECUTOR PACKET: Science Video Assembly MVP`.

## Purpose

Полный локальный цикл работы с роликами:

- скачивание медиа через `yt-dlp`;
- web dashboard для очереди, истории, настроек и статусов;
- Chrome extension для быстрого запуска скачивания из браузера;
- local transcription и получение субтитров;
- `Animated Subtitle Video Maker` для собственных видео пользователя;
- `Science Video Assembly MVP` как изолированный rights-aware workflow: script -> visual beats -> stock candidates -> approval -> timeline/source ledger;
- future candidate: `Video Content Analyzer` для анализа локальных или разрешённых видео через транскрипт с таймкодами и выбранные кадры.

## Confirmed Existing Repository State

- `app/` содержит FastAPI dashboard, SQLite state, background worker и yt-dlp service.
- `chrome_extension/` и `native_host/` образуют отдельный локальный контур расширения.
- `subtitle_studio/` существует как изолированная Remotion реализация Phase 1; Phase 1 принят владельцем.
- `research/VIDEO_CONTENT_ANALYZER_DONOR_ASSESSMENT.md` фиксирует будущий модуль видеоанализа и донорские подходы.
- `workflow-runs/0003-science-video-assembly-mvp/` содержит review, architecture, JSON schemas и implementation handoff.
- `science_assembly/` существует в PR `#3` как draft scaffold и требует validation / hardening перед merge.

## Confirmed Decisions

1. Проект предназначен для личного использования, а не для Chrome Web Store или продажи.
2. `Yt-Dlp-Download-Manager` остаётся единственным основным видео-проектом.
3. `Animated Subtitle Video Maker` разрешён внутри текущего проекта и Phase 1 принят.
4. Phase 2 transcription integration остаётся следующим крупным направлением, но не является активной задачей, пока открыт PR `#3`.
5. Решение владельца от 2026-06-20: разрешён bounded draft / MVP track `Science Video Assembly MVP` внутри этого репозитория.
6. `Science Video Assembly MVP` не является YouTube scraper. Автоматическое скачивание YouTube-контента для публикации запрещено в MVP-1.
7. Разрешённая MVP-граница: DeepSeek-assisted JSON planning, stock source search, manual approval, timeline JSON, source ledger JSON.
8. `Video Content Analyzer` по-прежнему не начинать как отдельный полноценный модуль без отдельного решения; использовать только ранее сохранённые research patterns.

## Active Execution Handoff

- Active PR: `#3 EXECUTOR PACKET: Science Video Assembly MVP`.
- Active workflow: `workflow-runs/0003-science-video-assembly-mvp/`.
- Draft code: `science_assembly/`.
- Required executor start: PR `#3` body, then `workflow-runs/0003-science-video-assembly-mvp/03_IMPLEMENTATION_HANDOFF_PACKET.md`.

## Current Safety Boundaries

- Не реализовывать automatic YouTube downloading for publication.
- Не обходить rights checks.
- Не ломать существующий downloader, extension/native host или принятый `subtitle_studio/` Phase 1.
- Не коммитить API keys.
- Не заявлять, что pipeline работает, без локального запуска и execution report.

## Latest Result

PR `#3` содержит planning packet и draft scaffold. Первое review обнаружило блокеры: source-of-truth рассинхронизация, второй stock adapter placeholder, duplicate candidate IDs и отсутствие тестов. Эти замечания должны быть закрыты в PR `#3` перед merge.

## Current Next Action

Закрыть review blockers по PR `#3`, запустить offline smoke test и pytest, затем вернуть `EXECUTION REPORT`. После принятия или отклонения PR `#3` вернуться к планированию Phase 2 transcription integration.
