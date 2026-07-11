const DEFAULT_FILTERS = Object.freeze({
  status: "all",
  warnings: "all",
  search: "",
  sort: "score_desc",
});

export function buildEmptyProjectWorkspaceState(debugLogs = []) {
  return {
    dashboard: null,
    workDir: "",
    loadState: { key: "load_waiting", className: "status-queued", params: {} },
    activity: null,
    quickMixEstimate: { status: "idle" },
    lastExportedPaths: [],
    sourceScan: null,
    zipImportResult: null,
    selectedSourcePath: "",
    manualSourceOverride: false,
    quickMixResult: null,
    sourceWorkDirAuto: true,
    selectedCandidateIds: new Set(),
    draftNotesByCandidateId: new Map(),
    debugLogs: [...debugLogs],
    filters: { ...DEFAULT_FILTERS },
    projectMaterialsFilters: {
      status: "all",
      mediaType: "all",
      search: "",
    },
    selectedMaterialEpisodeId: "",
    takeEditor: null,
  };
}

const state = {
  locale: "ru",
  ...buildEmptyProjectWorkspaceState(),
};

const STATUS_ORDER = {
  generated: 0,
  previewed: 1,
  approved: 2,
  rejected: 3,
  exported: 4,
};

const LOCALES = ["ru", "en"];
const DASHBOARD_LOCALE_STORAGE_KEY = "videoMixDashboardLocale";
let dashboardInitialized = false;
let activityTimerId = null;
let quickMixEstimateDebounceId = null;

const TRANSLATIONS = {
  ru: {
    page_title: "VIDEO MIX Дашборд",
    source_title: "Материалы",
    source_help: "Сначала выберите папку с исходными видео и создайте или обновите VIDEO MIX проект.",
    source_dir_label: "Папка с материалами",
    source_project_name_label: "Имя проекта",
    source_workdir_label: "Выходной work_dir",
    source_browse: "Выбрать материалы",
    source_browse_zip: "Загрузить ZIP",
    source_open_dir: "Открыть папку",
    source_open_workdir: "Открыть work_dir",
    source_drop_zip: "Перетащите папку или ZIP сюда",
    source_drop_zip_hover: "Отпустите, чтобы загрузить папку или ZIP",
    source_drop_zip_processing: "Загружаю материалы...",
    source_drop_zip_ready: "Принято: {name}",
    source_drop_zip_empty: "Не удалось прочитать содержимое папки",
    source_scan: "Сканировать",
    source_plan: "Создать / обновить проект",
    reset_button: "Reset",
    source_scan_empty: "Скан материалов ещё не запускался.",
    source_scan_result_title: "Результат сканирования",
    source_zip_result_title: "Результат ZIP-импорта",
    source_zip_blocks: "Найдено блоков",
    source_zip_takes: "Найдено дублей",
    source_zip_marker_videos: "Видео с маркерами",
    source_zip_marker_takes: "Создано marker-takes",
    source_zip_ignored: "Игнорировано файлов",
    source_zip_warnings: "Warnings",
    source_zip_warnings_title: "Предупреждения импорта",
    materials_stage_title: "Project Materials",
    materials_stage_help: "Один master asset в проекте, несколько Take-ссылок по назначению или reuse.",
    materials_open_modal: "Открыть Project Materials",
    materials_add_episode: "Добавить Episode",
    materials_add_file: "Добавить файл",
    materials_filter_status: "Статус",
    materials_filter_type: "Тип",
    materials_search: "Поиск",
    materials_search_placeholder: "filename",
    materials_count_all: "Всего",
    materials_count_unassigned: "Unassigned",
    materials_count_assigned: "Assigned",
    materials_count_reused: "Reused",
    materials_asset_unassigned: "Unassigned",
    materials_asset_assigned: "Assigned",
    materials_asset_reused: "Reused",
    materials_assign_here: "Assign сюда",
    materials_reuse_here: "Use again",
    materials_episode_selected: "Активный Episode",
    materials_episode_drop: "Перетащите сюда файл или material card",
    materials_episode_empty: "В этом Episode пока нет Takes.",
    materials_take_remove: "Убрать",
    materials_no_assets: "Нет материалов под текущие фильтры.",
    materials_no_episodes: "Episodes появятся после загрузки work_dir.",
    materials_assignment_locations: "Назначено в",
    materials_add_episode_done: "Episode добавлен",
    materials_episode_drop_done: "Файлы добавлены в Episode",
    materials_external_drop_unsupported: "Этот браузер не отдает локальный путь файла для внешнего drag-and-drop.",
    materials_take_edit: "Редактировать",
    materials_take_move_left: "Левее",
    materials_take_move_right: "Правее",
    timeline_title: "Timeline",
    timeline_help: "Горизонтальные дорожки будущего монтажа, собранные из Episode/Take назначений.",
    timeline_empty: "Назначьте хотя бы один Take, чтобы появился видимый timeline.",
    timeline_row_empty: "В этой дорожке пока нет Take blocks.",
    timeline_block_assigned: "Assigned",
    timeline_block_reused: "Reused",
    take_editor_title: "Редактор Take",
    take_editor_help: "Подрезка дубля и порядок внутри Episode.",
    take_editor_episode: "Episode",
    take_editor_take: "Take",
    take_editor_trim_start: "Начало, сек",
    take_editor_trim_end: "Конец, сек",
    take_editor_asset_duration: "Длительность исходника",
    take_editor_trim_duration: "Длительность Take",
    take_editor_save: "Сохранить",
    take_editor_cancel: "Отмена",
    take_editor_open_file: "Открыть файл",
    take_editor_no_take: "Выберите Take.",
    take_editor_validation: "Укажите корректный trim: начало должно быть меньше конца.",
    take_editor_saved: "Take обновлён",
    take_editor_reordered: "Порядок Take обновлён",
    source_scan_total_files: "Всего файлов",
    source_scan_supported_media: "Поддерживаемых media",
    source_scan_supported_videos: "Видео",
    source_scan_supported_photos: "Фото",
    source_scan_ignored: "Игнорировано / не поддерживается",
    source_scan_preview: "Превью файлов",
    source_scan_preview_more: "И ещё {count} файл(ов)",
    source_scan_actions: "Быстрые действия",
    project_files_title: "Файлы проекта",
    project_files_help: "Реальные файлы в папке проекта: можно добавлять и удалять.",
    project_files_add: "Добавить файлы",
    project_files_open: "Открыть папку проекта",
    project_files_empty: "Загрузите проект, чтобы увидеть файлы.",
    project_files_count: "{count} файлов",
    project_files_remove: "Удалить",
    project_files_open_file: "Открыть",
    project_files_media_video: "Видео",
    project_files_media_photo: "Фото",
    project_files_media_other: "Другое",
    project_files_confirm_remove: "Удалить файл {name} из проекта?",
    quickmix_title: "Быстрый микс",
    quickmix_help: "Прямая генерация готовых MP4 без обязательного approve/reject.",
    quickmix_duration_label: "Секунд на ролик",
    quickmix_count_label: "Сколько роликов",
    quickmix_episode_range_label: "Эпизоды внутри ролика, сек",
    quickmix_episode_min_label: "От",
    quickmix_episode_max_label: "До",
    quickmix_music_label: "Музыкальный трек (опционально)",
    quickmix_music_browse: "Выбрать трек",
    quickmix_music_drop: "Перетащите файл сюда",
    quickmix_use_music_duration: "Использовать всю длину трека",
    quickmix_opening_label: "Начальный кадр / клип (опционально)",
    quickmix_opening_browse: "Выбрать начало",
    quickmix_opening_drop: "Перетащите файл сюда",
    quickmix_closing_label: "Конечный кадр / клип (опционально)",
    quickmix_closing_browse: "Выбрать финал",
    quickmix_closing_drop: "Перетащите файл сюда",
    quickmix_use_closing_duration: "Использовать всю длину финала",
    quickmix_selected_none: "Файл не выбран",
    quickmix_selected_open: "Открыть файл",
    quickmix_selected_play: "Play",
    quickmix_selected_pause: "Pause",
    quickmix_selected_remove: "Удалить",
    quickmix_button: "Сгенерировать ролики",
    quickmix_estimate_idle: "Оценка появится после выбора материалов",
    quickmix_estimate_loading: "Считаю ориентир по текущему материалу...",
    quickmix_estimate_ready: "Ориентир: около {count} уникальных видео",
    quickmix_estimate_warn: "Если запросить больше {count}, повторы станут вероятны",
    quickmix_estimate_none: "Для такой длительности уникальных роликов без повторов почти не остаётся",
    quickmix_estimate_error: "Не удалось посчитать ориентир",
    quickmix_timer_idle: "Время: -",
    quickmix_timer_running: "Идёт: {elapsed}",
    quickmix_timer_done: "Затрачено: {elapsed}",
    quickmix_empty: "Quick Mix ещё не запускался.",
    quickmix_result_title: "Результат Quick Mix",
    quickmix_generated_count: "Сгенерировано MP4",
    quickmix_episode_groups: "Эпизоды",
    quickmix_take_count: "Найдено дублей",
    quickmix_marker_groups: "Эпизоды с magenta-разделителями",
    quickmix_variants_title: "Варианты",
    quickmix_variant_order: "Порядок эпизодов",
    quickmix_variant_takes: "Выбранные дубли",
    quickmix_output_paths: "Готовые файлы",
    quickmix_photos_supported: "Фото поддерживаются",
    quickmix_photos_unsupported: "Фото не поддерживаются",
    quickmix_duration_source_music: "Длительность взята из музыкального трека",
    quickmix_duration_source_manual: "Длительность взята из поля секунд",
    quickmix_music_used: "Музыка",
    quickmix_opening_used: "Стартовый медиа-кадр",
    quickmix_closing_used: "Финальный медиа-кадр",
    hero_title: "Локальный дашборд для Quick Mix, ревью и экспорта",
    hero_copy: "Выберите исходные материалы, запустите Быстрый микс для прямой генерации MP4 или загрузите готовый VIDEO MIX work_dir для обычного ревью, approve/reject и экспорта.",
    open_review: "Открыть review.html",
    open_exports: "Открыть exports",
    open_workdir: "Открыть work_dir",
    load_title: "Загрузка work_dir",
    load_help: "Используйте уже созданную рабочую папку VIDEO MIX.",
    load_waiting: "Ожидание",
    activity_title: "Сейчас происходит",
    activity_idle: "Ничего не выполняется",
    activity_elapsed: "Прошло",
    activity_running: "Идёт выполнение...",
    button_busy: "В работе...",
    workdir_label: "VIDEO MIX work_dir",
    browse_workdir: "Выбрать папку",
    load_dashboard: "Загрузить дашборд",
    copy_url: "Копировать URL",
    project_meta_empty: "Загрузите work_dir, чтобы увидеть метаданные проекта и сводные счётчики.",
    pipeline_title: "Пайплайн",
    pipeline_help: "Путь от ассетов до экспорта в одном локальном процессе.",
    pipeline_open: "Показать пайплайн",
    pipeline_close: "Закрыть",
    actions_title: "Действия",
    actions_help: "Используется только текущее поведение VIDEO MIX.",
    actions_help_quickmix: "В режиме Quick Mix кандидаты не нужны: готовые MP4 уже лежат в папке exports.",
    export_approved: "Экспортировать одобренных кандидатов",
    open_ready_videos: "Открыть папку с готовыми роликами",
    refresh_dashboard: "Обновить дашборд",
    debug_title: "Логи",
    debug_help: "Клики, запросы, ответы и ошибки выводятся сюда автоматически.",
    debug_clear: "Очистить логи",
    debug_empty: "Логи появятся после первого действия.",
    candidates_title: "Карточки кандидатов",
    candidates_help: "Миниатюра, score, template, предупреждения, исходные файлы и быстрые действия.",
    candidates_open: "Открыть кандидатов",
    candidates_close: "Закрыть",
    quickmix_outputs_title: "Готовые ролики",
    quickmix_outputs_help: "MVP-режим без кандидатов: всё, что сгенерировано, уже сохранено в exports.",
    quickmix_output_count: "{count} роликов",
    quickmix_no_outputs: "Готовые MP4 появятся здесь сразу после генерации Quick Mix.",
    quickmix_ready_files: "Готовые MP4",
    filter_status_label: "Статус",
    filter_status_all: "Все",
    filter_status_generated: "Сгенерированы",
    filter_status_approved: "Одобрены",
    filter_status_rejected: "Отклонены",
    filter_status_exported: "Экспортированы",
    filter_warnings_label: "Предупреждения",
    filter_warnings_all: "Все",
    filter_warnings_with: "С предупреждениями",
    filter_warnings_without: "Без предупреждений",
    sort_label: "Сортировка",
    sort_score_desc: "Score по убыванию",
    sort_score_asc: "Score по возрастанию",
    sort_duration_desc: "Длительность по убыванию",
    sort_duration_asc: "Длительность по возрастанию",
    sort_status: "По статусу",
    sort_template: "По template",
    sort_source: "По имени исходного файла",
    search_label: "Поиск",
    search_placeholder: "template или имя исходного файла",
    selected_count: "{count} выбрано",
    visible_count: "{count} видно",
    select_visible: "Выбрать видимые",
    clear_selection: "Сбросить выбор",
    approve_selected: "Одобрить выбранные",
    reject_selected: "Отклонить выбранные",
    no_workdir_loaded: "work_dir ещё не загружен.",
    no_candidates_match_filters: "Нет кандидатов, подходящих под текущие фильтры.",
    project_label: "Проект",
    pack_label: "Пакет",
    root_label: "Корень",
    summary_assets: "Ассеты",
    summary_clips: "Клипы",
    summary_candidates: "Кандидаты",
    summary_approved: "Одобрено",
    summary_exported: "Экспортировано",
    summary_rejected: "Отклонено",
    candidate_count: "{count} кандидатов",
    pipeline_empty: "Состояние пайплайна появится после загрузки work_dir.",
    pipeline_item_count: "{count} шт.",
    pipeline_assets: "Ассеты",
    pipeline_clips: "Клипы",
    pipeline_candidates: "Кандидаты",
    pipeline_review: "Ревью",
    pipeline_approval: "Одобрение",
    pipeline_export: "Экспорт",
    pipeline_state_ready: "готово",
    pipeline_state_pending: "ожидание",
    pipeline_state_active: "в работе",
    copy_approve: "Копировать approve",
    copy_reject: "Копировать reject",
    thumbnail_alt: "Миниатюра кандидата {candidateId}",
    no_thumbnail: "Без миниатюры",
    no_warnings: "Без предупреждений",
    no_exports: "Экспортов пока нет.",
    no_source_clips: "Исходные клипы не привязаны.",
    no_tags: "без тегов",
    select: "Выбрать",
    status_generated: "Сгенерирован",
    status_previewed: "Просмотрен",
    status_approved: "Одобрен",
    status_rejected: "Отклонён",
    status_exported: "Экспортирован",
    metric_score: "Score",
    metric_duration: "Длительность",
    metric_source_files: "Исходные файлы",
    section_warnings: "Предупреждения",
    section_source_filenames: "Имена исходных файлов",
    section_review_note: "Комментарий ревью",
    note_placeholder: "необязательный комментарий ревью",
    section_exports: "Экспорт",
    approve: "Одобрить",
    reject: "Отклонить",
    command_copied: "Команда скопирована",
    no_export_paths_session: "В этой сессии новых путей экспорта пока нет.",
    load_state_enter_source_dir: "Укажите папку с материалами",
    load_state_enter_duration: "Укажите корректную длительность в секундах",
    load_state_enter_output_count: "Укажите корректное количество роликов",
    load_state_enter_episode_range: "Укажите корректный диапазон эпизодов",
    load_state_enter_workdir: "Укажите work_dir",
    load_state_browsing_workdir: "Открываю выбор папки...",
    load_state_browse_canceled: "Выбор папки отменён",
    load_state_browsing_source: "Открываю выбор папки с материалами...",
    load_state_source_browse_canceled: "Выбор папки с материалами отменён",
    load_state_browsing_source_zip: "Открываю выбор ZIP-архива...",
    load_state_source_zip_browse_canceled: "Выбор ZIP-архива отменён",
    load_state_uploading_file: "Загружаю перетащенный файл...",
    load_state_uploaded_file: "Файл загружен",
    load_state_project_files_adding: "Добавляю файлы в проект...",
    load_state_project_files_added: "Файлы добавлены в проект",
    load_state_project_file_removing: "Удаляю файл из проекта...",
    load_state_project_file_removed: "Файл удалён из проекта",
    load_state_drop_zip_only: "Для материалов через drag and drop сейчас поддерживается только ZIP",
    load_state_scanning_source: "Сканирую материалы...",
    load_state_source_scanned: "Материалы просканированы",
    load_state_materials_assigning: "Назначаю material в Episode...",
    load_state_materials_assigned: "Material назначен",
    load_state_materials_reusing: "Добавляю reuse material...",
    load_state_materials_reused: "Material повторно использован",
    load_state_materials_unassigning: "Убираю Take...",
    load_state_materials_unassigned: "Take убран",
    load_state_materials_episode_needed: "Сначала выберите Episode",
    load_state_planning_source: "Создаю план проекта...",
    load_state_generating_review: "Генерирую review и thumbnails...",
    load_state_source_loaded: "Проект создан и загружен",
    load_state_quickmix_generating: "Генерирую Quick Mix MP4...",
    load_state_quickmix_ready: "Quick Mix готов",
    load_state_quickmix_ready_opened: "Quick Mix готов, папка с роликами открыта",
    load_state_browsing_music: "Открываю выбор музыкального файла...",
    load_state_music_browse_canceled: "Выбор музыкального файла отменён",
    load_state_browsing_opening: "Открываю выбор стартового файла...",
    load_state_opening_browse_canceled: "Выбор стартового файла отменён",
    load_state_browsing_closing: "Открываю выбор финального файла...",
    load_state_closing_browse_canceled: "Выбор финального файла отменён",
    load_state_loading: "Загрузка...",
    load_state_loaded: "Загружено",
    load_state_reset_done: "Проект сброшен",
    load_state_approving: "Одобрение...",
    load_state_rejecting: "Отклонение...",
    load_state_approved: "Одобрено",
    load_state_rejected: "Отклонено",
    load_state_select_candidate_first: "Сначала выберите хотя бы одного кандидата",
    load_state_no_visible_selected: "Среди выбранных нет кандидатов, видимых по текущим фильтрам",
    confirm_reject_selected: "Отклонить {count} выбранных кандидатов?",
    confirm_approve_selected: "Одобрить {count} выбранных кандидатов?",
    load_state_bulk_approving: "Массовое одобрение...",
    load_state_bulk_rejecting: "Массовое отклонение...",
    load_state_bulk_approved: "Массовое одобрение завершено",
    load_state_bulk_rejected: "Массовое отклонение завершено",
    confirm_export_approved: "Экспортировать всех кандидатов, которые сейчас одобрены?",
    load_state_exporting: "Экспорт...",
    load_state_export_complete: "Экспорт завершён",
    load_state_opened: "Открыто: {target}",
    url_copied: "URL скопирован",
    request_failed: "Запрос не выполнен",
  },
  en: {
    page_title: "VIDEO MIX Dashboard",
    source_title: "Materials",
    source_help: "Choose a source videos folder first, then create or update the VIDEO MIX project.",
    source_dir_label: "Source materials folder",
    source_project_name_label: "Project name",
    source_workdir_label: "Output work_dir",
    source_browse: "Browse materials",
    source_browse_zip: "Upload ZIP",
    source_open_dir: "Open folder",
    source_open_workdir: "Open work_dir",
    source_drop_zip: "Drop folder or ZIP here",
    source_drop_zip_hover: "Release to upload folder or ZIP",
    source_drop_zip_processing: "Uploading materials...",
    source_drop_zip_ready: "Accepted: {name}",
    source_drop_zip_empty: "Could not read folder contents",
    source_scan: "Scan",
    source_plan: "Create / update project",
    reset_button: "Reset",
    source_scan_empty: "Materials scan has not been run yet.",
    source_scan_result_title: "Scan result",
    source_zip_result_title: "ZIP import result",
    source_zip_blocks: "Blocks found",
    source_zip_takes: "Takes found",
    source_zip_marker_videos: "Marker videos",
    source_zip_marker_takes: "Marker takes created",
    source_zip_ignored: "Ignored files",
    source_zip_warnings: "Warnings",
    source_zip_warnings_title: "Import warnings",
    materials_stage_title: "Project Materials",
    materials_stage_help: "One master asset in the project, with multiple Take links through assign or reuse.",
    materials_open_modal: "Open Project Materials",
    materials_add_episode: "Add Episode",
    materials_add_file: "Add file",
    materials_filter_status: "Status",
    materials_filter_type: "Type",
    materials_search: "Search",
    materials_search_placeholder: "filename",
    materials_count_all: "All",
    materials_count_unassigned: "Unassigned",
    materials_count_assigned: "Assigned",
    materials_count_reused: "Reused",
    materials_asset_unassigned: "Unassigned",
    materials_asset_assigned: "Assigned",
    materials_asset_reused: "Reused",
    materials_assign_here: "Assign here",
    materials_reuse_here: "Use again",
    materials_episode_selected: "Active Episode",
    materials_episode_drop: "Drop a file or material card here",
    materials_episode_empty: "This Episode has no Takes yet.",
    materials_take_remove: "Remove",
    materials_no_assets: "No project materials match the current filters.",
    materials_no_episodes: "Episodes will appear after loading a work_dir.",
    materials_assignment_locations: "Assigned to",
    materials_add_episode_done: "Episode added",
    materials_episode_drop_done: "Files added to Episode",
    materials_external_drop_unsupported: "This browser does not expose local file paths for external drag-and-drop.",
    materials_take_edit: "Edit",
    materials_take_move_left: "Left",
    materials_take_move_right: "Right",
    timeline_title: "Timeline",
    timeline_help: "Horizontal editing tracks built from the current Episode/Take assignments.",
    timeline_empty: "Assign at least one Take to make the visible timeline appear.",
    timeline_row_empty: "This track has no Take blocks yet.",
    timeline_block_assigned: "Assigned",
    timeline_block_reused: "Reused",
    take_editor_title: "Take editor",
    take_editor_help: "Trim the Take and control its order inside the Episode.",
    take_editor_episode: "Episode",
    take_editor_take: "Take",
    take_editor_trim_start: "Start, sec",
    take_editor_trim_end: "End, sec",
    take_editor_asset_duration: "Source duration",
    take_editor_trim_duration: "Take duration",
    take_editor_save: "Save",
    take_editor_cancel: "Cancel",
    take_editor_open_file: "Open file",
    take_editor_no_take: "Select a Take.",
    take_editor_validation: "Enter a valid trim: start must be less than end.",
    take_editor_saved: "Take updated",
    take_editor_reordered: "Take order updated",
    source_scan_total_files: "Total files",
    source_scan_supported_media: "Supported media",
    source_scan_supported_videos: "Videos",
    source_scan_supported_photos: "Photos",
    source_scan_ignored: "Ignored / unsupported",
    source_scan_preview: "Preview files",
    source_scan_preview_more: "And {count} more file(s)",
    source_scan_actions: "Quick actions",
    project_files_title: "Project files",
    project_files_help: "Actual files inside the project folder: you can add and remove them.",
    project_files_add: "Add files",
    project_files_open: "Open project folder",
    project_files_empty: "Load a project to see its files.",
    project_files_count: "{count} files",
    project_files_remove: "Remove",
    project_files_open_file: "Open",
    project_files_media_video: "Video",
    project_files_media_photo: "Photo",
    project_files_media_other: "Other",
    project_files_confirm_remove: "Remove {name} from the project?",
    quickmix_title: "Quick Mix",
    quickmix_help: "Direct MP4 generation without mandatory approve/reject.",
    quickmix_duration_label: "Seconds per video",
    quickmix_count_label: "Number of videos",
    quickmix_episode_range_label: "Episode length inside video, sec",
    quickmix_episode_min_label: "From",
    quickmix_episode_max_label: "To",
    quickmix_music_label: "Music track (optional)",
    quickmix_music_browse: "Browse track",
    quickmix_music_drop: "Drop file here",
    quickmix_use_music_duration: "Use full track length",
    quickmix_opening_label: "Opening frame / clip (optional)",
    quickmix_opening_browse: "Browse opening",
    quickmix_opening_drop: "Drop file here",
    quickmix_closing_label: "Closing frame / clip (optional)",
    quickmix_closing_browse: "Browse ending",
    quickmix_closing_drop: "Drop file here",
    quickmix_use_closing_duration: "Use full closing length",
    quickmix_selected_none: "No file selected",
    quickmix_selected_open: "Open file",
    quickmix_selected_play: "Play",
    quickmix_selected_pause: "Pause",
    quickmix_selected_remove: "Remove",
    quickmix_button: "Generate videos",
    quickmix_estimate_idle: "Estimate will appear after source materials are selected",
    quickmix_estimate_loading: "Estimating from the current materials...",
    quickmix_estimate_ready: "Estimate: about {count} unique videos",
    quickmix_estimate_warn: "If you request more than {count}, repeats become likely",
    quickmix_estimate_none: "At this duration, almost no repeat-free unique videos remain",
    quickmix_estimate_error: "Could not calculate estimate",
    quickmix_timer_idle: "Time: -",
    quickmix_timer_running: "Running: {elapsed}",
    quickmix_timer_done: "Elapsed: {elapsed}",
    quickmix_empty: "Quick Mix has not been run yet.",
    quickmix_result_title: "Quick Mix result",
    quickmix_generated_count: "Generated MP4",
    quickmix_episode_groups: "Episodes",
    quickmix_take_count: "Detected takes",
    quickmix_marker_groups: "Episodes with magenta split",
    quickmix_variants_title: "Variants",
    quickmix_variant_order: "Episode order",
    quickmix_variant_takes: "Selected takes",
    quickmix_output_paths: "Output files",
    quickmix_photos_supported: "Photos supported",
    quickmix_photos_unsupported: "Photos not supported",
    quickmix_duration_source_music: "Duration was taken from the music track",
    quickmix_duration_source_manual: "Duration was taken from the seconds field",
    quickmix_music_used: "Music",
    quickmix_opening_used: "Opening media",
    quickmix_closing_used: "Closing media",
    hero_title: "Local dashboard for Quick Mix, review, and export",
    hero_copy: "Choose source materials for direct Quick Mix MP4 generation, or load an existing VIDEO MIX work_dir for review, approve/reject, and export.",
    open_review: "Open review.html",
    open_exports: "Open exports",
    open_workdir: "Open work_dir",
    load_title: "Load work_dir",
    load_help: "Use an already generated VIDEO MIX work folder.",
    load_waiting: "Waiting",
    activity_title: "Current activity",
    activity_idle: "Nothing is running",
    activity_elapsed: "Elapsed",
    activity_running: "Working...",
    button_busy: "Working...",
    workdir_label: "VIDEO MIX work_dir",
    browse_workdir: "Browse folder",
    load_dashboard: "Load dashboard",
    copy_url: "Copy URL",
    project_meta_empty: "Load a work_dir to see project metadata and summary counts.",
    pipeline_title: "Pipeline",
    pipeline_help: "Path from assets to export in one local flow.",
    pipeline_open: "Show pipeline",
    pipeline_close: "Close",
    actions_title: "Actions",
    actions_help: "Use existing VIDEO MIX behavior only.",
    actions_help_quickmix: "In Quick Mix mode, candidates are not needed: finished MP4 files are already in the exports folder.",
    export_approved: "Export approved candidates",
    open_ready_videos: "Open ready videos folder",
    refresh_dashboard: "Refresh dashboard",
    debug_title: "Logs",
    debug_help: "Clicks, requests, responses, and errors are shown here automatically.",
    debug_clear: "Clear logs",
    debug_empty: "Logs will appear after the first action.",
    candidates_title: "Candidate cards",
    candidates_help: "Thumbnail, score, template, warnings, source files, and direct actions.",
    candidates_open: "Open candidates",
    candidates_close: "Close",
    quickmix_outputs_title: "Ready videos",
    quickmix_outputs_help: "MVP mode without candidates: everything generated is already saved in exports.",
    quickmix_output_count: "{count} videos",
    quickmix_no_outputs: "Finished MP4 files will appear here right after Quick Mix generation.",
    quickmix_ready_files: "Ready MP4 files",
    filter_status_label: "Status",
    filter_status_all: "All",
    filter_status_generated: "Generated",
    filter_status_approved: "Approved",
    filter_status_rejected: "Rejected",
    filter_status_exported: "Exported",
    filter_warnings_label: "Warnings",
    filter_warnings_all: "All",
    filter_warnings_with: "With warnings",
    filter_warnings_without: "Without warnings",
    sort_label: "Sort",
    sort_score_desc: "Score desc",
    sort_score_asc: "Score asc",
    sort_duration_desc: "Duration desc",
    sort_duration_asc: "Duration asc",
    sort_status: "Status",
    sort_template: "Template",
    sort_source: "Source filename",
    search_label: "Search",
    search_placeholder: "template or source filename",
    selected_count: "{count} selected",
    visible_count: "{count} visible",
    select_visible: "Select visible",
    clear_selection: "Clear selection",
    approve_selected: "Approve selected",
    reject_selected: "Reject selected",
    no_workdir_loaded: "No work_dir loaded yet.",
    no_candidates_match_filters: "No candidates match the current filters.",
    project_label: "Project",
    pack_label: "Pack",
    root_label: "Root",
    summary_assets: "Assets",
    summary_clips: "Clips",
    summary_candidates: "Candidates",
    summary_approved: "Approved",
    summary_exported: "Exported",
    summary_rejected: "Rejected",
    candidate_count: "{count} candidates",
    pipeline_empty: "Pipeline state will appear after loading a work_dir.",
    pipeline_item_count: "{count} item(s)",
    pipeline_assets: "Assets",
    pipeline_clips: "Clips",
    pipeline_candidates: "Candidates",
    pipeline_review: "Review",
    pipeline_approval: "Approval",
    pipeline_export: "Export",
    pipeline_state_ready: "ready",
    pipeline_state_pending: "pending",
    pipeline_state_active: "active",
    copy_approve: "Copy approve",
    copy_reject: "Copy reject",
    thumbnail_alt: "{candidateId} thumbnail",
    no_thumbnail: "No thumbnail",
    no_warnings: "No warnings",
    no_exports: "No exports yet.",
    no_source_clips: "No source clips attached.",
    no_tags: "untagged",
    select: "Select",
    status_generated: "Generated",
    status_previewed: "Previewed",
    status_approved: "Approved",
    status_rejected: "Rejected",
    status_exported: "Exported",
    metric_score: "Score",
    metric_duration: "Duration",
    metric_source_files: "Source files",
    section_warnings: "Warnings",
    section_source_filenames: "Source filenames",
    section_review_note: "Review note",
    note_placeholder: "optional review note",
    section_exports: "Exports",
    approve: "Approve",
    reject: "Reject",
    command_copied: "Command copied",
    no_export_paths_session: "No new export paths in this session.",
    load_state_enter_source_dir: "Enter the source materials folder",
    load_state_enter_duration: "Enter a valid duration in seconds",
    load_state_enter_output_count: "Enter a valid video count",
    load_state_enter_episode_range: "Enter a valid episode range",
    load_state_enter_workdir: "Enter work_dir",
    load_state_browsing_workdir: "Opening folder picker...",
    load_state_browse_canceled: "Folder selection cancelled",
    load_state_browsing_source: "Opening source folder picker...",
    load_state_source_browse_canceled: "Source folder selection cancelled",
    load_state_browsing_source_zip: "Opening ZIP file picker...",
    load_state_source_zip_browse_canceled: "ZIP file selection cancelled",
    load_state_uploading_file: "Uploading dropped file...",
    load_state_uploaded_file: "File uploaded",
    load_state_project_files_adding: "Adding files to the project...",
    load_state_project_files_added: "Files added to the project",
    load_state_project_file_removing: "Removing file from the project...",
    load_state_project_file_removed: "File removed from the project",
    load_state_drop_zip_only: "For source materials drag and drop currently supports ZIP only",
    load_state_scanning_source: "Scanning source materials...",
    load_state_source_scanned: "Source materials scanned",
    load_state_materials_assigning: "Assigning material to Episode...",
    load_state_materials_assigned: "Material assigned",
    load_state_materials_reusing: "Reusing material...",
    load_state_materials_reused: "Material reused",
    load_state_materials_unassigning: "Removing Take...",
    load_state_materials_unassigned: "Take removed",
    load_state_materials_episode_needed: "Select an Episode first",
    load_state_planning_source: "Creating project plan...",
    load_state_generating_review: "Generating review and thumbnails...",
    load_state_source_loaded: "Project created and loaded",
    load_state_quickmix_generating: "Generating Quick Mix MP4 files...",
    load_state_quickmix_ready: "Quick Mix ready",
    load_state_quickmix_ready_opened: "Quick Mix ready, videos folder opened",
    load_state_browsing_music: "Opening music file picker...",
    load_state_music_browse_canceled: "Music file selection cancelled",
    load_state_browsing_opening: "Opening opening media picker...",
    load_state_opening_browse_canceled: "Opening media selection cancelled",
    load_state_browsing_closing: "Opening closing media picker...",
    load_state_closing_browse_canceled: "Closing media selection cancelled",
    load_state_loading: "Loading...",
    load_state_loaded: "Loaded",
    load_state_reset_done: "Project reset",
    load_state_approving: "Approving...",
    load_state_rejecting: "Rejecting...",
    load_state_approved: "Approved",
    load_state_rejected: "Rejected",
    load_state_select_candidate_first: "Select at least one candidate first",
    load_state_no_visible_selected: "No selected candidates match the current filters",
    confirm_reject_selected: "Reject {count} selected candidate(s)?",
    confirm_approve_selected: "Approve {count} selected candidate(s)?",
    load_state_bulk_approving: "Bulk approve...",
    load_state_bulk_rejecting: "Bulk reject...",
    load_state_bulk_approved: "Bulk approve complete",
    load_state_bulk_rejected: "Bulk reject complete",
    confirm_export_approved: "Export all currently approved candidates?",
    load_state_exporting: "Exporting...",
    load_state_export_complete: "Export complete",
    load_state_opened: "Opened: {target}",
    url_copied: "URL copied",
    request_failed: "Request failed",
  },
};

