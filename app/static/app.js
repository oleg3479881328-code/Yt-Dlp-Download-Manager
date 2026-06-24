import {
  buildTranscriptSelection,
  parseTranscriptText,
  resolveTranscriptEntryEnd,
} from "./transcript-picker.js";

const state = {
  analysis: null,
  selectedJobId: null,
  historyFilter: "all",
  settings: null,
  socket: null,
  latestHistory: [],
  transcript: {
    entries: [],
    startIndex: null,
    endIndex: null,
    error: null,
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

function escapeAttr(value) { return escapeHtml(value); }
function classToken(value) { return String(value ?? "unknown").replace(/[^A-Za-z0-9_-]/g, "-"); }
function statusClass(status) { return `status-chip status-${classToken(status)}`; }
function progressBar(value = 0) { return `<div class="progress"><span style="width:${Math.min(100, Math.max(4, Number(value) || 4))}%"></span></div>`; }

function safeUrl(value) {
  try {
    const parsed = new URL(String(value ?? ""), window.location.origin);
    if (["http:", "https:"].includes(parsed.protocol)) return parsed.href;
  } catch (_error) {}
  return "";
}

function thumbnailHtml(url, sizeClass = "") {
  const thumbnail = safeUrl(url);
  const classes = `thumb ${sizeClass}`.trim();
  return thumbnail
    ? `<img class="${escapeAttr(classes)}" src="${escapeAttr(thumbnail)}" alt="thumbnail">`
    : `<div class="${escapeAttr(classes)} placeholder">No Preview</div>`;
}

function formatJobMeta(job) {
  return [
    `Stage: ${job.stage || "-"}`,
    job.speed ? `Speed: ${job.speed}` : null,
    job.eta ? `ETA: ${job.eta}` : null,
    job.type === "playlist" ? `Items: ${job.item_completed || 0}/${job.item_total || 0}` : null,
  ].filter(Boolean).join(" • ");
}

function parseLooseTime(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  if (/^\d+(?:\.\d+)?$/.test(raw)) return Number(raw);
  const parts = raw.split(":").map((part) => part.trim());
  if (parts.length === 2) return Number(parts[0]) * 60 + Number(parts[1]);
  if (parts.length === 3) return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2]);
  return null;
}

function formatSeconds(seconds) {
  if (seconds === null || Number.isNaN(seconds)) return "—";
  const total = Math.max(0, Math.round(seconds));
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  return hh ? `${hh}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}` : `${mm}:${String(ss).padStart(2, "0")}`;
}

function updateRangePreview() {
  const start = parseLooseTime(qs("#segment-start")?.value);
  const end = parseLooseTime(qs("#segment-end")?.value);
  const duration = parseLooseTime(qs("#segment-duration")?.value);
  const target = qs("#range-preview");
  if (!target) return;
  if (start === null) {
    target.textContent = "No range";
    target.className = "range-preview";
    return;
  }
  const computedEnd = end !== null ? end : (duration !== null ? start + duration : null);
  if (computedEnd === null || computedEnd <= start) {
    target.textContent = "Range incomplete";
    target.className = "range-preview warning";
    return;
  }
  target.textContent = `${formatSeconds(start)} → ${formatSeconds(computedEnd)} • ${Math.round(computedEnd - start)}s`;
  target.className = "range-preview ready";
}

function parseTranscriptInput() {
  const text = qs("#transcript-input")?.value ?? "";
  const status = qs("#transcript-status");
  try {
    const entries = parseTranscriptText(text);
    state.transcript = {
      entries,
      startIndex: null,
      endIndex: null,
      error: null,
    };
    if (status) {
      status.textContent = `${entries.length} line(s) ready`;
      status.className = "status-chip status-completed";
    }
  } catch (error) {
    state.transcript = {
      entries: [],
      startIndex: null,
      endIndex: null,
      error: error.message,
    };
    if (status) {
      status.textContent = error.message;
      status.className = "status-chip status-failed";
    }
  }
  renderTranscriptPicker();
}

