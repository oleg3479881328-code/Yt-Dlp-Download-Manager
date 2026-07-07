const state = {
  dashboard: null,
  workDir: "",
  locale: "ru",
  loadState: { key: "load_waiting", className: "status-queued", params: {} },
  lastExportedPaths: [],
  sourceScan: null,
  quickMixResult: null,
  sourceWorkDirAuto: true,
  selectedCandidateIds: new Set(),
  draftNotesByCandidateId: new Map(),
  filters: {
    status: "all",
    warnings: "all",
    search: "",
    sort: "score_desc",
  },
  projectMaterialsFilters: {
    status: "all",
    mediaType: "all",
    search: "",
  },
  selectedMaterialEpisodeId: "",
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

const TRANSLATIONS = {
  ru: {
    page_title: "VIDEO MIX Дашборд",
    source_title: "Материалы",
    source_help: "Сначала выберите папку с исходными видео и создайте или обновите VIDEO MIX проект.",
    source_dir_label: "Папка с материалами",
    source_project_name_label: "Имя проекта",
    source_workdir_label: "Выходной work_dir",
    source_browse: "Выбрать материалы",
    source_scan: "Сканировать",
    source_plan: "Создать / обновить проект",
    source_open_materials: "Project Materials",
    source_scan_empty: "Скан материалов ещё не запускался.",
    source_scan_result_title: "Результат сканирования",
    source_scan_total_files: "Всего файлов",
    source_scan_supported_media: "Поддерживаемых media",
    source_scan_supported_videos: "Видео",
    source_scan_supported_photos: "Фото",
    source_scan_ignored: "Игнорировано / не поддерживается",
    source_scan_preview: "Превью файлов",
    source_scan_preview_more: "И ещё {count} файл(ов)",
    source_source_dir: "Папка материалов",
    source_suggested_workdir: "Рекомендуемый work_dir",
    quickmix_title: "Быстрый микс",
    quickmix_help: "Прямая генерация готовых MP4 без обязательного approve/reject.",
    quickmix_duration_label: "Секунд на ролик",
    quickmix_count_label: "Сколько роликов",
    quickmix_button: "Сгенерировать ролики",
    quickmix_empty: "Quick Mix ещё не запускался.",
    quickmix_result_title: "Результат Quick Mix",
    quickmix_generated_count: "Сгенерировано MP4",
    quickmix_output_paths: "Готовые файлы",
    quickmix_photos_supported: "Фото поддерживаются",
    quickmix_photos_unsupported: "Фото не поддерживаются",
    hero_title: "Локальный дашборд для Quick Mix, ревью и экспорта",
    hero_copy: "Выберите исходные материалы, запустите Быстрый микс для прямой генерации MP4 или загрузите готовый VIDEO MIX work_dir для обычного ревью, approve/reject и экспорта.",
    open_review: "Открыть review.html",
    open_exports: "Открыть exports",
    open_workdir: "Открыть work_dir",
    load_title: "Загрузка work_dir",
    load_help: "Используйте уже созданную рабочую папку VIDEO MIX.",
    load_waiting: "Ожидание",
    workdir_label: "VIDEO MIX work_dir",
    browse_workdir: "Выбрать папку",
    load_dashboard: "Загрузить дашборд",
    copy_url: "Копировать URL",
    close_button: "Закрыть",
    project_meta_empty: "Загрузите work_dir, чтобы увидеть метаданные проекта и сводные счётчики.",
    pipeline_title: "Пайплайн",
    pipeline_help: "Путь от ассетов до экспорта в одном локальном процессе.",
    actions_title: "Действия",
    actions_help: "Используется только текущее поведение VIDEO MIX.",
    export_approved: "Экспортировать одобренных кандидатов",
    refresh_dashboard: "Обновить дашборд",
    materials_stage_title: "Project Materials",
    materials_stage_help: "Логическое назначение master asset -> Episode -> Take без перемещения файлов на диске.",
    materials_open_modal: "Открыть Project Materials",
    materials_add_episode: "Добавить Episode",
    materials_modal_help: "Drag unassigned asset в Episode. Повтор того же asset — только через explicit reuse.",
    materials_filter_status: "Статус",
    materials_filter_type: "Тип",
    materials_search: "Поиск",
    materials_search_placeholder: "имя файла",
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
    materials_episode_drop: "Перетащите сюда material card",
    materials_episode_empty: "В этом Episode пока нет Takes.",
    materials_take_remove: "Убрать",
    materials_no_assets: "Нет материалов под текущие фильтры.",
    materials_no_episodes: "Episodes появятся после загрузки work_dir.",
    materials_assignment_locations: "Назначено в",
    materials_reuse_hint: "Для повторного использования сначала выберите Episode.",
    materials_add_episode_done: "Episode добавлен",
    timeline_title: "Timeline",
    timeline_help: "Горизонтальные дорожки будущего монтажа, собранные из Episode/Take назначений.",
    timeline_empty: "Назначьте хотя бы один Take, чтобы появился видимый timeline.",
    timeline_row_empty: "В этой дорожке пока нет Take blocks.",
    timeline_block_assigned: "Assigned",
    timeline_block_reused: "Reused",
    load_state_materials_assigning: "Назначаю material в Episode...",
    load_state_materials_assigned: "Material назначен",
    load_state_materials_reusing: "Добавляю reuse material...",
    load_state_materials_reused: "Material повторно использован",
    load_state_materials_unassigning: "Убираю Take...",
    load_state_materials_unassigned: "Take убран",
    load_state_materials_episode_needed: "Сначала выберите Episode",
    load_state_materials_modal_opened: "Project Materials открыт",
    request_asset_reuse: "Материал уже назначен. Используйте explicit reuse.",
    candidates_title: "Карточки кандидатов",
    candidates_help: "Миниатюра, score, template, предупреждения, исходные файлы и быстрые действия.",
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
    load_state_enter_workdir: "Укажите work_dir",
    load_state_browsing_workdir: "Открываю выбор папки...",
    load_state_browse_canceled: "Выбор папки отменён",
    load_state_browsing_source: "Открываю выбор папки с материалами...",
    load_state_source_browse_canceled: "Выбор папки с материалами отменён",
    load_state_scanning_source: "Сканирую материалы...",
    load_state_source_scanned: "Материалы просканированы",
    load_state_planning_source: "Создаю план проекта...",
    load_state_generating_review: "Генерирую review и thumbnails...",
    load_state_source_loaded: "Проект создан и загружен",
    load_state_quickmix_generating: "Генерирую Quick Mix MP4...",
    load_state_quickmix_ready: "Quick Mix готов",
    load_state_loading: "Загрузка...",
    load_state_loaded: "Загружено",
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
    source_scan: "Scan",
    source_plan: "Create / update project",
    source_open_materials: "Project Materials",
    source_scan_empty: "Materials scan has not been run yet.",
    source_scan_result_title: "Scan result",
    source_scan_total_files: "Total files",
    source_scan_supported_media: "Supported media",
    source_scan_supported_videos: "Videos",
    source_scan_supported_photos: "Photos",
    source_scan_ignored: "Ignored / unsupported",
    source_scan_preview: "Preview files",
    source_scan_preview_more: "And {count} more file(s)",
    source_source_dir: "Source folder",
    source_suggested_workdir: "Suggested work_dir",
    quickmix_title: "Quick Mix",
    quickmix_help: "Direct MP4 generation without mandatory approve/reject.",
    quickmix_duration_label: "Seconds per video",
    quickmix_count_label: "Number of videos",
    quickmix_button: "Generate videos",
    quickmix_empty: "Quick Mix has not been run yet.",
    quickmix_result_title: "Quick Mix result",
    quickmix_generated_count: "Generated MP4",
    quickmix_output_paths: "Output files",
    quickmix_photos_supported: "Photos supported",
    quickmix_photos_unsupported: "Photos not supported",
    hero_title: "Local dashboard for Quick Mix, review, and export",
    hero_copy: "Choose source materials for direct Quick Mix MP4 generation, or load an existing VIDEO MIX work_dir for review, approve/reject, and export.",
    open_review: "Open review.html",
    open_exports: "Open exports",
    open_workdir: "Open work_dir",
    load_title: "Load work_dir",
    load_help: "Use an already generated VIDEO MIX work folder.",
    load_waiting: "Waiting",
    workdir_label: "VIDEO MIX work_dir",
    browse_workdir: "Browse folder",
    load_dashboard: "Load dashboard",
    copy_url: "Copy URL",
    close_button: "Close",
    project_meta_empty: "Load a work_dir to see project metadata and summary counts.",
    pipeline_title: "Pipeline",
    pipeline_help: "Path from assets to export in one local flow.",
    actions_title: "Actions",
    actions_help: "Use existing VIDEO MIX behavior only.",
    export_approved: "Export approved candidates",
    refresh_dashboard: "Refresh dashboard",
    materials_stage_title: "Project Materials",
    materials_stage_help: "Logical master asset -> Episode -> Take assignment without moving files on disk.",
    materials_open_modal: "Open Project Materials",
    materials_add_episode: "Add Episode",
    materials_modal_help: "Drag an unassigned asset into an Episode. Reuse the same asset only through explicit reuse.",
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
    materials_episode_drop: "Drop a material card here",
    materials_episode_empty: "This Episode has no Takes yet.",
    materials_take_remove: "Remove",
    materials_no_assets: "No project materials match the current filters.",
    materials_no_episodes: "Episodes will appear after loading a work_dir.",
    materials_assignment_locations: "Assigned to",
    materials_reuse_hint: "Select an Episode first before reuse.",
    materials_add_episode_done: "Episode added",
    timeline_title: "Timeline",
    timeline_help: "Horizontal editing tracks built from the current Episode/Take assignments.",
    timeline_empty: "Assign at least one Take to make the visible timeline appear.",
    timeline_row_empty: "This track has no Take blocks yet.",
    timeline_block_assigned: "Assigned",
    timeline_block_reused: "Reused",
    load_state_materials_assigning: "Assigning material to Episode...",
    load_state_materials_assigned: "Material assigned",
    load_state_materials_reusing: "Reusing material...",
    load_state_materials_reused: "Material reused",
    load_state_materials_unassigning: "Removing Take...",
    load_state_materials_unassigned: "Take removed",
    load_state_materials_episode_needed: "Select an Episode first",
    load_state_materials_modal_opened: "Project Materials opened",
    request_asset_reuse: "This asset is already assigned. Use explicit reuse.",
    candidates_title: "Candidate cards",
    candidates_help: "Thumbnail, score, template, warnings, source files, and direct actions.",
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
    load_state_enter_workdir: "Enter work_dir",
    load_state_browsing_workdir: "Opening folder picker...",
    load_state_browse_canceled: "Folder selection cancelled",
    load_state_browsing_source: "Opening source folder picker...",
    load_state_source_browse_canceled: "Source folder selection cancelled",
    load_state_scanning_source: "Scanning source materials...",
    load_state_source_scanned: "Source materials scanned",
    load_state_planning_source: "Creating project plan...",
    load_state_generating_review: "Generating review and thumbnails...",
    load_state_source_loaded: "Project created and loaded",
    load_state_quickmix_generating: "Generating Quick Mix MP4 files...",
    load_state_quickmix_ready: "Quick Mix ready",
    load_state_loading: "Loading...",
    load_state_loaded: "Loaded",
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

function fileUrl(relativePath) {
  if (!state.workDir || !relativePath) return "";
  const params = new URLSearchParams({
    work_dir: state.workDir,
    relative_path: relativePath,
  });
  return `/api/video-mix/file?${params.toString()}`;
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

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || t("request_failed"));
  }
  return response.json();
}

function setLoadState(label, className) {
  const element = qs("#vm-load-state");
  if (!element) return;
  element.textContent = label;
  element.className = `status-chip ${className}`;
}

function setLocalizedLoadState(key, className, params = {}) {
  state.loadState = { key, className, params };
  setLoadState(t(key, params), className);
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
    ["#vm-source-title", "source_title"],
    ["#vm-source-help", "source_help"],
    ["#vm-quickmix-title", "quickmix_title"],
    ["#vm-quickmix-help", "quickmix_help"],
    ["#vm-source-dir-label", "source_dir_label"],
    ["#vm-source-project-name-label", "source_project_name_label"],
    ["#vm-source-workdir-label", "source_workdir_label"],
    ["#vm-quickmix-duration-label", "quickmix_duration_label"],
    ["#vm-quickmix-count-label", "quickmix_count_label"],
    ["#vm-source-browse-btn", "source_browse"],
    ["#vm-source-scan-btn", "source_scan"],
    ["#vm-source-plan-btn", "source_plan"],
    ["#vm-open-project-materials-btn", "source_open_materials"],
    ["#vm-quickmix-btn", "quickmix_button"],
    ["#vm-workdir-label", "workdir_label"],
    ["#vm-browse-workdir-btn", "browse_workdir"],
    ["#vm-load-btn", "load_dashboard"],
    ["#vm-copy-url-btn", "copy_url"],
    ["#vm-pipeline-title", "pipeline_title"],
    ["#vm-pipeline-help", "pipeline_help"],
    ["#vm-actions-title", "actions_title"],
    ["#vm-actions-help", "actions_help"],
    ["#vm-export-btn", "export_approved"],
    ["#vm-refresh-btn", "refresh_dashboard"],
    ["#vm-materials-stage-title", "materials_stage_title"],
    ["#vm-materials-stage-help", "materials_stage_help"],
    ["#vm-add-episode-btn", "materials_add_episode"],
    ["#vm-open-project-materials-inline-btn", "materials_open_modal"],
    ["#vm-timeline-title", "timeline_title"],
    ["#vm-timeline-help", "timeline_help"],
    ["#vm-project-materials-title", "materials_stage_title"],
    ["#vm-project-materials-help", "materials_modal_help"],
    ["#vm-close-project-materials-btn", "close_button"],
    ["#vm-project-materials-filter-status-label", "materials_filter_status"],
    ["#vm-project-materials-filter-type-label", "materials_filter_type"],
    ["#vm-project-materials-search-label", "materials_search"],
    ["#vm-candidates-title", "candidates_title"],
    ["#vm-candidates-help", "candidates_help"],
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
  const projectMaterialsSearch = qs("#vm-project-materials-search");
  if (projectMaterialsSearch) {
    projectMaterialsSearch.placeholder = t("materials_search_placeholder");
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
  return sourceDir.replace(/[\\/]+$/, "") + "\\_video_mix_work";
}

function renderSourceScanSummary() {
  const target = qs("#vm-source-scan-summary");
  if (!target) return;
  if (!state.sourceScan) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("source_scan_empty"))}</div>`;
    return;
  }
  const preview = (state.sourceScan.preview_files || [])
    .map((name) => `<li><code>${escapeHtml(name)}</code></li>`)
    .join("");
  const moreCount = Math.max(0, Number(state.sourceScan.supported_media_count || 0) - Number((state.sourceScan.preview_files || []).length));
  const moreLine = moreCount ? `<div class="muted">${escapeHtml(t("source_scan_preview_more", { count: moreCount }))}</div>` : "";
  target.innerHTML = `
    <div class="video-mix-project-panel">
      <div><span>${escapeHtml(t("source_source_dir"))}</span><code>${escapeHtml(state.sourceScan.source_dir)}</code></div>
      <div><span>${escapeHtml(t("source_suggested_workdir"))}</span><code>${escapeHtml(state.sourceScan.suggested_work_dir)}</code></div>
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
    target.innerHTML = `<div class="empty">${escapeHtml(t("materials_no_episodes"))}</div>`;
    return;
  }
  target.innerHTML = episodes.map((episode) => {
    const takes = (episode.takes || []).length
      ? episode.takes.map((take) => `
        <div class="video-mix-take-chip">
          <div>
            <strong>${escapeHtml(take.file_name)}</strong>
            <div class="muted">${escapeHtml(t(`materials_asset_${take.mode}`))} · ${escapeHtml(take.media_type)} · ${escapeHtml(formatDurationMs(take.duration_ms || 0))}</div>
          </div>
          <button class="ghost-btn video-mix-take-remove-btn" type="button" data-episode-id="${escapeAttr(episode.episode_id)}" data-take-id="${escapeAttr(take.take_id)}">${escapeHtml(t("materials_take_remove"))}</button>
        </div>
      `).join("")
      : `<div class="empty compact">${escapeHtml(t("materials_episode_empty"))}</div>`;
    return `
      <article class="video-mix-episode-card${episode.episode_id === selectedEpisodeId ? " is-selected" : ""}" data-episode-id="${escapeAttr(episode.episode_id)}">
        <div class="video-mix-episode-header">
          <div>
            <h3>${escapeHtml(episode.label)}</h3>
            <div class="muted">${escapeHtml(episode.episode_id)}</div>
          </div>
          <span class="status-chip ${episode.episode_id === selectedEpisodeId ? "status-active" : "status-idle"}">${escapeHtml(episode.episode_id === selectedEpisodeId ? t("materials_episode_selected") : `${(episode.takes || []).length} takes`)}</span>
        </div>
        <div class="video-mix-episode-drop-zone" data-episode-drop="${escapeAttr(episode.episode_id)}">${escapeHtml(t("materials_episode_drop"))}</div>
        <div class="video-mix-episode-takes">${takes}</div>
      </article>
    `;
  }).join("");

  target.querySelectorAll("[data-episode-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      state.selectedMaterialEpisodeId = card.dataset.episodeId || "";
      renderAll();
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
      const raw = event.dataTransfer?.getData("application/json") || "";
      if (!raw) return;
      const payload = JSON.parse(raw);
      await assignProjectMaterialToEpisode(payload.asset_id, zone.dataset.episodeDrop || "", Boolean(payload.reuse));
    });
  });
  target.querySelectorAll(".video-mix-take-remove-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      await unassignProjectMaterialTake(button.dataset.episodeId || "", button.dataset.takeId || "");
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
        <button class="video-mix-timeline-block${row.episode_id === selectedEpisodeId ? " is-selected" : ""}" type="button" data-timeline-episode-id="${escapeAttr(row.episode_id)}">
          <strong>${escapeHtml(block.file_name)}</strong>
          <span>${escapeHtml(block.media_type)} · ${escapeHtml(formatDurationMs(block.duration_ms || 0))}</span>
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
  const outputLinks = (state.quickMixResult.output_paths || []).length
    ? (state.quickMixResult.output_paths || [])
        .map((path) => `<a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>`)
        .join("")
    : `<div class="muted">${escapeHtml(t("no_exports"))}</div>`;
  target.innerHTML = `
    <div class="video-mix-summary-grid">
      <div class="video-mix-summary-card"><span>${escapeHtml(t("quickmix_generated_count"))}</span><strong>${escapeHtml(state.quickMixResult.generated_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_videos"))}</span><strong>${escapeHtml(state.quickMixResult.video_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_scan_supported_photos"))}</span><strong>${escapeHtml(state.quickMixResult.image_count)}</strong></div>
      <div class="video-mix-summary-card"><span>${escapeHtml(t("source_workdir_label"))}</span><code>${escapeHtml(state.quickMixResult.work_dir)}</code></div>
    </div>
    <div class="video-mix-section">
      <h4>${escapeHtml(t("quickmix_output_paths"))}</h4>
      <div class="video-mix-export-list">${outputLinks}</div>
    </div>
    <div class="muted">${escapeHtml(state.quickMixResult.photo_support ? t("quickmix_photos_supported") : t("quickmix_photos_unsupported"))}</div>
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
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("project_meta_empty"))}</div>`;
    summaryTarget.innerHTML = "";
    countChip.textContent = t("candidate_count", { count: 0 });
    countChip.className = "status-chip status-idle";
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

  countChip.textContent = t("candidate_count", { count: summary.candidate_count });
  countChip.className = `status-chip ${summary.candidate_count ? "status-completed" : "status-idle"}`;
}