const qs = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function formatDurationMs(value) {
  const totalSeconds = Math.max(0, Math.round((Number(value) || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatSecondsValue(value) {
  return (Math.max(0, Number(value) || 0) / 1000).toFixed(1);
}

function fileUrl(relativePath) {
  if (!state.workDir || !relativePath) return "";
  const params = new URLSearchParams({
    work_dir: state.workDir,
    relative_path: relativePath,
  });
  return `/api/video-mix/file?${params.toString()}`;
}

function localMediaUrl(filePath) {
  if (!filePath) return "";
  return `/api/video-mix/local-media?${new URLSearchParams({ file_path: filePath }).toString()}`;
}

async function openLocalMediaFile(filePath) {
  if (!filePath) return;
  await fetchJson("/api/video-mix/open-local-file", {
    method: "POST",
    body: JSON.stringify({ file_path: filePath }),
  });
}

async function openLocalPath(path) {
  if (!path) return;
  await fetchJson("/api/video-mix/open-local-path", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

function buildSelectedMediaModalContent(filePath, inputSelector) {
  const name = baseName(filePath);
  const url = localMediaUrl(filePath);
  const escapedFilePath = escapeAttr(filePath);
  const escapedInputSelector = escapeAttr(inputSelector);
  const kind = previewMediaKind(filePath);
  let mediaHtml = `<div class="muted">${escapeHtml(name)}</div>`;
  if (kind === "video") {
    mediaHtml = `<video class="video-mix-selected-modal-media" src="${escapeAttr(url)}" controls preload="metadata"></video>`;
  } else if (kind === "image") {
    mediaHtml = `<img class="video-mix-selected-modal-media" src="${escapeAttr(url)}" alt="${escapeAttr(name)}">`;
  } else if (kind === "audio") {
    mediaHtml = `<audio class="video-mix-selected-modal-audio" src="${escapeAttr(url)}" controls preload="metadata"></audio>`;
  }
  return `
    <div class="video-mix-selected-modal-content">
      <div class="video-mix-selected-modal-head">
        <strong>${escapeHtml(name)}</strong>
      </div>
      <div class="video-mix-selected-modal-stage">
        ${mediaHtml}
      </div>
      <div class="video-mix-selected-modal-actions">
        <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        <button type="button" class="video-mix-selected-remove" data-remove-local-file="${escapedFilePath}" data-remove-input="${escapedInputSelector}">×</button>
      </div>
    </div>
  `;
}

function closeSelectedMediaModal() {
  const dialog = qs("#vm-selected-media-modal");
  if (!dialog) return;
  dialog.close();
}

function bindSelectedMediaActionButtons(root = document, options = {}) {
  root.querySelectorAll("[data-toggle-audio-preview]").forEach((button) => {
    button.onclick = (event) => {
      event.stopPropagation();
      const preview = button.closest(".video-mix-selected-preview");
      const audio = preview?.querySelector(".video-mix-selected-inline-audio");
      if (!(audio instanceof HTMLAudioElement)) return;
      root.querySelectorAll(".video-mix-selected-inline-audio").forEach((candidate) => {
        if (candidate instanceof HTMLAudioElement && candidate !== audio) {
          candidate.pause();
          candidate.currentTime = 0;
          const otherButton = candidate.closest(".video-mix-selected-preview")?.querySelector("[data-toggle-audio-preview]");
          if (otherButton) {
            otherButton.textContent = t("quickmix_selected_play");
          }
        }
      });
      if (audio.paused) {
        void audio.play();
        button.textContent = t("quickmix_selected_pause");
      } else {
        audio.pause();
        button.textContent = t("quickmix_selected_play");
      }
      audio.onended = () => {
        button.textContent = t("quickmix_selected_play");
      };
      audio.onpause = () => {
        if (audio.currentTime === 0 || audio.ended) {
          button.textContent = t("quickmix_selected_play");
        }
      };
    };
  });
  root.querySelectorAll("[data-open-local-file]").forEach((button) => {
    button.onclick = async (event) => {
      event.stopPropagation();
      const filePath = button.getAttribute("data-open-local-file") || "";
      if (!filePath) return;
      setLocalizedLoadState("load_state_loading", "status-downloading");
      try {
        await openLocalMediaFile(filePath);
        setLocalizedLoadState("load_state_loaded", "status-completed");
      } catch (error) {
        state.loadState = null;
        setLoadState(error.message, "status-failed");
      }
    };
  });
  root.querySelectorAll("[data-remove-local-file]").forEach((button) => {
    button.onclick = (event) => {
      event.stopPropagation();
      const filePath = button.getAttribute("data-remove-local-file") || "";
      const targetSelector = button.getAttribute("data-remove-input") || "";
      if (!filePath || !targetSelector) return;
      removeQuickMixFile(targetSelector, filePath);
      renderQuickMixSelections();
      scheduleQuickMixEstimateRefresh();
      if (options.closeModalOnRemove) {
        closeSelectedMediaModal();
      }
    };
    button.setAttribute("aria-label", t("quickmix_selected_remove"));
    button.setAttribute("title", t("quickmix_selected_remove"));
  });
}

function showSelectedMediaModal(filePath, inputSelector) {
  const dialog = qs("#vm-selected-media-modal");
  const body = qs("#vm-selected-media-modal-body");
  if (!dialog || !body || !filePath) return;
  body.innerHTML = buildSelectedMediaModalContent(filePath, inputSelector);
  bindSelectedMediaActionButtons(body, { closeModalOnRemove: true });
  dialog.showModal();
}

function closeTakeEditorModal() {
  state.takeEditor = null;
  qs("#vm-take-editor-modal")?.close();
}

function findEpisodeTake(episodeId, takeId) {
  const materials = projectMaterials();
  const episode = (materials.episodes || []).find((item) => item.episode_id === episodeId);
  if (!episode) return { episode: null, take: null, takeIndex: -1 };
  const takeIndex = (episode.takes || []).findIndex((item) => item.take_id === takeId);
  if (takeIndex < 0) return { episode, take: null, takeIndex: -1 };
  return { episode, take: episode.takes[takeIndex], takeIndex };
}

function buildTakeEditorPreview(filePath) {
  const normalizedPath = String(filePath || "").trim();
  if (!normalizedPath) {
    return `<div class="empty compact">${escapeHtml(t("take_editor_no_take"))}</div>`;
  }
  const kind = previewMediaKind(normalizedPath);
  const url = localMediaUrl(normalizedPath);
  const name = baseName(normalizedPath);
  if (kind === "video") {
    return `<video class="video-mix-take-editor-media" src="${escapeAttr(url)}" controls preload="metadata"></video>`;
  }
  if (kind === "image") {
    return `<img class="video-mix-take-editor-media" src="${escapeAttr(url)}" alt="${escapeAttr(name)}">`;
  }
  if (kind === "audio") {
    return `<audio class="video-mix-take-editor-audio" src="${escapeAttr(url)}" controls preload="metadata"></audio>`;
  }
  return `<div class="empty compact">${escapeHtml(name)}</div>`;
}

function renderTakeEditorModal() {
  const body = qs("#vm-take-editor-body");
  if (!body) return;
  if (!state.takeEditor) {
    body.innerHTML = `<div class="empty">${escapeHtml(t("take_editor_no_take"))}</div>`;
    return;
  }
  const { episode, take, takeIndex } = findEpisodeTake(state.takeEditor.episodeId, state.takeEditor.takeId);
  if (!episode || !take) {
    body.innerHTML = `<div class="empty">${escapeHtml(t("take_editor_no_take"))}</div>`;
    return;
  }
  const takeCount = (episode.takes || []).length;
  const startSeconds = state.takeEditor.startSeconds ?? Number(formatSecondsValue(take.source_start_ms));
  const endSeconds = state.takeEditor.endSeconds ?? Number(formatSecondsValue(take.source_end_ms));
  const trimmedDurationMs = Math.max(0, Number(take.source_end_ms || 0) - Number(take.source_start_ms || 0));
  body.innerHTML = `
    <div class="video-mix-take-editor-layout">
      <div class="video-mix-take-editor-preview">
        ${buildTakeEditorPreview(take.source_path)}
      </div>
      <div class="video-mix-take-editor-meta">
        <div class="video-mix-take-editor-head">
          <strong>${escapeHtml(take.file_name || take.take_id || "")}</strong>
          <span class="status-chip status-idle">${escapeHtml(`${t("take_editor_episode")}: ${episode.label}`)}</span>
        </div>
        <div class="muted">${escapeHtml(`${t("take_editor_take")}: #${take.order}`)}</div>
        <div class="video-mix-take-editor-stats">
          <div class="video-mix-summary-card"><span>${escapeHtml(t("take_editor_asset_duration"))}</span><strong>${escapeHtml(formatDurationMs(take.asset_duration_ms || 0))}</strong></div>
          <div class="video-mix-summary-card"><span>${escapeHtml(t("take_editor_trim_duration"))}</span><strong>${escapeHtml(formatDurationMs(trimmedDurationMs))}</strong></div>
        </div>
        <div class="video-mix-take-editor-fields">
          <label class="field">
            <span>${escapeHtml(t("take_editor_trim_start"))}</span>
            <input id="vm-take-editor-start-input" type="number" min="0" step="0.1" value="${escapeAttr(String(startSeconds))}">
          </label>
          <label class="field">
            <span>${escapeHtml(t("take_editor_trim_end"))}</span>
            <input id="vm-take-editor-end-input" type="number" min="0.1" step="0.1" value="${escapeAttr(String(endSeconds))}">
          </label>
        </div>
        <div class="actions-row video-mix-take-editor-actions">
          <button type="button" class="ghost-btn" data-open-local-file="${escapeAttr(take.source_path || "")}">${escapeHtml(t("take_editor_open_file"))}</button>
          <button type="button" class="ghost-btn" id="vm-take-editor-move-left-btn" ${takeIndex <= 0 ? "disabled" : ""}>${escapeHtml(t("materials_take_move_left"))}</button>
          <button type="button" class="ghost-btn" id="vm-take-editor-move-right-btn" ${takeIndex >= takeCount - 1 ? "disabled" : ""}>${escapeHtml(t("materials_take_move_right"))}</button>
          <button type="button" class="ghost-btn" id="vm-take-editor-remove-btn">${escapeHtml(t("materials_take_remove"))}</button>
        </div>
        <div class="actions-row video-mix-take-editor-actions">
          <button type="button" class="accent-btn" id="vm-take-editor-save-btn">${escapeHtml(t("take_editor_save"))}</button>
          <button type="button" class="ghost-btn" id="vm-take-editor-cancel-btn">${escapeHtml(t("take_editor_cancel"))}</button>
        </div>
      </div>
    </div>
  `;
  bindSelectedMediaActionButtons(body);
  qs("#vm-take-editor-cancel-btn")?.addEventListener("click", () => closeTakeEditorModal());
  qs("#vm-take-editor-save-btn")?.addEventListener("click", async () => saveTakeEditorChanges());
  qs("#vm-take-editor-move-left-btn")?.addEventListener("click", async () => moveTakeWithinEpisode(episode.episode_id, take.take_id, -1));
  qs("#vm-take-editor-move-right-btn")?.addEventListener("click", async () => moveTakeWithinEpisode(episode.episode_id, take.take_id, 1));
  qs("#vm-take-editor-remove-btn")?.addEventListener("click", async () => {
    await unassignProjectMaterialTake(episode.episode_id, take.take_id);
    closeTakeEditorModal();
  });
}

function openTakeEditor(episodeId, takeId) {
  const { episode, take } = findEpisodeTake(episodeId, takeId);
  if (!episode || !take) return;
  state.selectedMaterialEpisodeId = episodeId;
  state.takeEditor = {
    episodeId,
    takeId,
    startSeconds: Number(formatSecondsValue(take.source_start_ms)),
    endSeconds: Number(formatSecondsValue(take.source_end_ms)),
  };
  renderAll();
  const dialog = qs("#vm-take-editor-modal");
  if (dialog && !dialog.open) {
    dialog.showModal();
  }
}

async function saveTakeEditorChanges() {
  if (!state.takeEditor) return;
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  const startSeconds = Number(qs("#vm-take-editor-start-input")?.value || 0);
  const endSeconds = Number(qs("#vm-take-editor-end-input")?.value || 0);
  if (!(startSeconds >= 0) || !(endSeconds > startSeconds)) {
    setLoadState(t("take_editor_validation"), "status-failed");
    return;
  }
  const sourceStartMs = Math.round(startSeconds * 1000);
  const sourceEndMs = Math.round(endSeconds * 1000);
  setLocalizedLoadState("activity_running", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/takes/update", {
      method: "POST",
      body: JSON.stringify({
        work_dir: workDir,
        episode_id: state.takeEditor.episodeId,
        take_id: state.takeEditor.takeId,
        source_start_ms: sourceStartMs,
        source_end_ms: sourceEndMs,
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.selectedMaterialEpisodeId = state.takeEditor.episodeId;
    state.takeEditor.startSeconds = startSeconds;
    state.takeEditor.endSeconds = endSeconds;
    renderTakeEditorModal();
    renderAll();
    setLocalizedLoadState("take_editor_saved", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function reorderEpisodeTakes(episodeId, orderedTakeIds) {
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  const payload = await fetchJson("/api/video-mix/project-materials/takes/reorder", {
    method: "POST",
    body: JSON.stringify({
      work_dir: workDir,
      episode_id: episodeId,
      ordered_take_ids: orderedTakeIds,
    }),
  });
  applyDashboardPayload(payload.dashboard);
  state.selectedMaterialEpisodeId = episodeId;
  if (state.takeEditor?.episodeId === episodeId) {
    renderTakeEditorModal();
  }
  renderAll();
}

async function moveTakeWithinEpisode(episodeId, takeId, delta) {
  const { episode, takeIndex } = findEpisodeTake(episodeId, takeId);
  if (!episode || takeIndex < 0) return;
  const targetIndex = takeIndex + delta;
  if (targetIndex < 0 || targetIndex >= (episode.takes || []).length) return;
  const orderedTakeIds = (episode.takes || []).map((take) => take.take_id);
  const [movedTakeId] = orderedTakeIds.splice(takeIndex, 1);
  orderedTakeIds.splice(targetIndex, 0, movedTakeId);
  try {
    await reorderEpisodeTakes(episodeId, orderedTakeIds);
    setLocalizedLoadState("take_editor_reordered", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

function parseQuickMixFileList(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return [];
  }
  if (value.startsWith("[")) {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item || "").trim()).filter(Boolean);
      }
    } catch (_error) {
      return [];
    }
  }
  return [value];
}

function writeQuickMixFileList(inputSelector, paths) {
  const input = qs(inputSelector);
  if (!input) return;
  const unique = [];
  const seen = new Set();
  (paths || []).forEach((path) => {
    const normalized = String(path || "").trim();
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    unique.push(normalized);
  });
  input.value = JSON.stringify(unique);
}

function readQuickMixFileList(inputSelector) {
  return parseQuickMixFileList(qs(inputSelector)?.value || "");
}

function appendQuickMixFiles(inputSelector, filePaths) {
  writeQuickMixFileList(inputSelector, [...readQuickMixFileList(inputSelector), ...(filePaths || [])]);
}

function removeQuickMixFile(inputSelector, filePath) {
  writeQuickMixFileList(
    inputSelector,
    readQuickMixFileList(inputSelector).filter((item) => item !== filePath),
  );
}

function compareStrings(a, b) {
  return String(a || "").localeCompare(String(b || ""));
}

export function resolveInitialLocale(searchValue = "", storedLocale = "") {
  const params = new URLSearchParams(String(searchValue || ""));
  const lang = params.get("lang");
  if (LOCALES.includes(lang)) {
    return lang;
  }
  if (LOCALES.includes(storedLocale)) {
    return storedLocale;
  }
  return "ru";
}

export function translate(locale, key, params = {}) {
  const table = TRANSLATIONS[locale] || TRANSLATIONS.ru;
  const fallback = TRANSLATIONS.ru[key] || key;
  const raw = table[key] || fallback;
  return String(raw).replaceAll(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ""));
}

function t(key, params = {}) {
  return translate(state.locale, key, params);
}

function formatDebugTimestamp(date = new Date()) {
  return date.toLocaleTimeString([], { hour12: false });
}

function debugLog(kind, message, details = "") {
  const entry = {
    at: formatDebugTimestamp(),
    kind: String(kind || "info"),
    message: String(message || ""),
    details: details ? String(details) : "",
  };
  state.debugLogs = [...state.debugLogs, entry].slice(-120);
  renderDebugLog();
}

async function fetchJson(url, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  debugLog("request", `${method} ${url}`);
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    debugLog("error", `${method} ${url}`, `${response.status} ${payload.detail || t("request_failed")}`);
    throw new Error(payload.detail || t("request_failed"));
  }
  debugLog("response", `${method} ${url}`, `HTTP ${response.status}`);
  return response.json();
}

async function uploadDroppedFile(file, purpose) {
  debugLog("request", `UPLOAD ${purpose}`, file?.name || "");
  const fileBytes = await file.arrayBuffer();
  const response = await fetch("/api/video-mix/upload-file", {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      "x-video-mix-upload-purpose": purpose,
      "x-video-mix-upload-filename": encodeURIComponent(file.name || "upload.bin"),
    },
    body: fileBytes,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    debugLog("error", `UPLOAD ${purpose}`, payload.detail || t("request_failed"));
    throw new Error(payload.detail || t("request_failed"));
  }
  debugLog("response", `UPLOAD ${purpose}`, `HTTP ${response.status}`);
  return response.json();
}

async function importZipArchive(file, { projectName = "", workDir = "" } = {}) {
  debugLog("request", "IMPORT ZIP", file?.name || "");
  const formData = new FormData();
  formData.append("file", file, file?.name || "upload.zip");
  formData.append("project_name", projectName);
  formData.append("work_dir", workDir);
  const response = await fetch("/api/video-mix/import-zip", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    debugLog("error", "IMPORT ZIP", payload.detail || t("request_failed"));
    throw new Error(payload.detail || t("request_failed"));
  }
  debugLog("response", "IMPORT ZIP", `HTTP ${response.status}`);
  return response.json();
}

async function uploadDroppedSourceTreeFile(file, sessionId, relativePath) {
  debugLog("request", "UPLOAD source_tree", relativePath || file?.name || "");
  const fileBytes = await file.arrayBuffer();
  const response = await fetch("/api/video-mix/upload-file", {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      "x-video-mix-upload-purpose": "source_tree",
      "x-video-mix-upload-filename": encodeURIComponent(file.name || "upload.bin"),
      "x-video-mix-upload-session": sessionId,
      "x-video-mix-upload-relative-path": encodeURIComponent(relativePath),
    },
    body: fileBytes,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    debugLog("error", "UPLOAD source_tree", payload.detail || t("request_failed"));
    throw new Error(payload.detail || t("request_failed"));
  }
  debugLog("response", "UPLOAD source_tree", `HTTP ${response.status}`);
  return response.json();
}

function readFileEntry(entry) {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject);
  });
}

function readDirectoryEntries(reader) {
  return new Promise((resolve, reject) => {
    reader.readEntries(resolve, reject);
  });
}

function setDropZoneMessage(selector, messageKey, params = {}) {
  const zone = qs(selector);
  if (!zone) return;
  zone.textContent = t(messageKey, params);
}

function resetDropZoneMessage(selector, defaultKey) {
  const zone = qs(selector);
  if (!zone) return;
  zone.textContent = t(defaultKey);
  zone.classList.remove("is-processing");
}

async function collectDirectoryFiles(entry, prefix = "") {
  if (entry.isFile) {
    const file = await readFileEntry(entry);
    return [{ file, relativePath: prefix ? `${prefix}/${file.name}` : file.name }];
  }
  if (!entry.isDirectory) {
    return [];
  }

  const reader = entry.createReader();
  const children = [];
  while (true) {
    const batch = await readDirectoryEntries(reader);
    if (!batch.length) break;
    children.push(...batch);
  }

  const files = [];
  for (const child of children) {
    const childPrefix = prefix ? `${prefix}/${child.name}` : child.name;
    if (child.isDirectory) {
      files.push(...await collectDirectoryFiles(child, childPrefix));
    } else {
      const file = await readFileEntry(child);
      files.push({ file, relativePath: childPrefix });
    }
  }
  return files;
}

async function collectDirectoryFilesFromHandle(handle, prefix = "") {
  if (!handle) {
    return [];
  }
  if (handle.kind === "file") {
    const file = await handle.getFile();
    return [{ file, relativePath: prefix ? `${prefix}/${file.name}` : file.name }];
  }
  if (handle.kind !== "directory") {
    return [];
  }
  const files = [];
  for await (const child of handle.values()) {
    const childPrefix = prefix ? `${prefix}/${child.name}` : child.name;
    if (child.kind === "directory") {
      files.push(...await collectDirectoryFilesFromHandle(child, childPrefix));
    } else {
      const file = await child.getFile();
      files.push({ file, relativePath: childPrefix });
    }
  }
  return files;
}

function setLoadState(label, className) {
  const element = qs("#vm-load-state");
  if (!element) return;
  element.textContent = label;
  element.className = `status-chip ${className}`;
  debugLog("state", label, className);
}

function setLocalizedLoadState(key, className, params = {}) {
  state.loadState = { key, className, params };
  setLoadState(t(key, params), className);
}

function formatElapsedMs(elapsedMs) {
  const totalSeconds = Math.max(0, Math.floor(Number(elapsedMs || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function setButtonBusy(selector, isBusy, busyText = "") {
  const button = qs(selector);
  if (!button) return;
  if (!button.dataset.idleText) {
    button.dataset.idleText = button.textContent || "";
  }
  button.disabled = isBusy;
  button.classList.toggle("is-busy", isBusy);
  button.setAttribute("aria-busy", isBusy ? "true" : "false");
  button.textContent = isBusy ? (busyText || t("button_busy")) : button.dataset.idleText;
}

function clearActivityTimer() {
  if (activityTimerId) {
    window.clearInterval(activityTimerId);
    activityTimerId = null;
  }
}

function ensureActivityTimer() {
  clearActivityTimer();
  activityTimerId = window.setInterval(() => {
    if (!state.activity?.startedAt) {
      clearActivityTimer();
      return;
    }
    renderActivityPanel();
    renderQuickMixTimer();
  }, 1000);
}

function startActivity(selector, messageKey, fallbackMessage = "") {
  state.activity = {
    selector,
    messageKey,
    fallbackMessage,
    startedAt: Date.now(),
  };
  setButtonBusy(selector, true, fallbackMessage || t("button_busy"));
  renderActivityPanel();
  renderQuickMixTimer();
  ensureActivityTimer();
}

function stopActivity() {
  if (state.activity?.selector) {
    setButtonBusy(state.activity.selector, false);
  }
  state.activity = null;
  clearActivityTimer();
  renderActivityPanel();
  renderQuickMixTimer();
}

function renderActivityPanel() {
  const target = qs("#vm-activity-panel");
  if (!target) return;
  if (!state.activity) {
    target.innerHTML = `
      <div class="video-mix-activity-idle">
        <span class="video-mix-activity-dot"></span>
        <span>${escapeHtml(t("activity_idle"))}</span>
      </div>
    `;
    return;
  }
  const message = state.activity.messageKey
    ? t(state.activity.messageKey, state.loadState?.params || {})
    : (state.activity.fallbackMessage || t("activity_running"));
  const elapsed = formatElapsedMs(Date.now() - state.activity.startedAt);
  target.innerHTML = `
    <div class="video-mix-activity-live">
      <div class="video-mix-activity-head">
        <span class="video-mix-spinner" aria-hidden="true"></span>
        <strong>${escapeHtml(message)}</strong>
      </div>
      <div class="video-mix-activity-meta">
        <span>${escapeHtml(t("activity_elapsed"))}: ${escapeHtml(elapsed)}</span>
      </div>
    </div>
  `;
}

function statusLabel(status) {
  return t(`status_${status}`) || status;
}

function pipelineLabel(step) {
  return t(`pipeline_${step.id}`) || step.label || step.id;
}

function pipelineStateLabel(stateValue) {
  return t(`pipeline_state_${stateValue}`) || stateValue;
}

function renderDebugLog() {
  const target = qs("#vm-debug-log");
  if (!target) return;
  if (!state.debugLogs.length) {
    target.innerHTML = `<div class="muted">${escapeHtml(t("debug_empty"))}</div>`;
    return;
  }
  target.innerHTML = state.debugLogs.slice().reverse().map((entry) => `
    <div class="video-mix-debug-entry">
      <div class="video-mix-debug-head">
        <span class="video-mix-debug-time">${escapeHtml(entry.at)}</span>
        <span class="video-mix-debug-kind">${escapeHtml(entry.kind)}</span>
      </div>
      <div class="video-mix-debug-message">${escapeHtml(entry.message)}</div>
      ${entry.details ? `<div class="video-mix-debug-details">${escapeHtml(entry.details)}</div>` : ""}
    </div>
  `).join("");
}

function syncLayoutMode() {
  if (typeof document === "undefined") return;
  document.body.classList.toggle("video-mix-quickmix-mode", isQuickMixMode());
}

function readStoredLocale() {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(DASHBOARD_LOCALE_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function persistLocale() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(DASHBOARD_LOCALE_STORAGE_KEY, state.locale);
  } catch {}
}

function syncLocaleToUrl() {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("lang", state.locale);
  if (state.workDir) {
    params.set("work_dir", state.workDir);
  }
  history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
}

function applyStaticTranslations() {
  if (typeof document === "undefined") return;
  document.documentElement.lang = state.locale;
  document.title = t("page_title");

  const textUpdates = [
    ["#vm-hero-title", "hero_title"],
    ["#vm-hero-copy", "hero_copy"],
    ["#vm-open-review", "open_review"],
    ["#vm-open-exports", "open_exports"],
    ["#vm-open-workdir", "open_workdir"],
    ["#vm-load-title", "load_title"],
    ["#vm-load-help", "load_help"],
    ["#vm-activity-title", "activity_title"],
    ["#vm-source-title", "source_title"],
    ["#vm-source-help", "source_help"],
    ["#vm-materials-stage-title", "materials_stage_title"],
    ["#vm-materials-stage-help", "materials_stage_help"],
    ["#vm-add-episode-btn", "materials_add_episode"],
    ["#vm-open-project-materials-inline-btn", "materials_open_modal"],
    ["#vm-project-materials-title", "materials_stage_title"],
    ["#vm-project-materials-help", "materials_stage_help"],
    ["#vm-close-project-materials-btn", "pipeline_close"],
    ["#vm-project-materials-filter-status-label", "materials_filter_status"],
    ["#vm-project-materials-filter-type-label", "materials_filter_type"],
    ["#vm-project-materials-search-label", "materials_search"],
    ["#vm-timeline-title", "timeline_title"],
    ["#vm-timeline-help", "timeline_help"],
    ["#vm-take-editor-title", "take_editor_title"],
    ["#vm-take-editor-help", "take_editor_help"],
    ["#vm-close-take-editor-btn", "pipeline_close"],
    ["#vm-quickmix-title", "quickmix_title"],
    ["#vm-quickmix-help", "quickmix_help"],
    ["#vm-source-dir-label", "source_dir_label"],
    ["#vm-source-project-name-label", "source_project_name_label"],
    ["#vm-source-workdir-label", "source_workdir_label"],
    ["#vm-source-open-dir-btn", "source_open_dir"],
    ["#vm-source-open-workdir-btn", "source_open_workdir"],
    ["#vm-project-files-title", "project_files_title"],
    ["#vm-project-files-help", "project_files_help"],
    ["#vm-project-files-add-btn", "project_files_add"],
    ["#vm-project-files-open-btn", "project_files_open"],
    ["#vm-quickmix-duration-label", "quickmix_duration_label"],
    ["#vm-quickmix-count-label", "quickmix_count_label"],
    ["#vm-quickmix-music-label", "quickmix_music_label"],
    ["#vm-quickmix-music-drop-zone", "quickmix_music_drop"],
    ["#vm-quickmix-music-browse-btn", "quickmix_music_browse"],
    ["#vm-quickmix-use-music-duration-label", "quickmix_use_music_duration"],
    ["#vm-quickmix-opening-label", "quickmix_opening_label"],
    ["#vm-quickmix-opening-drop-zone", "quickmix_opening_drop"],
    ["#vm-quickmix-opening-browse-btn", "quickmix_opening_browse"],
    ["#vm-quickmix-closing-label", "quickmix_closing_label"],
    ["#vm-quickmix-closing-drop-zone", "quickmix_closing_drop"],
    ["#vm-quickmix-closing-browse-btn", "quickmix_closing_browse"],
    ["#vm-quickmix-use-closing-duration-label", "quickmix_use_closing_duration"],
    ["#vm-source-browse-btn", "source_browse"],
    ["#vm-source-zip-browse-btn", "source_browse_zip"],
    ["#vm-source-drop-zone", "source_drop_zip"],
    ["#vm-source-scan-btn", "source_scan"],
    ["#vm-source-plan-btn", "source_plan"],
    ["#vm-reset-btn", "reset_button"],
    ["#vm-quickmix-btn", "quickmix_button"],
    ["#vm-quickmix-open-exports-btn", "open_ready_videos"],
    ["#vm-workdir-label", "workdir_label"],
    ["#vm-browse-workdir-btn", "browse_workdir"],
    ["#vm-load-btn", "load_dashboard"],
    ["#vm-copy-url-btn", "copy_url"],
    ["#vm-pipeline-title", "pipeline_title"],
    ["#vm-pipeline-help", "pipeline_help"],
    ["#vm-open-pipeline-modal-btn", "pipeline_open"],
    ["#vm-pipeline-modal-title", "pipeline_title"],
    ["#vm-pipeline-modal-help", "pipeline_help"],
    ["#vm-close-pipeline-modal-btn", "pipeline_close"],
    ["#vm-actions-title", "actions_title"],
    ["#vm-actions-help", "actions_help"],
    ["#vm-export-btn", "export_approved"],
    ["#vm-refresh-btn", "refresh_dashboard"],
    ["#vm-debug-title", "debug_title"],
    ["#vm-debug-help", "debug_help"],
    ["#vm-debug-clear-btn", "debug_clear"],
    ["#vm-candidates-title", "candidates_title"],
    ["#vm-candidates-help", "candidates_help"],
    ["#vm-open-candidates-modal-btn", "candidates_open"],
    ["#vm-close-candidates-modal-btn", "candidates_close"],
    ["#vm-filter-status-label", "filter_status_label"],
    ["#vm-filter-status-all", "filter_status_all"],
    ["#vm-filter-status-generated", "filter_status_generated"],
    ["#vm-filter-status-approved", "filter_status_approved"],
    ["#vm-filter-status-rejected", "filter_status_rejected"],
    ["#vm-filter-status-exported", "filter_status_exported"],
    ["#vm-filter-warnings-label", "filter_warnings_label"],
    ["#vm-filter-warnings-all", "filter_warnings_all"],
    ["#vm-filter-warnings-with", "filter_warnings_with"],
    ["#vm-filter-warnings-without", "filter_warnings_without"],
    ["#vm-sort-label", "sort_label"],
    ["#vm-sort-score-desc", "sort_score_desc"],
    ["#vm-sort-score-asc", "sort_score_asc"],
    ["#vm-sort-duration-desc", "sort_duration_desc"],
    ["#vm-sort-duration-asc", "sort_duration_asc"],
    ["#vm-sort-status", "sort_status"],
    ["#vm-sort-template", "sort_template"],
    ["#vm-sort-source", "sort_source"],
    ["#vm-search-label", "search_label"],
    ["#vm-select-visible", "select_visible"],
    ["#vm-clear-selection", "clear_selection"],
    ["#vm-approve-selected", "approve_selected"],
    ["#vm-reject-selected", "reject_selected"],
  ];

  textUpdates.forEach(([selector, key]) => {
    const element = qs(selector);
    if (element) {
      element.textContent = t(key);
    }
  });

  const searchInput = qs("#vm-search");
  if (searchInput) {
    searchInput.placeholder = t("search_placeholder");
  }
  const projectMaterialsSearchInput = qs("#vm-project-materials-search");
  if (projectMaterialsSearchInput) {
    projectMaterialsSearchInput.placeholder = t("materials_search_placeholder");
  }

  const workDirInput = qs("#vm-workdir-input");
  if (workDirInput) {
    workDirInput.placeholder = "C:\\path\\to\\video_mix_validation\\work";
  }
  const sourceDirInput = qs("#vm-source-dir-input");
  if (sourceDirInput) {
    sourceDirInput.placeholder = "C:\\path\\to\\source_materials";
  }
  const sourceProjectNameInput = qs("#vm-source-project-name-input");
  if (sourceProjectNameInput) {
    sourceProjectNameInput.placeholder = "Wedding Validation";
  }
  const sourceWorkDirInput = qs("#vm-source-workdir-input");
  if (sourceWorkDirInput) {
    sourceWorkDirInput.placeholder = "C:\\path\\to\\source_materials\\_video_mix_work";
  }
  const musicInput = qs("#vm-quickmix-music-input");
  if (musicInput) {
    musicInput.placeholder = "C:\\path\\to\\music.mp3";
  }
  const openingInput = qs("#vm-quickmix-opening-input");
  if (openingInput) {
    openingInput.placeholder = "C:\\path\\to\\opening.jpg";
  }
  const closingInput = qs("#vm-quickmix-closing-input");
  if (closingInput) {
    closingInput.placeholder = "C:\\path\\to\\closing.mp4";
  }

  const localeButtons = [
    ["#vm-lang-ru", "ru"],
    ["#vm-lang-en", "en"],
  ];
  localeButtons.forEach(([selector, locale]) => {
    const button = qs(selector);
    if (!button) return;
    button.classList.toggle("is-active", state.locale === locale);
    button.setAttribute("aria-pressed", state.locale === locale ? "true" : "false");
  });

  if (state.loadState?.key) {
    setLoadState(t(state.loadState.key, state.loadState.params || {}), state.loadState.className || "status-queued");
  }
}

function defaultSourceWorkDir(sourceDir) {
  if (!sourceDir) return "";
  const normalized = sourceDir.replace(/[\\/]+$/, "");
  if (/\.zip$/i.test(normalized)) {
    return normalized.replace(/\.zip$/i, "") + "_video_mix_work";
  }
  return normalized + "\\_video_mix_work";
}

function currentSourcePath() {
  return qs("#vm-source-dir-input")?.value?.trim()
    || state.selectedSourcePath
    || state.sourceScan?.source_dir
    || "";
}

function setManualSourcePath(sourcePath) {
  const normalized = String(sourcePath || "").trim();
  state.selectedSourcePath = normalized;
  state.manualSourceOverride = Boolean(normalized);
  const input = qs("#vm-source-dir-input");
  if (input) {
    input.value = normalized;
  }
}

function baseName(filePath) {
  const normalized = String(filePath || "").trim().replace(/[\\/]+$/, "");
  if (!normalized) return "";
  const parts = normalized.split(/[\\/]/);
  return parts[parts.length - 1] || normalized;
}

function previewMediaKind(filePath) {
  const lower = String(filePath || "").toLowerCase();
  if (/\.(mp4|mov|mkv|webm|m4v)$/.test(lower)) return "video";
  if (/\.(jpg|jpeg|png|webp|heic)$/.test(lower)) return "image";
  if (/\.(mp3|wav|m4a|aac|ogg|flac)$/.test(lower)) return "audio";
  return "file";
}

function selectedMediaPreviewHtml(filePath, inputSelector) {
  const name = baseName(filePath);
  const url = localMediaUrl(filePath);
  const escapedFilePath = escapeAttr(filePath);
  const escapedInputSelector = escapeAttr(inputSelector);
  const kind = previewMediaKind(filePath);
  if (!filePath) {
    return escapeHtml(t("quickmix_selected_none"));
  }
  if (kind === "video") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
        <button type="button" class="video-mix-selected-remove video-mix-selected-remove-float" data-remove-local-file="${escapedFilePath}" data-remove-input="${escapedInputSelector}">×</button>
        <button type="button" class="video-mix-selected-thumb" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
          <video class="video-mix-selected-media" src="${escapeAttr(url)}" muted preload="metadata" tabindex="-1"></video>
        </button>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  if (kind === "image") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
        <button type="button" class="video-mix-selected-remove video-mix-selected-remove-float" data-remove-local-file="${escapedFilePath}" data-remove-input="${escapedInputSelector}">×</button>
        <button type="button" class="video-mix-selected-thumb" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
          <img class="video-mix-selected-media" src="${escapeAttr(url)}" alt="${escapeAttr(name)}">
        </button>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  if (kind === "audio") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
        <button type="button" class="video-mix-selected-remove video-mix-selected-remove-float" data-remove-local-file="${escapedFilePath}" data-remove-input="${escapedInputSelector}">×</button>
        <button type="button" class="video-mix-selected-thumb video-mix-selected-audio-thumb" data-preview-modal-file="${escapedFilePath}" data-preview-input="${escapedInputSelector}">
          <span class="video-mix-selected-audio-label">${escapeHtml(name)}</span>
        </button>
        <audio class="video-mix-selected-inline-audio" src="${escapeAttr(url)}" preload="metadata"></audio>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-toggle-audio-preview="true">${escapeHtml(t("quickmix_selected_play"))}</button>
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  return `
    <div class="video-mix-selected-actions">
      <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
      <button type="button" class="video-mix-selected-remove" data-remove-local-file="${escapedFilePath}" data-remove-input="${escapedInputSelector}">×</button>
    </div>
  `;
}

function episodeTakePreviewHtml(filePath) {
  const normalizedPath = String(filePath || "").trim();
  if (!normalizedPath) {
    return "";
  }
  const name = baseName(normalizedPath);
  const url = localMediaUrl(normalizedPath);
  const escapedFilePath = escapeAttr(normalizedPath);
  const kind = previewMediaKind(normalizedPath);
  if (kind === "video") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}">
        <button type="button" class="video-mix-selected-thumb" data-preview-modal-file="${escapedFilePath}">
          <video class="video-mix-selected-media" src="${escapeAttr(url)}" muted preload="metadata" tabindex="-1"></video>
        </button>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  if (kind === "image") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}">
        <button type="button" class="video-mix-selected-thumb" data-preview-modal-file="${escapedFilePath}">
          <img class="video-mix-selected-media" src="${escapeAttr(url)}" alt="${escapeAttr(name)}">
        </button>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  if (kind === "audio") {
    return `
      <div class="video-mix-selected-preview" data-preview-modal-file="${escapedFilePath}">
        <button type="button" class="video-mix-selected-thumb video-mix-selected-audio-thumb" data-preview-modal-file="${escapedFilePath}">
          <span class="video-mix-selected-audio-label">${escapeHtml(name)}</span>
        </button>
        <audio class="video-mix-selected-inline-audio" src="${escapeAttr(url)}" preload="metadata"></audio>
        <div class="video-mix-selected-actions">
          <button type="button" class="video-mix-selected-open" data-toggle-audio-preview="true">${escapeHtml(t("quickmix_selected_play"))}</button>
          <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
        </div>
      </div>
    `;
  }
  return `
    <div class="video-mix-selected-actions">
      <button type="button" class="video-mix-selected-open" data-open-local-file="${escapedFilePath}">${escapeHtml(t("quickmix_selected_open"))}</button>
    </div>
  `;
}

function episodeTakeCompactPreviewHtml(filePath) {
  const normalizedPath = String(filePath || "").trim();
  if (!normalizedPath) {
    return `<div class="video-mix-take-thumb video-mix-take-thumb-empty"></div>`;
  }
  const name = baseName(normalizedPath);
  const url = localMediaUrl(normalizedPath);
  const kind = previewMediaKind(normalizedPath);
  if (kind === "video") {
    return `<video class="video-mix-take-thumb-media" src="${escapeAttr(url)}" muted preload="metadata" tabindex="-1"></video>`;
  }
  if (kind === "image") {
    return `<img class="video-mix-take-thumb-media" src="${escapeAttr(url)}" alt="${escapeAttr(name)}">`;
  }
  if (kind === "audio") {
    return `<div class="video-mix-take-thumb-audio" aria-label="${escapeAttr(name)}">♪</div>`;
  }
  return `<div class="video-mix-take-thumb-fallback" aria-label="${escapeAttr(name)}"></div>`;
}

function renderQuickMixSelections() {
  const mappings = [
    ["#vm-quickmix-music-input", "#vm-quickmix-music-selected"],
    ["#vm-quickmix-opening-input", "#vm-quickmix-opening-selected"],
    ["#vm-quickmix-closing-input", "#vm-quickmix-closing-selected"],
  ];
  mappings.forEach(([inputSelector, outputSelector]) => {
    const input = qs(inputSelector);
    const output = qs(outputSelector);
    if (!input || !output) return;
    const values = readQuickMixFileList(inputSelector);
    output.innerHTML = values.length
      ? values.map((value) => selectedMediaPreviewHtml(value, inputSelector)).join("")
      : escapeHtml(t("quickmix_selected_none"));
    output.classList.toggle("is-empty", !values.length);
    output.title = values.join("\n");
    bindSelectedMediaActionButtons(output);
    output.querySelectorAll(".video-mix-selected-thumb[data-preview-modal-file]").forEach((card) => {
      card.onclick = () => {
        const filePath = card.getAttribute("data-preview-modal-file") || "";
        const targetSelector = card.getAttribute("data-preview-input") || "";
        showSelectedMediaModal(filePath, targetSelector);
      };
    });
  });
}

function renderQuickMixEstimate() {
  const target = qs("#vm-quickmix-estimate");
  if (!target) return;
  if (!state.quickMixEstimate || state.quickMixEstimate.status === "idle") {
    target.textContent = t("quickmix_estimate_idle");
    return;
  }
  if (state.quickMixEstimate.status === "loading") {
    target.textContent = t("quickmix_estimate_loading");
    return;
  }
  if (state.quickMixEstimate.status === "error") {
    target.textContent = state.quickMixEstimate.message || t("quickmix_estimate_error");
    return;
  }

  const estimatedCount = Number(state.quickMixEstimate.estimated_unique_outputs || 0);
  const requestedCount = Number(qs("#vm-quickmix-count-input")?.value || 0);
  const baseLine = estimatedCount > 0
    ? t("quickmix_estimate_ready", { count: estimatedCount })
    : t("quickmix_estimate_none");
  const warningLine = estimatedCount > 0 && requestedCount > estimatedCount
    ? ` ${t("quickmix_estimate_warn", { count: estimatedCount })}`
    : "";
  target.textContent = `${baseLine}${warningLine}`;
}

function renderQuickMixTimer() {
  const target = qs("#vm-quickmix-timer");
  if (!target) return;
  if (state.activity?.selector === "#vm-quickmix-btn" && state.activity?.startedAt) {
    target.textContent = t("quickmix_timer_running", {
      elapsed: formatElapsedMs(Date.now() - state.activity.startedAt),
    });
    return;
  }
  const elapsedMs = Number(state.quickMixResult?.generation_elapsed_ms || state.dashboard?.quick_mix?.generation_elapsed_ms || 0);
  if (elapsedMs > 0) {
    target.textContent = t("quickmix_timer_done", {
      elapsed: formatElapsedMs(elapsedMs),
    });
    return;
  }
  target.textContent = t("quickmix_timer_idle");
}

async function refreshQuickMixEstimate() {
  const sourceDir = qs("#vm-source-dir-input")?.value?.trim() || state.sourceScan?.source_dir || "";
  const durationSeconds = Number(qs("#vm-quickmix-duration-input")?.value || 0);
  const episodeDurationMinSeconds = Number(qs("#vm-quickmix-episode-min-input")?.value || 0);
  const episodeDurationMaxSeconds = Number(qs("#vm-quickmix-episode-max-input")?.value || 0);
  const musicPaths = readQuickMixFileList("#vm-quickmix-music-input");
  const useMusicDuration = Boolean(qs("#vm-quickmix-use-music-duration")?.checked);
  const openingMediaPaths = readQuickMixFileList("#vm-quickmix-opening-input");
  const closingMediaPaths = readQuickMixFileList("#vm-quickmix-closing-input");
  const useClosingDuration = Boolean(qs("#vm-quickmix-use-closing-duration")?.checked);

  if (!sourceDir || !(durationSeconds > 0) || !(episodeDurationMinSeconds > 0) || !(episodeDurationMaxSeconds > 0)) {
    state.quickMixEstimate = { status: "idle" };
    renderQuickMixEstimate();
    return;
  }

  state.quickMixEstimate = { status: "loading" };
  renderQuickMixEstimate();

  try {
    const payload = await fetchJson("/api/video-mix/quick-mix-estimate", {
      method: "POST",
      body: JSON.stringify({
        source_dir: sourceDir,
        duration_seconds: durationSeconds,
        episode_duration_min_seconds: episodeDurationMinSeconds,
        episode_duration_max_seconds: episodeDurationMaxSeconds,
        music_path: musicPaths[0] || "",
        music_paths: musicPaths,
        use_music_duration: useMusicDuration,
        opening_media_path: openingMediaPaths[0] || "",
        opening_media_paths: openingMediaPaths,
        closing_media_path: closingMediaPaths[0] || "",
        closing_media_paths: closingMediaPaths,
        use_closing_duration: useClosingDuration,
      }),
    });
    state.quickMixEstimate = {
      status: "ready",
      ...payload,
    };
  } catch (error) {
    state.quickMixEstimate = {
      status: "error",
      message: error?.message || t("quickmix_estimate_error"),
    };
  }
  renderQuickMixEstimate();
}

function scheduleQuickMixEstimateRefresh(delayMs = 250) {
  if (quickMixEstimateDebounceId) {
    window.clearTimeout(quickMixEstimateDebounceId);
  }
  quickMixEstimateDebounceId = window.setTimeout(() => {
    quickMixEstimateDebounceId = null;
    refreshQuickMixEstimate();
  }, delayMs);
}

function renderSourceScanSummary() {
  const target = qs("#vm-source-scan-summary");
  if (!target) return;
  const zipImport = state.zipImportResult || state.dashboard?.zip_import || null;
  if (zipImport?.block_count) {
    const warningLines = (zipImport.warnings || [])
      .map((warning) => `<li><code>${escapeHtml(warning.path || "-")}</code> ${escapeHtml(warning.message || warning.code || "")}</li>`)
      .join("");
    target.innerHTML = `
      <div class="video-mix-section">
        <h4>${escapeHtml(t("source_zip_result_title"))}</h4>
        <div class="actions-row video-mix-compact-actions">
          <button type="button" class="ghost-btn" data-open-local-path="${escapeAttr(zipImport.extracted_root || state.dashboard?.project?.root_path || "")}">${escapeHtml(t("source_open_dir"))}</button>
          <button type="button" class="ghost-btn" data-open-local-path="${escapeAttr(state.workDir || zipImport.work_dir || qs("#vm-source-workdir-input")?.value?.trim() || "")}">${escapeHtml(t("source_open_workdir"))}</button>
        </div>
      </div>
      <div class="video-mix-summary-grid">
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_blocks"))}</span><strong>${escapeHtml(zipImport.block_count)}</strong></div>
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_takes"))}</span><strong>${escapeHtml(zipImport.total_take_count || 0)}</strong></div>
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_marker_videos"))}</span><strong>${escapeHtml(zipImport.marker_video_count || 0)}</strong></div>
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_marker_takes"))}</span><strong>${escapeHtml(zipImport.marker_split_take_count || 0)}</strong></div>
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_ignored"))}</span><strong>${escapeHtml(zipImport.ignored_file_count || 0)}</strong></div>
        <div class="video-mix-summary-card"><span>${escapeHtml(t("source_zip_warnings"))}</span><strong>${escapeHtml(zipImport.warning_count || 0)}</strong></div>
      </div>
      ${warningLines ? `<div class="video-mix-section"><h4>${escapeHtml(t("source_zip_warnings_title"))}</h4><ul class="video-mix-preview-list">${warningLines}</ul></div>` : ""}
    `;
    bindOpenLocalPathButtons(target);
    return;
  }
  if (!state.sourceScan) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("source_scan_empty"))}</div>`;
    return;
  }
  const hasCounts = Number.isFinite(Number(state.sourceScan.total_files))
    && Number.isFinite(Number(state.sourceScan.supported_media_count));
  if (!hasCounts) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("source_scan_empty"))}</div>`;
    return;
  }
  const preview = (state.sourceScan.preview_files || [])
    .map((name) => `<li><code>${escapeHtml(name)}</code></li>`)
    .join("");
  const moreCount = Math.max(0, Number(state.sourceScan.supported_media_count || 0) - Number((state.sourceScan.preview_files || []).length));
  const moreLine = moreCount ? `<div class="muted">${escapeHtml(t("source_scan_preview_more", { count: moreCount }))}</div>` : "";
  target.innerHTML = `
    <div class="video-mix-section">
      <h4>${escapeHtml(t("source_scan_actions"))}</h4>
      <div class="actions-row video-mix-compact-actions">
        <button type="button" class="ghost-btn" data-open-local-path="${escapeAttr(state.sourceScan.source_dir)}">${escapeHtml(t("source_open_dir"))}</button>
        <button type="button" class="ghost-btn" data-open-local-path="${escapeAttr(state.sourceScan.suggested_work_dir)}">${escapeHtml(t("source_open_workdir"))}</button>
      </div>
    </div>
    <div class="video-mix-summary-grid">
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_total_files"))}</span><strong>${escapeHtml(state.sourceScan.total_files)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_media"))}</span><strong>${escapeHtml(state.sourceScan.supported_media_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_videos"))}</span><strong>${escapeHtml(state.sourceScan.supported_video_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_photos"))}</span><strong>${escapeHtml(state.sourceScan.supported_photo_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_ignored"))}</span><strong>${escapeHtml(state.sourceScan.ignored_or_unsupported_count)}</strong></div>
    </div>
    <div class="video-mix-section">
      <h4>${escapeHtml(t("source_scan_preview"))}</h4>
      <ul class="video-mix-preview-list">${preview}</ul>
      ${moreLine}
    </div>
  `;
  bindOpenLocalPathButtons(target);
}

function mediaTypeLabel(mediaType) {
  return t(`project_files_media_${mediaType}`) || mediaType || t("project_files_media_other");
}

function applyProjectFilesPayload(payload) {
  if (!state.dashboard) {
    state.dashboard = { project_files: payload };
    return;
  }
  state.dashboard.project_files = payload;
}

function renderProjectFiles() {
  const target = qs("#vm-project-files-panel");
  if (!target) return;
  const projectFiles = state.dashboard?.project_files;
  if (!projectFiles?.source_dir) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("project_files_empty"))}</div>`;
    return;
  }
  const files = Array.isArray(projectFiles.files) ? projectFiles.files : [];
  if (!files.length) {
    target.innerHTML = `
      <div class="video-mix-project-files-header">
        <strong>${escapeHtml(t("project_files_count", { count: 0 }))}</strong>
      </div>
      <div class="empty">${escapeHtml(t("project_files_empty"))}</div>
    `;
    return;
  }
  target.innerHTML = `
    <div class="video-mix-project-files-header">
      <strong>${escapeHtml(t("project_files_count", { count: Number(projectFiles.file_count || files.length) }))}</strong>
    </div>
    <div class="video-mix-project-file-list">
      ${files.map((file) => `
        <div class="video-mix-project-file-row">
          <div class="video-mix-project-file-meta">
            <strong>${escapeHtml(file.name || file.relative_path || "")}</strong>
            <span class="muted">${escapeHtml(file.relative_path || "")}</span>
          </div>
          <div class="video-mix-project-file-actions">
            <span class="video-mix-pill">${escapeHtml(mediaTypeLabel(file.media_type || "other"))}</span>
            <button type="button" class="ghost-btn" data-open-local-path="${escapeAttr(file.absolute_path || "")}">${escapeHtml(t("project_files_open_file"))}</button>
            <button type="button" class="ghost-btn" data-remove-project-file="${escapeAttr(file.relative_path || "")}" data-remove-project-file-name="${escapeAttr(file.name || file.relative_path || "")}">${escapeHtml(t("project_files_remove"))}</button>
          </div>
        </div>
      `).join("")}
    </div>
  `;
  bindOpenLocalPathButtons(target);
  target.querySelectorAll("[data-remove-project-file]").forEach((button) => {
    button.onclick = async () => {
      await removeProjectFile(
        button.getAttribute("data-remove-project-file") || "",
        button.getAttribute("data-remove-project-file-name") || "",
      );
    };
  });
}