function handleTranscriptLineClick(index) {
  const transcript = state.transcript;
  if (!transcript.entries.length) return;

  if (transcript.startIndex === null || (transcript.startIndex !== null && transcript.endIndex !== null)) {
    state.transcript.startIndex = index;
    state.transcript.endIndex = null;
  } else if (transcript.endIndex === null) {
    if (index < transcript.startIndex) {
      state.transcript.startIndex = index;
    } else {
      state.transcript.endIndex = index;
    }
  }

  renderTranscriptPicker();
}

function applyTranscriptRange() {
  try {
    const selection = buildTranscriptSelection(
      state.transcript.entries,
      state.transcript.startIndex,
      state.transcript.endIndex,
    );
    qs("#segment-start").value = formatSeconds(selection.start);
    qs("#segment-end").value = formatSeconds(selection.end);
    qs("#segment-duration").value = "";
    if (!qs("#segment-label").value.trim()) {
      qs("#segment-label").value = selection.label;
    }
    updateRangePreview();
    const status = qs("#transcript-status");
    if (status) {
      status.textContent = "Selected range applied to clip fields";
      status.className = "status-chip status-completed";
    }
  } catch (error) {
    const status = qs("#transcript-status");
    if (status) {
      status.textContent = error.message;
      status.className = "status-chip status-failed";
    }
  }
}

function clearTranscriptPicker() {
  qs("#transcript-input").value = "";
  qs("#transcript-file").value = "";
  state.transcript = {
    entries: [],
    startIndex: null,
    endIndex: null,
    error: null,
  };
  const status = qs("#transcript-status");
  if (status) {
    status.textContent = "Waiting for transcript";
    status.className = "status-chip status-queued";
  }
  renderTranscriptPicker();
}

function renderTranscriptPicker() {
  const transcript = state.transcript;
  const listTarget = qs("#transcript-lines");
  const previewTarget = qs("#transcript-selection-preview");
  const useButton = qs("#use-transcript-range-btn");
  if (!listTarget || !previewTarget || !useButton) return;

  if (!transcript.entries.length) {
    listTarget.innerHTML = `<div class="empty">Paste transcript text or load an SRT file to begin.</div>`;
    previewTarget.innerHTML = `<div class="empty">Select a start line and an end line to preview the episode range.</div>`;
    useButton.disabled = true;
    return;
  }

  const lower = transcript.startIndex !== null && transcript.endIndex !== null
    ? Math.min(transcript.startIndex, transcript.endIndex)
    : transcript.startIndex;
  const upper = transcript.startIndex !== null && transcript.endIndex !== null
    ? Math.max(transcript.startIndex, transcript.endIndex)
    : transcript.startIndex;

  listTarget.innerHTML = transcript.entries.map((entry, index) => {
    const resolvedEnd = resolveTranscriptEntryEnd(transcript.entries, index);
    const isStart = transcript.startIndex === index;
    const isEnd = transcript.endIndex === index;
    const inRange = lower !== null && upper !== null && index >= lower && index <= upper;
    return `
      <button class="transcript-line${isStart ? " is-start" : ""}${isEnd ? " is-end" : ""}${inRange ? " is-selected" : ""}" data-transcript-index="${escapeAttr(index)}" type="button">
        <span class="transcript-time">${escapeHtml(formatSeconds(entry.start))}${resolvedEnd !== null ? ` → ${escapeHtml(formatSeconds(resolvedEnd))}` : ""}</span>
        <span class="transcript-text">${escapeHtml(entry.text)}</span>
      </button>
    `;
  }).join("");

  try {
    const selection = buildTranscriptSelection(
      transcript.entries,
      transcript.startIndex,
      transcript.endIndex,
    );
    previewTarget.innerHTML = `
      <div class="selection-metrics">
        <div><span>Start</span><strong>${escapeHtml(formatSeconds(selection.start))}</strong></div>
        <div><span>End</span><strong>${escapeHtml(formatSeconds(selection.end))}</strong></div>
        <div><span>Duration</span><strong>${escapeHtml(`${selection.duration}s`)}</strong></div>
        <div><span>Label</span><strong>${escapeHtml(selection.label || "clip")}</strong></div>
      </div>
      <div class="selection-snippet">${escapeHtml(selection.snippet || "No transcript text in selection.")}</div>
    `;
    useButton.disabled = false;
  } catch (_error) {
    previewTarget.innerHTML = `<div class="empty">Click one line for start, then another line for end.</div>`;
    useButton.disabled = true;
  }

  document.querySelectorAll("[data-transcript-index]").forEach((element) => {
    element.onclick = () => handleTranscriptLineClick(Number(element.dataset.transcriptIndex));
  });
}

