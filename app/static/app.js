const state = { analysis: null, selectedJobId: null, historyFilter: "all", settings: null, socket: null };
const qs = (selector) => document.querySelector(selector);

function statusClass(status) { return `status-chip status-${status}`; }
function progressBar(value = 0) { return `<div class="progress"><span style="width:${Math.max(4, value || 4)}%"></span></div>`; }

function formatJobMeta(job) {
  return [
    `Stage: ${job.stage || "-"}`,
    job.speed ? `Speed: ${job.speed}` : null,
    job.eta ? `ETA: ${job.eta}` : null,
    job.type === "playlist" ? `Items: ${job.item_completed || 0}/${job.item_total || 0}` : null,
  ].filter(Boolean).join(" • ");
}

function renderAnalysis() {
  const target = qs("#analysis-result");
  const status = qs("#analysis-status");
  if (!state.analysis) {
    target.innerHTML = `<div class="analysis-empty">Analyze a URL to inspect metadata before queueing.</div>`;
    status.textContent = "Waiting for URL";
    return;
  }
  const a = state.analysis;
  status.textContent = a.type === "playlist" ? `Playlist detected • ${a.item_count} items` : "Single item detected";
  target.innerHTML = `
    <div class="job-card">
      <div class="media-line">
        ${a.thumbnail ? `<img class="thumb large" src="${a.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder large">No Preview</div>`}
        <div>
          <h3>${a.title}</h3>
          <div class="job-meta">
            <span>${a.type}</span>
            <span>${a.item_count} item(s)</span>
            <span>${a.extractor || "source unknown"}</span>
          </div>
        </div>
      </div>
    </div>
    ${(a.entries || []).slice(0, 8).map((entry) => `
      <div class="item-row">
        <strong>${entry.index}. ${entry.title}</strong>
        <div class="muted">${entry.duration ? `${entry.duration}s` : "Duration unavailable"}</div>
      </div>
    `).join("")}
  `;
}

function renderDashboard(data) {
  qs("#worker-state").textContent = `Worker: ${data.worker_state}`;
  qs("#queue-size").textContent = `Queue: ${data.queue_size}`;
  qs("#system-status").innerHTML = `
    <div class="row"><strong>Worker</strong><span class="${statusClass(data.worker_state)}">${data.worker_state}</span></div>
    <div class="row"><strong>Queue Size</strong><span>${data.queue_size}</span></div>
    <div class="row"><strong>Errors</strong><span>${data.errors_count}</span></div>
  `;
  qs("#active-jobs").innerHTML = data.active_jobs.length ? data.active_jobs.map((job) => `
    <div class="job-card" data-job="${job.id}">
      <div class="card-header">
        <div class="media-line">
          ${job.analysis_json?.thumbnail ? `<img class="thumb" src="${job.analysis_json.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder">No Preview</div>`}
          <div>
            <h3>${job.title || job.url}</h3>
            <div class="${statusClass(job.status)}">${job.status}</div>
          </div>
        </div>
        <span>${job.type}</span>
      </div>
      ${progressBar(job.progress)}
      <div class="job-meta">${formatJobMeta(job)}</div>
    </div>
  `).join("") : `<div class="empty">No jobs yet. Add a URL above to begin.</div>`;
  qs("#queue-preview").innerHTML = data.queue_preview.length ? data.queue_preview.map((job) => `
    <div class="row" data-job="${job.id}">
      <strong>${job.title || job.url}</strong>
      <div class="row-meta">Position ${job.queue_position || "-"}</div>
    </div>
  `).join("") : `<div class="empty">Queue is empty.</div>`;
}

function renderQueue(jobs) {
  qs("#queue-list").innerHTML = jobs.length ? jobs.map(queueRow).join("") : `<div class="empty">Queue is empty.</div>`;
}

function renderHistory(jobs) {
  qs("#history-list").innerHTML = jobs.length ? jobs.map(historyRow).join("") : `<div class="empty">History is empty.</div>`;
}

