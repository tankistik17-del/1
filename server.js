// Прототип сервиса записи на консультации.
// Без внешних зависимостей: node server.js
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.env.PORT) || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin';
const DATA_FILE = process.env.DATA_FILE || path.join(__dirname, 'data', 'db.json');
const PUBLIC_DIR = path.join(__dirname, 'public');

// ---------- хранилище ----------

let db = { curators: [], slots: [], events: [] };

function load() {
  if (fs.existsSync(DATA_FILE)) {
    db = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } else {
    seed();
    save();
  }
}

function save() {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  const tmp = DATA_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(db, null, 2));
  fs.renameSync(tmp, DATA_FILE);
}

const id = () => crypto.randomBytes(8).toString('hex');
// Код без похожих символов (0/O, 1/I/L), чтобы ученик мог ввести его руками
const code = (len = 6) => {
  const abc = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  let s = '';
  for (const b of crypto.randomBytes(len)) s += abc[b % abc.length];
  return s;
};

function logEvent(type, slot, extra = {}) {
  db.events.push({ id: id(), type, slotId: slot.id, curatorId: slot.curatorId, at: new Date().toISOString(), ...extra });
}

// ---------- даты (время хранится как локальное "YYYY-MM-DDTHH:MM") ----------

const pad = (n) => String(n).padStart(2, '0');
const fmtLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const nowLocal = () => fmtLocal(new Date());
function mondayOf(dateStr) {
  const d = new Date(dateStr.slice(0, 10) + 'T00:00');
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return fmtLocal(d).slice(0, 10);
}
function addDays(dateStr, n) {
  const d = new Date(dateStr.slice(0, 10) + 'T00:00');
  d.setDate(d.getDate() + n);
  return fmtLocal(d).slice(0, 10);
}
const isValidLocal = (s) => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(s) && !isNaN(new Date(s));

// ---------- демо-данные ----------

function seed() {
  const names = ['Анна Смирнова', 'Иван Петров'];
  const students = ['Маша К.', 'Петя Л.', 'Света Н.', 'Дима О.', 'Катя Р.', 'Артём С.'];
  const monday = mondayOf(nowLocal());
  const prevMonday = addDays(monday, -7);
  names.forEach((name, ci) => {
    const c = { id: id(), name, bookingCode: code(), token: code(20), active: true, createdAt: new Date().toISOString() };
    db.curators.push(c);
    for (const week of [prevMonday, monday]) {
      for (let d = 0; d < 5; d++) {
        for (const t of ci === 0 ? ['16:00', '17:00', '18:00'] : ['10:00', '11:30', '19:00']) {
          const start = `${addDays(week, d)}T${t}`;
          const slot = { id: id(), curatorId: c.id, start, durationMin: 45, status: 'free', booking: null, outcome: null, createdAt: new Date().toISOString() };
          db.slots.push(slot);
          const r = Math.random();
          if (r < 0.55) {
            slot.status = 'booked';
            slot.booking = { studentName: students[Math.floor(Math.random() * students.length)], contact: '@telegram', topic: 'Разбор домашки', createdAt: new Date().toISOString() };
            logEvent('booked', slot);
            if (start < nowLocal()) {
              slot.outcome = Math.random() < 0.8 ? 'attended' : 'no_show';
            }
          }
        }
      }
    }
  });
}

// ---------- HTTP-утилиты ----------

function send(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(body));
}
const fail = (res, status, message) => send(res, status, { error: message });

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (c) => {
      data += c;
      if (data.length > 1e6) req.destroy();
    });
    req.on('end', () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch {
        reject(new Error('bad json'));
      }
    });
  });
}

const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.svg': 'image/svg+xml' };
function serveFile(res, file) {
  const full = path.join(PUBLIC_DIR, file);
  if (!full.startsWith(PUBLIC_DIR) || !fs.existsSync(full) || fs.statSync(full).isDirectory()) {
    res.writeHead(404);
    return res.end('Not found');
  }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(full)] || 'application/octet-stream' });
  fs.createReadStream(full).pipe(res);
}