function renderAnalysis() {
  const target = qs("#analysis-result");
  const status = qs("#analysis-status");
  if (!target || !status) return;
  if (!state.analysis) {
    target.innerHTML = `<div class="analysis-empty">Analyze a URL to inspect metadata before creating a clip.</div>`;
    status.textContent = "Waiting for URL";
    status.className = "status-chip status-queued";
    return;
  }
  const a = state.analysis;
  status.textContent = a.type === "playlist" ? `Playlist • ${a.item_count} items` : "Ready for range";
  status.className = a.type === "playlist" ? "status-chip status-failed" : "status-chip status-completed";
  target.innerHTML = `
    <div class="analysis-preview">
      ${thumbnailHtml(a.thumbnail, "poster")}
      <div class="analysis-copy">
        <h3>${escapeHtml(a.title)}</h3>
        <div class="job-meta">
          <span>${escapeHtml(a.type)}</span>
          <span>${escapeHtml(a.item_count)} item(s)</span>
          <span>${escapeHtml(a.extractor || "source unknown")}</span>
          ${a.duration ? `<span>${escapeHtml(formatSeconds(Number(a.duration)))} total</span>` : ""}
        </div>
        ${a.type === "playlist" ? `<div class="notice warning">MVP 1 segment jobs support a single video URL only. Use a direct item URL.</div>` : `<div class="notice ok">Enter a start/end or start/duration and create a clip job.</div>`}
      </div>
    </div>
    ${(a.entries || []).slice(0, 8).map((entry) => `
      <div class="item-row">
        <strong>${escapeHtml(entry.index)}. ${escapeHtml(entry.title)}</strong>
        <div class="muted">${entry.duration ? `${escapeHtml(formatSeconds(Number(entry.duration)))} duration` : "Duration unavailable"}</div>
      </div>
    `).join("")}
  `;
}

function renderDashboard(data) {
  qs("#worker-state").textContent = `Worker: ${data.worker_state}`;
  qs("#queue-size").textContent = `Queue: ${data.queue_size}`;
  qs("#system-status").innerHTML = `
    <div class="row"><strong>Worker</strong><span class="${statusClass(data.worker_state)}">${escapeHtml(data.worker_state)}</span></div>
    <div class="row"><strong>Queue Size</strong><span>${escapeHtml(data.queue_size)}</span></div>
    <div class="row"><strong>Errors</strong><span>${escapeHtml(data.errors_count)}</span></div>
  `;
  qs("#active-jobs").innerHTML = data.active_jobs.length ? data.active_jobs.map((job) => `
    <div class="job-card" data-job="${escapeAttr(job.id)}">
      <div class="card-header">
        <div class="media-line">
          ${thumbnailHtml(job.analysis_json?.thumbnail)}
          <div>
            <h3>${escapeHtml(job.title || job.url)}</h3>
            <div class="${statusClass(job.status)}">${escapeHtml(job.status)}</div>
          </div>
        </div>
        <span>${job.analysis_json?.segment ? "clip" : escapeHtml(job.type)}</span>
      </div>
      ${progressBar(job.progress)}
      <div class="job-meta">${escapeHtml(formatJobMeta(job))}</div>
    </div>
  `).join("") : `<div class="empty">No active jobs yet.</div>`;
  qs("#queue-preview").innerHTML = data.queue_preview.length ? data.queue_preview.map((job) => `
    <div class="row" data-job="${escapeAttr(job.id)}">
      <strong>${escapeHtml(job.title || job.url)}</strong>
      <div class="row-meta">Position ${escapeHtml(job.queue_position || "-")}</div>
    </div>
  `).join("") : `<div class="empty">Queue is empty.</div>`;
}

