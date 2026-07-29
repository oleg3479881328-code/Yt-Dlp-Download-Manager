const grid = document.getElementById("video-grid");
const countLabel = document.getElementById("video-count");
const secureNote = document.getElementById("secure-note");
const template = document.getElementById("video-card-template");
const toast = document.getElementById("toast");
const refreshButton = document.getElementById("refresh-videos");

const tokenFromUrl = new URLSearchParams(window.location.search).get("token") || "";
if (tokenFromUrl) sessionStorage.setItem("reviewPortalToken", tokenFromUrl);
const token = tokenFromUrl || sessionStorage.getItem("reviewPortalToken") || "";

function apiUrl(path) {
  const url = new URL(path, window.location.origin);
  if (token) url.searchParams.set("token", token);
  return url.toString();
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("X-Review-Token", token);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl(path), { ...options, headers });
  if (!response.ok) {
    let detail = `Ошибка ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = `toast visible${isError ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = "toast"; }, 2600);
}

function formatTime(ms) {
  if (ms == null) return "";
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  const tenths = Math.floor((totalSeconds - Math.floor(totalSeconds)) * 10);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${tenths}`;
}

function chooseRecorderMime() {
  if (!window.MediaRecorder) return "";
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return options.find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const value = String(reader.result || "");
      resolve(value.includes(",") ? value.split(",", 2)[1] : value);
    };
    reader.onerror = () => reject(reader.error || new Error("Не удалось прочитать голосовую запись"));
    reader.readAsDataURL(blob);
  });
}

function stopOtherVideos(activeVideo) {
  document.querySelectorAll("video").forEach((video) => {
    if (video !== activeVideo && !video.paused) video.pause();
  });
}

function renderAttachments(container, state) {
  container.replaceChildren();
  if (state.timecodeMs != null) {
    const chip = document.createElement("span");
    chip.className = "attachment-chip";
    chip.innerHTML = `📍 ${formatTime(state.timecodeMs)} <button type="button" aria-label="Убрать таймкод">×</button>`;
    chip.querySelector("button").addEventListener("click", () => {
      state.timecodeMs = null;
      state.pinButton.setAttribute("aria-pressed", "false");
      state.pinButton.querySelector(".tool-label").textContent = "Отметить момент";
      renderAttachments(container, state);
    });
    container.append(chip);
  }
  if (state.audioBlob) {
    const chip = document.createElement("span");
    chip.className = "attachment-chip";
    chip.innerHTML = `🎙️ Голос записан · ${Math.max(1, Math.round(state.audioDurationMs / 1000))} сек <button type="button" aria-label="Удалить голос">×</button>`;
    chip.querySelector("button").addEventListener("click", () => {
      state.audioBlob = null;
      state.audioDurationMs = 0;
      renderAttachments(container, state);
    });
    container.append(chip);
  }
}

function updateRecordingButton(state, active) {
  const label = state.micButton.querySelector(".tool-label");
  state.micButton.classList.toggle("recording", active);
  state.micButton.setAttribute("aria-pressed", active ? "true" : "false");
  label.textContent = active ? "Остановить запись" : "Записать голос";
}

async function startRecording(state, attachments, status) {
  if (!window.isSecureContext) {
    status.textContent = "Микрофон работает только на HTTPS или localhost.";
    status.className = "card-status error";
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    status.textContent = "Этот браузер не поддерживает запись голоса.";
    status.className = "card-status error";
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mimeType = chooseRecorderMime();
  const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
  state.recorder = recorder;
  state.recordingChunks = [];
  state.recordingStartedAt = Date.now();
  state.audioMime = recorder.mimeType || mimeType || "audio/webm";

  recorder.addEventListener("dataavailable", (event) => {
    if (event.data?.size) state.recordingChunks.push(event.data);
  });
  recorder.addEventListener("stop", () => {
    state.audioDurationMs = Date.now() - state.recordingStartedAt;
    state.audioBlob = new Blob(state.recordingChunks, { type: state.audioMime });
    stream.getTracks().forEach((track) => track.stop());
    state.recorder = null;
    updateRecordingButton(state, false);
    renderAttachments(attachments, state);
    status.textContent = "Голос записан. Нажмите «Отправить».";
    status.className = "card-status";
  });
  recorder.start(250);
  updateRecordingButton(state, true);
  status.textContent = "Идёт запись…";
  status.className = "card-status";
}

function stopRecording(state) {
  if (state.recorder && state.recorder.state !== "inactive") state.recorder.stop();
}

function buildCard(video, index) {
  const fragment = template.content.cloneNode(true);
  const card = fragment.querySelector(".video-card");
  const player = fragment.querySelector("video");
  const title = fragment.querySelector("h2");
  const number = fragment.querySelector(".video-number");
  const textarea = fragment.querySelector("textarea");
  const pinButton = fragment.querySelector(".pin-button");
  const micButton = fragment.querySelector(".mic-button");
  const sendButton = fragment.querySelector(".send-button");
  const attachments = fragment.querySelector(".attachment-row");
  const status = fragment.querySelector(".card-status");

  title.textContent = video.title;
  number.textContent = `${index + 1}`;
  player.dataset.src = apiUrl(`/api/review/videos/${encodeURIComponent(video.video_id)}/stream`);
  player.setAttribute("aria-label", video.title);

  const state = {
    video,
    player,
    pinButton,
    micButton,
    timecodeMs: null,
    audioBlob: null,
    audioDurationMs: 0,
    audioMime: "audio/webm",
    recorder: null,
    recordingChunks: [],
    recordingStartedAt: 0,
  };

  player.addEventListener("play", () => stopOtherVideos(player));

  pinButton.addEventListener("click", () => {
    player.pause();
    state.timecodeMs = Math.round((player.currentTime || 0) * 1000);
    pinButton.setAttribute("aria-pressed", "true");
    pinButton.querySelector(".tool-label").textContent = formatTime(state.timecodeMs);
    renderAttachments(attachments, state);
    status.textContent = `Отмечен момент ${formatTime(state.timecodeMs)}.`;
    status.className = "card-status";
  });

  micButton.addEventListener("click", async () => {
    try {
      if (state.recorder) {
        stopRecording(state);
      } else {
        await startRecording(state, attachments, status);
      }
    } catch (error) {
      updateRecordingButton(state, false);
      status.textContent = error?.name === "NotAllowedError" ? "Разрешите доступ к микрофону в браузере." : (error.message || "Не удалось включить микрофон.");
      status.className = "card-status error";
    }
  });

  sendButton.addEventListener("click", async () => {
    const text = textarea.value.trim();
    if (!text && !state.audioBlob) {
      status.textContent = "Напишите замечание или запишите голос.";
      status.className = "card-status error";
      return;
    }
    if (state.recorder) {
      status.textContent = "Сначала остановите запись голоса.";
      status.className = "card-status error";
      return;
    }

    sendButton.disabled = true;
    pinButton.disabled = true;
    micButton.disabled = true;
    status.textContent = "Отправляю замечание…";
    status.className = "card-status";

    try {
      const audioBase64 = state.audioBlob ? await blobToBase64(state.audioBlob) : null;
      await apiFetch("/api/review/comments", {
        method: "POST",
        body: JSON.stringify({
          video_id: video.video_id,
          text,
          timecode_ms: state.timecodeMs,
          audio_base64: audioBase64,
          audio_mime: state.audioBlob?.type || state.audioMime || null,
          author: "Ольга",
        }),
      });
      textarea.value = "";
      state.timecodeMs = null;
      state.audioBlob = null;
      state.audioDurationMs = 0;
      pinButton.setAttribute("aria-pressed", "false");
      pinButton.querySelector(".tool-label").textContent = "Отметить момент";
      renderAttachments(attachments, state);
      status.textContent = "Замечание отправлено.";
      status.className = "card-status success";
      showToast(`Отправлено: ${video.title}`);
    } catch (error) {
      status.textContent = error.message || "Не удалось отправить замечание.";
      status.className = "card-status error";
      showToast(status.textContent, true);
    } finally {
      sendButton.disabled = false;
      pinButton.disabled = false;
      micButton.disabled = false;
    }
  });

  card.dataset.videoId = video.video_id;
  return fragment;
}

function activateLazyPlayers() {
  const videos = [...document.querySelectorAll("video[data-src]")];
  if (!("IntersectionObserver" in window)) {
    videos.forEach((video) => { video.src = video.dataset.src; delete video.dataset.src; });
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const video = entry.target;
      video.src = video.dataset.src;
      delete video.dataset.src;
      observer.unobserve(video);
    });
  }, { rootMargin: "600px 0px" });
  videos.forEach((video) => observer.observe(video));
}

async function loadVideos() {
  countLabel.textContent = "Загрузка роликов…";
  grid.innerHTML = "";
  try {
    const payload = await apiFetch("/api/review/videos");
    countLabel.textContent = `${payload.count} ${payload.count === 1 ? "ролик" : "роликов"}`;
    if (!payload.videos.length) {
      grid.innerHTML = '<div class="empty-state">В папке пока нет роликов для согласования.</div>';
      return;
    }
    const batch = document.createDocumentFragment();
    payload.videos.forEach((video, index) => batch.append(buildCard(video, index)));
    grid.append(batch);
    activateLazyPlayers();
  } catch (error) {
    countLabel.textContent = "Не удалось загрузить ролики";
    grid.innerHTML = `<div class="empty-state">${error.message || "Ошибка загрузки"}</div>`;
    showToast(error.message || "Ошибка загрузки", true);
  }
}

secureNote.textContent = window.isSecureContext ? "Микрофон доступен" : "Для микрофона нужен HTTPS";
refreshButton.addEventListener("click", loadVideos);
loadVideos();
