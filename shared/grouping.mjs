// Распознавание листов таблицы: какие листы — журналы групп, какие — пробники.
// Используется сервером (синк из Google Sheets) и браузером (загрузка .xlsx).

export function cv(x) { return String(x == null ? '' : x).trim(); }

export function headCells(rows, n) {
  let a = [];
  for (let r = 0; r < Math.min(n, rows.length); r++) a = a.concat(rows[r] || []);
  return a.map(x => String(x == null ? '' : x));
}

export function isJournal(rows) {
  const h = headCells(rows, 4);
  return h.some(x => /учен/i.test(x)) && h.some(x => /недел/i.test(x));
}

export function isMocks(name, rows) {
  const h = headCells(rows, 5);
  return h.some(x => /^\s*пробник\s*\d+/i.test(x)) || (/пробник/i.test(name) && h.some(x => /фио|учен/i.test(x)));
}

export function groupNameFromSheet(name) {
  return String(name)
    .replace(/успеваемост[а-яё]*|пробник[а-яё]*|посещаемост[а-яё]*|журнал[а-яё]*/ig, '')
    .replace(/^[\s_\-–—]+|[\s_\-–—]+$/g, '')
    .trim() || String(name).trim();
}

export function cleanFileName(fn) {
  return String(fn)
    .replace(/\.(xlsx|xls|xlsm)$/i, '')
    .replace(/^копия[_\s]*/i, '')
    .replace(/_+/g, ' ')
    .trim() || 'Группа';
}

// sheets: [{name, rows}] → [{name, journal, mocks}]
export function extractGroupsFromSheets(sheets, fallbackName) {
  const jn = sheets.filter(s => isJournal(s.rows));
  const mk = sheets.filter(s => isMocks(s.name, s.rows));
  if (jn.length <= 1) {
    const j = jn[0] || sheets.find(s => headCells(s.rows, 4).some(x => /учен/i.test(x)));
    if (!j) return [];
    return [{ name: cleanFileName(fallbackName), journal: j.rows, mocks: mk[0] ? mk[0].rows : null }];
  }
  return jn.map(j => {
    const gn = groupNameFromSheet(j.name);
    const m = mk.find(m => groupNameFromSheet(m.name) === gn) || null;
    return { name: gn, journal: j.rows, mocks: m ? m.rows : null };
  });
}
