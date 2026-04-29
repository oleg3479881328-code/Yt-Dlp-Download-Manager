const DEFAULT_SETTINGS = {
  nativeHostName: "com.oleg.ytdlp",
  workMode: "mini",
  defaultMode: "video",
  quality: "best",
  outputDirectory: "C:\\yt-dlp\\DOWNLOADS",
  ytDlpPath: "C:\\yt-dlp\\yt-dlp.exe",
  ffmpegPath: "C:\\yt-dlp\\ffmpeg.exe",
  saveHistory: true,
  defaultTranscribeAudio: false,
  defaultTranscriptionLanguage: "auto",
  defaultTranscriptSecondMarks: true
};

async function getSettings() {
  const stored = await chrome.storage.local.get(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS, ...stored };
}

function createMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "download-with-ytdlp",
      title: "Скачать через yt-dlp",
      contexts: ["link", "video", "page"]
    });
  });
}

async function appendHistory(entry) {
  const { history = [] } = await chrome.storage.local.get({ history: [] });
  history.unshift(entry);
  await chrome.storage.local.set({ history: history.slice(0, 50) });
}

async function replaceHistoryEntry(jobId, patch) {
  const { history = [] } = await chrome.storage.local.get({ history: [] });
  const next = history.map((item) => item.id === jobId ? { ...item, ...patch } : item);
  await chrome.storage.local.set({ history: next });
}

function extractUrl(info, tab) {
  return info.linkUrl || info.srcUrl || info.pageUrl || tab?.url || "";
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: chrome.runtime.getURL("icons/notify-128.png"),
    title,
    message
  }).catch((error) => {
    console.warn("Notification failed:", error);
  });
}

async function callNative(message) {
  const settings = await getSettings();
  return chrome.runtime.sendNativeMessage(settings.nativeHostName, message);
}

async function callNativeWithPort(message) {
  const settings = await getSettings();
  return await new Promise((resolve, reject) => {
    const port = chrome.runtime.connectNative(settings.nativeHostName);
    let settled = false;

    const finish = (callback) => (value) => {
      if (settled) {
        return;
      }
      settled = true;
      try {
        port.disconnect();
      } catch (_error) {
      }
      callback(value);
    };

    port.onMessage.addListener(finish(resolve));
    port.onDisconnect.addListener(() => {
      const error = chrome.runtime.lastError;
      if (settled) {
        return;
      }
      settled = true;
      reject(new Error(error?.message || "Native host disconnected before responding"));
    });

    try {
      port.postMessage(message);
    } catch (error) {
      finish(reject)(error);
    }
  });
}

async function queueDownload(url, source = "manual", modeOverride = null, qualityOverride = null, metadata = null, transcribeOverride = null, transcriptionLanguageOverride = null, transcriptSecondMarksOverride = null, nativeCall = callNative) {
  if (!url) {
    throw new Error("URL not found");
  }
  const settings = await getSettings();
  const transcribeAudio = transcribeOverride ?? settings.defaultTranscribeAudio;
  const transcriptionLanguage = transcriptionLanguageOverride ?? settings.defaultTranscriptionLanguage;
  const transcriptSecondMarks = transcriptSecondMarksOverride ?? settings.defaultTranscriptSecondMarks;
  const response = await nativeCall({
    action: "download",
    url,
    mode: modeOverride || settings.defaultMode,
    quality: qualityOverride || settings.quality,
    transcribeAudio,
    transcriptionLanguage,
    transcriptSecondMarks,
    title: metadata?.title || null,
    thumbnail: metadata?.thumbnail || null,
    outputDirectory: settings.outputDirectory,
    ytDlpPath: settings.ytDlpPath,
    ffmpegPath: settings.ffmpegPath
  });
  if (!response?.ok) {
    throw new Error(response?.error || "Native host error");
  }
  if (settings.saveHistory) {
    const entry = {
      id: response.jobId,
      url,
      source,
      mode: modeOverride || settings.defaultMode,
      createdAt: new Date().toISOString(),
      outputDirectory: settings.outputDirectory,
      status: "started",
      transcribeAudio,
      transcriptionLanguage,
      logPath: response.logPath,
      title: metadata?.title || null,
      thumbnail: metadata?.thumbnail || null
    };
    await appendHistory(entry);
  }
  notify("yt-dlp", response.message || "Download started");
  return response;
}

