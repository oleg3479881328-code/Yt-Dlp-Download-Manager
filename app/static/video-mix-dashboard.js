const state = {
  dashboard: null,
  workDir: "",
  selectedCandidateIds: new Set(),
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
    throw new Error(payload.detail || "Request failed");
  }
  return response.json();
}

function setLoadState(label, className) {
  const element = qs("#vm-load-state");
  if (!element) return;
  element.textContent = label;
  element.className = `status-chip ${className}`;
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
    target.innerHTML = `<div class="empty">Load a work_dir to see project metadata and summary counts.</div>`;
    summaryTarget.innerHTML = "";
    countChip.textContent = "0 candidates";
    countChip.className = "status-chip status-idle";
    return;
  }

  const { project, work_dir: workDir, summary } = state.dashboard;
  target.innerHTML = `
    <div class="video-mix-project-panel">
      <div><span>Project</span><strong>${escapeHtml(project.name)}</strong></div>
      <div><span>Pack</span><strong>${escapeHtml(project.industry_pack)}</strong></div>
      <div><span>Root</span><code>${escapeHtml(project.root_path)}</code></div>
      <div><span>work_dir</span><code>${escapeHtml(workDir)}</code></div>
    </div>
  `;
  const items = [
    ["Assets", summary.asset_count],
    ["Clips", summary.clip_count],
    ["Candidates", summary.candidate_count],
    ["Approved", summary.approved_candidate_count],
    ["Exported", summary.exported_candidate_count],
    ["Rejected", summary.status_totals.rejected || 0],
  ];
  summaryTarget.innerHTML = items.map(([label, value]) => `
    <div class="video-mix-summary-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");

  countChip.textContent = `${summary.candidate_count} candidate(s)`;
  countChip.className = `status-chip ${summary.candidate_count ? "status-completed" : "status-idle"}`;
}

function renderPipeline() {
  const target = qs("#vm-pipeline");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">Pipeline state will appear after loading a work_dir.</div>`;
    return;
  }
  target.innerHTML = state.dashboard.pipeline.map((step) => `
    <div class="pipeline-step ${escapeAttr(step.state === "ready" ? "active" : "")}">
      <strong>${escapeHtml(step.label)}</strong>
      <span>${escapeHtml(step.count)} item(s)</span>
      <span class="video-mix-step-state">${escapeHtml(step.state)}</span>
    </div>
  `).join("");
}

function candidateCommandButtons(candidate) {
  return `
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.approve_command)}">Copy approve</button>
    <button class="ghost-btn" type="button" data-copy-command="${escapeAttr(candidate.reject_command)}">Copy reject</button>
  `;
}

function renderSelectionSummary(visible) {
  const selectedCount = state.selectedCandidateIds.size;
  qs("#vm-selected-count").textContent = `${selectedCount} selected`;
  qs("#vm-visible-count").textContent = `${visible.length} visible`;
}