function projectMaterials() {
  return state.dashboard?.project_materials || { episodes: [], assets: [], counts: { all: 0, unassigned: 0, assigned: 0, reused: 0 } };
}

function ensureSelectedMaterialEpisode() {
  const episodes = projectMaterials().episodes || [];
  if (!episodes.length) {
    state.selectedMaterialEpisodeId = "";
    return "";
  }
  if (!episodes.some((episode) => episode.episode_id === state.selectedMaterialEpisodeId)) {
    state.selectedMaterialEpisodeId = episodes[0].episode_id;
  }
  return state.selectedMaterialEpisodeId;
}

function filteredProjectMaterialsAssets() {
  const materials = projectMaterials();
  return (materials.assets || []).filter((asset) => {
    if (state.projectMaterialsFilters.status !== "all" && asset.assignment_state !== state.projectMaterialsFilters.status) {
      return false;
    }
    if (state.projectMaterialsFilters.mediaType !== "all" && asset.media_type !== state.projectMaterialsFilters.mediaType) {
      return false;
    }
    if (state.projectMaterialsFilters.search) {
      const haystack = `${asset.file_name} ${asset.source_path}`.toLowerCase();
      if (!haystack.includes(state.projectMaterialsFilters.search)) {
        return false;
      }
    }
    return true;
  });
}