function queueRow(job) {
  return `
    <div class="row" data-job="${escapeAttr(job.id)}">
      <div><strong>${escapeHtml(job.title || job.url)}</strong><div class="row-meta">${escapeHtml(formatJobMeta(job))}</div></div>
      <div>${job.analysis_json?.segment ? "clip" : escapeHtml(job.type)}</div>
      <div class="${statusClass(job.status)}">${escapeHtml(job.status)}</div>
      <div class="row-actions">
        <button data-action="select" data-id="${escapeAttr(job.id)}">Details</button>
        <button data-action="cancel" data-id="${escapeAttr(job.id)}">Cancel</button>
        <button data-action="remove" data-id="${escapeAttr(job.id)}">Remove</button>
      </div>
    </div>
  `;
}

function historyRow(job) {
  return `
    <div class="row" data-job="${escapeAttr(job.id)}">
      <div class="media-line">
        ${thumbnailHtml(job.analysis_json?.thumbnail)}
        <div><strong>${escapeHtml(job.title || job.url)}</strong><div class="row-meta">${escapeHtml(job.finished_at || job.created_at || "-")}</div></div>
      </div>
      <div>${job.analysis_json?.segment ? "clip" : escapeHtml(job.type)}</div>
      <div class="${statusClass(job.status)}">${escapeHtml(job.status)}</div>
      <div class="row-actions">
        <button data-action="select" data-id="${escapeAttr(job.id)}">Details</button>
        <button data-action="retry" data-id="${escapeAttr(job.id)}">Retry</button>
        ${job.output_path ? `<button data-action="open-file" data-id="${escapeAttr(job.id)}">Open File</button>` : ""}
        ${job.output_path ? `<button data-action="open-folder" data-id="${escapeAttr(job.id)}">Open Folder</button>` : ""}
        ${job.output_path ? `<a class="download-btn" href="/api/download/${escapeAttr(job.id)}">Download</a>` : ""}
      </div>
    </div>
  `;
}

function renderQueue(jobs) { qs("#queue-list").innerHTML = jobs.length ? jobs.map(queueRow).join("") : `<div class="empty">Queue is empty.</div>`; }
function renderHistory(jobs) { qs("#history-list").innerHTML = jobs.length ? jobs.map(historyRow).join("") : `<div class="empty">History is empty.</div>`; }

function renderClipLibrary(jobs) {
  const target = qs("#clip-library");
  if (!target) return;
  const clips = (jobs || []).filter((job) => job.analysis_json?.segment);
  target.innerHTML = clips.length ? clips.slice(0, 12).map((job) => {
    const segment = job.analysis_json.segment;
    return `
      <div class="clip-row" data-job="${escapeAttr(job.id)}">
        <div>
          <strong>${escapeHtml(segment.label || "clip")}</strong>
          <div class="row-meta">
            <span>${escapeHtml(formatSeconds(segment.start))} → ${escapeHtml(formatSeconds(segment.end))}</span>
            <span>${escapeHtml(segment.duration)}s</span>
            <span class="${statusClass(job.status)}">${escapeHtml(job.status)}</span>
          </div>
          <div class="muted clip-path">${escapeHtml(job.output_path || job.title || job.url)}</div>
        </div>
        <div class="row-actions">
          <button data-action="select" data-id="${escapeAttr(job.id)}">Details</button>
          ${job.output_path ? `<button data-action="open-file" data-id="${escapeAttr(job.id)}">Open</button>` : ""}
          ${job.output_path ? `<button data-action="open-folder" data-id="${escapeAttr(job.id)}">Folder</button>` : ""}
        </div>
      </div>
    `;
  }).join("") : `<div class="empty">No clip jobs yet. Create one from the workbench above.</div>`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Request failed");
  }
  return response.json();
}