function renderCandidates() {
  const target = qs("#vm-candidates");
  if (!state.dashboard) {
    target.innerHTML = `<div class="empty">No work_dir loaded yet.</div>`;
    renderSelectionSummary([]);
    return;
  }

  const candidates = visibleCandidates();
  renderSelectionSummary(candidates);
  if (!candidates.length) {
    target.innerHTML = `<div class="empty">No candidates match the current filters.</div>`;
    return;
  }

  target.innerHTML = candidates.map((candidate) => {
    const isSelected = state.selectedCandidateIds.has(candidate.candidate_id);
    const thumbnail = candidate.thumbnail_path
      ? `<img class="video-mix-thumb" src="${escapeAttr(fileUrl(candidate.thumbnail_path))}" alt="${escapeAttr(candidate.candidate_id)} thumbnail">`
      : `<div class="video-mix-thumb video-mix-thumb-placeholder">No thumbnail</div>`;
    const warnings = candidate.warnings.length
      ? candidate.warnings.map((warning) => `<span class="video-mix-pill warning">${escapeHtml(warning)}</span>`).join("")
      : `<span class="video-mix-pill ok">No warnings</span>`;
    const exports = candidate.export_paths.length
      ? candidate.export_paths.map((path) => `
          <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
        `).join("")
      : `<div class="muted">No exports yet.</div>`;
    const sources = candidate.source_clips.length
      ? candidate.source_clips.map((clip) => `
          <div class="video-mix-source-row">
            <strong>${escapeHtml(clip.source_filename)}</strong>
            <span>${escapeHtml(formatDurationMs(clip.start_ms))} → ${escapeHtml(formatDurationMs(clip.end_ms))}</span>
            <span>${escapeHtml(clip.tags.join(", ") || "untagged")}</span>
          </div>
        `).join("")
      : `<div class="muted">No source clips attached.</div>`;
    const noteValue = escapeAttr(candidate.review_notes || "");
    return `
      <article class="video-mix-candidate-card ${isSelected ? "is-selected" : ""}">
        <div class="video-mix-card-toolbar">
          <label class="video-mix-select-toggle">
            <input type="checkbox" data-select-candidate="${escapeAttr(candidate.candidate_id)}" ${isSelected ? "checked" : ""}>
            <span>Select</span>
          </label>
          <span class="status-chip status-${escapeAttr(candidate.status)}">${escapeHtml(candidate.status)}</span>
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
              <div><span>Duration</span><strong>${escapeHtml(formatDurationMs(candidate.duration_ms))}</strong></div>
              <div><span>Source files</span><strong>${escapeHtml(candidate.source_filenames.length)}</strong></div>
            </div>
          </div>
        </div>
        <div class="video-mix-section">
          <h4>Warnings</h4>
          <div class="video-mix-pill-row">${warnings}</div>
        </div>
        <div class="video-mix-section">
          <h4>Source filenames</h4>
          <div class="video-mix-source-list">${sources}</div>
        </div>
        <div class="video-mix-section">
          <h4>Review note</h4>
          <textarea class="video-mix-note" data-note-for="${escapeAttr(candidate.candidate_id)}" rows="3" placeholder="optional review note">${noteValue}</textarea>
        </div>
        <div class="video-mix-section">
          <h4>Exports</h4>
          <div class="video-mix-export-list">${exports}</div>
        </div>
        <div class="video-mix-actions">
          <button class="accent-btn" type="button" data-approve="${escapeAttr(candidate.candidate_id)}">Approve</button>
          <button class="ghost-btn" type="button" data-reject="${escapeAttr(candidate.candidate_id)}">Reject</button>
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
      setLoadState("Command copied", "status-completed");
    };
  });
}

function renderExportsPanel(paths = []) {
  const target = qs("#vm-exports-list");
  if (!paths.length) {
    target.innerHTML = `<div class="muted">No new export paths in this session.</div>`;
    return;
  }
  target.innerHTML = paths.map((path) => `
    <a class="video-mix-export-link" href="${escapeAttr(fileUrl(path))}" target="_blank" rel="noreferrer">${escapeHtml(path)}</a>
  `).join("");
}

function renderAll() {
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
  syncSelectionToVisible();
  renderAll();
}

async function loadDashboard(workDirOverride = "") {
  const input = qs("#vm-workdir-input");
  const workDir = workDirOverride || input.value.trim();
  if (!workDir) {
    setLoadState("Enter work_dir", "status-failed");
    return;
  }
  state.workDir = workDir;
  setLoadState("Loading...", "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/dashboard?${new URLSearchParams({ work_dir: workDir }).toString()}`);
    applyDashboardPayload(payload);
    input.value = workDir;
    renderExportsPanel([]);
    setLoadState("Loaded", "status-completed");
    history.replaceState({}, "", `${window.location.pathname}?${new URLSearchParams({ work_dir: workDir }).toString()}`);
  } catch (error) {
    state.dashboard = null;
    state.selectedCandidateIds = new Set();
    renderAll();
    renderExportsPanel([]);
    setLoadState(error.message, "status-failed");
  }
}

function noteForCandidate(candidateId) {
  return qs(`[data-note-for="${CSS.escape(candidateId)}"]`)?.value?.trim() || "";
}

function noteForBulkSelection() {
  const firstSelected = [...state.selectedCandidateIds][0];
  return firstSelected ? noteForCandidate(firstSelected) : "";
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
  setLoadState(`${action}...`, "status-downloading");
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
    setLoadState(`${action}d`, "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

async function submitBulkCandidateAction(action) {
  if (!state.workDir || state.selectedCandidateIds.size === 0) {
    setLoadState("Select at least one candidate first", "status-failed");
    return;
  }
  if (action === "reject" && !window.confirm(`Reject ${state.selectedCandidateIds.size} selected candidate(s)?`)) {
    return;
  }
  if (action === "approve" && !window.confirm(`Approve ${state.selectedCandidateIds.size} selected candidate(s)?`)) {
    return;
  }
  setLoadState(`Bulk ${action}...`, "status-downloading");
  try {
    const payload = await fetchJson(`/api/video-mix/candidates/bulk/${action}`, {
      method: "POST",
      body: JSON.stringify({
        work_dir: state.workDir,
        candidate_ids: [...state.selectedCandidateIds],
        note: noteForBulkSelection(),
      }),
    });
    applyDashboardPayload(payload.dashboard);
    renderExportsPanel([]);
    clearSelection();
    setLoadState(`Bulk ${action} complete`, "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

async function exportApprovedCandidates() {
  if (!state.workDir) return;
  if (!window.confirm("Export all currently approved candidates?")) {
    return;
  }
  setLoadState("Exporting...", "status-downloading");
  try {
    const payload = await fetchJson("/api/video-mix/export", {
      method: "POST",
      body: JSON.stringify({ work_dir: state.workDir, ffmpeg: "ffmpeg" }),
    });
    applyDashboardPayload(payload.dashboard);
    renderExportsPanel(payload.exported_paths || []);
    setLoadState("Export complete", "status-completed");
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
    setLoadState(`Opened ${target}`, "status-completed");
  } catch (error) {
    setLoadState(error.message, "status-failed");
  }
}

function copyCurrentUrl() {
  navigator.clipboard.writeText(window.location.href);
  setLoadState("URL copied", "status-completed");
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

init();