const str = (v, max = 200) => (typeof v === 'string' ? v.trim().slice(0, max) : '');

// ---------- представления ----------

const publicSlot = (s) => ({ id: s.id, start: s.start, durationMin: s.durationMin });
const curatorSlot = (s) => ({ id: s.id, start: s.start, durationMin: s.durationMin, status: s.status, booking: s.booking, outcome: s.outcome });
const curatorFor = (token) => db.curators.find((c) => c.token === token && c.active);

function stats(from, to) {
  const inRange = (s) => (!from || s.start >= from) && (!to || s.start < to + 'T99');
  const now = nowLocal();
  const rows = db.curators.map((c) => {
    const slots = db.slots.filter((s) => s.curatorId === c.id && inRange(s));
    const booked = slots.filter((s) => s.status === 'booked');
    const past = booked.filter((s) => s.start < now);
    const cancelled = db.events.filter((e) => e.curatorId === c.id && e.type.startsWith('cancelled') && inRange({ start: e.slotStart || '' })).length;
    return {
      curatorId: c.id,
      name: c.name,
      active: c.active,
      offered: slots.length,
      booked: booked.length,
      free: slots.length - booked.length,
      fillRate: slots.length ? Math.round((booked.length / slots.length) * 100) : 0,
      attended: past.filter((s) => s.outcome === 'attended').length,
      noShow: past.filter((s) => s.outcome === 'no_show').length,
      unmarked: past.filter((s) => !s.outcome).length,
      upcoming: booked.length - past.length,
      cancelled,
      students: new Set(booked.map((s) => s.booking.studentName.toLowerCase())).size,
    };
  });

  // по неделям — для графика
  const weeks = {};
  for (const s of db.slots) {
    if (!inRange(s)) continue;
    const w = mondayOf(s.start);
    weeks[w] ??= { week: w, offered: 0, booked: 0, attended: 0, noShow: 0 };
    weeks[w].offered++;
    if (s.status === 'booked') weeks[w].booked++;
    if (s.outcome === 'attended') weeks[w].attended++;
    if (s.outcome === 'no_show') weeks[w].noShow++;
  }
  return { rows, weeks: Object.values(weeks).sort((a, b) => a.week.localeCompare(b.week)) };
}

