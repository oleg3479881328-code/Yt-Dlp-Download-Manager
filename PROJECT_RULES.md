# PROJECT RULES — yt-dlp Download Manager

## Scope

Этот проект — личный локальный Windows-инструмент Олега для:

- скачивания медиа через `yt-dlp`;
- управления загрузками через web dashboard;
- запуска загрузок через Chrome extension;
- local transcription в `.srt` и `.txt`;
- создания собственных видео с burned-in animated subtitles;
- rights-aware assembly of educational / science-popular videos from scripts and allowed stock/source candidates.

Не считать проект публичным продуктом, коммерческим приложением или расширением для Chrome Web Store без отдельного решения владельца.

## Operating Mode

- Project Execution OS mode: `compact`.
- Repository is the durable source of truth.
- Current state lives in `PROJECT_STATE.md`.
- Historical sequence lives in `logs/PROJECT_LOG.md`.
- Each substantial review or implementation change should leave one concrete next action.

## State Separation Rules

Всегда различать:

- proposed state — обсуждено, но не записано и не проверено;
- committed state — записано в GitHub repository;
- validated state — подтверждено реальным запуском или тестом;
- reviewed state — оценено с выводом о принятии, предупреждении или блокировке.

Нельзя утверждать, что загрузка, расширение, транскрибация, рендеринг видео, AI pipeline или исправление работают, пока нет результата реального запуска или теста.

## Current Architecture Rules

1. Web dashboard и standalone Chrome extension/native host сейчас разрешены как два отдельных runtime contours, потому что инструмент личный.
2. Не начинать архитектурное объединение существующих контуров без отдельной задачи и подтверждённой боли от дублирования.
3. `Animated Subtitle Video Maker` разрешён внутри текущего репозитория как отдельный узкий модуль; Phase 1 принят.
4. `Science Video Assembly MVP` разрешён владельцем 2026-06-20 как bounded draft track внутри текущего репозитория через PR `#3`.
5. `science_assembly/` должен оставаться изолированным до validation and acceptance.
6. Новый AI/source workflow не должен ломать или переписывать существующую загрузку медиа, extension/native host или `subtitle_studio/`.

## Quality Rules

1. MVP-first: первая версия нового модуля должна доказывать один узкий workflow, а не строить полноценный редактор.
2. Один проверяемый шаг за раз.
3. Любой предполагаемый баг сначала помечать как `suspected`, затем подтверждать запуском и только после этого исправлять.
4. После реализации запускать сценарий, который доказывает результат.
5. Не хранить скачанные файлы, исходные пользовательские ролики, отрендеренные видео, локальную базу данных, сборки native host или виртуальное окружение в GitHub.
6. Для AI-generated JSON требуется validation before use.

## Science Video Assembly MVP Boundary

Разрешённая MVP-1 граница:

1. short script;
2. DeepSeek-assisted visual beats JSON;
3. stock source candidates from allowed providers;
4. DeepSeek-assisted ranking JSON;
5. manual approval file;
6. timeline JSON;
7. source ledger JSON.

Preview render optional. Publication automation out of scope.

## Current Forbidden Actions

- не превращать личный инструмент в публичный продукт без отдельного решения;
- не начинать публикацию Chrome extension;
- не переписывать существующие download runtimes ради нового модуля;
- не считать suspected bugs доказанными без реального запуска;
- не расширять `subtitle_studio` без отдельной задачи;
- не реализовывать automatic YouTube downloading for publication в `Science Video Assembly MVP`;
- не обходить rights checks;
- не коммитить API keys.

## Local Safety Rules

- Приложение должно оставаться локальным и использовать loopback address `127.0.0.1`, если отдельно не принято другое решение.
- Не публиковать локальные пути, скачанные пользовательские медиа, исходные ролики, отрендеренные видео, логи с приватными URL или локальную SQLite-базу.
- Проверять изменения в native host особенно внимательно: он взаимодействует с локальной файловой системой и запускает локальные программы.

## Evidence Rules

Для существенных изменений сохранять в `logs/PROJECT_LOG.md`:

- дату;
- что проверено или изменено;
- какой вывод подтверждён;
- что ещё не проверено;
- один следующий шаг.

## Current Next Action

Закрыть PR `#3` review blockers, запустить offline smoke test and pytest, вернуть execution report. После принятия или закрытия PR `#3` вернуться к Phase 2 transcription planning.
