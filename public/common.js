// Общие хелперы для всех страниц
async function api(url, opts = {}) {
  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Ошибка сервера');
  return data;
}

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const pad = (n) => String(n).padStart(2, '0');
const toLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const parseLocal = (s) => new Date(s.length === 10 ? s + 'T00:00' : s);
function addDays(dateStr, n) {
  const d = parseLocal(dateStr.slice(0, 10));
  d.setDate(d.getDate() + n);
  return toLocal(d).slice(0, 10);
}
function mondayOf(dateStr) {
  const d = parseLocal(dateStr.slice(0, 10));
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return toLocal(d).slice(0, 10);
}
const fmtDay = (s) => parseLocal(s).toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' });
const fmtShortDay = (s) => parseLocal(s).toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' });
const fmtTime = (s) => s.slice(11, 16);
function endTime(start, dur) {
  const d = parseLocal(start);
  d.setMinutes(d.getMinutes() + dur);
  return toLocal(d).slice(11, 16);
}

function modal(html) {
  const bg = document.createElement('div');
  bg.className = 'modal-bg';
  bg.innerHTML = `<div class="modal">${html}</div>`;
  bg.addEventListener('click', (e) => e.target === bg && bg.remove());
  document.body.appendChild(bg);
  return bg;
}

function copy(text, btn) {
  navigator.clipboard?.writeText(text).then(() => {
    if (!btn) return;
    const old = btn.textContent;
    btn.textContent = 'Скопировано';
    setTimeout(() => (btn.textContent = old), 1200);
  });
}
