const state = {
  dashboard: null,
  workDir: "",
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

const STATUS_LABELS = {
  generated: "Сгенерирован",
  previewed: "Просмотрен",
  approved: "Одобрен",
  rejected: "Отклонён",
  exported: "Экспортирован",
};

const PIPELINE_LABELS = {
  assets: "Ассеты",
  clips: "Клипы",
  candidates: "Кандидаты",
  review: "Ревью",
  approval: "Одобрение",
  export: "Экспорт",
};

const PIPELINE_STATE_LABELS = {
  ready: "готово",
  pending: "ожидание",
  active: "в работе",
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

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Запрос не выполнен");
  }
  return response.json();
}

function setLoadState(label, className) {
  const element = qs("#vm-load-state");
  if (!element) return;
  element.textContent = label;
  element.className = `status-chip ${className}`;
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status;
}

function pipelineLabel(step) {
  return PIPELINE_LABELS[step.id] || step.label || step.id;
}

function pipelineStateLabel(stateValue) {
  return PIPELINE_STATE_LABELS[stateValue] || stateValue;
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
    target.innerHTML = `<div class="empty">Загрузите work_dir, чтобы увидеть метаданные проекта и сводные счётчики.</div>`;
    summaryTarget.innerHTML = "";
    countChip.textContent = "0 кандидатов";
    countChip.className = "status-chip status-idle";
    return;
  }

  const { project, work_dir: workDir, summary } = state.dashboard;
  target.innerHTML = `
    <div class="video-mix-project-panel">
      <div><span>Проект</span><strong>${escapeHtml(project.name)}</strong></div>
      <div><span>Пакет</span><strong>${escapeHtml(project.industry_pack)}</strong></div>
      <div><span>Корень</span><code>${escapeHtml(project.root_path)}</code></div>
      <div><span>work_dir</span><code>${escapeHtml(workDir)}</code></div>
    </div>
  `;
  const items = [
    ["Ассеты", summary.asset_count],
    ["Клипы", summary.clip_count],
    ["Кандидаты", summary.candidate_count],
    ["Одобрено", summary.approved_candidate_count],
    ["Экспортировано", summary.exported_candidate_count],
    ["Отклонено", summary.status_totals.rejected || 0],
  ];
  summaryTarget.innerHTML = items.map(([label, value]) => `
    <div class="video-mix-summary-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");

  countChip.textContent = `${summary.candidate_count} кандидатов`;
  countChip.className = `status-chip ${summary.candidate_count ? "status-completed" : "status-idle"}`;
}

function renderPipeline() {
  const target = qs("#vm-pipeline");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">Состояние пайплайна появится после загрузки work_dir.</div>`;
    return;
  }
  target.innerHTML = state.dashboard.pipeline.map((step) => `
    <div class="pipeline-step ${escapeAttr(step.state === "ready" ? "active" : "")}">
      <strong>${escapeHtml(pipelineLabel(step))}</strong>
      <span>${escapeHtml(step.count)} шт.</span>
      <span class="video-mix-step-state">${escapeHtml(pipelineStateLabel(step.state))}</span>
    </div>
  `).join("");
}

function candidateCommandButtons(candidate) {
  return `
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.approve_command)}">Копировать approve</button>
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.reject_command)}">Копировать reject</button>
  `;
}