function queueRow(job) {
  return `
    <div class="row" data-job="${job.id}">
      <div><strong>${job.title || job.url}</strong><div class="row-meta">${formatJobMeta(job)}</div></div>
      <div>${job.type}</div>
      <div class="${statusClass(job.status)}">${job.status}</div>
      <div class="row-actions">
        <button data-action="select" data-id="${job.id}">Details</button>
        <button data-action="cancel" data-id="${job.id}">Cancel</button>
        <button data-action="remove" data-id="${job.id}">Remove</button>
      </div>
    </div>
  `;
}

function historyRow(job) {
  return `
    <div class="row" data-job="${job.id}">
      <div class="media-line">
        ${job.analysis_json?.thumbnail ? `<img class="thumb" src="${job.analysis_json.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder">No Preview</div>`}
        <div><strong>${job.title || job.url}</strong><div class="row-meta">${job.finished_at || job.created_at || "-"}</div></div>
      </div>
      <div>${job.type}</div>
      <div class="${statusClass(job.status)}">${job.status}</div>
      <div class="row-actions">
        <button data-action="select" data-id="${job.id}">Details</button>
        <button data-action="retry" data-id="${job.id}">Retry</button>
        ${job.output_path ? `<button data-action="open-file" data-id="${job.id}">Open File</button>` : ""}
        ${job.output_path ? `<button data-action="open-folder" data-id="${job.id}">Open Folder</button>` : ""}
        ${job.output_path ? `<a class="download-btn" href="/api/download/${job.id}">Download</a>` : ""}
      </div>
    </div>
  `;
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
  renderDashboard(payload.dashboard);
  renderQueue(payload.queue || []);
  renderHistory(payload.history || []);
  if (payload.selected_job) {
    renderDetails(payload.selected_job);
  } else if (!state.selectedJobId) {
    qs("#details-title").textContent = "No job selected";
    qs("#details-body").innerHTML = `<div class="empty">Choose a job to inspect progress, playlist items, and logs.</div>`;
  }
  bindRowActions();
}

function renderDetails(job) {
  state.selectedJobId = job.id;
  qs("#details-title").textContent = job.title || job.url;
  const playlistBlock = job.playlist_items?.length ? `
    <div>
      <h3>Playlist Items</h3>
      <div class="playlist-list">
        ${job.playlist_items.map((item) => `
          <div class="item-row">
            <strong>${item.item_index + 1}. ${item.title}</strong>
            <div class="row-meta">
              <span class="${statusClass(item.status)}">${item.status}</span>
              <span>${item.progress || 0}%</span>
              ${item.output_path ? `<button data-action="open-item-file" data-id="${item.id}">Open File</button>` : ""}
              ${item.output_path ? `<button data-action="open-item-folder" data-id="${item.id}">Open Folder</button>` : ""}
              ${item.output_path ? `<a class="download-btn" href="/api/download/item/${item.id}">Download</a>` : ""}
            </div>
          </div>
        `).join("")}
      </div>
    </div>` : "";
  qs("#details-body").innerHTML = `
    <div class="job-card">
      <div class="card-header">
        <div class="media-line">
          ${job.analysis_json?.thumbnail ? `<img class="thumb large" src="${job.analysis_json.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder large">No Preview</div>`}
          <div><h3>${job.title || job.url}</h3><div class="${statusClass(job.status)}">${job.status}</div></div>
        </div>
      </div>
      ${progressBar(job.progress)}
      <div class="job-meta"><span>${job.stage || "-"}</span><span>${job.speed || "Speed unavailable"}</span><span>${job.eta || "ETA unavailable"}</span></div>
      <div class="details-actions">
        <button data-action="retry" data-id="${job.id}">Retry</button>
        <button data-action="cancel" data-id="${job.id}">Cancel</button>
        ${job.output_path ? `<button data-action="open-file" data-id="${job.id}">Open File</button>` : ""}
        ${job.output_path ? `<button data-action="open-folder" data-id="${job.id}">Open Folder</button>` : ""}
        ${job.output_path ? `<a class="download-btn" href="/api/download/${job.id}">Download file</a>` : ""}
      </div>
    </div>
    ${playlistBlock}
    <div>
      <h3>Logs</h3>
      <div class="log-list">
        ${(job.logs || []).length ? job.logs.map((log) => `<div class="log-row"><strong>${log.timestamp}</strong><div class="muted">${log.message}</div></div>`).join("") : `<div class="empty">No logs yet.</div>`}
      </div>
    </div>
  `;
  bindRowActions();
}