function applySocketState(payload) {
  state.latestHistory = payload.history || [];
  renderDashboard(payload.dashboard);
  renderQueue(payload.queue || []);
  renderHistory(payload.history || []);
  renderClipLibrary(payload.history || []);
  if (payload.selected_job) {
    renderDetails(payload.selected_job);
  } else if (!state.selectedJobId) {
    qs("#details-title").textContent = "No job selected";
    qs("#details-body").innerHTML = `<div class="empty">Choose a clip/job to inspect output, range metadata, and logs.</div>`;
  }
  bindRowActions();
}

function renderDetails(job) {
  state.selectedJobId = job.id;
  qs("#details-title").textContent = job.analysis_json?.segment ? `Clip: ${job.analysis_json.segment.label}` : (job.title || job.url);
  const segment = job.analysis_json?.segment;
  const segmentBlock = segment ? `
    <div class="segment-summary">
      <h3>Selected Segment</h3>
      <div class="segment-metrics">
        <div><span>Start</span><strong>${escapeHtml(formatSeconds(segment.start))}</strong></div>
        <div><span>End</span><strong>${escapeHtml(formatSeconds(segment.end))}</strong></div>
        <div><span>Duration</span><strong>${escapeHtml(segment.duration)}s</strong></div>
        <div><span>Label</span><strong>${escapeHtml(segment.label)}</strong></div>
      </div>
      <div class="muted">Range expression: ${escapeHtml(segment.section_expression)}</div>
    </div>` : "";
  const playlistBlock = job.playlist_items?.length ? `
    <div>
      <h3>Playlist Items</h3>
      <div class="playlist-list">
        ${job.playlist_items.map((item) => `
          <div class="item-row">
            <strong>${escapeHtml((item.item_index || 0) + 1)}. ${escapeHtml(item.title)}</strong>
            <div class="row-meta">
              <span class="${statusClass(item.status)}">${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.progress || 0)}%</span>
              ${item.output_path ? `<button data-action="open-item-file" data-id="${escapeAttr(item.id)}">Open File</button>` : ""}
              ${item.output_path ? `<button data-action="open-item-folder" data-id="${escapeAttr(item.id)}">Open Folder</button>` : ""}
              ${item.output_path ? `<a class="download-btn" href="/api/download/item/${escapeAttr(item.id)}">Download</a>` : ""}
            </div>
          </div>
        `).join("")}
      </div>
    </div>` : "";
  qs("#details-body").innerHTML = `
    <div class="job-card">
      <div class="card-header">
        <div class="media-line">
          ${thumbnailHtml(job.analysis_json?.thumbnail, "large")}
          <div><h3>${escapeHtml(job.title || job.url)}</h3><div class="${statusClass(job.status)}">${escapeHtml(job.status)}</div></div>
        </div>
      </div>
      ${progressBar(job.progress)}
      <div class="job-meta"><span>${escapeHtml(job.stage || "-")}</span><span>${escapeHtml(job.speed || "Speed unavailable")}</span><span>${escapeHtml(job.eta || "ETA unavailable")}</span></div>
      ${segmentBlock}
      ${job.output_path ? `<div class="output-box"><span>Output</span><code>${escapeHtml(job.output_path)}</code></div>` : ""}
      <div class="details-actions">
        <button data-action="retry" data-id="${escapeAttr(job.id)}">Retry</button>
        <button data-action="cancel" data-id="${escapeAttr(job.id)}">Cancel</button>
        ${job.output_path ? `<button data-action="open-file" data-id="${escapeAttr(job.id)}">Open File</button>` : ""}
        ${job.output_path ? `<button data-action="open-folder" data-id="${escapeAttr(job.id)}">Open Folder</button>` : ""}
        ${job.output_path ? `<a class="download-btn" href="/api/download/${escapeAttr(job.id)}">Download file</a>` : ""}
      </div>
    </div>
    ${playlistBlock}
    <div>
      <h3>Logs</h3>
      <div class="log-list">
        ${(job.logs || []).length ? job.logs.map((log) => `<div class="log-row"><strong>${escapeHtml(log.timestamp)}</strong><div class="muted">${escapeHtml(log.message)}</div></div>`).join("") : `<div class="empty">No logs yet.</div>`}
      </div>
    </div>
  `;
  bindRowActions();
}