function renderMaterialEpisodes() {
  const target = qs("#vm-material-episodes");
  if (!target) return;
  const materials = projectMaterials();
  const episodes = materials.episodes || [];
  const selectedEpisodeId = ensureSelectedMaterialEpisode();
  if (!episodes.length) {
    target.innerHTML = `<div class="empty">${escapeHtml(activeWorkDir() ? "Эпизодов пока нет. Нажмите «Добавить Episode»." : t("materials_no_episodes"))}</div>`;
    return;
  }
  target.innerHTML = episodes.map((episode) => {
    const takes = (episode.takes || []).length
      ? episode.takes.map((take) => `
        <button
          class="video-mix-take-chip"
          type="button"
          data-take-editor-open="true"
          data-take-episode-id="${escapeAttr(episode.episode_id)}"
          data-take-editor-id="${escapeAttr(take.take_id)}"
          aria-label="${escapeAttr(take.file_name || take.take_id || "")}"
          title="${escapeAttr(take.file_name || take.take_id || "")}"
        >
          ${episodeTakeCompactPreviewHtml(take.source_path)}
        </button>
      `).join("")
      : `<div class="empty compact">${escapeHtml(t("materials_episode_empty"))}</div>`;
    return `
      <article class="video-mix-episode-card${episode.episode_id === selectedEpisodeId ? " is-selected" : ""}" data-episode-id="${escapeAttr(episode.episode_id)}">
        <div class="video-mix-episode-header">
          <div>
            <h3>${escapeHtml(episode.label)}</h3>
            <div class="muted">${escapeHtml(episode.episode_id)}</div>
          </div>
          <div class="video-mix-episode-header-actions">
            <span class="status-chip ${episode.episode_id === selectedEpisodeId ? "status-active" : "status-idle"}">${escapeHtml(episode.episode_id === selectedEpisodeId ? t("materials_episode_selected") : `${(episode.takes || []).length} takes`)}</span>
            <button class="ghost-btn video-mix-episode-add-file-btn" type="button" data-episode-add-file="${escapeAttr(episode.episode_id)}">${escapeHtml(t("materials_add_file"))}</button>
          </div>
        </div>
        <div class="video-mix-episode-drop-zone" data-episode-drop="${escapeAttr(episode.episode_id)}">${escapeHtml(t("materials_episode_drop"))}</div>
        <div class="video-mix-episode-takes-strip">${takes}</div>
      </article>
    `;
  }).join("");

  target.querySelectorAll(".video-mix-episode-card[data-episode-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      state.selectedMaterialEpisodeId = card.dataset.episodeId || "";
      renderAll();
    });
    ["dragenter", "dragover"].forEach((eventName) => {
      card.addEventListener(eventName, (event) => {
        event.preventDefault();
        card.classList.add("is-dragover");
      });
    });
    ["dragleave", "dragend", "drop"].forEach((eventName) => {
      card.addEventListener(eventName, () => card.classList.remove("is-dragover"));
    });
    card.addEventListener("drop", async (event) => {
      event.preventDefault();
      const files = Array.from(event.dataTransfer?.files || []);
      if (files.length) {
        await uploadProjectMaterialsToEpisode(files, card.dataset.episodeId || "");
        return;
      }
      const raw = event.dataTransfer?.getData("application/json") || "";
      if (!raw) return;
      const payload = JSON.parse(raw);
      await assignProjectMaterialToEpisode(payload.asset_id, card.dataset.episodeId || "", Boolean(payload.reuse));
    });
  });
  target.querySelectorAll("[data-episode-drop]").forEach((zone) => {
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.add("is-dragover");
      });
    });
    ["dragleave", "dragend", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, () => zone.classList.remove("is-dragover"));
    });
    zone.addEventListener("drop", async (event) => {
      event.preventDefault();
      const files = Array.from(event.dataTransfer?.files || []);
      if (files.length) {
        await uploadProjectMaterialsToEpisode(files, zone.dataset.episodeDrop || "");
        return;
      }
      const raw = event.dataTransfer?.getData("application/json") || "";
      if (!raw) return;
      const payload = JSON.parse(raw);
      await assignProjectMaterialToEpisode(payload.asset_id, zone.dataset.episodeDrop || "", Boolean(payload.reuse));
    });
  });
  target.querySelectorAll("[data-take-editor-open='true']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openTakeEditor(button.dataset.takeEpisodeId || "", button.dataset.takeEditorId || "");
    });
  });
  target.querySelectorAll("[data-episode-add-file]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const nativeInput = qs("#vm-episode-file-native-input");
      if (!nativeInput) return;
      nativeInput.dataset.targetEpisodeId = button.dataset.episodeAddFile || "";
      if (typeof nativeInput.showPicker === "function") {
        nativeInput.showPicker();
        return;
      }
      nativeInput.click();
    });
  });
}