function pushSocketContext() {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
  state.socket.send(JSON.stringify({
    history_filter: state.historyFilter,
    selected_job_id: state.selectedJobId,
  }));
}

async function loadSettings() {
  const settings = await fetchJson("/api/settings");
  state.settings = settings;
  qs("#settings-form").innerHTML = `
    <div class="setting-row"><label for="output_directory">Output directory</label><input id="output_directory" name="output_directory" value="${settings.output_directory}"></div>
    <div class="setting-row"><label for="default_mode">Default mode</label><select id="default_mode" name="default_mode"><option value="video" ${settings.default_mode === "video" ? "selected" : ""}>Video</option><option value="audio" ${settings.default_mode === "audio" ? "selected" : ""}>Audio</option></select></div>
    <div class="setting-row"><label for="quality">Quality / format</label><input id="quality" name="quality" value="${settings.quality}"></div>
    <div class="setting-row"><label for="retry_enabled">Retry enabled</label><select id="retry_enabled" name="retry_enabled"><option value="true" ${settings.retry_enabled ? "selected" : ""}>Enabled</option><option value="false" ${!settings.retry_enabled ? "selected" : ""}>Disabled</option></select></div>
    <div class="setting-row"><label for="retry_count">Retry count</label><input id="retry_count" name="retry_count" type="number" min="0" value="${settings.retry_count}"></div>
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
      if (action === "select") {
        state.selectedJobId = id;
        pushSocketContext();
        return;
      }
      if (action === "open-file") {
        await fetchJson(`/api/open/job/${id}`, { method: "POST" });
        return;
      }
      if (action === "open-folder") {
        await fetchJson(`/api/open/job/${id}/folder`, { method: "POST" });
        return;
      }
      if (action === "open-item-file") {
        await fetchJson(`/api/open/item/${id}`, { method: "POST" });
        return;
      }
      if (action === "open-item-folder") {
        await fetchJson(`/api/open/item/${id}/folder`, { method: "POST" });
        return;
      }
      if (action === "retry") await fetchJson(`/api/jobs/${id}/retry`, { method: "POST" });
      if (action === "cancel") await fetchJson(`/api/jobs/${id}/cancel`, { method: "POST" });
      if (action === "remove") await fetchJson(`/api/jobs/${id}`, { method: "DELETE" });
      if (action === "remove" && state.selectedJobId === id) {
        state.selectedJobId = null;
      }
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
    try {
      const payload = await fetchJson("/api/analyze", { method: "POST", body: JSON.stringify({ url }) });
      state.analysis = payload.analysis;
      renderAnalysis();
    } catch (error) {
      qs("#analysis-status").textContent = error.message;
      qs("#analysis-result").innerHTML = `<div class="empty">${error.message}</div>`;
    }
  });
  qs("#queue-btn").addEventListener("click", async () => {
    const url = qs("#url-input").value.trim();
    if (!url) return;
    try {
      const payload = await fetchJson("/api/jobs", {
        method: "POST",
        body: JSON.stringify({
          url,
          mode: state.settings?.default_mode || "video",
          quality: state.settings?.quality || "bestvideo*+bestaudio/best",
        }),
      });
      state.selectedJobId = payload.job.id;
      pushSocketContext();
    } catch (error) {
      qs("#analysis-status").textContent = error.message;
    }
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
  socket.onclose = () => {
    setTimeout(connectSocket, 1500);
  };
}

async function init() {
  bindNavigation();
  bindFilters();
  bindAnalyze();
  bindSettingsSubmit();
  await loadSettings();
  renderAnalysis();
  connectSocket();
}

init();
