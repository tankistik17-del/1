import { DatabaseSync } from 'node:sqlite';
import { scryptSync, randomBytes, timingSafeEqual } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const DB_PATH = process.env.DB_PATH || './data/retention.db';
mkdirSync(dirname(DB_PATH), { recursive: true });

export const db = new DatabaseSync(DB_PATH);

db.exec(`
  PRAGMA journal_mode = WAL;
  CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    role     TEXT NOT NULL,
    salt     TEXT NOT NULL,
    passhash TEXT NOT NULL,
    displayName TEXT NOT NULL DEFAULT ''
  );
  CREATE TABLE IF NOT EXISTS sessions (
    token     TEXT PRIMARY KEY,
    username  TEXT NOT NULL,
    createdAt INTEGER NOT NULL,
    expiresAt INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS groups (
    name      TEXT PRIMARY KEY,
    journal   TEXT NOT NULL,
    mocks     TEXT,
    updatedAt INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS snapshots (
    groupName  TEXT NOT NULL,
    weekKey    INTEGER NOT NULL,
    perStudent TEXT NOT NULL,
    kpi        TEXT NOT NULL,
    savedAt    INTEGER NOT NULL,
    PRIMARY KEY (groupName, weekKey)
  );
  CREATE TABLE IF NOT EXISTS called (
    studentId TEXT PRIMARY KEY,
    byUser    TEXT NOT NULL,
    time      TEXT NOT NULL,
    date      TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
  );
`);

function hashPassword(password, salt) {
  return scryptSync(password, salt, 32).toString('hex');
}

export function verifyPassword(user, password) {
  const expected = Buffer.from(user.passhash, 'hex');
  const actual = Buffer.from(hashPassword(password, user.salt), 'hex');
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

export function setPassword(username, password) {
  const salt = randomBytes(16).toString('hex');
  db.prepare('UPDATE users SET salt = ?, passhash = ? WHERE username = ?')
    .run(salt, hashPassword(password, salt), username);
}

function seedUser(username, role, displayName, envPassword, defaultPassword) {
  const existing = db.prepare('SELECT username FROM users WHERE username = ?').get(username);
  if (!existing) {
    const salt = randomBytes(16).toString('hex');
    db.prepare('INSERT INTO users (username, role, salt, passhash, displayName) VALUES (?, ?, ?, ?, ?)')
      .run(username, role, salt, hashPassword(envPassword || defaultPassword, salt), displayName);
    if (!envPassword) {
      console.log(`[users] создан пользователь "${username}" с паролем по умолчанию "${defaultPassword}" — смените через переменную окружения`);
    }
  } else if (envPassword) {
    // переменная окружения — источник истины для пароля
    setPassword(username, envPassword);
  }
}

seedUser('tutor', 'tutor', 'Репетитор', process.env.TUTOR_PASSWORD, 'tutor123');
seedUser('admin', 'admin', 'Администратор', process.env.ADMIN_PASSWORD, 'admin123');

export function getUser(username) {
  return db.prepare('SELECT * FROM users WHERE username = ?').get(username);
}

const SESSION_TTL_MS = 30 * 24 * 3600 * 1000;

export function createSession(username) {
  const token = randomBytes(32).toString('hex');
  const now = Date.now();
  db.prepare('INSERT INTO sessions (token, username, createdAt, expiresAt) VALUES (?, ?, ?, ?)')
    .run(token, username, now, now + SESSION_TTL_MS);
  return token;
}

export function getSession(token) {
  if (!token) return null;
  const s = db.prepare('SELECT * FROM sessions WHERE token = ?').get(token);
  if (!s) return null;
  if (s.expiresAt < Date.now()) {
    db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
    return null;
  }
  return s;
}

export function deleteSession(token) {
  db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
}

export function getSetting(key) {
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key);
  return row ? row.value : null;
}

export function setSetting(key, value) {
  if (value == null) db.prepare('DELETE FROM settings WHERE key = ?').run(key);
  else db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value').run(key, value);
}

export function upsertGroup(name, journal, mocks) {
  db.prepare(`INSERT INTO groups (name, journal, mocks, updatedAt) VALUES (?, ?, ?, ?)
              ON CONFLICT(name) DO UPDATE SET journal = excluded.journal, mocks = excluded.mocks, updatedAt = excluded.updatedAt`)
    .run(name, JSON.stringify(journal), mocks ? JSON.stringify(mocks) : null, Date.now());
}

export function listGroups() {
  return db.prepare('SELECT * FROM groups ORDER BY name').all().map(g => ({
    name: g.name,
    journal: JSON.parse(g.journal),
    mocks: g.mocks ? JSON.parse(g.mocks) : null,
    updatedAt: g.updatedAt,
  }));
}

export function renameGroup(oldName, newName) {
  const exists = db.prepare('SELECT name FROM groups WHERE name = ?').get(newName);
  if (exists) return { ok: false, error: 'Группа с таким именем уже есть' };
  const src = db.prepare('SELECT name FROM groups WHERE name = ?').get(oldName);
  if (!src) return { ok: false, error: 'Группа не найдена' };
  db.prepare('UPDATE groups SET name = ? WHERE name = ?').run(newName, oldName);
  db.prepare('UPDATE snapshots SET groupName = ? WHERE groupName = ?').run(newName, oldName);
  const calls = db.prepare('SELECT * FROM called').all();
  for (const c of calls) {
    const sep = c.studentId.indexOf('|');
    if (sep > 0 && c.studentId.slice(0, sep) === oldName) {
      const nid = newName + c.studentId.slice(sep);
      db.prepare('DELETE FROM called WHERE studentId = ?').run(c.studentId);
      db.prepare('INSERT OR REPLACE INTO called (studentId, byUser, time, date) VALUES (?, ?, ?, ?)')
        .run(nid, c.byUser, c.time, c.date);
    }
  }
  return { ok: true };
}

export function upsertSnapshot(groupName, weekKey, perStudent, kpi) {
  db.prepare(`INSERT INTO snapshots (groupName, weekKey, perStudent, kpi, savedAt) VALUES (?, ?, ?, ?, ?)
              ON CONFLICT(groupName, weekKey) DO UPDATE SET perStudent = excluded.perStudent, kpi = excluded.kpi, savedAt = excluded.savedAt`)
    .run(groupName, weekKey, JSON.stringify(perStudent), JSON.stringify(kpi), Date.now());
}

export function listSnapshots() {
  return db.prepare('SELECT * FROM snapshots ORDER BY groupName, weekKey').all().map(s => ({
    groupName: s.groupName,
    weekKey: s.weekKey,
    perStudent: JSON.parse(s.perStudent),
    kpi: JSON.parse(s.kpi),
    savedAt: s.savedAt,
  }));
}

export function markCalled(studentId, byUser, time, date) {
  db.prepare('INSERT OR REPLACE INTO called (studentId, byUser, time, date) VALUES (?, ?, ?, ?)')
    .run(studentId, byUser, time, date);
}

export function listCalled() {
  const out = {};
  for (const c of db.prepare('SELECT * FROM called').all()) {
    out[c.studentId] = { time: c.time, date: c.date, by: c.byUser };
  }
  return out;
}