function renderMaterialTimeline() {
  const target = qs("#vm-material-timeline");
  if (!target) return;
  const materials = projectMaterials();
  const rows = materials.timeline?.rows || [];
  const selectedEpisodeId = ensureSelectedMaterialEpisode();
  if (!rows.length || !materials.timeline?.has_blocks) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("timeline_empty"))}</div>`;
    return;
  }
  target.innerHTML = rows.map((row) => {
    const blocks = (row.blocks || []).length
      ? row.blocks.map((block) => `
        <button class="video-mix-timeline-block${row.episode_id === selectedEpisodeId ? " is-selected" : ""}" type="button" data-timeline-episode-id="${escapeAttr(row.episode_id)}" data-timeline-take-id="${escapeAttr(block.take_id)}">
          <strong>${escapeHtml(block.file_name)}</strong>
          <span>#${escapeHtml(block.order)} · ${escapeHtml(block.media_type)} · ${escapeHtml(formatDurationMs(block.duration_ms || 0))}</span>
          <span>${escapeHtml(formatSecondsValue(block.source_start_ms))}s → ${escapeHtml(formatSecondsValue(block.source_end_ms))}s</span>
          <span class="video-mix-timeline-block-mode">${escapeHtml(t(`timeline_block_${block.mode}`))}</span>
        </button>
      `).join("")
      : `<div class="video-mix-timeline-row-empty">${escapeHtml(t("timeline_row_empty"))}</div>`;
    return `
      <div class="video-mix-timeline-row${row.episode_id === selectedEpisodeId ? " is-selected" : ""}">
        <div class="video-mix-timeline-row-label">
          <strong>${escapeHtml(row.label)}</strong>
          <span class="muted">${escapeHtml(row.episode_id)}</span>
        </div>
        <div class="video-mix-timeline-track">
          ${blocks}
        </div>
      </div>
    `;
  }).join("");

  target.querySelectorAll("[data-timeline-episode-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedMaterialEpisodeId = button.dataset.timelineEpisodeId || "";
      if (button.dataset.timelineTakeId) {
        openTakeEditor(button.dataset.timelineEpisodeId || "", button.dataset.timelineTakeId || "");
        return;
      }
      renderAll();
    });
  });
}

function renderProjectMaterialsModal() {
  const countsTarget = qs("#vm-project-materials-counts");
  const gridTarget = qs("#vm-project-materials-grid");
  if (!countsTarget || !gridTarget) return;
  const materials = projectMaterials();
  const assets = filteredProjectMaterialsAssets();
  const selectedEpisodeId = ensureSelectedMaterialEpisode();
  countsTarget.innerHTML = `
    <span class="status-chip status-idle">${escapeHtml(t("materials_count_all"))}: ${escapeHtml(materials.counts?.all || 0)}</span>
    <span class="status-chip status-idle">${escapeHtml(t("materials_count_unassigned"))}: ${escapeHtml(materials.counts?.unassigned || 0)}</span>
    <span class="status-chip status-idle">${escapeHtml(t("materials_count_assigned"))}: ${escapeHtml(materials.counts?.assigned || 0)}</span>
    <span class="status-chip status-idle">${escapeHtml(t("materials_count_reused"))}: ${escapeHtml(materials.counts?.reused || 0)}</span>
  `;
  if (!assets.length) {
    gridTarget.innerHTML = `<div class="empty">${escapeHtml(t("materials_no_assets"))}</div>`;
    return;
  }
  gridTarget.innerHTML = assets.map((asset) => {
    const assignments = (asset.assignments || []).map((assignment) => assignment.episode_label).join(", ");
    const isUnassigned = asset.assignment_state === "unassigned";
    return `
      <article class="video-mix-material-card" draggable="${isUnassigned ? "true" : "false"}" data-asset-id="${escapeAttr(asset.asset_id)}">
        <div class="video-mix-material-thumb">${escapeHtml(String(asset.media_type || "file").slice(0, 1).toUpperCase())}</div>
        <div class="video-mix-material-body">
          <strong>${escapeHtml(asset.file_name)}</strong>
          <div class="muted">${escapeHtml(asset.media_type)} · ${escapeHtml(formatDurationMs(asset.duration_ms || 0))}</div>
          <div class="status-chip status-idle">${escapeHtml(t(`materials_asset_${asset.assignment_state}`))}</div>
          ${assignments ? `<div class="muted">${escapeHtml(t("materials_assignment_locations"))}: ${escapeHtml(assignments)}</div>` : ""}
        </div>
        <div class="video-mix-material-actions">
          <button class="ghost-btn video-mix-material-assign-btn" type="button" data-asset-id="${escapeAttr(asset.asset_id)}" ${selectedEpisodeId ? "" : "disabled"}>${escapeHtml(t("materials_assign_here"))}</button>
          <button class="ghost-btn video-mix-material-reuse-btn" type="button" data-asset-id="${escapeAttr(asset.asset_id)}" ${selectedEpisodeId ? "" : "disabled"}>${escapeHtml(t("materials_reuse_here"))}</button>
        </div>
      </article>
    `;
  }).join("");
  gridTarget.querySelectorAll(".video-mix-material-card[draggable='true']").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      const payload = { asset_id: card.dataset.assetId, reuse: false };
      event.dataTransfer?.setData("application/json", JSON.stringify(payload));
      event.dataTransfer.effectAllowed = "move";
    });
  });
  gridTarget.querySelectorAll(".video-mix-material-assign-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      await assignProjectMaterialToEpisode(button.dataset.assetId || "", ensureSelectedMaterialEpisode(), false);
    });
  });
  gridTarget.querySelectorAll(".video-mix-material-reuse-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      await assignProjectMaterialToEpisode(button.dataset.assetId || "", ensureSelectedMaterialEpisode(), true);
    });
  });
}

function renderQuickMixSummary() {
  const target = qs("#vm-quickmix-summary");
  if (!target) return;
  if (!state.quickMixResult) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("quickmix_empty"))}</div>`;
    return;
  }
  const episodeGroups = state.quickMixResult.episode_groups || [];
  const totalTakeCount = episodeGroups.reduce((sum, group) => sum + Number(group.take_count || 0), 0);
  const markerEpisodeCount = episodeGroups.filter((group) => group.marker_split).length;
  const variants = state.quickMixResult.variants || [];
  target.innerHTML = `
    <div class="video-mix-summary-grid">
      <div class="video-mix-summary-card"><span>${escapeHtml(t("quickmix_generated_count"))}</span><strong>${escapeHtml(state.quickMixResult.generated_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_videos"))}</span><strong>${escapeHtml(state.quickMixResult.video_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_photos"))}</span><strong>${escapeHtml(state.quickMixResult.image_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("quickmix_episode_groups"))}</span><strong>${escapeHtml(episodeGroups.length)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("quickmix_take_count"))}</span><strong>${escapeHtml(totalTakeCount)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("quickmix_marker_groups"))}</span><strong>${escapeHtml(markerEpisodeCount)}</strong></div>
    </div>
    <div class="muted">${escapeHtml(t(state.quickMixResult.duration_source === "music" ? "quickmix_duration_source_music" : "quickmix_duration_source_manual"))}</div>
    <div class="muted">${escapeHtml(state.quickMixResult.photo_support ? t("quickmix_photos_supported") : t("quickmix_photos_unsupported"))}</div>
    ${variants.length ? `
      <div class="video-mix-section">
        <h4>${escapeHtml(t("quickmix_variants_title"))}</h4>
        <div class="video-mix-source-list">
          ${variants.map((variant) => `
            <div class="video-mix-source-row">
              <strong>${escapeHtml(variant.variant_id || "")}</strong>
              <span>${escapeHtml(t("quickmix_variant_order"))}: ${escapeHtml((variant.selected_takes || []).map((take) => take.episode_label || take.episode_id).join(" → "))}</span>
              <span>${escapeHtml(t("quickmix_variant_takes"))}: ${escapeHtml((variant.selected_takes || []).map((take) => `${take.episode_label || take.episode_id} / take ${take.take_index}`).join(" | "))}</span>
            </div>
          `).join("")}
        </div>
      </div>
    ` : ""}
  `;
}

function setLocale(locale) {
  if (!LOCALES.includes(locale) || locale === state.locale) return;
  state.locale = locale;
  persistLocale();
  applyStaticTranslations();
  syncLocaleToUrl();
  renderAll();
}

function visibleCandidates() {
  if (!state.dashboard?.candidates?.length) {
    return [];
  }

  const filtered = state.dashboard.candidates.filter((candidate) => {
    if (state.filters.status !== "all" && candidate.status !== state.filters.status) {
      return false;
    }
    if (state.filters.warnings === "with_warnings" && candidate.warnings.length === 0) {
      return false;
    }
    if (state.filters.warnings === "without_warnings" && candidate.warnings.length > 0) {
      return false;
    }
    if (state.filters.search) {
      const haystack = [
        candidate.template_id,
        ...(candidate.source_filenames || []),
        candidate.candidate_id,
      ].join(" ").toLowerCase();
      if (!haystack.includes(state.filters.search)) {
        return false;
      }
    }
    return true;
  });

  const sorted = [...filtered];
  sorted.sort((left, right) => {
    switch (state.filters.sort) {
      case "score_asc":
        return Number(left.score) - Number(right.score);
      case "score_desc":
        return Number(right.score) - Number(left.score);
      case "duration_asc":
        return Number(left.duration_ms) - Number(right.duration_ms);
      case "duration_desc":
        return Number(right.duration_ms) - Number(left.duration_ms);
      case "status_asc":
        return (STATUS_ORDER[left.status] ?? 99) - (STATUS_ORDER[right.status] ?? 99);
      case "template_asc":
        return compareStrings(left.template_id, right.template_id);
      case "source_asc":
        return compareStrings(left.source_filenames?.[0], right.source_filenames?.[0]);
      default:
        return Number(right.score) - Number(left.score);
    }
  });
  return sorted;
}

export function filterSelectedCandidateIdsToVisible(selectedCandidateIds, visibleCandidateIds) {
  const selected = selectedCandidateIds instanceof Set
    ? selectedCandidateIds
    : new Set(selectedCandidateIds || []);
  return [...(visibleCandidateIds || [])].filter((candidateId) => selected.has(candidateId));
}

export function collectDraftNotesFromElements(noteElements) {
  const drafts = new Map();
  for (const element of noteElements || []) {
    const candidateId = element?.dataset?.noteFor;
    if (!candidateId) continue;
    drafts.set(candidateId, String(element.value ?? ""));
  }
  return drafts;
}

