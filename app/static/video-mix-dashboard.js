const state = {
  dashboard: null,
  workDir: "",
  locale: "ru",
  loadState: { key: "load_waiting", className: "status-queued", params: {} },
  lastExportedPaths: [],
  selectedCandidateIds: new Set(),
  draftNotesByCandidateId: new Map(),
  filters: {
    status: "all",
    warnings: "all",
    search: "",
    sort: "score_desc",
  },
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
    hero_title: "Локальный дашборд для ревью, одобрения и экспорта",
    hero_copy: "Загрузите готовый VIDEO MIX work_dir, проверьте состояние пайплайна, просмотрите миниатюры кандидатов и одобрите или отклоните их прямо в локальном браузере.",
    open_review: "Открыть review.html",
    open_exports: "Открыть exports",
    open_workdir: "Открыть work_dir",
    load_title: "Загрузка work_dir",
    load_help: "Используйте уже созданную рабочую папку VIDEO MIX.",
    load_waiting: "Ожидание",
    workdir_label: "VIDEO MIX work_dir",
    load_dashboard: "Загрузить дашборд",
    copy_url: "Копировать URL",
    project_meta_empty: "Загрузите work_dir, чтобы увидеть метаданные проекта и сводные счётчики.",
    pipeline_title: "Пайплайн",
    pipeline_help: "Путь от ассетов до экспорта в одном локальном процессе.",
    actions_title: "Действия",
    actions_help: "Используется только текущее поведение VIDEO MIX.",
    export_approved: "Экспортировать одобренных кандидатов",
    refresh_dashboard: "Обновить дашборд",
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
    load_state_enter_workdir: "Укажите work_dir",
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
    hero_title: "Local dashboard for review, approval, and export",
    hero_copy: "Load an existing VIDEO MIX work_dir, inspect the pipeline state, review candidate thumbnails, and approve or reject without leaving the local browser.",
    open_review: "Open review.html",
    open_exports: "Open exports",
    open_workdir: "Open work_dir",
    load_title: "Load work_dir",
    load_help: "Use an already generated VIDEO MIX work folder.",
    load_waiting: "Waiting",
    workdir_label: "VIDEO MIX work_dir",
    load_dashboard: "Load dashboard",
    copy_url: "Copy URL",
    project_meta_empty: "Load a work_dir to see project metadata and summary counts.",
    pipeline_title: "Pipeline",
    pipeline_help: "Path from assets to export in one local flow.",
    actions_title: "Actions",
    actions_help: "Use existing VIDEO MIX behavior only.",
    export_approved: "Export approved candidates",
    refresh_dashboard: "Refresh dashboard",
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
    load_state_enter_workdir: "Enter work_dir",
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
    ["#vm-workdir-label", "workdir_label"],
    ["#vm-load-btn", "load_dashboard"],
    ["#vm-copy-url-btn", "copy_url"],
    ["#vm-pipeline-title", "pipeline_title"],
    ["#vm-pipeline-help", "pipeline_help"],
    ["#vm-actions-title", "actions_title"],
    ["#vm-actions-help", "actions_help"],
    ["#vm-export-btn", "export_approved"],
    ["#vm-refresh-btn", "refresh_dashboard"],
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
}

function bindActions() {
  qs("#vm-lang-ru").onclick = () => setLocale("ru");
  qs("#vm-lang-en").onclick = () => setLocale("en");
  qs("#vm-load-btn").onclick = () => loadDashboard();
  qs("#vm-refresh-btn").onclick = () => loadDashboard(state.workDir);
  qs("#vm-export-btn").onclick = () => exportApprovedCandidates();
  qs("#vm-open-review").onclick = () => openTarget("review");
  qs("#vm-open-exports").onclick = () => openTarget("exports");
  qs("#vm-open-workdir").onclick = () => openTarget("work_dir");
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