function renderPipeline() {
  const target = qs("#vm-pipeline");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">${escapeHtml(t("pipeline_empty"))}</div>`;
    return;
  }
  target.innerHTML = state.dashboard.pipeline.map((step) => `
    <div class="pipeline-step ${escapeAttr(step.state === "ready" ? "active" : "")}">
      <strong>${escapeHtml(pipelineLabel(step))}</strong>
      <span>${escapeHtml(t("pipeline_item_count", { count: step.count }))}</span>
      <span class="video-mix-step-state">${escapeHtml(pipelineStateLabel(step.state))}</span>
    </div>
  `).join("");
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
  syncSelectionToVisible();
  renderSourceScanSummary();
  renderQuickMixSummary();
  renderMaterialEpisodes();
  renderMaterialTimeline();
  renderProjectMaterialsModal();
  renderProjectMeta();
  renderPipeline();
  renderCandidates();
  renderExportsPanel(state.lastExportedPaths || []);
}

function applyDashboardPayload(payload) {
  state.dashboard = payload;
  state.draftNotesByCandidateId = new Map();
  syncSelectionToVisible();
  renderAll();
}

async function loadDashboard(workDirOverride = "") {
  const input = qs("#vm-workdir-input");
  const workDir = workDirOverride || input.value.trim();
  if (!workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLocalizedLoadState("load_state_loading", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/dashboard?${new URLSearchParams({ work_dir: workDir }).toString()}`);
    applyDashboardPayload(payload);
    input.value = workDir;
    state.lastExportedPaths = [];
    renderExportsPanel([]);
    setLocalizedLoadState("load_state_loaded", "status-completed");
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
  const initialDir = qs("#vm-source-dir-input")?.value?.trim() || "";
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
    qs("#vm-source-dir-input").value = payload.source_dir;
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = defaultSourceWorkDir(payload.source_dir);
      state.sourceWorkDirAuto = true;
    }
    state.sourceScan = null;
    state.quickMixResult = null;
    renderSourceScanSummary();
    renderQuickMixSummary();
    setLocalizedLoadState("load_state_loaded", "status-completed");
  } catch (error) {
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function scanSourceMaterials() {
  const sourceDir = qs("#vm-source-dir-input")?.value?.trim() || "";
  if (!sourceDir) {
    setLocalizedLoadState("load_state_enter_source_dir", "status-failed");
    return;
  }
  setLocalizedLoadState("load_state_scanning_source", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/source/scan", {
      method: "POST",
      body: JSON.stringify({ source_dir: sourceDir }),
    });
    state.sourceScan = payload;
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
    setLocalizedLoadState("load_state_source_scanned", "status-completed");
  } catch (error) {
    state.sourceScan = null;
    state.quickMixResult = null;
    renderSourceScanSummary();
    renderQuickMixSummary();
    state.loadState = null;
    setLoadState(error.message, "status-failed");
  }
}

async function planSourceMaterials() {
  const sourceDir = qs("#vm-source-dir-input")?.value?.trim() || "";
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
    qs("#vm-source-dir-input").value = payload.source_dir;
    qs("#vm-source-project-name-input").value = payload.project_name || projectName;
    qs("#vm-source-workdir-input").value = payload.work_dir;
    qs("#vm-workdir-input").value = payload.work_dir;
    state.workDir = payload.work_dir;
    applyDashboardPayload(payload.dashboard);
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
  const sourceDir = qs("#vm-source-dir-input")?.value?.trim() || "";
  const projectName = qs("#vm-source-project-name-input")?.value?.trim() || "";
  const outputWorkDir = qs("#vm-source-workdir-input")?.value?.trim() || defaultSourceWorkDir(sourceDir);
  const durationSeconds = Number(qs("#vm-quickmix-duration-input")?.value || 0);
  const outputCount = Number(qs("#vm-quickmix-count-input")?.value || 0);
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
      }),
    });
    state.quickMixResult = payload;
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
    qs("#vm-workdir-input").value = payload.work_dir;
    state.workDir = payload.work_dir;
    applyDashboardPayload(payload.dashboard);
    state.lastExportedPaths = payload.output_paths || [];
    renderExportsPanel(state.lastExportedPaths);
    setLocalizedLoadState("load_state_quickmix_ready", "status-completed");
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
  if (!state.workDir || !state.dashboard) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  ensureSelectedMaterialEpisode();
  qs("#vm-project-materials-modal")?.showModal();
  setLocalizedLoadState("load_state_materials_modal_opened", "status-completed");
}

function closeProjectMaterialsModal() {
  qs("#vm-project-materials-modal")?.close();
}

async function createProjectMaterialsEpisode() {
  if (!state.workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/episodes", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir }),
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
  if (!state.workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  if (!episodeId) {
    setLocalizedLoadState("load_state_materials_episode_needed", "status-failed");
    return;
  }
  setLocalizedLoadState(reuse ? "load_state_materials_reusing" : "load_state_materials_assigning", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/assign", {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
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

async function unassignProjectMaterialTake(episodeId, takeId) {
  if (!state.workDir) {
    setLocalizedLoadState("load_state_enter_workdir", "status-failed");
    return;
  }
  setLocalizedLoadState("load_state_materials_unassigning", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/project-materials/unassign", {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
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
    state.filters.status = event.target.value;
    renderAll();
  };
  qs("#vm-filter-warnings").onchange = (event) => {
    state.filters.warnings = event.target.value;
    renderAll();
  };
  qs("#vm-sort").onchange = (event) => {
    state.filters.sort = event.target.value;
    renderAll();
  };
  qs("#vm-search").oninput = (event) => {
    state.filters.search = String(event.target.value || "").trim().toLowerCase();
    renderAll();
  };
  qs("#vm-project-materials-filter-status").onchange = (event) => {
    state.projectMaterialsFilters.status = event.target.value;
    renderProjectMaterialsModal();
  };
  qs("#vm-project-materials-filter-type").onchange = (event) => {
    state.projectMaterialsFilters.mediaType = event.target.value;
    renderProjectMaterialsModal();
  };
  qs("#vm-project-materials-search").oninput = (event) => {
    state.projectMaterialsFilters.search = String(event.target.value || "").trim().toLowerCase();
    renderProjectMaterialsModal();
  };
}

function bindActions() {
  qs("#vm-lang-ru").onclick = () => setLocale("ru");
  qs("#vm-lang-en").onclick = () => setLocale("en");
  qs("#vm-source-browse-btn").onclick = () => browseSourceDir();
  qs("#vm-source-scan-btn").onclick = () => scanSourceMaterials();
  qs("#vm-source-plan-btn").onclick = () => planSourceMaterials();
  qs("#vm-open-project-materials-btn").onclick = () => openProjectMaterialsModal();
  qs("#vm-quickmix-btn").onclick = () => quickMixSourceMaterials();
  qs("#vm-browse-workdir-btn").onclick = () => browseWorkDir();
  qs("#vm-load-btn").onclick = () => loadDashboard();
  qs("#vm-refresh-btn").onclick = () => loadDashboard(state.workDir);
  qs("#vm-export-btn").onclick = () => exportApprovedCandidates();
  qs("#vm-open-review").onclick = () => openTarget("review");
  qs("#vm-open-exports").onclick = () => openTarget("exports");
  qs("#vm-open-workdir").onclick = () => openTarget("work_dir");
  qs("#vm-add-episode-btn").onclick = () => createProjectMaterialsEpisode();
  qs("#vm-open-project-materials-inline-btn").onclick = () => openProjectMaterialsModal();
  qs("#vm-close-project-materials-btn").onclick = () => closeProjectMaterialsModal();
  qs("#vm-copy-url-btn").onclick = () => copyCurrentUrl();
  qs("#vm-select-visible").onclick = () => selectVisibleCandidates();
  qs("#vm-clear-selection").onclick = () => clearSelection();
  qs("#vm-approve-selected").onclick = () => submitBulkCandidateAction("approve");
  qs("#vm-reject-selected").onclick = () => submitBulkCandidateAction("reject");
  qs("#vm-workdir-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadDashboard();
    }
  });
  qs("#vm-source-dir-input").addEventListener("input", () => {
    if (state.sourceWorkDirAuto || !qs("#vm-source-workdir-input").value.trim()) {
      qs("#vm-source-workdir-input").value = defaultSourceWorkDir(qs("#vm-source-dir-input").value.trim());
      state.sourceWorkDirAuto = true;
    }
    state.quickMixResult = null;
  });
  qs("#vm-source-workdir-input").addEventListener("input", () => {
    const sourceDir = qs("#vm-source-dir-input").value.trim();
    state.sourceWorkDirAuto = qs("#vm-source-workdir-input").value.trim() === defaultSourceWorkDir(sourceDir);
  });
  bindFilterControls();
}

function initFromQuery() {
  const workDir = new URLSearchParams(window.location.search).get("work_dir");
  if (workDir) {
    qs("#vm-workdir-input").value = workDir;
    loadDashboard(workDir);
  }
}

function init() {
  state.locale = resolveInitialLocale(window.location.search, readStoredLocale());
  bindActions();
  applyStaticTranslations();
  renderAll();
  initFromQuery();
}

if (typeof document !== "undefined") {
  init();
}
