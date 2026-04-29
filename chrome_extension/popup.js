const DEFAULTS = {
  workMode: "mini",
  defaultMode: "video"
};

async function loadSettings() {
  const settings = await chrome.storage.local.get(DEFAULTS);
  document.getElementById("workMode").value = settings.workMode;
  document.getElementById("defaultMode").value = settings.defaultMode;
}

async function saveSettings() {
  await chrome.storage.local.set({
    workMode: document.getElementById("workMode").value,
    defaultMode: document.getElementById("defaultMode").value
  });
}

function setStatus(message, isError = false) {
  const node = document.getElementById("status");
  node.textContent = message;
  node.className = isError ? "status error" : "status ok";
}

async function refreshMiniHistory() {
  await chrome.runtime.sendMessage({ action: "status" });
  const { history = [] } = await chrome.storage.local.get({ history: [] });
  const top = history.slice(0, 3);
  document.getElementById("miniHistory").innerHTML = top.length ? top.map((item) => `
    <div class="history-row compact">
      <strong>${item.title || item.url}</strong>
      <div class="muted">${item.status || "started"} ${item.progress ? `• ${item.progress}%` : ""}</div>
    </div>
  `).join("") : `<div class="muted">Пока пусто.</div>`;
}

document.getElementById("workMode").addEventListener("change", async () => {
  await saveSettings();
  setStatus("Режим сохранен");
});

document.getElementById("defaultMode").addEventListener("change", async () => {
  await saveSettings();
  setStatus("Режим загрузки сохранен");
});

document.getElementById("openFull").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ action: "openFullPage" });
  window.close();
});

document.getElementById("openFolder").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ action: "openFolder" });
  setStatus(response.ok ? "Папка открыта" : (response.error || "Не удалось открыть папку"), !response.ok);
});

document.getElementById("openLastFile").addEventListener("click", async () => {
  const response = await chrome.runtime.sendMessage({ action: "openLastFile" });
  setStatus(response.ok ? "Последний файл открыт" : (response.error || "Не удалось открыть файл"), !response.ok);
});

document.getElementById("openOptions").addEventListener("click", () => chrome.runtime.openOptionsPage());

loadSettings().then(refreshMiniHistory);