export function resolveReviewNoteValue(candidate, draftNotesByCandidateId = new Map()) {
  if (draftNotesByCandidateId.has(candidate.candidate_id)) {
    return draftNotesByCandidateId.get(candidate.candidate_id) || "";
  }
  return candidate.review_notes || "";
}

function quickMixOutputPaths() {
  if (state.quickMixResult?.output_paths?.length) {
    return state.quickMixResult.output_paths;
  }
  if (state.dashboard?.quick_mix?.output_paths?.length) {
    return state.dashboard.quick_mix.output_paths;
  }
  return [];
}

function isQuickMixMode() {
  return Boolean(state.quickMixResult || state.dashboard?.quick_mix);
}

function syncSelectionToVisible() {
  if (!state.dashboard?.candidates?.length) {
    state.selectedCandidateIds = new Set();
    return;
  }
  const validIds = new Set(state.dashboard.candidates.map((candidate) => candidate.candidate_id));
  state.selectedCandidateIds = new Set(
    [...state.selectedCandidateIds].filter((candidateId) => validIds.has(candidateId)),
  );
}

function renderProjectMeta() {
  const target = qs("#vm-project-meta");
  const summaryTarget = qs("#vm-summary-grid");
  const countChip = qs("#vm-candidate-count");
  const isQuickMix = isQuickMixMode();
  const outputPaths = quickMixOutputPaths();
  const actionsHelp = qs("#vm-actions-help");
  const exportButton = qs("#vm-export-btn");
  const candidatesTitle = qs("#vm-candidates-title");
  const candidatesHelp = qs("#vm-candidates-help");
  const candidateToolbar = qs("#vm-candidate-toolbar");
  const selectionBar = qs("#vm-selection-bar");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("project_meta_empty"))}</div>`;
    summaryTarget.innerHTML = "";
    countChip.textContent = t("candidate_count", { count: 0 });
    countChip.className = "status-chip status-idle";
    actionsHelp.textContent = t("actions_help");
    exportButton.textContent = t("export_approved");
    candidatesTitle.textContent = t("candidates_title");
    candidatesHelp.textContent = t("candidates_help");
    candidateToolbar.hidden = false;
    selectionBar.hidden = false;
    return;
  }

  const { project, work_dir: workDir, summary } = state.dashboard;
  target.innerHTML = `
    <div class="video-mix-project-panel">
      <div><span>${escapeHtml(t("project_label"))}</span><strong>${escapeHtml(project.name)}</strong></div>
      <div><span>${escapeHtml(t("pack_label"))}</span><strong>${escapeHtml(project.industry_pack)}</strong></div>
      <div><span>${escapeHtml(t("root_label"))}</span><code>${escapeHtml(project.root_path)}</code></div>
      <div><span>work_dir</span><code>${escapeHtml(workDir)}</code></div>
    </div>
  `;
  const items = [
    [t("summary_assets"), summary.asset_count],
    [t("summary_clips"), summary.clip_count],
    [t("summary_candidates"), summary.candidate_count],
    [t("summary_approved"), summary.approved_candidate_count],
    [t("summary_exported"), summary.exported_candidate_count],
    [t("summary_rejected"), summary.status_totals.rejected || 0],
  ];
  summaryTarget.innerHTML = items.map(([label, value]) => `
    <div class="video-mix-summary-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");

  if (isQuickMix) {
    countChip.textContent = t("quickmix_output_count", { count: outputPaths.length });
    countChip.className = `status-chip ${outputPaths.length ? "status-completed" : "status-idle"}`;
    actionsHelp.textContent = t("actions_help_quickmix");
    exportButton.textContent = t("open_ready_videos");
    candidatesTitle.textContent = t("quickmix_outputs_title");
    candidatesHelp.textContent = t("quickmix_outputs_help");
    candidateToolbar.hidden = true;
    selectionBar.hidden = true;
    return;
  }

  countChip.textContent = t("candidate_count", { count: summary.candidate_count });
  countChip.className = `status-chip ${summary.candidate_count ? "status-completed" : "status-idle"}`;
  actionsHelp.textContent = t("actions_help");
  exportButton.textContent = t("export_approved");
  candidatesTitle.textContent = t("candidates_title");
  candidatesHelp.textContent = t("candidates_help");
  candidateToolbar.hidden = false;
  selectionBar.hidden = false;
}

function renderPipeline() {
  const targets = [qs("#vm-pipeline"), qs("#vm-pipeline-modal-body")].filter(Boolean);
  if (!targets.length) {
    return;
  }
  if (!state.dashboard) {
    const emptyHtml = `<div class="empty">${escapeHtml(t("pipeline_empty"))}</div>`;
    targets.forEach((target) => {
      target.innerHTML = emptyHtml;
    });
    return;
  }
  const pipelineHtml = state.dashboard.pipeline.map((step) => `
    <div class="pipeline-step ${escapeAttr(step.state === "ready" ? "active" : "")}">
      <strong>${escapeHtml(pipelineLabel(step))}</strong>
      <span>${escapeHtml(t("pipeline_item_count", { count: step.count }))}</span>
      <span class="video-mix-step-state">${escapeHtml(pipelineStateLabel(step.state))}</span>
    </div>
  `).join("");
  targets.forEach((target) => {
    target.innerHTML = pipelineHtml;
  });
}

function candidateCommandButtons(candidate) {
  return `
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.approve_command)}">${escapeHtml(t("copy_approve"))}</button>
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.reject_command)}">${escapeHtml(t("copy_reject"))}</button>
  `;
}

function renderSelectionSummary(visible) {
  const selectedCount = state.selectedCandidateIds.size;
  qs("#vm-selected-count").textContent = t("selected_count", { count: selectedCount });
  qs("#vm-visible-count").textContent = t("visible_count", { count: visible.length });
}

function cacheDraftNotes() {
  if (typeof document === "undefined") return;
  const drafts = collectDraftNotesFromElements(document.querySelectorAll("[data-note-for]"));
  drafts.forEach((value, candidateId) => {
    state.draftNotesByCandidateId.set(candidateId, value);
  });
}

function renderCandidates() {
  const target = qs("#vm-candidates");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("no_workdir_loaded"))}</div>`;
    renderSelectionSummary([]);
    return;
  }

  if (isQuickMixMode()) {
    const outputPaths = quickMixOutputPaths();
    renderSelectionSummary([]);
    if (!outputPaths.length) {
      target.innerHTML = `<div class="empty">${escapeHtml(t("quickmix_no_outputs"))}</div>`;
      return;
    }
    target.innerHTML = `
      <article class="video-mix-candidate-card">
        <div class="video-mix-section">
          <h4>${escapeHtml(t("quickmix_ready_files"))}</h4>
          <div class="video-mix-export-list">
            ${outputPaths.map((path) => `
              <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
            `).join("")}
          </div>
        </div>
      </article>
    `;
    return;
  }

  const candidates = visibleCandidates();
  renderSelectionSummary(candidates);
  if (!candidates.length) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("no_candidates_match_filters"))}</div>`;
    return;
  }

  target.innerHTML = candidates.map((candidate) => {
    const isSelected = state.selectedCandidateIds.has(candidate.candidate_id);
    const thumbnail = candidate.thumbnail_path
      ? `<img class="video-mix-thumb" src="${escapeAttr(fileUrl(candidate.thumbnail_path))}" alt="${escapeAttr(t("thumbnail_alt", { candidateId: candidate.candidate_id }))}">`
      : `<div class="video-mix-thumb video-mix-thumb-placeholder">${escapeHtml(t("no_thumbnail"))}</div>`;
    const warnings = candidate.warnings.length
      ? candidate.warnings.map((warning) => `<span class="video-mix-pill warning">${escapeHtml(warning)}</span>`).join("")
      : `<span class="video-mix-pill ok">${escapeHtml(t("no_warnings"))}</span>`;
    const exports = candidate.export_paths.length
      ? candidate.export_paths.map((path) => `
          <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
        `).join("")
      : `<div class="muted">${escapeHtml(t("no_exports"))}</div>`;
    const sources = candidate.source_clips.length
      ? candidate.source_clips.map((clip) => `
          <div class="video-mix-source-row">
            <strong>${escapeHtml(clip.source_filename)}</strong>
            <span>${escapeHtml(formatDurationMs(clip.start_ms))} → ${escapeHtml(formatDurationMs(clip.end_ms))}</span>
            <span>${escapeHtml(clip.tags.join(", ") || t("no_tags"))}</span>
          </div>
        `).join("")
      : `<div class="muted">${escapeHtml(t("no_source_clips"))}</div>`;
    const noteValue = escapeAttr(resolveReviewNoteValue(candidate, state.draftNotesByCandidateId));
    return `
      <article class="video-mix-candidate-card ${isSelected ? "is-selected" : ""}">
        <div class="video-mix-card-toolbar">
          <label class="video-mix-select-toggle">
            <input type="checkbox" data-select-candidate="${escapeAttr(candidate.candidate_id)}" ${isSelected ? "checked" : ""}>
            <span>${escapeHtml(t("select"))}</span>
          </label>
          <span class="status-chip status-${escapeAttr(candidate.status)}">${escapeHtml(statusLabel(candidate.status))}</span>
        </div>
        <div class="video-mix-card-top">
          ${thumbnail}
          <div class="video-mix-card-head">
            <div class="card-header">
              <div>
                <h3>${escapeHtml(candidate.candidate_id)}</h3>
                <p class="muted">${escapeHtml(candidate.template_id)}</p>
              </div>
            </div>
            <div class="video-mix-metrics">
              <div><span>${escapeHtml(t("metric_score"))}</span><strong>${escapeHtml(candidate.score)}</strong></div>
              <div><span>${escapeHtml(t("metric_duration"))}</span><strong>${escapeHtml(formatDurationMs(candidate.duration_ms))}</strong></div>
              <div><span>${escapeHtml(t("metric_source_files"))}</span><strong>${escapeHtml(candidate.source_filenames.length)}</strong></div>
            </div>
          </div>
        </div>
        <div class="video-mix-section">
          <h4>${escapeHtml(t("section_warnings"))}</h4>
          <div class="video-mix-pill-row">${warnings}</div>
        </div>
        <div class="video-mix-section">
          <h4>${escapeHtml(t("section_source_filenames"))}</h4>
          <div class="video-mix-source-list">${sources}</div>
        </div>
        <div class="video-mix-section">
          <h4>${escapeHtml(t("section_review_note"))}</h4>
          <textarea class="video-mix-note" data-note-for="${escapeAttr(candidate.candidate_id)}" rows="3" placeholder="${escapeAttr(t("note_placeholder"))}">${noteValue}</textarea>
        </div>
        <div class="video-mix-section">
          <h4>${escapeHtml(t("section_exports"))}</h4>
          <div class="video-mix-export-list">${exports}</div>
        </div>
        <div class="video-mix-actions">
          <button class="accent-btn" type="button" data-approve="${escapeAttr(candidate.candidate_id)}">${escapeHtml(t("approve"))}</button>
          <button class="ghost-btn" type="button" data-reject="${escapeAttr(candidate.candidate_id)}">${escapeHtml(t("reject"))}</button>
          ${candidateCommandButtons(candidate)}
        </div>
      </article>
    `;
  }).join("");

  document.querySelectorAll("[data-select-candidate]").forEach((checkbox) => {
    checkbox.onchange = () => toggleSelection(checkbox.dataset.selectCandidate, checkbox.checked);
  });
  document.querySelectorAll("[data-approve]").forEach((button) => {
    button.onclick = () => submitCandidateStatus(button.dataset.approve, "approve");
  });
  document.querySelectorAll("[data-reject]").forEach((button) => {
    button.onclick = () => submitCandidateStatus(button.dataset.reject, "reject");
  });
  document.querySelectorAll("[data-copy-command]").forEach((button) => {
    button.onclick = async () => {
      await navigator.clipboard.writeText(button.dataset.copyCommand);
      setLoadState(t("command_copied"), "status-completed");
    };
  });
  document.querySelectorAll("[data-note-for]").forEach((textarea) => {
    textarea.oninput = () => {
      state.draftNotesByCandidateId.set(textarea.dataset.noteFor, textarea.value);
    };
  });
}

function renderExportsPanel(paths = []) {
  const target = qs("#vm-exports-list");
  if (!paths.length) {
    target.innerHTML = `<div class="muted">${escapeHtml(t("no_export_paths_session"))}</div>`;
    return;
  }
  target.innerHTML = paths.map((path) => `
    <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
  `).join("");
}

function renderAll() {
  cacheDraftNotes();
  syncLayoutMode();
  syncSelectionToVisible();
  renderActivityPanel();
  renderQuickMixSelections();
  renderQuickMixTimer();
  renderQuickMixEstimate();
  renderSourceScanSummary();
  renderProjectFiles();
  renderMaterialEpisodes();
  renderMaterialTimeline();
  renderTakeEditorModal();
  renderProjectMaterialsModal();
  renderQuickMixSummary();
  renderProjectMeta();
  renderPipeline();
  renderCandidates();
  renderExportsPanel(state.lastExportedPaths || []);
  renderDebugLog();
}

function closeOpenDashboardDialogs() {
  const dialogSelectors = ["#vm-pipeline-modal", "#vm-selected-media-modal", "#vm-take-editor-modal", "#vm-candidates-modal", "#vm-project-materials-modal"];
  dialogSelectors.forEach((selector) => {
    const dialog = qs(selector);
    if (dialog?.open) {
      dialog.close();
    }
  });
}

function resetProjectWorkspace() {
  stopActivity();
  closeOpenDashboardDialogs();
  if (quickMixEstimateDebounceId) {
    window.clearTimeout(quickMixEstimateDebounceId);
    quickMixEstimateDebounceId = null;
  }

  qs("#vm-source-dir-input").value = "";
  qs("#vm-source-project-name-input").value = "";
  qs("#vm-source-workdir-input").value = "";
  qs("#vm-workdir-input").value = "";
  qs("#vm-quickmix-duration-input").value = "10";
  qs("#vm-quickmix-count-input").value = "2";
  qs("#vm-quickmix-use-music-duration").checked = false;
  qs("#vm-quickmix-use-closing-duration").checked = false;
  qs("#vm-search").value = "";
  qs("#vm-filter-status").value = DEFAULT_FILTERS.status;
  qs("#vm-filter-warnings").value = DEFAULT_FILTERS.warnings;
  qs("#vm-sort").value = DEFAULT_FILTERS.sort;
  qs("#vm-quickmix-music-native-input").value = "";
  qs("#vm-quickmix-opening-native-input").value = "";
  qs("#vm-quickmix-closing-native-input").value = "";
  qs("#vm-project-files-native-input").value = "";
  writeQuickMixFileList("#vm-quickmix-music-input", []);
  writeQuickMixFileList("#vm-quickmix-opening-input", []);
  writeQuickMixFileList("#vm-quickmix-closing-input", []);

  Object.assign(state, buildEmptyProjectWorkspaceState(state.debugLogs));
  renderAll();
  setLocalizedLoadState("load_state_reset_done", "status-queued");
  syncLocaleToUrl();
}

function applyDashboardPayload(payload) {
  state.dashboard = payload;
  state.zipImportResult = payload?.zip_import || null;
  state.draftNotesByCandidateId = new Map();
  if (payload?.quick_mix) {
    state.quickMixResult = {
      ...payload.quick_mix,
      work_dir: payload.work_dir || payload.quick_mix.work_dir || "",
      output_paths: payload.quick_mix.output_paths || [],
      duration_source: payload.quick_mix.duration_source || (payload.quick_mix.use_music_duration ? "music" : "manual"),
      photo_support: true,
      video_count: Number(payload.quick_mix.video_count ?? state.sourceScan?.supported_video_count ?? 0),
      image_count: Number(payload.quick_mix.image_count ?? state.sourceScan?.supported_photo_count ?? 0),
    };
  }
  syncSelectionToVisible();
  renderAll();
}

function activeWorkDir() {
  const fromState = String(state.workDir || "").trim();
  if (fromState) return fromState;
  const fromSource = String(qs("#vm-source-workdir-input")?.value || "").trim();
  if (fromSource) return fromSource;
  const fromManual = String(qs("#vm-workdir-input")?.value || "").trim();
  if (fromManual) return fromManual;
  return String(new URLSearchParams(window.location.search).get("work_dir") || "").trim();
}