async function analyzeUrl(url) {
  const settings = await getSettings();
  return callNative({
    action: "analyze",
    url,
    ytDlpPath: settings.ytDlpPath
  });
}

async function fetchStatuses(jobId = null) {
  const settings = await getSettings();
  const response = await callNative({
    action: "status",
    jobId,
    outputDirectory: settings.outputDirectory
  });
  if (response.ok && Array.isArray(response.jobs)) {
    for (const job of response.jobs) {
      await replaceHistoryEntry(job.jobId, {
        status: job.status,
        progress: job.progress,
        outputPath: job.outputPath,
        updatedAt: job.updatedAt,
        lastMessage: job.lastMessage,
        thumbnail: job.thumbnail
      });
    }
  }
  return response;
}

async function handleContextAction(info, tab) {
  const url = extractUrl(info, tab);
  const settings = await getSettings();
  if (settings.workMode === "full") {
    const page = chrome.runtime.getURL(`app.html?url=${encodeURIComponent(url)}`);
    await chrome.tabs.create({ url: page });
    return;
  }
  try {
    await queueDownload(
      url,
      "context-menu",
      null,
      null,
      null,
      null,
      null,
      null,
      callNativeWithPort
    );
  } catch (error) {
    notify("yt-dlp error", error.message || "Failed to start download");
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  const current = await chrome.storage.local.get(DEFAULT_SETTINGS);
  await chrome.storage.local.set({ ...DEFAULT_SETTINGS, ...current });
  createMenus();
});

chrome.runtime.onStartup.addListener(createMenus);
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "download-with-ytdlp") {
    handleContextAction(info, tab);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    try {
      if (message.action === "queueDownload") {
        const result = await queueDownload(
          message.url,
          message.source || "popup",
          message.mode || null,
          message.quality || null,
          message.metadata || null,
          message.transcribeAudio ?? null,
          message.transcriptionLanguage ?? null,
          message.transcriptSecondMarks ?? null
        );
        sendResponse(result);
        return;
      }
      if (message.action === "openFullPage") {
        const page = chrome.runtime.getURL(`app.html${message.url ? `?url=${encodeURIComponent(message.url)}` : ""}`);
        await chrome.tabs.create({ url: page });
        sendResponse({ ok: true });
        return;
      }
      if (message.action === "openFolder") {
        const settings = await getSettings();
        const response = await callNative({
          action: "open_folder",
          outputDirectory: settings.outputDirectory
        });
        sendResponse(response);
        return;
      }
      if (message.action === "analyze") {
        sendResponse(await analyzeUrl(message.url));
        return;
      }
      if (message.action === "status") {
        sendResponse(await fetchStatuses(message.jobId || null));
        return;
      }
      if (message.action === "openLastFile") {
        const settings = await getSettings();
        sendResponse(await callNative({
          action: "open_last_file",
          outputDirectory: settings.outputDirectory
        }));
        return;
      }
      if (message.action === "openJobFile") {
        const settings = await getSettings();
        sendResponse(await callNative({
          action: "open_job_file",
          outputDirectory: settings.outputDirectory,
          jobId: message.jobId
        }));
        return;
      }
      if (message.action === "openJobFolder") {
        const settings = await getSettings();
        sendResponse(await callNative({
          action: "open_job_folder",
          outputDirectory: settings.outputDirectory,
          jobId: message.jobId
        }));
        return;
      }
      if (message.action === "probe") {
        const settings = await getSettings();
        const response = await callNative({
          action: "probe",
          ytDlpPath: settings.ytDlpPath,
          ffmpegPath: settings.ffmpegPath,
          outputDirectory: settings.outputDirectory
        });
        sendResponse(response);
        return;
      }
      sendResponse({ ok: false, error: "Unsupported action" });
    } catch (error) {
      sendResponse({ ok: false, error: error.message || "Unknown error" });
    }
  })();
  return true;
});