function renderSelectionSummary(visible) {
  const selectedCount = state.selectedCandidateIds.size;
  qs("#vm-selected-count").textContent = `${selectedCount} выбрано`;
  qs("#vm-visible-count").textContent = `${visible.length} видно`;
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
    target.innerHTML = `<div class="empty">work_dir ещё не загружен.</div>`;
    renderSelectionSummary([]);
    return;
  }

  const candidates = visibleCandidates();
  renderSelectionSummary(candidates);
  if (!candidates.length) {
    target.innerHTML = `<div class="empty">Нет кандидатов, подходящих под текущие фильтры.</div>`;
    return;
  }

  target.innerHTML = candidates.map((candidate) => {
    const isSelected = state.selectedCandidateIds.has(candidate.candidate_id);
    const thumbnail = candidate.thumbnail_path
      ? `<img class="video-mix-thumb" src="${escapeAttr(fileUrl(candidate.thumbnail_path))}" alt="Миниатюра кандидата ${escapeAttr(candidate.candidate_id)}">`
      : `<div class="video-mix-thumb video-mix-thumb-placeholder">Без миниатюры</div>`;
    const warnings = candidate.warnings.length
      ? candidate.warnings.map((warning) => `<span class="video-mix-pill warning">${escapeHtml(warning)}</span>`).join("")
      : `<span class="video-mix-pill ok">Без предупреждений</span>`;
    const exports = candidate.export_paths.length
      ? candidate.export_paths.map((path) => `
          <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
        `).join("")
      : `<div class="muted">Экспортов пока нет.</div>`;
    const sources = candidate.source_clips.length
      ? candidate.source_clips.map((clip) => `
          <div class="video-mix-source-row">
            <strong>${escapeHtml(clip.source_filename)}</strong>
            <span>${escapeHtml(formatDurationMs(clip.start_ms))} → ${escapeHtml(formatDurationMs(clip.end_ms))}</span>
            <span>${escapeHtml(clip.tags.join(", ") || "без тегов")}</span>
          </div>
        `).join("")
      : `<div class="muted">Исходные клипы не привязаны.</div>`;
    const noteValue = escapeAttr(resolveReviewNoteValue(candidate, state.draftNotesByCandidateId));
    return `
      <article class="video-mix-candidate-card ${isSelected ? "is-selected" : ""}">
        <div class="video-mix-card-toolbar">
          <label class="video-mix-select-toggle">
            <input type="checkbox" data-select-candidate="${escapeAttr(candidate.candidate_id)}" ${isSelected ? "checked" : ""}>
            <span>Выбрать</span>
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
              <div><span>Score</span><strong>${escapeHtml(candidate.score)}</strong></div>
              <div><span>Длительность</span><strong>${escapeHtml(formatDurationMs(candidate.duration_ms))}</strong></div>
              <div><span>Исходные файлы</span><strong>${escapeHtml(candidate.source_filenames.length)}</strong></div>
            </div>
          </div>
        </div>
        <div class="video-mix-section">
          <h4>Предупреждения</h4>
          <div class="video-mix-pill-row">${warnings}</div>
        </div>
        <div class="video-mix-section">
          <h4>Имена исходных файлов</h4>
          <div class="video-mix-source-list">${sources}</div>
        </div>
        <div class="video-mix-section">
          <h4>Комментарий ревью</h4>
          <textarea class="video-mix-note" data-note-for="${escapeAttr(candidate.candidate_id)}" rows="3" placeholder="необязательный комментарий ревью">${noteValue}</textarea>
        </div>
        <div class="video-mix-section">
          <h4>Экспорт</h4>
          <div class="video-mix-export-list">${exports}</div>
        </div>
        <div class="video-mix-actions">
          <button class="accent-btn" type="button" data-approve="${escapeAttr(candidate.candidate_id)}">Одобрить</button>
          <button class="ghost-btn" type="button" data-reject="${escapeAttr(candidate.candidate_id)}">Отклонить</button>
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
      setLoadState("Команда скопирована", "status-completed");
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
    target.innerHTML = `<div class="muted">В этой сессии новых путей экспорта пока нет.</div>`;
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
  if (!state.dashboard) {
    renderExportsPanel([]);
  }
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
    setLoadState("Укажите work_dir", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLoadState("Загрузка...", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/dashboard?${new URLSearchParams({ work_dir: workDir }).toString()}`);
    applyDashboardPayload(payload);
    input.value = workDir;
    renderExportsPanel([]);
    setLoadState("Загружено", "status-completed");
    history.replaceState({}, "", `${window.location.pathname}?${new URLSearchParams({ work_dir: workDir }).toString()}`);
  } catch (error) {
    state.dashboard = null;
    state.selectedCandidateIds = new Set();
    state.draftNotesByCandidateId = new Map();
    renderAll();
    renderExportsPanel([]);
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
  setLoadState(action === "approve" ? "Одобрение..." : "Отклонение...", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/candidates/${encodeURIComponent(candidateId)}/${action}`, {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        note: noteForCandidate(candidateId),
      }),
    });
    applyDashboardPayload(payload.dashboard);
    renderExportsPanel([]);
    setLoadState(action === "approve" ? "Одобрено" : "Отклонено", "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

async function submitBulkCandidateAction(action) {
  const candidateIds = visibleSelectedCandidateIds();
  if (!state.workDir || state.selectedCandidateIds.size === 0) {
    setLoadState("Сначала выберите хотя бы одного кандидата", "status-failed");
    return;
  }
  if (candidateIds.length === 0) {
    setLoadState("Среди выбранных нет кандидатов, видимых по текущим фильтрам", "status-failed");
    return;
  }
  if (action === "reject" && !window.confirm(`Отклонить ${candidateIds.length} выбранных кандидатов?`)) {
    return;
  }
  if (action === "approve" && !window.confirm(`Одобрить ${candidateIds.length} выбранных кандидатов?`)) {
    return;
  }
  setLoadState(action === "approve" ? "Массовое одобрение..." : "Массовое отклонение...", "status-downloading");
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
    renderExportsPanel([]);
    clearSelection();
    setLoadState(action === "approve" ? "Массовое одобрение завершено" : "Массовое отклонение завершено", "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

async function exportApprovedCandidates() {
  if (!state.workDir) return;
  if (!window.confirm("Экспортировать всех кандидатов, которые сейчас одобрены?")) {
    return;
  }
  setLoadState("Экспорт...", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/export", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir, ffmpeg: "ffmpeg" }),
    });
    applyDashboardPayload(payload.dashboard);
    renderExportsPanel(payload.exported_paths || []);
    setLoadState("Экспорт завершён", "status-completed");
  } catch (error) {
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
    setLoadState(`Открыто: ${target}`, "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

function copyCurrentUrl() {
  navigator.clipboard.writeText(window.location.href);
  setLoadState("URL скопирован", "status-completed");
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
  bindActions();
  renderAll();
  initFromQuery();
}

if (typeof document !== "undefined") {
  init();
}
