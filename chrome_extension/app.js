const FALLBACK = {
  defaultMode: "video",
  quality: "best",
  defaultTranscribeAudio: false,
  defaultTranscriptionLanguage: "auto",
  defaultTranscriptSecondMarks: true
};

let pollTimer = null;
let currentAnalysis = null;

function qs(id) {
  return document.getElementById(id);
}

function setStatus(message, isError = false) {
  const node = qs("status");
  node.textContent = message;
  node.className = isError ? "status error" : "status ok";
}

async function loadState() {
  const params = new URLSearchParams(window.location.search);
  const settings = await chrome.storage.local.get(FALLBACK);
  qs("url").value = params.get("url") || "";
  qs("mode").value = settings.defaultMode || FALLBACK.defaultMode;
  qs("quality").value = settings.quality || FALLBACK.quality;
  qs("transcribeAudio").checked = Boolean(settings.defaultTranscribeAudio);
  qs("transcriptionLanguage").value = settings.defaultTranscriptionLanguage || FALLBACK.defaultTranscriptionLanguage;
  qs("transcriptSecondMarks").checked = Boolean(settings.defaultTranscriptSecondMarks);
  qs("transcriptionLanguage").disabled = !qs("transcribeAudio").checked;
  qs("transcriptSecondMarks").disabled = !qs("transcribeAudio").checked;
  await refreshStatuses();
  const { history = [] } = await chrome.storage.local.get({ history: [] });
  qs("history").innerHTML = history.length ? history.map((item) => `
    <div class="history-row">
      <div class="history-top">
        ${item.thumbnail ? `<img class="thumb mini" src="${item.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder mini">No Preview</div>`}
        <div>
          <strong>${item.title || item.url}</strong>
          <div class="muted">${item.mode} • ${item.status || "started"} ${item.progress ? `• ${item.progress}%` : ""} ${item.transcribeAudio ? "• transcript" : ""}</div>
          <div class="muted">${item.lastMessage || item.createdAt}</div>
        </div>
      </div>
      <div class="history-actions">
        <button data-action="job-file" data-job-id="${item.id}">Open File</button>
        <button data-action="job-folder" data-job-id="${item.id}">Open Folder</button>
      </div>
    </div>
  `).join("") : `<div class="muted">История пока пустая.</div>`;
  bindHistoryActions();
}

qs("transcribeAudio").addEventListener("change", () => {
  qs("transcriptionLanguage").disabled = !qs("transcribeAudio").checked;
  qs("transcriptSecondMarks").disabled = !qs("transcribeAudio").checked;
});

function renderPreview(analysis) {
  const node = qs("preview");
  if (!analysis) {
    node.classList.add("hidden");
    node.innerHTML = "";
    return;
  }
  node.classList.remove("hidden");
  node.innerHTML = `
    <div class="preview-line">
      ${analysis.thumbnail ? `<img class="thumb" src="${analysis.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder">No Preview</div>`}
      <div>
        <strong>${analysis.title}</strong>
        <div class="muted">${analysis.type} • ${analysis.itemCount} item(s)</div>
        <div class="muted">${analysis.extractor || "source unknown"} ${analysis.duration ? `• ${analysis.duration}s` : ""}</div>
      </div>
    </div>
    ${analysis.entries?.length ? `
      <div class="playlist-preview">
        ${analysis.entries.map((entry) => `
          <div class="playlist-row">
            ${entry.thumbnail ? `<img class="thumb mini" src="${entry.thumbnail}" alt="thumbnail">` : `<div class="thumb placeholder mini">Item</div>`}
            <div>
              <strong>${entry.title}</strong>
              <div class="muted">${entry.duration ? `${entry.duration}s` : "Duration unavailable"}</div>
            </div>
          </div>
        `).join("")}
      </div>
    ` : ""}
  `;
}

async function refreshStatuses() {
  await chrome.runtime.sendMessage({ action: "status" });
}

async function analyzeCurrentUrl() {
  const url = qs("url").value.trim();
  if (!url) {
    setStatus("Сначала вставьте URL", true);
    return;
  }
  const response = await chrome.runtime.sendMessage({ action: "analyze", url });
  if (!response.ok) {
    currentAnalysis = null;
    renderPreview(null);
    setStatus(response.error, true);
    return;
  }
  currentAnalysis = response.analysis;
  renderPreview(response.analysis);
  setStatus("Анализ готов");
}

qs("download").addEventListener("click", async () => {
  try {
    const response = await chrome.runtime.sendMessage({
      action: "queueDownload",
      source: "full-mode",
      url: qs("url").value.trim(),
      mode: qs("mode").value,
      quality: qs("quality").value.trim(),
      transcribeAudio: qs("transcribeAudio").checked,
      transcriptionLanguage: qs("transcriptionLanguage").value,
      transcriptSecondMarks: qs("transcriptSecondMarks").checked,
      metadata: currentAnalysis ? {
        title: currentAnalysis.title,
        thumbnail: currentAnalysis.thumbnail
      } : null
    });
    setStatus(response.ok ? (response.message || "Загрузка запущена") : response.error, !response.ok);
    await chrome.storage.local.set({
      quality: qs("quality").value.trim(),
      defaultMode: qs("mode").value,
      defaultTranscribeAudio: qs("transcribeAudio").checked,
      defaultTranscriptionLanguage: qs("transcriptionLanguage").value,
      defaultTranscriptSecondMarks: qs("transcriptSecondMarks").checked
    });
    await loadState();
  } catch (error) {
    setStatus(error.message || "Ошибка запуска", true);
  }
});

function bindHistoryActions() {
  document.querySelectorAll("[data-action='job-file']").forEach((button) => {
    button.onclick = async () => {
      const response = await chrome.runtime.sendMessage({ action: "openJobFile", jobId: button.dataset.jobId });
      setStatus(response.ok ? "Файл открыт" : response.error, !response.ok);
    };
  });
  document.querySelectorAll("[data-action='job-folder']").forEach((button) => {
    button.onclick = async () => {
      const response = await chrome.runtime.sendMessage({ action: "openJobFolder", jobId: button.dataset.jobId });
      setStatus(response.ok ? "Папка открыта" : response.error, !response.ok);
    };
  });
}

qs("probe").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ action: "probe" });
  setStatus(response.ok ? response.message : response.error, !response.ok);
});

qs("analyze").addEventListener("click", analyzeCurrentUrl);

qs("openFolder").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ action: "openFolder" });
  setStatus(response.ok ? "Папка открыта" : response.error, !response.ok);
});

qs("openLastFile").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ action: "openLastFile" });
  setStatus(response.ok ? "Последний файл открыт" : response.error, !response.ok);
});

qs("openOptions").addEventListener("click", () => chrome.runtime.openOptionsPage());

loadState().then(() => {
  const params = new URLSearchParams(window.location.search);
  if (params.get("url")) {
    analyzeCurrentUrl().catch(() => {});
  }
  pollTimer = setInterval(async () => {
    await loadState();
  }, 3000);
});