function pushSocketContext() {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
  state.socket.send(JSON.stringify({ history_filter: state.historyFilter, selected_job_id: state.selectedJobId }));
}

async function loadSettings() {
  const settings = await fetchJson("/api/settings");
  state.settings = settings;
  qs("#settings-form").innerHTML = `
    <div class="setting-row"><label for="output_directory">Output directory</label><input id="output_directory" name="output_directory" value="${escapeAttr(settings.output_directory)}"></div>
    <div class="setting-row"><label for="default_mode">Default mode</label><select id="default_mode" name="default_mode"><option value="video" ${settings.default_mode === "video" ? "selected" : ""}>Video</option><option value="audio" ${settings.default_mode === "audio" ? "selected" : ""}>Audio</option></select></div>
    <div class="setting-row"><label for="quality">Quality / format</label><input id="quality" name="quality" value="${escapeAttr(settings.quality)}"></div>
    <div class="setting-row"><label for="retry_enabled">Retry enabled</label><select id="retry_enabled" name="retry_enabled"><option value="true" ${settings.retry_enabled ? "selected" : ""}>Enabled</option><option value="false" ${!settings.retry_enabled ? "selected" : ""}>Disabled</option></select></div>
    <div class="setting-row"><label for="retry_count">Retry count</label><input id="retry_count" name="retry_count" type="number" min="0" value="${escapeAttr(settings.retry_count)}"></div>
    <button class="accent-btn" type="submit">Save settings</button>
  `;
}

function bindNavigation() {
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".screen").forEach((screen) => screen.classList.remove("active"));
      button.classList.add("active");
      qs(`#screen-${button.dataset.screen}`).classList.add("active");
    });
  });
}

function bindFilters() {
  document.querySelectorAll(".filter-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelectorAll(".filter-btn").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.historyFilter = button.dataset.filter;
      pushSocketContext();
    });
  });
}