function csvCell(v) {
  const s = v == null ? '' : String(v);
  return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// ---------- роутинг ----------

async function handle(req, res) {
  const url = new URL(req.url, 'http://x');
  const p = url.pathname;
  const m = (re) => p.match(re);
  let r;

  // страницы
  if (req.method === 'GET' && !p.startsWith('/api/')) {
    if (p === '/' || m(/^\/c\/[A-Za-z0-9]+$/)) return serveFile(res, 'index.html');
    if (m(/^\/curator\/[A-Za-z0-9]+$/)) return serveFile(res, 'curator.html');
    if (p === '/admin') return serveFile(res, 'admin.html');
    return serveFile(res, p.slice(1));
  }

  let body = {};
  if (req.method === 'POST' || req.method === 'PATCH' || req.method === 'PUT') {
    try {
      body = await readBody(req);
    } catch {
      return fail(res, 400, 'Некорректный запрос');
    }
  }

  // ===== ученик: видит только куратора по коду и только свободные будущие слоты =====
  if ((r = m(/^\/api\/public\/([A-Za-z0-9]+)$/)) && req.method === 'GET') {
    const c = db.curators.find((x) => x.bookingCode === r[1].toUpperCase() && x.active);
    if (!c) return fail(res, 404, 'Куратор с таким кодом не найден');
    const now = nowLocal();
    const slots = db.slots.filter((s) => s.curatorId === c.id && s.status === 'free' && s.start > now).sort((a, b) => a.start.localeCompare(b.start));
    return send(res, 200, { curator: { name: c.name }, slots: slots.map(publicSlot) });
  }

  if ((r = m(/^\/api\/public\/([A-Za-z0-9]+)\/book$/)) && req.method === 'POST') {
    const c = db.curators.find((x) => x.bookingCode === r[1].toUpperCase() && x.active);
    if (!c) return fail(res, 404, 'Куратор с таким кодом не найден');
    const slot = db.slots.find((s) => s.id === body.slotId && s.curatorId === c.id);
    if (!slot) return fail(res, 404, 'Слот не найден');
    if (slot.status !== 'free' || slot.start <= nowLocal()) return fail(res, 409, 'Этот слот уже заняли — выберите другой');
    const studentName = str(body.studentName, 80);
    const contact = str(body.contact, 80);
    if (!studentName || !contact) return fail(res, 400, 'Укажите имя и контакт');
    slot.status = 'booked';
    slot.booking = { studentName, contact, topic: str(body.topic, 300), createdAt: new Date().toISOString(), cancelCode: code(8) };
    logEvent('booked', slot);
    save();
    return send(res, 200, { ok: true, slot: publicSlot(slot), curator: c.name, cancelCode: slot.booking.cancelCode });
  }

  if (p === '/api/public/cancel' && req.method === 'POST') {
    const cc = str(body.cancelCode, 20).toUpperCase();
    const slot = cc && db.slots.find((s) => s.booking && s.booking.cancelCode === cc);
    if (!slot) return fail(res, 404, 'Запись с таким кодом не найдена');
    if (slot.start <= nowLocal()) return fail(res, 409, 'Консультация уже прошла');
    logEvent('cancelled_by_student', slot, { slotStart: slot.start, studentName: slot.booking.studentName });
    slot.status = 'free';
    slot.booking = null;
    save();
    return send(res, 200, { ok: true });
  }

  // ===== куратор: доступ по секретной ссылке =====
  if ((r = m(/^\/api\/curator\/([A-Za-z0-9]+)(\/.*)?$/))) {
    const c = curatorFor(r[1]);
    if (!c) return fail(res, 403, 'Ссылка недействительна');
    const sub = r[2] || '';

    if (sub === '' && req.method === 'GET') {
      const slots = db.slots.filter((s) => s.curatorId === c.id).sort((a, b) => a.start.localeCompare(b.start));
      return send(res, 200, { curator: { name: c.name, bookingCode: c.bookingCode }, slots: slots.map(curatorSlot) });
    }

    // добавить слоты пачкой: [{start, durationMin}]
    if (sub === '/slots' && req.method === 'POST') {
      const items = Array.isArray(body.slots) ? body.slots.slice(0, 500) : [];
      const existing = new Set(db.slots.filter((s) => s.curatorId === c.id).map((s) => s.start));
      let added = 0;
      let skipped = 0;
      for (const it of items) {
        const dur = Math.min(Math.max(Number(it.durationMin) || 45, 10), 240);
        if (!isValidLocal(it.start) || it.start <= nowLocal() || existing.has(it.start)) {
          skipped++;
          continue;
        }
        existing.add(it.start);
        db.slots.push({ id: id(), curatorId: c.id, start: it.start, durationMin: dur, status: 'free', booking: null, outcome: null, createdAt: new Date().toISOString() });
        added++;
      }
      save();
      return send(res, 200, { added, skipped });
    }

    if ((r = sub.match(/^\/slots\/([a-f0-9]+)$/))) {
      const slot = db.slots.find((s) => s.id === r[1] && s.curatorId === c.id);
      if (!slot) return fail(res, 404, 'Слот не найден');

      if (req.method === 'DELETE') {
        if (slot.status === 'booked') {
          logEvent('cancelled_by_curator', slot, { slotStart: slot.start, studentName: slot.booking.studentName });
        }
        db.slots = db.slots.filter((s) => s !== slot);
        save();
        return send(res, 200, { ok: true });
      }

      if (req.method === 'PATCH') {
        if ('outcome' in body) {
          if (slot.status !== 'booked') return fail(res, 400, 'На слот никто не записан');
          if (![null, 'attended', 'no_show'].includes(body.outcome)) return fail(res, 400, 'Некорректный статус');
          slot.outcome = body.outcome;
        }
        if (body.freeUp && slot.status === 'booked') {
          logEvent('cancelled_by_curator', slot, { slotStart: slot.start, studentName: slot.booking.studentName });
          slot.status = 'free';
          slot.booking = null;
          slot.outcome = null;
        }
        save();
        return send(res, 200, { slot: curatorSlot(slot) });
      }
    }
    return fail(res, 404, 'Не найдено');
  }

  // ===== репетитор (админ) =====
  if (p.startsWith('/api/admin/')) {
    const key = req.headers['x-admin-key'] || url.searchParams.get('key');
    if (key !== ADMIN_PASSWORD) return fail(res, 401, 'Неверный пароль');
    const sub = p.slice('/api/admin'.length);

    if (sub === '/curators' && req.method === 'GET') {
      return send(res, 200, db.curators.map(({ id, name, bookingCode, token, active }) => ({ id, name, bookingCode, token, active })));
    }
    if (sub === '/curators' && req.method === 'POST') {
      const name = str(body.name, 80);
      if (!name) return fail(res, 400, 'Укажите имя куратора');
      const c = { id: id(), name, bookingCode: code(), token: code(20), active: true, createdAt: new Date().toISOString() };
      db.curators.push(c);
      save();
      return send(res, 200, c);
    }
    if ((r = sub.match(/^\/curators\/([a-f0-9]+)$/)) && req.method === 'PATCH') {
      const c = db.curators.find((x) => x.id === r[1]);
      if (!c) return fail(res, 404, 'Куратор не найден');
      if (typeof body.active === 'boolean') c.active = body.active;
      if (body.name) c.name = str(body.name, 80);
      if (body.regenerate === 'token') c.token = code(20);
      if (body.regenerate === 'bookingCode') c.bookingCode = code();
      save();
      return send(res, 200, c);
    }
    if (sub === '/stats' && req.method === 'GET') {
      return send(res, 200, stats(url.searchParams.get('from'), url.searchParams.get('to')));
    }
    if (sub === '/export.csv' && req.method === 'GET') {
      const from = url.searchParams.get('from');
      const to = url.searchParams.get('to');
      const names = Object.fromEntries(db.curators.map((c) => [c.id, c.name]));
      const outcome = { attended: 'пришёл', no_show: 'не пришёл' };
      const lines = [['Дата и время', 'Длительность, мин', 'Куратор', 'Статус', 'Ученик', 'Контакт', 'Тема', 'Итог'].join(';')];
      db.slots
        .filter((s) => (!from || s.start >= from) && (!to || s.start < to + 'T99'))
        .sort((a, b) => a.start.localeCompare(b.start))
        .forEach((s) => {
          lines.push(
            [s.start.replace('T', ' '), s.durationMin, names[s.curatorId], s.status === 'booked' ? 'занят' : 'свободен', s.booking?.studentName, s.booking?.contact, s.booking?.topic, outcome[s.outcome]]
              .map(csvCell)
              .join(';'),
          );
        });
      res.writeHead(200, { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename="consultations.csv"' });
      return res.end('﻿' + lines.join('\n'));
    }
    return fail(res, 404, 'Не найдено');
  }

  fail(res, 404, 'Не найдено');
}

load();
http
  .createServer((req, res) => {
    handle(req, res).catch((e) => {
      console.error(e);
      fail(res, 500, 'Внутренняя ошибка');
    });
  })
  .listen(PORT, () => {
    const base = `http://localhost:${PORT}`;
    console.log(`\nСервер запущен: ${base}\n`);
    console.log(`Репетитор (статистика):  ${base}/admin   пароль: ${ADMIN_PASSWORD}`);
    for (const c of db.curators.filter((x) => x.active)) {
      console.log(`\n${c.name}`);
      console.log(`  ссылка для учеников:  ${base}/c/${c.bookingCode}`);
      console.log(`  кабинет куратора:     ${base}/curator/${c.token}`);
    }
    console.log('');
  });
