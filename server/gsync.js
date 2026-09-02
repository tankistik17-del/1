import { extractGroupsFromSheets } from '../shared/grouping.mjs';
import { getSetting, setSetting, upsertGroup } from './db.js';

// Подключение можно задать в интерфейсе или переменными окружения GS_URL/GS_TOKEN
// (env удобен для хостинга без постоянного диска — данные восстановятся после перезапуска).
export function gsConfig() {
  return {
    url: getSetting('gs_url') || process.env.GS_URL || '',
    token: getSetting('gs_token') || process.env.GS_TOKEN || '',
  };
}

// Синхронизация с Google Sheets через опубликованный Apps Script (doGet).
export async function syncFromGoogleSheets() {
  const { url, token } = gsConfig();
  if (!url) return { ok: false, error: 'Google Sheets не подключён' };
  try {
    const sep = url.includes('?') ? '&' : '?';
    const r = await fetch(url + sep + 'token=' + encodeURIComponent(token), { redirect: 'follow' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    const sheets = (data.sheets || []).map(s => ({ name: s.name, rows: s.rows }));
    if (!sheets.length) throw new Error('Пусто: лист не найден');
    const groups = extractGroupsFromSheets(sheets, data.name || 'Google Sheets');
    if (!groups.length) throw new Error('Не распознан ни один журнал (нужны колонки «ученик» и «неделя»)');
    for (const g of groups) upsertGroup(g.name, g.journal, g.mocks);
    setSetting('gs_last_sync', new Date().toISOString());
    setSetting('gs_last_error', null);
    return { ok: true, groups: groups.map(g => g.name) };
  } catch (e) {
    setSetting('gs_last_error', String(e.message || e));
    return { ok: false, error: String(e.message || e) };
  }
}

let timer = null;

export function scheduleSync(intervalMinutes) {
  if (timer) clearInterval(timer);
  const min = Math.max(5, intervalMinutes || 30);
  timer = setInterval(async () => {
    if (!gsConfig().url) return;
    const res = await syncFromGoogleSheets();
    console.log('[gsync] автосинхронизация:', res.ok ? 'ок (' + res.groups.join(', ') + ')' : 'ошибка: ' + res.error);
  }, min * 60 * 1000);
  timer.unref?.();
}