function bindRowActions() {
  document.querySelectorAll("[data-action]").forEach((element) => {
    element.onclick = async () => {
      const { action, id } = element.dataset;
      if (!id) return;
      if (action === "select") { state.selectedJobId = id; pushSocketContext(); return; }
      if (action === "open-file") { await fetchJson(`/api/open/job/${encodeURIComponent(id)}`, { method: "POST" }); return; }
      if (action === "open-folder") { await fetchJson(`/api/open/job/${encodeURIComponent(id)}/folder`, { method: "POST" }); return; }
      if (action === "open-item-file") { await fetchJson(`/api/open/item/${encodeURIComponent(id)}`, { method: "POST" }); return; }
      if (action === "open-item-folder") { await fetchJson(`/api/open/item/${encodeURIComponent(id)}/folder`, { method: "POST" }); return; }
      if (action === "retry") await fetchJson(`/api/jobs/${encodeURIComponent(id)}/retry`, { method: "POST" });
      if (action === "cancel") await fetchJson(`/api/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" });
      if (action === "remove") await fetchJson(`/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (action === "remove" && state.selectedJobId === id) state.selectedJobId = null;
      pushSocketContext();
    };
  });
  document.querySelectorAll("[data-job]").forEach((row) => {
    row.onclick = async (event) => {
      if (event.target.closest("[data-action]")) return;
      state.selectedJobId = row.dataset.job;
      pushSocketContext();
    };
  });
}

function bindAnalyze() {
  qs("#analyze-btn").addEventListener("click", async () => {
    const url = qs("#url-input").value.trim();
    if (!url) return;
    qs("#analysis-status").textContent = "Analyzing...";
    qs("#analysis-status").className = "status-chip status-downloading";
    try {
      const payload = await fetchJson("/api/analyze", { method: "POST", body: JSON.stringify({ url }) });
      state.analysis = payload.analysis;
      renderAnalysis();
    } catch (error) {
      qs("#analysis-status").textContent = error.message;
      qs("#analysis-status").className = "status-chip status-failed";
      qs("#analysis-result").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
  });
  qs("#queue-btn").addEventListener("click", async () => {
    const url = qs("#url-input").value.trim();
    if (!url) return;
    const segmentStart = qs("#segment-start").value.trim();
    const segmentEnd = qs("#segment-end").value.trim();
    const segmentDuration = qs("#segment-duration").value.trim();
    const segmentLabel = qs("#segment-label").value.trim();
    const body = { url, mode: state.settings?.default_mode || "video", quality: state.settings?.quality || "bestvideo*+bestaudio/best" };
    if (segmentStart || segmentEnd || segmentDuration || segmentLabel) {
      if (segmentStart) body.segment_start = segmentStart;
      if (segmentEnd) body.segment_end = segmentEnd;
      if (segmentDuration) body.segment_duration = segmentDuration;
      if (segmentLabel) body.segment_label = segmentLabel;
    }
    try {
      const payload = await fetchJson("/api/jobs", { method: "POST", body: JSON.stringify(body) });
      state.selectedJobId = payload.job.id;
      pushSocketContext();
      document.querySelector('[data-screen="dashboard"]')?.click();
    } catch (error) {
      qs("#analysis-status").textContent = error.message;
      qs("#analysis-status").className = "status-chip status-failed";
    }
  });
  qs("#clear-workbench-btn").addEventListener("click", () => {
    qs("#url-input").value = "";
    qs("#segment-start").value = "";
    qs("#segment-end").value = "";
    qs("#segment-duration").value = "";
    qs("#segment-label").value = "";
    state.analysis = null;
    renderAnalysis();
    updateRangePreview();
  });
  ["#segment-start", "#segment-end", "#segment-duration", "#segment-label"].forEach((selector) => {
    qs(selector).addEventListener("input", updateRangePreview);
  });
}

function bindTranscriptPicker() {
  qs("#parse-transcript-btn").addEventListener("click", () => parseTranscriptInput());
  qs("#clear-transcript-btn").addEventListener("click", () => clearTranscriptPicker());
  qs("#use-transcript-range-btn").addEventListener("click", () => applyTranscriptRange());
  qs("#transcript-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    qs("#transcript-input").value = text;
    parseTranscriptInput();
  });
}

function bindSettingsSubmit() {
  document.addEventListener("submit", async (event) => {
    if (event.target.id !== "settings-form") return;
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    await fetchJson("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        output_directory: data.output_directory,
        default_mode: data.default_mode,
        quality: data.quality,
        retry_enabled: data.retry_enabled === "true",
        retry_count: Number(data.retry_count || 0),
      }),
    });
    await loadSettings();
    pushSocketContext();
  });
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/state`);
  state.socket = socket;
  socket.onopen = () => pushSocketContext();
  socket.onmessage = (event) => applySocketState(JSON.parse(event.data));
  socket.onclose = () => { setTimeout(connectSocket, 1500); };
}

async function init() {
  bindNavigation();
  bindFilters();
  bindAnalyze();
  bindTranscriptPicker();
  bindSettingsSubmit();
  await loadSettings();
  renderAnalysis();
  renderTranscriptPicker();
  updateRangePreview();
  connectSocket();
}

init();
