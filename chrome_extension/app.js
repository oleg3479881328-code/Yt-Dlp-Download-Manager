const FALLBACK = {
  nativeHostName: "com.oleg.ytdlp",
  outputDirectory: "C:\\yt-dlp\\DOWNLOADS",
  defaultMode: "video",
  quality: "best",
  defaultTranscribeAudio: false,
  defaultTranscriptionLanguage: "auto",
  defaultTranscriptSecondMarks: true
};

const UPLOAD_CHUNK_BYTES = 256 * 1024;

let pollTimer = null;
let currentAnalysis = null;

function qs(id) {
  return document.getElementById(id);
}

function syncTranscriptionControls() {
  const hasLocalFile = Boolean(qs("localFile")?.files?.length);
  const enabled = qs("transcribeAudio").checked || hasLocalFile;
  qs("transcriptionLanguage").disabled = !enabled;
  qs("transcriptSecondMarks").disabled = !enabled;
}

function setStatus(message, isError = false) {
  const node = qs("status");
  node.textContent = message;
  node.className = isError ? "status error" : "status ok";
}

function bytesToBase64(bytes) {
  let binary = "";
  const step = 0x8000;
  for (let index = 0; index < bytes.length; index += step) {
    const slice = bytes.subarray(index, index + step);
    binary += String.fromCharCode(...slice);
  }
  return btoa(binary);
}

function sendNativePortMessage(port, payload) {
  return new Promise((resolve, reject) => {
    const onMessage = (message) => {
      cleanup();
      resolve(message);
    };
    const onDisconnect = () => {
      cleanup();
      reject(new Error(chrome.runtime.lastError?.message || "Native host disconnected"));
    };
    const cleanup = () => {
      port.onMessage.removeListener(onMessage);
      port.onDisconnect.removeListener(onDisconnect);
    };
    port.onMessage.addListener(onMessage);
    port.onDisconnect.addListener(onDisconnect);
    port.postMessage(payload);
  });
}

async function appendUploadedHistory(entry) {
  const { history = [] } = await chrome.storage.local.get({ history: [] });
  history.unshift(entry);
  await chrome.storage.local.set({ history: history.slice(0, 50) });
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
  syncTranscriptionControls();
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
  syncTranscriptionControls();
});

qs("localFile").addEventListener("change", () => {
  syncTranscriptionControls();
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

qs("transcribeLocalFile").addEventListener("click", async () => {
  const file = qs("localFile").files?.[0];
  if (!file) {
    setStatus("Сначала выберите аудио- или видеофайл", true);
    return;
  }

  const settings = await chrome.storage.local.get(FALLBACK);
  const port = chrome.runtime.connectNative(settings.nativeHostName || FALLBACK.nativeHostName);

  try {
    setStatus("Подготавливаю загрузку файла...");
    const startResponse = await sendNativePortMessage(port, {
      action: "upload_transcribe_start",
      filename: file.name,
      size: file.size,
      mimeType: file.type,
      outputDirectory: settings.outputDirectory || FALLBACK.outputDirectory,
      transcriptSecondMarks: qs("transcriptSecondMarks").checked,
      transcriptionLanguage: qs("transcriptionLanguage").value
    });
    if (!startResponse.ok) {
      throw new Error(startResponse.error || "Не удалось начать передачу файла");
    }

    let uploadedBytes = 0;
    for (let offset = 0; offset < file.size; offset += UPLOAD_CHUNK_BYTES) {
      const chunkBuffer = await file.slice(offset, offset + UPLOAD_CHUNK_BYTES).arrayBuffer();
      const chunkBytes = new Uint8Array(chunkBuffer);
      uploadedBytes += chunkBytes.length;
      const chunkResponse = await sendNativePortMessage(port, {
        action: "upload_transcribe_chunk",
        uploadId: startResponse.uploadId,
        chunkBase64: bytesToBase64(chunkBytes)
      });
      if (!chunkResponse.ok) {
        throw new Error(chunkResponse.error || "Ошибка передачи файла");
      }
      const percent = file.size ? Math.min(100, Math.round((uploadedBytes / file.size) * 100)) : 100;
      setStatus(`Передача файла в native host: ${percent}%`);
    }

    const finishResponse = await sendNativePortMessage(port, {
      action: "upload_transcribe_finish",
      uploadId: startResponse.uploadId
    });
    if (!finishResponse.ok) {
      throw new Error(finishResponse.error || "Не удалось поставить транскрибацию в очередь");
    }

    await appendUploadedHistory({
      id: finishResponse.jobId,
      url: "",
      source: "local-upload",
      mode: "local-file",
      createdAt: new Date().toISOString(),
      outputDirectory: finishResponse.outputDirectory || settings.outputDirectory || FALLBACK.outputDirectory,
      status: "started",
      progress: 0,
      transcribeAudio: true,
      transcriptionLanguage: qs("transcriptionLanguage").value,
      transcriptSecondMarks: qs("transcriptSecondMarks").checked,
      logPath: finishResponse.logPath,
      outputPath: finishResponse.outputPath,
      title: file.name,
      thumbnail: null,
      lastMessage: "Локальный файл поставлен в очередь на транскрибацию"
    });

    setStatus("Файл передан. Транскрибация запущена.");
    await loadState();
  } catch (error) {
    setStatus(error.message || "Ошибка загрузки файла", true);
  } finally {
    try {
      port.disconnect();
    } catch (_error) {
    }
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
