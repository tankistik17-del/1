import express from 'express';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  getUser, verifyPassword, createSession, getSession, deleteSession,
  getSetting, setSetting, upsertGroup, listGroups, renameGroup,
  upsertSnapshot, listSnapshots, markCalled, listCalled,
} from './db.js';
import { syncFromGoogleSheets, scheduleSync, gsConfig } from './gsync.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const app = express();

app.use(express.json({ limit: '50mb' }));

// --- сессии ---
function readToken(req) {
  const m = /(?:^|;\s*)sid=([a-f0-9]{64})/.exec(req.headers.cookie || '');
  return m ? m[1] : null;
}

function requireAuth(req, res, next) {
  const session = getSession(readToken(req));
  if (!session) return res.status(401).json({ error: 'unauthorized' });
  req.user = getUser(session.username);
  req.sessionToken = session.token;
  next();
}

// простая защита от перебора пароля
const loginAttempts = new Map();
function throttleLogin(req, res, next) {
  const key = req.ip || 'unknown';
  const rec = loginAttempts.get(key) || { count: 0, resetAt: Date.now() + 15 * 60 * 1000 };
  if (Date.now() > rec.resetAt) { rec.count = 0; rec.resetAt = Date.now() + 15 * 60 * 1000; }
  if (rec.count >= 20) return res.status(429).json({ error: 'Слишком много попыток, подождите 15 минут' });
  rec.count++;
  loginAttempts.set(key, rec);
  next();
}

// --- API ---
app.post('/api/login', throttleLogin, (req, res) => {
  const { username, password } = req.body || {};
  const user = getUser(String(username || '').trim().toLowerCase());
  if (!user || !verifyPassword(user, String(password || ''))) {
    return res.status(401).json({ error: 'Неверный логин или пароль' });
  }
  const token = createSession(user.username);
  res.setHeader('Set-Cookie', `sid=${token}; HttpOnly; Path=/; Max-Age=${30 * 24 * 3600}; SameSite=Lax`);
  res.json({ ok: true, username: user.username, role: user.role, displayName: user.displayName });
});

app.post('/api/logout', requireAuth, (req, res) => {
  deleteSession(req.sessionToken);
  res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax');
  res.json({ ok: true });
});

app.get('/api/me', requireAuth, (req, res) => {
  res.json({ username: req.user.username, role: req.user.role, displayName: req.user.displayName });
});

app.get('/api/state', requireAuth, (req, res) => {
  res.json({
    me: { username: req.user.username, role: req.user.role, displayName: req.user.displayName },
    groups: listGroups(),
    snapshots: listSnapshots(),
    called: listCalled(),
    gs: {
      configured: !!gsConfig().url,
      url: gsConfig().url,
      lastSync: getSetting('gs_last_sync'),
      lastError: getSetting('gs_last_error'),
    },
  });
});

// приём групп, разобранных из .xlsx в браузере
app.post('/api/groups/ingest', requireAuth, (req, res) => {
  const groups = Array.isArray(req.body?.groups) ? req.body.groups : [];
  let saved = 0;
  for (const g of groups) {
    if (!g || typeof g.name !== 'string' || !Array.isArray(g.journal)) continue;
    upsertGroup(g.name.trim(), g.journal, Array.isArray(g.mocks) ? g.mocks : null);
    saved++;
  }
  res.json({ ok: true, saved });
});

app.post('/api/groups/rename', requireAuth, (req, res) => {
  const { oldName, newName } = req.body || {};
  const nn = String(newName || '').trim();
  if (!oldName || !nn) return res.status(400).json({ error: 'Нужны oldName и newName' });
  const result = renameGroup(String(oldName), nn);
  if (!result.ok) return res.status(409).json({ error: result.error });
  res.json({ ok: true });
});

app.post('/api/snapshots', requireAuth, (req, res) => {
  const { groupName, weekKey, perStudent, kpi } = req.body || {};
  if (typeof groupName !== 'string' || typeof weekKey !== 'number' || !Array.isArray(perStudent) || !kpi) {
    return res.status(400).json({ error: 'Неверный формат снапшота' });
  }
  upsertSnapshot(groupName, weekKey, perStudent, kpi);
  res.json({ ok: true });
});

app.post('/api/called', requireAuth, (req, res) => {
  const { studentId } = req.body || {};
  if (typeof studentId !== 'string' || !studentId) return res.status(400).json({ error: 'Нужен studentId' });
  const d = new Date();
  const time = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  markCalled(studentId, req.user.displayName || req.user.username, time, d.toISOString().slice(0, 10));
  res.json({ ok: true, called: listCalled() });
});

app.post('/api/gs-config', requireAuth, (req, res) => {
  const { url, token } = req.body || {};
  const cleanUrl = String(url || '').trim();
  setSetting('gs_url', cleanUrl || null);
  const cleanToken = String(token || '').trim();
  // пустое поле токена не стирает ранее сохранённый токен (его не видно в форме)
  if (cleanToken || !cleanUrl) setSetting('gs_token', cleanToken || null);
  if (!cleanUrl) { setSetting('gs_last_sync', null); setSetting('gs_last_error', null); }
  res.json({ ok: true });
});

app.post('/api/sync', requireAuth, async (req, res) => {
  const result = await syncFromGoogleSheets();
  if (!result.ok) return res.status(502).json(result);
  res.json(result);
});

// --- статика и страницы ---
const pub = path.join(__dirname, '..', 'public');

app.get('/', (req, res) => {
  if (!getSession(readToken(req))) return res.redirect('/login.html');
  res.sendFile(path.join(pub, 'index.html'));
});

app.use(express.static(pub));
app.use('/shared', express.static(path.join(__dirname, '..', 'shared')));

app.listen(PORT, () => {
  console.log(`Пульт удержания запущен: http://localhost:${PORT}`);
  scheduleSync(Number(process.env.SYNC_INTERVAL_MIN || 30));
  if (gsConfig().url) {
    syncFromGoogleSheets().then(r =>
      console.log('[gsync] синхронизация при старте:', r.ok ? 'ок' : 'ошибка: ' + r.error));
  }
});
