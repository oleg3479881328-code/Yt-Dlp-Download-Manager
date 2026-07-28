const DEFAULTS = {
  nativeHostName: "com.oleg.ytdlp",
  defaultMode: "video",
  quality: "best",
  outputDirectory: "C:\\yt-dlp\\DOWNLOADS",
  ytDlpPath: "C:\\yt-dlp\\yt-dlp.exe",
  ffmpegPath: "C:\\yt-dlp\\ffmpeg.exe",
  autoUpdateYtDlp: true,
  updateChannel: "nightly",
  cookiesBrowser: "none",
  impersonateBrowser: false,
  defaultTranscribeAudio: false,
  defaultTranscriptionLanguage: "auto",
  defaultTranscriptSecondMarks: true
};

const BOOLEAN_FIELDS = new Set([
  "defaultTranscribeAudio",
  "defaultTranscriptSecondMarks",
  "autoUpdateYtDlp",
  "impersonateBrowser",
]);

function setStatus(message, isError = false) {
  const node = document.getElementById("status");
  node.textContent = message;
  node.className = isError ? "status error" : "status ok";
}

async function loadSettings() {
  const settings = await chrome.storage.local.get(DEFAULTS);
  for (const [key, value] of Object.entries(DEFAULTS)) {
    const node = document.getElementById(key);
    if (BOOLEAN_FIELDS.has(key)) {
      node.checked = Boolean(settings[key] ?? value);
      continue;
    }
    node.value = settings[key] ?? value;
  }
}

async function saveSettings() {
  const payload = {};
  for (const key of Object.keys(DEFAULTS)) {
    const node = document.getElementById(key);
    payload[key] = BOOLEAN_FIELDS.has(key) ? node.checked : node.value;
  }
  await chrome.storage.local.set(payload);
  setStatus("Настройки сохранены");
}

document.getElementById("save").addEventListener("click", saveSettings);
document.getElementById("probe").addEventListener("click", async () => {
  await saveSettings();
  const response = await chrome.runtime.sendMessage({ action: "probe" });
  setStatus(response.ok ? response.message : response.error, !response.ok);
});
document.getElementById("updateYtDlp").addEventListener("click", async () => {
  await saveSettings();
  setStatus("Обновляю yt-dlp...");
  const response = await chrome.runtime.sendMessage({ action: "updateYtDlp" });
  setStatus(
    response.ok
      ? `yt-dlp обновлён: ${response.versionBefore} → ${response.versionAfter}`
      : response.error,
    !response.ok
  );
});
document.getElementById("openFolder").addEventListener("click", async () => {
  await saveSettings();
  const response = await chrome.runtime.sendMessage({ action: "openFolder" });
  setStatus(response.ok ? "Папка открыта" : response.error, !response.ok);
});

loadSettings();
