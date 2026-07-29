const list = document.getElementById("comment-list");
const countLabel = document.getElementById("comment-count");
const filter = document.getElementById("status-filter");
const refreshButton = document.getElementById("refresh-comments");
const template = document.getElementById("comment-card-template");
const toast = document.getElementById("toast");

const tokenFromUrl = new URLSearchParams(window.location.search).get("token") || "";
if (tokenFromUrl) sessionStorage.setItem("reviewPortalAdminToken", tokenFromUrl);
const token = tokenFromUrl || sessionStorage.getItem("reviewPortalAdminToken") || "";

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
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = `toast visible${isError ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = "toast"; }, 2400);
}

function formatTime(ms) {
  if (ms == null) return "Без таймкода";
  const total = Math.max(0, ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = Math.floor(total % 60);
  const tenths = Math.floor((total - Math.floor(total)) * 10);
  return `📍 ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${tenths}`;
}

function formatDate(value) {
  try { return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
  catch { return value; }
}

function buildCommentCard(comment) {
  const fragment = template.content.cloneNode(true);
  fragment.querySelector(".comment-video").textContent = comment.video_name;
  fragment.querySelector(".comment-title").textContent = comment.author || "Клиент";
  const chip = fragment.querySelector(".timecode-chip");
  chip.textContent = formatTime(comment.timecode_ms);
  if (comment.timecode_ms == null) chip.style.opacity = "0.58";

  const text = fragment.querySelector(".comment-text");
  if (comment.text) text.textContent = comment.text;
  else {
    text.textContent = "Текстового комментария нет — приложена голосовая запись.";
    text.classList.add("empty");
  }

  const audioContainer = fragment.querySelector(".comment-audio");
  if (comment.audio_path) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = apiUrl(`/api/admin/comments/${encodeURIComponent(comment.id)}/audio`);
    audioContainer.append(audio);
  }

  fragment.querySelector(".comment-created").textContent = formatDate(comment.created_at);
  const statusSelect = fragment.querySelector(".comment-status-select");
  statusSelect.value = comment.status;
  statusSelect.addEventListener("change", async () => {
    statusSelect.disabled = true;
    try {
      await apiFetch(`/api/admin/comments/${encodeURIComponent(comment.id)}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: statusSelect.value }),
      });
      showToast("Статус обновлён");
      if (filter.value && filter.value !== statusSelect.value) loadComments();
    } catch (error) {
      statusSelect.value = comment.status;
      showToast(error.message || "Не удалось обновить статус", true);
    } finally {
      statusSelect.disabled = false;
    }
  });
  return fragment;
}

async function loadComments() {
  list.innerHTML = "";
  countLabel.textContent = "Загрузка замечаний…";
  const suffix = filter.value ? `?status=${encodeURIComponent(filter.value)}` : "";
  try {
    const payload = await apiFetch(`/api/admin/comments${suffix}`);
    countLabel.textContent = `${payload.count} ${payload.count === 1 ? "замечание" : "замечаний"}`;
    if (!payload.comments.length) {
      list.innerHTML = '<div class="empty-state">Замечаний с таким статусом пока нет.</div>';
      return;
    }
    const batch = document.createDocumentFragment();
    payload.comments.forEach((comment) => batch.append(buildCommentCard(comment)));
    list.append(batch);
  } catch (error) {
    countLabel.textContent = "Не удалось загрузить замечания";
    list.innerHTML = `<div class="empty-state">${error.message || "Ошибка загрузки"}</div>`;
    showToast(error.message || "Ошибка загрузки", true);
  }
}

filter.addEventListener("change", loadComments);
refreshButton.addEventListener("click", loadComments);
loadComments();