async function loadDashboard(workDirOverride = "") {
  const input = qs("#vm-workdir-input");
  const workDir = workDirOverride || input.value.trim() || activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLocalizedLoadState("load_state_loading", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/dashboard?${new URLSearchParams({ work_dir: workDir }).toString()}`);
    const shouldHydrateSource = !state.manualSourceOverride;
    state.sourceScan = null;
    if (payload?.quick_mix?.source_dir) {
      if (shouldHydrateSource) {
        state.selectedSourcePath = payload.quick_mix.source_dir;
        qs("#vm-source-dir-input").value = payload.quick_mix.source_dir;
      }
      if (!qs("#vm-source-project-name-input").value.trim()) {
        qs("#vm-source-project-name-input").value = payload.project?.name || "";
      }
      qs("#vm-source-workdir-input").value = payload.work_dir || workDir;
      writeQuickMixFileList("#vm-quickmix-music-input", payload.quick_mix.music_paths || (payload.quick_mix.music_path ? [payload.quick_mix.music_path] : []));
      qs("#vm-quickmix-use-music-duration").checked = Boolean(
        payload.quick_mix.use_music_duration ?? (payload.quick_mix.duration_source === "music"),
      );
      qs("#vm-quickmix-use-closing-duration").checked = Boolean(payload.quick_mix.use_closing_duration);
      writeQuickMixFileList("#vm-quickmix-opening-input", payload.quick_mix.opening_media_paths || (payload.quick_mix.opening_media_path ? [payload.quick_mix.opening_media_path] : []));
      writeQuickMixFileList("#vm-quickmix-closing-input", payload.quick_mix.closing_media_paths || (payload.quick_mix.closing_media_path ? [payload.quick_mix.closing_media_path] : []));
      if (payload.quick_mix.duration_seconds) {
        qs("#vm-quickmix-duration-input").value = String(payload.quick_mix.duration_seconds);
      }
      if (payload.quick_mix.output_count) {
        qs("#vm-quickmix-count-input").value = String(payload.quick_mix.output_count);
      }
      if (payload.quick_mix.episode_duration_min_seconds) {
        qs("#vm-quickmix-episode-min-input").value = String(payload.quick_mix.episode_duration_min_seconds);
      }
      if (payload.quick_mix.episode_duration_max_seconds) {
        qs("#vm-quickmix-episode-max-input").value = String(payload.quick_mix.episode_duration_max_seconds);
      }
    } else if (payload?.project?.root_path && shouldHydrateSource) {
      state.selectedSourcePath = payload.project.root_path;
      qs("#vm-source-dir-input").value = payload.project.root_path;
    }
    applyDashboardPayload(payload);
    input.value = workDir;
    state.lastExportedPaths = [];
    renderExportsPanel([]);
    scheduleQuickMixEstimateRefresh(0);
    if (shouldHydrateSource) {
      await scanSourceMaterials();
    }
    syncLocaleToUrl();
  } catch (error) {
    state.dashboard = null;
    state.lastExportedPaths = [];
    state.selectedCandidateIds = new Set();
    state.draftNotesByCandidateId = new Map();
    renderAll();
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function browseWorkDir() {
  const initialDir = qs("#vm-workdir-input")?.value?.trim() || state.workDir || "";
  setLocalizedLoadState("load_state_browsing_workdir", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/pick-workdir", {
      method: "POST",
      body: JSON.stringify({ initial_dir: initialDir }),
    });
    if (payload.canceled) {
      setLocalizedLoadState("load_state_browse_canceled", "status-idle");
      return;
    }
    qs("#vm-workdir-input").value = payload.work_dir;
    await loadDashboard(payload.work_dir);
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function browseSourceDir() {
  const initialDir = currentSourcePath();
  setLocalizedLoadState("load_state_browsing_source", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/pick-source-folder", {
      method: "POST",
      body: JSON.stringify({ initial_dir: initialDir }),
    });
    if (payload.canceled) {
      setLocalizedLoadState("load_state_source_browse_canceled", "status-idle");
      return;
    }
    setManualSourcePath(payload.source_dir);
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = defaultSourceWorkDir(payload.source_dir);
      state.sourceWorkDirAuto = true;
    }
    state.sourceScan = null;
    state.quickMixResult = null;
    renderSourceScanSummary();
    renderQuickMixSummary();
    scheduleQuickMixEstimateRefresh();
    await scanSourceMaterials();
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function browseSourceZip() {
  const initialDir = currentSourcePath();
  setLocalizedLoadState("load_state_browsing_source_zip", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/pick-file", {
      method: "POST",
      body: JSON.stringify({ initial_dir: initialDir, title: "Select source ZIP file" }),
    });
    if (payload.canceled) {
      setLocalizedLoadState("load_state_source_zip_browse_canceled", "status-idle");
      return;
    }
    const projectName = qs("#vm-source-project-name-input")?.value?.trim() || "";
    const outputWorkDir = qs("#vm-source-workdir-input")?.value?.trim() || defaultSourceWorkDir(payload.file_path);
    const importPayload = await fetchJson("/api/video-mix/import-zip-path", {
      method: "POST",
      body: JSON.stringify({
        zip_path: payload.file_path,
        project_name: projectName,
        work_dir: outputWorkDir,
      }),
    });
    applyZipImportPayload(importPayload, payload.file_path, projectName, outputWorkDir);
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

function applyZipImportPayload(payload, sourcePathHint = "", projectName = "", outputWorkDir = "") {
  const effectiveWorkDir = outputWorkDir || payload.work_dir || defaultSourceWorkDir(sourcePathHint || "");
  state.zipImportResult = payload.zip_import_report || null;
  state.sourceScan = null;
  state.quickMixResult = null;
  state.selectedSourcePath = payload.project_root || sourcePathHint || "";
  qs("#vm-source-dir-input").value = payload.project_root || sourcePathHint || "";
  qs("#vm-source-project-name-input").value = payload.project_name || projectName || "";
  qs("#vm-source-workdir-input").value = payload.work_dir || effectiveWorkDir;
  qs("#vm-workdir-input").value = payload.work_dir || effectiveWorkDir;
  state.workDir = payload.work_dir || effectiveWorkDir;
  applyDashboardPayload(payload.dashboard);
  renderQuickMixSummary();
  scheduleQuickMixEstimateRefresh(0);
  setLocalizedLoadState("load_state_source_loaded", "status-completed");
  syncLocaleToUrl();
}

async function importZipFromFile(file, sourcePathHint = "", projectName = "", outputWorkDir = "") {
  setLocalizedLoadState("load_state_uploading_file", "status-downloading");
  const effectiveWorkDir = outputWorkDir || defaultSourceWorkDir(sourcePathHint || file?.name || "");
  const payload = await importZipArchive(file, {
    projectName,
    workDir: effectiveWorkDir,
  });
  applyZipImportPayload(payload, sourcePathHint, projectName, effectiveWorkDir);
}

async function browseQuickMixFile(inputSelector, title, loadingKey, canceledKey) {
  const existingPaths = readQuickMixFileList(inputSelector);
  const initialDir = existingPaths[existingPaths.length - 1] || qs("#vm-source-dir-input")?.value?.trim() || "";
  setLocalizedLoadState(loadingKey, "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/pick-file", {
      method: "POST",
      body: JSON.stringify({ initial_dir: initialDir, title }),
    });
    if (payload.canceled) {
      setLocalizedLoadState(canceledKey, "status-idle");
      return;
    }
    appendQuickMixFiles(inputSelector, [payload.file_path]);
    renderQuickMixSelections();
    scheduleQuickMixEstimateRefresh();
    setLocalizedLoadState("load_state_loaded", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function uploadNativeSelectedFile(hiddenValueSelector, purpose, nativeInputSelector) {
  const nativeInput = qs(nativeInputSelector);
  const files = Array.from(nativeInput?.files || []);
  if (!files.length) {
    return;
  }
  setLocalizedLoadState("load_state_uploading_file", "status-downloading");
  try {
    const uploadedPaths = [];
    for (const file of files) {
      const payload = await uploadDroppedFile(file, purpose);
      uploadedPaths.push(payload.file_path);
    }
    appendQuickMixFiles(hiddenValueSelector, uploadedPaths);
    renderQuickMixSelections();
    scheduleQuickMixEstimateRefresh();
    setLocalizedLoadState("load_state_uploaded_file", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  } finally {
    if (nativeInput) {
      nativeInput.value = "";
    }
  }
}

function applyDroppedFileToInput(inputSelector, filePath) {
  const input = qs(inputSelector);
  if (!input) return;
  if (inputSelector !== "#vm-source-dir-input") {
    appendQuickMixFiles(inputSelector, [filePath]);
    renderQuickMixSelections();
    scheduleQuickMixEstimateRefresh();
    return;
  }
  setManualSourcePath(filePath);
  if (inputSelector === "#vm-source-dir-input") {
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = defaultSourceWorkDir(filePath);
      state.sourceWorkDirAuto = true;
    }
    state.sourceScan = null;
    state.quickMixResult = null;
    renderSourceScanSummary();
    renderQuickMixSummary();
    scheduleQuickMixEstimateRefresh();
  } else {
    renderQuickMixSelections();
    scheduleQuickMixEstimateRefresh();
  }
}

async function handleDroppedFiles(inputSelector, purpose, files, invalidMessage) {
  const droppedFiles = Array.from(files || []);
  if (!droppedFiles.length) return;
  if (purpose === "source_zip" && !/\.zip$/i.test(droppedFiles[0]?.name || "")) {
    setLoadState(invalidMessage, "status-failed");
    resetDropZoneMessage("#vm-source-drop-zone", "source_drop_zip");
    return;
  }
  setLocalizedLoadState("load_state_uploading_file", "status-downloading");
  try {
    const uploadedPaths = [];
    for (const file of droppedFiles) {
      const payload = await uploadDroppedFile(file, purpose);
      uploadedPaths.push(payload.file_path);
    }
    if (inputSelector === "#vm-source-dir-input") {
      applyDroppedFileToInput(inputSelector, uploadedPaths[0]);
      await scanSourceMaterials();
    } else {
      appendQuickMixFiles(inputSelector, uploadedPaths);
      renderQuickMixSelections();
      scheduleQuickMixEstimateRefresh();
    }
    setLocalizedLoadState("load_state_uploaded_file", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
    if (purpose === "source_zip") {
      resetDropZoneMessage("#vm-source-drop-zone", "source_drop_zip");
    }
  }
}

async function handleDroppedSource(event) {
  const items = Array.from(event.dataTransfer?.items || []);
  const file = event.dataTransfer?.files?.[0];
  const firstItem = items.find((item) => item.kind === "file");
  const entry = firstItem && typeof firstItem.webkitGetAsEntry === "function" ? firstItem.webkitGetAsEntry() : null;
  const handle = firstItem && typeof firstItem.getAsFileSystemHandle === "function"
    ? await firstItem.getAsFileSystemHandle().catch(() => null)
    : null;
  const droppedName = handle?.name || entry?.name || file?.name || "";

  if (entry?.isDirectory || handle?.kind === "directory") {
    setLocalizedLoadState("load_state_uploading_file", "status-downloading");
    setDropZoneMessage("#vm-source-drop-zone", "source_drop_zip_processing");
    qs("#vm-source-drop-zone")?.classList.add("is-processing");
    try {
      const sessionId = (typeof crypto !== "undefined" && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
      const files = entry?.isDirectory
        ? await collectDirectoryFiles(entry)
        : await collectDirectoryFilesFromHandle(handle);
      if (!files.length) {
        throw new Error(t("source_drop_zip_empty"));
      }
      let rootDir = "";
      for (const item of files) {
        const payload = await uploadDroppedSourceTreeFile(item.file, sessionId, item.relativePath);
        rootDir = payload.root_dir || rootDir;
      }
      if (!rootDir) {
        throw new Error(t("request_failed"));
      }
      applyDroppedFileToInput("#vm-source-dir-input", rootDir);
      setDropZoneMessage("#vm-source-drop-zone", "source_drop_zip_ready", { name: droppedName || baseName(rootDir) });
      qs("#vm-source-drop-zone")?.classList.remove("is-processing");
      await scanSourceMaterials();
      return;
    } catch (error) {
      state.loadState = null;
      setLoadState(error.message, "status-failed");
      resetDropZoneMessage("#vm-source-drop-zone", "source_drop_zip");
      return;
    }
  }

  setDropZoneMessage("#vm-source-drop-zone", "source_drop_zip_processing");
  qs("#vm-source-drop-zone")?.classList.add("is-processing");
  if (file && /\.zip$/i.test(file.name || "")) {
    try {
      const projectName = qs("#vm-source-project-name-input")?.value?.trim() || "";
      const outputWorkDir = qs("#vm-source-workdir-input")?.value?.trim() || defaultSourceWorkDir(file.name || "");
      await importZipFromFile(file, file.name || "", projectName, outputWorkDir);
    } catch (error) {
      state.loadState = null;
      setLoadState(error.message, "status-failed");
      resetDropZoneMessage("#vm-source-drop-zone", "source_drop_zip");
      return;
    }
  } else {
    await handleDroppedFiles("#vm-source-dir-input", "source_zip", file ? [file] : [], t("load_state_drop_zip_only"));
  }
  if (file?.name) {
    setDropZoneMessage("#vm-source-drop-zone", "source_drop_zip_ready", { name: file.name });
    qs("#vm-source-drop-zone")?.classList.remove("is-processing");
  } else {
    resetDropZoneMessage("#vm-source-drop-zone", "source_drop_zip");
  }
}

async function addProjectFilesFromPaths(filePaths) {
  if (!state.workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  const normalizedPaths = Array.from(filePaths || []).map((value) => String(value || "").trim()).filter(Boolean);
  if (!normalizedPaths.length) {
    return;
  }
  setLocalizedLoadState("load_state_project_files_adding", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-files/add", {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        file_paths: normalizedPaths,
      }),
    });
    applyProjectFilesPayload(payload.project_files);
    state.sourceScan = payload.source_scan || state.sourceScan;
    renderAll();
    scheduleQuickMixEstimateRefresh(0);
    setLocalizedLoadState("load_state_project_files_added", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function uploadProjectFiles(files) {
  const droppedFiles = Array.from(files || []);
  if (!droppedFiles.length) return;
  setLocalizedLoadState("load_state_project_files_adding", "status-downloading");
  try {
    const uploadedPaths = [];
    for (const file of droppedFiles) {
      const payload = await uploadDroppedFile(file, "project_files");
      uploadedPaths.push(payload.file_path);
    }
    await addProjectFilesFromPaths(uploadedPaths);
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function handleDroppedProjectFiles(event) {
  await uploadProjectFiles(event.dataTransfer?.files || []);
}

async function removeProjectFile(relativePath, fileName = "") {
  if (!state.workDir || !relativePath) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  const confirmed = window.confirm(t("project_files_confirm_remove", { name: fileName || relativePath }));
  if (!confirmed) {
    return;
  }
  setLocalizedLoadState("load_state_project_file_removing", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-files/remove", {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        relative_path: relativePath,
      }),
    });
    applyProjectFilesPayload(payload.project_files);
    state.sourceScan = payload.source_scan || state.sourceScan;
    renderAll();
    scheduleQuickMixEstimateRefresh(0);
    setLocalizedLoadState("load_state_project_file_removed", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function openProjectSourceDir() {
  const sourceDir = state.dashboard?.project_files?.source_dir || state.dashboard?.project?.root_path || "";
  if (!sourceDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  await openLocalPath(sourceDir);
}

function bindDropZone(zoneSelector, inputSelector, purpose, invalidMessage) {
  const zone = qs(zoneSelector);
  if (!zone) return;
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      zone.classList.add("is-dragover");
    });
  });
  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.stopPropagation();
      zone.classList.remove("is-dragover");
    });
  });
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    await handleDroppedFiles(inputSelector, purpose, event.dataTransfer?.files || [], invalidMessage);
  });
}

function bindNativeQuickMixPicker(buttonSelector, nativeInputSelector, hiddenValueSelector, purpose, loadingKey, zoneSelector = "") {
  const nativeInput = qs(nativeInputSelector);
  const zone = zoneSelector ? qs(zoneSelector) : null;
  if (!nativeInput) {
    return;
  }
  const openPicker = () => {
    debugLog("click", `native-picker ${purpose}`, zoneSelector || nativeInputSelector);
    setLocalizedLoadState(loadingKey, "status-downloading");
    if (typeof nativeInput.showPicker === "function") {
      nativeInput.showPicker();
      return;
    }
    nativeInput.click();
  };
  if (zone) {
    zone.addEventListener("click", openPicker);
  }
  nativeInput.addEventListener("change", async () => {
    await uploadNativeSelectedFile(hiddenValueSelector, purpose, nativeInputSelector);
  });
}

function bindSourceDropZone(zoneSelector) {
  const zone = qs(zoneSelector);
  if (!zone) return;
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("is-dragover");
      if (!zone.classList.contains("is-processing")) {
        zone.textContent = t("source_drop_zip_hover");
      }
    });
  });
  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, () => {
      zone.classList.remove("is-dragover");
      if (!zone.classList.contains("is-processing")) {
        zone.textContent = t("source_drop_zip");
      }
    });
  });
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    await handleDroppedSource(event);
  });
}

function bindProjectFilesDropZone(zoneSelector) {
  const zone = qs(zoneSelector);
  if (!zone) return;
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("is-dragover");
    });
  });
  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, () => zone.classList.remove("is-dragover"));
  });
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    await handleDroppedProjectFiles(event);
  });
}

async function scanSourceMaterials() {
  const sourceDir = currentSourcePath();
  if (!sourceDir) {
    setLocalizedLoadState("load_state_enter_source_dir", "status-failed");
    return;
  }
  setLocalizedLoadState("load_state_scanning_source", "status-downloading");
  try {
    qs("#vm-source-dir-input").value = sourceDir;
    const payload = await fetchJson("/api/video-mix/source/scan", {
      method: "POST",
      body: JSON.stringify({ source_dir: sourceDir }),
    });
    state.sourceScan = payload;
    state.zipImportResult = null;
    state.selectedSourcePath = payload.source_dir || sourceDir;
    state.quickMixResult = null;
    qs("#vm-source-dir-input").value = payload.source_dir;
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = payload.suggested_work_dir;
      state.sourceWorkDirAuto = true;
    }
    if (!qs("#vm-source-project-name-input").value.trim()) {
      qs("#vm-source-project-name-input").value = payload.source_dir.split(/[/\\]/).pop() || "";
    }
    renderSourceScanSummary();
    renderQuickMixSummary();
    scheduleQuickMixEstimateRefresh(0);
    setLocalizedLoadState("load_state_source_scanned", "status-completed");
  } catch (error) {
    state.sourceScan = null;
    state.quickMixResult = null;
    renderSourceScanSummary();
    renderQuickMixSummary();
    state.quickMixEstimate = { status: "idle" };
    renderQuickMixEstimate();
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function planSourceMaterials() {
  const sourceDir = currentSourcePath();
  const projectName = qs("#vm-source-project-name-input")?.value?.trim() || "";
  const outputWorkDir = qs("#vm-source-workdir-input")?.value?.trim() || defaultSourceWorkDir(sourceDir);
  if (!sourceDir) {
    setLocalizedLoadState("load_state_enter_source_dir", "status-failed");
    return;
  }
  setLocalizedLoadState("load_state_planning_source", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/source/plan", {
      method: "POST",
      body: JSON.stringify({
        source_dir: sourceDir,
        project_name: projectName,
        work_dir: outputWorkDir,
      }),
    });
    state.sourceScan = {
      ...(state.sourceScan || {}),
      source_dir: payload.source_dir,
      suggested_work_dir: payload.work_dir,
    };
    state.zipImportResult = null;
    qs("#vm-source-dir-input").value = payload.source_dir;
    qs("#vm-source-project-name-input").value = payload.project_name || projectName;
    qs("#vm-source-workdir-input").value = payload.work_dir;
    qs("#vm-workdir-input").value = payload.work_dir;
    state.workDir = payload.work_dir;
    applyDashboardPayload(payload.dashboard);
    if (!payload.dashboard?.project_materials?.episodes?.length && payload.work_dir) {
      const materialsPayload = await fetchJson("/api/video-mix/project-materials/episodes", {
        method: "POST",
        body: JSON.stringify({ work_dir: payload.work_dir }),
      });
      applyDashboardPayload(materialsPayload.dashboard);
    }
    scheduleQuickMixEstimateRefresh(0);
    setLocalizedLoadState("load_state_generating_review", "status-downloading");
    renderExportsPanel([]);
    setLocalizedLoadState("load_state_source_loaded", "status-completed");
    syncLocaleToUrl();
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function quickMixSourceMaterials() {
  const sourceDir = currentSourcePath();
  const projectName = qs("#vm-source-project-name-input")?.value?.trim() || "";
  const outputWorkDir = qs("#vm-source-workdir-input")?.value?.trim() || defaultSourceWorkDir(sourceDir);
  const durationSeconds = Number(qs("#vm-quickmix-duration-input")?.value || 0);
  const outputCount = Number(qs("#vm-quickmix-count-input")?.value || 0);
  const episodeDurationMinSeconds = Number(qs("#vm-quickmix-episode-min-input")?.value || 0);
  const episodeDurationMaxSeconds = Number(qs("#vm-quickmix-episode-max-input")?.value || 0);
  const musicPaths = readQuickMixFileList("#vm-quickmix-music-input");
  const useMusicDuration = Boolean(qs("#vm-quickmix-use-music-duration")?.checked);
  const openingMediaPaths = readQuickMixFileList("#vm-quickmix-opening-input");
  const closingMediaPaths = readQuickMixFileList("#vm-quickmix-closing-input");
  const useClosingDuration = Boolean(qs("#vm-quickmix-use-closing-duration")?.checked);
  if (!sourceDir) {
    setLocalizedLoadState("load_state_enter_source_dir", "status-failed");
    return;
  }
  if (!(durationSeconds > 0)) {
    setLocalizedLoadState("load_state_enter_duration", "status-failed");
    return;
  }
  if (!(outputCount > 0)) {
    setLocalizedLoadState("load_state_enter_output_count", "status-failed");
    return;
  }
  if (!(episodeDurationMinSeconds > 0) || !(episodeDurationMaxSeconds > 0) || episodeDurationMaxSeconds < episodeDurationMinSeconds) {
    setLocalizedLoadState("load_state_enter_episode_range", "status-failed");
    return;
  }
  setLocalizedLoadState("load_state_quickmix_generating", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/quick-mix", {
      method: "POST",
      body: JSON.stringify({
        source_dir: sourceDir,
        project_name: projectName,
        work_dir: outputWorkDir,
        duration_seconds: durationSeconds,
        output_count: outputCount,
        episode_duration_min_seconds: episodeDurationMinSeconds,
        episode_duration_max_seconds: episodeDurationMaxSeconds,
        music_path: musicPaths[0] || "",
        music_paths: musicPaths,
        use_music_duration: useMusicDuration,
        opening_media_path: openingMediaPaths[0] || "",
        opening_media_paths: openingMediaPaths,
        closing_media_path: closingMediaPaths[0] || "",
        closing_media_paths: closingMediaPaths,
        use_closing_duration: useClosingDuration,
      }),
    });
    state.quickMixResult = payload;
    state.zipImportResult = null;
    state.sourceScan = {
      ...(state.sourceScan || {}),
      source_dir: payload.source_dir,
      suggested_work_dir: payload.work_dir,
      supported_video_count: payload.video_count,
      supported_photo_count: payload.image_count,
    };
    qs("#vm-source-dir-input").value = payload.source_dir;
    qs("#vm-source-project-name-input").value = payload.project_name || projectName;
    qs("#vm-source-workdir-input").value = payload.work_dir;
    qs("#vm-quickmix-episode-min-input").value = String(payload.episode_duration_min_seconds ?? episodeDurationMinSeconds);
    qs("#vm-quickmix-episode-max-input").value = String(payload.episode_duration_max_seconds ?? episodeDurationMaxSeconds);
    writeQuickMixFileList("#vm-quickmix-music-input", payload.music_paths || (payload.music_path ? [payload.music_path] : musicPaths));
    qs("#vm-quickmix-use-music-duration").checked = Boolean(payload.use_music_duration);
    qs("#vm-quickmix-use-closing-duration").checked = Boolean(payload.use_closing_duration);
    writeQuickMixFileList("#vm-quickmix-opening-input", payload.opening_media_paths || (payload.opening_media_path ? [payload.opening_media_path] : openingMediaPaths));
    writeQuickMixFileList("#vm-quickmix-closing-input", payload.closing_media_paths || (payload.closing_media_path ? [payload.closing_media_path] : closingMediaPaths));
    qs("#vm-workdir-input").value = payload.work_dir;
    state.workDir = payload.work_dir;
    applyDashboardPayload(payload.dashboard);
    scheduleQuickMixEstimateRefresh(0);
    state.lastExportedPaths = payload.output_paths || [];
    renderExportsPanel(state.lastExportedPaths);
    await fetchJson("/api/video-mix/open", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir, target: "exports" }),
    });
    setLocalizedLoadState("load_state_quickmix_ready_opened", "status-completed");
    syncLocaleToUrl();
  } catch (error) {
    state.quickMixResult = null;
    renderQuickMixSummary();
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

function noteForCandidate(candidateId) {
  return qs(`[data-note-for="${CSS.escape(candidateId)}"]`)?.value?.trim() || "";
}

function noteForBulkSelection() {
  const firstSelected = visibleSelectedCandidateIds()[0];
  return firstSelected ? noteForCandidate(firstSelected) : "";
}

function visibleSelectedCandidateIds() {
  return filterSelectedCandidateIdsToVisible(
    state.selectedCandidateIds,
    visibleCandidates().map((candidate) => candidate.candidate_id),
  );
}

function toggleSelection(candidateId, selected) {
  if (!candidateId) return;
  if (selected) {
    state.selectedCandidateIds.add(candidateId);
  } else {
    state.selectedCandidateIds.delete(candidateId);
  }
  renderAll();
}

function selectVisibleCandidates() {
  visibleCandidates().forEach((candidate) => state.selectedCandidateIds.add(candidate.candidate_id));
  renderAll();
}

function clearSelection() {
  state.selectedCandidateIds = new Set();
  renderAll();
}

async function submitCandidateStatus(candidateId, action) {
  if (!candidateId || !state.workDir) return;
  setLocalizedLoadState(action === "approve" ? "load_state_approving" : "load_state_rejecting", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/candidates/${encodeURIComponent(candidateId)}/${action}`, {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        note: noteForCandidate(candidateId),
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.lastExportedPaths = [];
    renderExportsPanel([]);
    setLocalizedLoadState(action === "approve" ? "load_state_approved" : "load_state_rejected", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function submitBulkCandidateAction(action) {
  const candidateIds = visibleSelectedCandidateIds();
  if (!state.workDir || state.selectedCandidateIds.size === 0) {
    setLocalizedLoadState("load_state_select_candidate_first", "status-failed");
    return;
  }
  if (candidateIds.length === 0) {
    setLocalizedLoadState("load_state_no_visible_selected", "status-failed");
    return;
  }
  if (action === "reject" && !window.confirm(t("confirm_reject_selected", { count: candidateIds.length }))) {
    return;
  }
  if (action === "approve" && !window.confirm(t("confirm_approve_selected", { count: candidateIds.length }))) {
    return;
  }
  setLocalizedLoadState(action === "approve" ? "load_state_bulk_approving" : "load_state_bulk_rejecting", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/candidates/bulk/${action}`, {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        candidate_ids: candidateIds,
        note: noteForBulkSelection(),
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.lastExportedPaths = [];
    renderExportsPanel([]);
    clearSelection();
    setLocalizedLoadState(action === "approve" ? "load_state_bulk_approved" : "load_state_bulk_rejected", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function exportApprovedCandidates() {
  if (!state.workDir) return;
  if (isQuickMixMode()) {
    await openTarget("exports");
    return;
  }
  if (!window.confirm(t("confirm_export_approved"))) {
    return;
  }
  setLocalizedLoadState("load_state_exporting", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/export", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir, ffmpeg: "ffmpeg" }),
    });
    applyDashboardPayload(payload.dashboard);
    state.lastExportedPaths = payload.exported_paths || [];
    renderExportsPanel(state.lastExportedPaths);
    setLocalizedLoadState("load_state_export_complete", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function openTarget(target) {
  if (!state.workDir) return;
  try {
    await fetchJson("/api/video-mix/open", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir, target }),
    });
    setLocalizedLoadState("load_state_opened", "status-completed", { target });
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

function copyCurrentUrl() {
  navigator.clipboard.writeText(window.location.href);
  setLocalizedLoadState("url_copied", "status-completed");
}

function openProjectMaterialsModal() {
  const workDir = activeWorkDir();
  if (!workDir || !state.dashboard) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  state.workDir = workDir;
  ensureSelectedMaterialEpisode();
  qs("#vm-project-materials-modal")?.showModal();
}

function closeProjectMaterialsModal() {
  qs("#vm-project-materials-modal")?.close();
}

async function createProjectMaterialsEpisode() {
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  state.workDir = workDir;
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/episodes", {
      method: "POST",
      body: JSON.stringify({ work_dir: workDir }),
    });
    applyDashboardPayload(payload.dashboard);
    ensureSelectedMaterialEpisode();
    setLocalizedLoadState("materials_add_episode_done", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function assignProjectMaterialToEpisode(assetId, episodeId, reuse = false) {
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  if (!episodeId) {
    setLocalizedLoadState("load_state_materials_episode_needed", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLocalizedLoadState(reuse ? "load_state_materials_reusing" : "load_state_materials_assigning", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/assign", {
      method: "POST",
      body: JSON.stringify({
        work_dir: workDir,
        asset_id: assetId,
        episode_id: episodeId,
        reuse,
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.selectedMaterialEpisodeId = episodeId;
    setLocalizedLoadState(reuse ? "load_state_materials_reused" : "load_state_materials_assigned", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function uploadProjectMaterialsToEpisode(files, episodeId) {
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  if (!episodeId) {
    setLocalizedLoadState("load_state_materials_episode_needed", "status-failed");
    return;
  }
  state.workDir = workDir;
  const droppedFiles = Array.from(files || []).filter(Boolean);
  if (!droppedFiles.length) return;
  setLocalizedLoadState("load_state_materials_assigning", "status-downloading");
  try {
    const filePaths = [];
    for (const file of droppedFiles) {
      const payload = await uploadDroppedFile(file, "project_materials");
      filePaths.push(payload.file_path);
    }
    const payload = await fetchJson("/api/video-mix/project-materials/external-drop", {
      method: "POST",
      body: JSON.stringify({
        work_dir: workDir,
        episode_id: episodeId,
        file_paths: filePaths,
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.selectedMaterialEpisodeId = episodeId;
    setLocalizedLoadState("materials_episode_drop_done", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function unassignProjectMaterialTake(episodeId, takeId) {
  const workDir = activeWorkDir();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLocalizedLoadState("load_state_materials_unassigning", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/unassign", {
      method: "POST",
      body: JSON.stringify({
        work_dir: workDir,
        episode_id: episodeId,
        take_id: takeId,
      }),
    });
    applyDashboardPayload(payload.dashboard);
    state.selectedMaterialEpisodeId = episodeId;
    setLocalizedLoadState("load_state_materials_unassigned", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

function bindFilterControls() {
  qs("#vm-filter-status").onchange = (event) => {
    debugLog("click", "#vm-filter-status", event.target.value);
    state.filters.status = event.target.value;
    renderAll();
  };
  qs("#vm-filter-warnings").onchange = (event) => {
    debugLog("click", "#vm-filter-warnings", event.target.value);
    state.filters.warnings = event.target.value;
    renderAll();
  };
  qs("#vm-sort").onchange = (event) => {
    debugLog("click", "#vm-sort", event.target.value);
    state.filters.sort = event.target.value;
    renderAll();
  };
  qs("#vm-search").oninput = (event) => {
    debugLog("input", "#vm-search", String(event.target.value || ""));
    state.filters.search = String(event.target.value || "").trim().toLowerCase();
    renderAll();
  };
  const materialsStatus = qs("#vm-project-materials-filter-status");
  if (materialsStatus) {
    materialsStatus.onchange = (event) => {
      state.projectMaterialsFilters.status = event.target.value;
      renderProjectMaterialsModal();
    };
  }
  const materialsType = qs("#vm-project-materials-filter-type");
  if (materialsType) {
    materialsType.onchange = (event) => {
      state.projectMaterialsFilters.mediaType = event.target.value;
      renderProjectMaterialsModal();
    };
  }
  const materialsSearch = qs("#vm-project-materials-search");
  if (materialsSearch) {
    materialsSearch.oninput = (event) => {
      state.projectMaterialsFilters.search = String(event.target.value || "").trim().toLowerCase();
      renderProjectMaterialsModal();
    };
  }
}

function bindButtonAction(selector, label, handler, options = {}) {
  const element = qs(selector);
  if (!element) {
    debugLog("error", `bind ${selector}`, "element missing");
    return;
  }
  element.onclick = async () => {
    if (element.disabled) {
      return;
    }
    debugLog("click", label, selector);
    if (options.activityKey || options.activityText) {
      startActivity(selector, options.activityKey || "", options.activityText || "");
    }
    try {
      await handler();
    } catch (error) {
      debugLog("error", label, error?.message || String(error));
      throw error;
    } finally {
      if (options.activityKey || options.activityText) {
        stopActivity();
      }
    }
  };
}

function bindOpenLocalPathButtons(root = document) {
  root.querySelectorAll("[data-open-local-path]").forEach((button) => {
    button.onclick = async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const path = button.getAttribute("data-open-local-path") || "";
      if (!path) return;
      setLocalizedLoadState("load_state_loading", "status-downloading");
      try {
        await openLocalPath(path);
        setLocalizedLoadState("load_state_loaded", "status-completed");
      } catch (error) {
        state.loadState = null;
        setLoadState(error.message, "status-failed");
      }
    };
  });
}

function bindActions() {
  bindButtonAction("#vm-lang-ru", "lang ru", async () => setLocale("ru"));
  bindButtonAction("#vm-lang-en", "lang en", async () => setLocale("en"));
  bindButtonAction("#vm-source-browse-btn", "browse source", browseSourceDir);
  bindButtonAction("#vm-source-zip-browse-btn", "browse source zip", browseSourceZip);
  bindButtonAction("#vm-source-open-dir-btn", "open source dir", async () => {
    const sourceDir = qs("#vm-source-dir-input")?.value?.trim() || state.sourceScan?.source_dir || "";
    if (!sourceDir) {
      setLocalizedLoadState("load_state_enter_source_dir", "status-failed");
      return;
    }
    await openLocalPath(sourceDir);
  });
  bindButtonAction("#vm-source-open-workdir-btn", "open source workdir", async () => {
    const workDir = qs("#vm-source-workdir-input")?.value?.trim() || state.sourceScan?.suggested_work_dir || "";
    if (!workDir) {
      setLocalizedLoadState("load_state_enter_workdir", "status-failed");
      return;
    }
    await openLocalPath(workDir);
  });
  if (qs("#vm-project-files-add-btn")) {
    bindButtonAction("#vm-project-files-add-btn", "add project files", async () => {
      const nativeInput = qs("#vm-project-files-native-input");
      if (!nativeInput) {
        return;
      }
      debugLog("click", "native-picker project_files", "#vm-project-files-native-input");
      if (typeof nativeInput.showPicker === "function") {
        nativeInput.showPicker();
        return;
      }
      nativeInput.click();
    });
  }
  if (qs("#vm-project-files-open-btn")) {
    bindButtonAction("#vm-project-files-open-btn", "open project source dir", openProjectSourceDir);
  }
  bindButtonAction("#vm-add-episode-btn", "add materials episode", createProjectMaterialsEpisode);
  bindButtonAction("#vm-open-project-materials-inline-btn", "open project materials", async () => openProjectMaterialsModal());
  bindButtonAction("#vm-close-project-materials-btn", "close project materials", async () => closeProjectMaterialsModal());
  bindButtonAction("#vm-source-scan-btn", "scan source", scanSourceMaterials, { activityKey: "load_state_scanning_source" });
  bindButtonAction("#vm-source-plan-btn", "plan source", planSourceMaterials, { activityKey: "load_state_planning_source" });
  bindButtonAction("#vm-reset-btn", "reset project workspace", async () => resetProjectWorkspace());
  bindButtonAction("#vm-quickmix-music-browse-btn", "browse music", async () =>
    browseQuickMixFile("#vm-quickmix-music-input", "Select music track", "load_state_browsing_music", "load_state_music_browse_canceled"));
  bindButtonAction("#vm-quickmix-opening-browse-btn", "browse opening", async () =>
    browseQuickMixFile("#vm-quickmix-opening-input", "Select opening media", "load_state_browsing_opening", "load_state_opening_browse_canceled"));
  bindButtonAction("#vm-quickmix-closing-browse-btn", "browse closing", async () =>
    browseQuickMixFile("#vm-quickmix-closing-input", "Select closing media", "load_state_browsing_closing", "load_state_closing_browse_canceled"));
  bindButtonAction("#vm-quickmix-btn", "quick mix", quickMixSourceMaterials, { activityKey: "load_state_quickmix_generating" });
  bindButtonAction("#vm-quickmix-open-exports-btn", "quick mix open exports", async () => openTarget("exports"));
  bindButtonAction("#vm-browse-workdir-btn", "browse workdir", browseWorkDir);
  bindButtonAction("#vm-load-btn", "load dashboard", async () => loadDashboard(), { activityKey: "load_state_loading" });
  bindButtonAction("#vm-refresh-btn", "refresh dashboard", async () => loadDashboard(state.workDir), { activityKey: "load_state_loading" });
  bindButtonAction("#vm-export-btn", "export/open ready videos", exportApprovedCandidates, { activityKey: "load_state_exporting" });
  bindButtonAction("#vm-open-pipeline-modal-btn", "open pipeline modal", async () => {
    const dialog = qs("#vm-pipeline-modal");
    if (!dialog) return;
    dialog.showModal();
  });
  bindButtonAction("#vm-open-candidates-modal-btn", "open candidates modal", async () => {
    const dialog = qs("#vm-candidates-modal");
    if (!dialog) return;
    dialog.showModal();
  });
  bindButtonAction("#vm-close-pipeline-modal-btn", "close pipeline modal", async () => {
    const dialog = qs("#vm-pipeline-modal");
    if (!dialog) return;
    dialog.close();
  });
  bindButtonAction("#vm-close-candidates-modal-btn", "close candidates modal", async () => {
    const dialog = qs("#vm-candidates-modal");
    if (!dialog) return;
    dialog.close();
  });
  bindButtonAction("#vm-close-selected-media-modal-btn", "close selected media modal", async () => {
    closeSelectedMediaModal();
  });
  bindButtonAction("#vm-close-take-editor-btn", "close take editor modal", async () => {
    closeTakeEditorModal();
  });
  bindButtonAction("#vm-open-review", "open review", async () => openTarget("review"));
  bindButtonAction("#vm-open-exports", "open exports", async () => openTarget("exports"));
  bindButtonAction("#vm-open-workdir", "open workdir", async () => openTarget("work_dir"));
  bindButtonAction("#vm-copy-url-btn", "copy url", async () => copyCurrentUrl());
  bindButtonAction("#vm-select-visible", "select visible", async () => selectVisibleCandidates());
  bindButtonAction("#vm-clear-selection", "clear selection", async () => clearSelection());
  bindButtonAction("#vm-approve-selected", "approve selected", async () => submitBulkCandidateAction("approve"), { activityKey: "load_state_bulk_approving" });
  bindButtonAction("#vm-reject-selected", "reject selected", async () => submitBulkCandidateAction("reject"), { activityKey: "load_state_bulk_rejecting" });
  bindButtonAction("#vm-debug-clear-btn", "clear debug log", async () => {
    state.debugLogs = [];
    renderDebugLog();
  });
  qs("#vm-workdir-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      debugLog("keypress", "#vm-workdir-input", "Enter");
      loadDashboard();
    }
  });
  qs("#vm-source-dir-input").addEventListener("input", () => {
    const sourcePath = qs("#vm-source-dir-input").value.trim();
    debugLog("input", "#vm-source-dir-input", sourcePath);
    state.selectedSourcePath = sourcePath;
    state.manualSourceOverride = Boolean(sourcePath);
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = defaultSourceWorkDir(sourcePath);
      state.sourceWorkDirAuto = true;
    }
    state.quickMixResult = null;
    state.quickMixEstimate = { status: "idle" };
    renderQuickMixEstimate();
  });
  qs("#vm-quickmix-duration-input").addEventListener("input", () => {
    debugLog("input", "#vm-quickmix-duration-input", qs("#vm-quickmix-duration-input").value.trim());
    scheduleQuickMixEstimateRefresh();
  });
  qs("#vm-quickmix-count-input").addEventListener("input", () => {
    debugLog("input", "#vm-quickmix-count-input", qs("#vm-quickmix-count-input").value.trim());
    renderQuickMixEstimate();
  });
  qs("#vm-quickmix-episode-min-input").addEventListener("input", () => {
    debugLog("input", "#vm-quickmix-episode-min-input", qs("#vm-quickmix-episode-min-input").value.trim());
    scheduleQuickMixEstimateRefresh();
  });
  qs("#vm-quickmix-episode-max-input").addEventListener("input", () => {
    debugLog("input", "#vm-quickmix-episode-max-input", qs("#vm-quickmix-episode-max-input").value.trim());
    scheduleQuickMixEstimateRefresh();
  });
  qs("#vm-quickmix-use-music-duration").addEventListener("change", () => {
    debugLog("click", "#vm-quickmix-use-music-duration", String(qs("#vm-quickmix-use-music-duration").checked));
    scheduleQuickMixEstimateRefresh();
  });
  qs("#vm-quickmix-use-closing-duration").addEventListener("change", () => {
    debugLog("click", "#vm-quickmix-use-closing-duration", String(qs("#vm-quickmix-use-closing-duration").checked));
    scheduleQuickMixEstimateRefresh();
  });
  qs("#vm-source-workdir-input").addEventListener("input", () => {
    const sourceDir = qs("#vm-source-dir-input").value.trim();
    debugLog("input", "#vm-source-workdir-input", qs("#vm-source-workdir-input").value.trim());
    state.sourceWorkDirAuto = qs("#vm-source-workdir-input").value.trim() === defaultSourceWorkDir(sourceDir);
  });
  if (qs("#vm-project-files-native-input")) {
    qs("#vm-project-files-native-input").addEventListener("change", async (event) => {
      await uploadProjectFiles(event.target.files || []);
      event.target.value = "";
    });
  }
  qs("#vm-episode-file-native-input").addEventListener("change", async (event) => {
    const targetEpisodeId = event.target.dataset.targetEpisodeId || state.selectedMaterialEpisodeId || "";
    await uploadProjectMaterialsToEpisode(event.target.files || [], targetEpisodeId);
    event.target.value = "";
    event.target.dataset.targetEpisodeId = "";
  });
  bindSourceDropZone("#vm-source-drop-zone");
  if (qs("#vm-project-files-panel")) {
    bindProjectFilesDropZone("#vm-project-files-panel");
  }
  bindDropZone("#vm-quickmix-music-drop-surface", "#vm-quickmix-music-input", "music", "");
  bindDropZone("#vm-quickmix-music-drop-zone", "#vm-quickmix-music-input", "music", "");
  bindDropZone("#vm-quickmix-opening-drop-surface", "#vm-quickmix-opening-input", "opening", "");
  bindDropZone("#vm-quickmix-opening-drop-zone", "#vm-quickmix-opening-input", "opening", "");
  bindDropZone("#vm-quickmix-closing-drop-surface", "#vm-quickmix-closing-input", "closing", "");
  bindDropZone("#vm-quickmix-closing-drop-zone", "#vm-quickmix-closing-input", "closing", "");
  bindNativeQuickMixPicker(
    "#vm-quickmix-music-browse-btn",
    "#vm-quickmix-music-native-input",
    "#vm-quickmix-music-input",
    "music",
    "load_state_browsing_music",
    "#vm-quickmix-music-selected",
  );
  bindNativeQuickMixPicker(
    "#vm-quickmix-opening-browse-btn",
    "#vm-quickmix-opening-native-input",
    "#vm-quickmix-opening-input",
    "opening",
    "load_state_browsing_opening",
    "#vm-quickmix-opening-selected",
  );
  bindNativeQuickMixPicker(
    "#vm-quickmix-closing-browse-btn",
    "#vm-quickmix-closing-native-input",
    "#vm-quickmix-closing-input",
    "closing",
    "load_state_browsing_closing",
    "#vm-quickmix-closing-selected",
  );
  bindFilterControls();
  bindOpenLocalPathButtons();
  debugLog("init", "bindActions complete");
}

function initFromQuery() {
  const workDir = new URLSearchParams(window.location.search).get("work_dir");
  if (workDir) {
    qs("#vm-workdir-input").value = workDir;
    qs("#vm-source-workdir-input").value = workDir;
    state.workDir = workDir;
    loadDashboard(workDir);
  }
}

function init() {
  if (dashboardInitialized) {
    return;
  }
  dashboardInitialized = true;
  debugLog("init", "dashboard init start", document.readyState);
  state.locale = resolveInitialLocale(window.location.search, readStoredLocale());
  bindActions();
  applyStaticTranslations();
  renderAll();
  initFromQuery();
  debugLog("init", "dashboard init complete");
}

if (typeof document !== "undefined") {
  window.addEventListener("error", (event) => {
    debugLog("window-error", event.message || "window error", `${event.filename || ""}:${event.lineno || ""}`);
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason?.message || event.reason || "unhandled rejection";
    debugLog("promise-error", "unhandled rejection", String(reason));
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
  window.addEventListener("load", init, { once: true });
}
