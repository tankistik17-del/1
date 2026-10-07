/* Tutor group workbook parser: SheetJS workbook (read with {cellStyles:true, cellDates:true}) → compact group model,
   and model → metrics. Runs in the browser (global XLSX) and in node (module.exports). */
(function (root) {
  'use strict';

  /* ---------- small helpers ---------- */
  const enc = (r, c) => colName(c) + (r + 1);
  function colName(c) { let s = ''; c += 1; while (c) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = (c - 1 - m) / 26; } return s; }
  const low = s => String(s == null ? '' : s).replace(/\s+/g, ' ').trim().toLowerCase();
  const isDate = v => v instanceof Date && !isNaN(v);
  const pad = n => String(n).padStart(2, '0');
  const iso = d => d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate());
  const utc = (y, m, d) => new Date(Date.UTC(y, m - 1, d));
  // SheetJS gives dates at local midnight (give or take a few seconds); take the local calendar day it shows.
  const dayOf = v => { const t = new Date(v.getTime() + 3600e3); return utc(t.getFullYear(), t.getMonth() + 1, t.getDate()); };
  const plural = (n, one, few, many) => { const a = Math.abs(n) % 100, b = a % 10; return a > 10 && a < 20 ? many : b === 1 ? one : b >= 2 && b <= 4 ? few : many; };

  function normName(s) {
    return low(s).replace(/ё/g, 'е').replace(/\([^)]*\)/g, ' ').replace(/[^a-zа-я\s-]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function lev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length; if (!m || !n) return m || n;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[n];
  }
  /** Find the roster index for a name: exact → same words → typo (≤2 edits). Returns {i, how} or null. */
  function matchName(name, roster, allow) {
    const n = normName(name); if (!n) return null;
    const ok = k => !allow || allow(k);
    let i = roster.findIndex((r, k) => r.key === n && ok(k)); if (i >= 0) return { i, how: 'exact' };
    const words = n.split(' ').sort().join(' ');
    i = roster.findIndex((r, k) => r.key.split(' ').sort().join(' ') === words && ok(k)); if (i >= 0) return { i, how: 'order' };
    let best = -1, bestD = 3;
    roster.forEach((r, k) => { if (!ok(k)) return; const d = lev(r.key, n); if (d < bestD) { bestD = d; best = k; } });
    return best >= 0 && n.length > 5 ? { i: best, how: 'typo' } : null;
  }

  /* ---------- sheet access ---------- */
  function sheetView(ws) {
    const range = ws['!ref'] ? XLSXref().utils.decode_range(ws['!ref']) : { s: { r: 0, c: 0 }, e: { r: -1, c: -1 } };
    const owner = new Map(); // merged continuation cell -> top-left
    for (const m of ws['!merges'] || []) for (let r = m.s.r; r <= m.e.r; r++) for (let c = m.s.c; c <= m.e.c; c++) if (r !== m.s.r || c !== m.s.c) owner.set(r + ':' + c, m);
    const get = (r, c) => ws[enc(r, c)];
    return {
      rows: range.e.r + 1, cols: range.e.c + 1, merges: ws['!merges'] || [],
      cont: (r, c) => owner.has(r + ':' + c),
      mergeAt: (r, c) => (ws['!merges'] || []).find(m => m.s.r === r && m.s.c === c) || null,
      v(r, c) { const x = get(r, c); if (!x || x.t === 'z' || x.t === 'e' || x.v == null) return null; if (x.t === 'd' || isDate(x.v)) return dayOf(new Date(x.v)); if (typeof x.v === 'string') { const s = x.v.replace(/\s+/g, ' ').trim(); return s === '' ? null : s; } return x.v; },
      fill(r, c) { const x = get(r, c); const f = x && x.s && x.s.fgColor; if (!f || !f.rgb || (x.s.patternType && x.s.patternType !== 'solid')) return null; return String(f.rgb).slice(-6).toUpperCase(); },
    };
  }
  let XLSXlib = null;
  function XLSXref() { if (XLSXlib) return XLSXlib; XLSXlib = root.XLSX || (typeof require === 'function' ? require('xlsx') : null); return XLSXlib; }

  function colorKind(hex) {
    if (!hex || !/^[0-9A-F]{6}$/.test(hex)) return null;
    const n = parseInt(hex, 16), r = (n >> 16 & 255) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255;
    const max = Math.max(r, g, b), d = max - Math.min(r, g, b);
    if (max < 0.25 || d / max < 0.12) return null;
    let h = max === r ? 60 * (((g - b) / d) % 6) : max === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4);
    if (h < 0) h += 360;
    if (h >= 75 && h <= 165) return 'green';
    if (h >= 40 && h < 75) return 'yellow';
    if (h >= 340 || h <= 20) return 'red';
    return null;
  }

  const LEGEND = /урок|конспект|отсутст|отсутсв|присутств|пропуск|показател|итог|средн|сумма|был на|не был/;
  /** Student rows below `from`: non-empty name cells, stop after 2 consecutive empties once names have started.
      A row that comes right after an empty one must also pass `hasData` (if given), so a legend is not read as a student. */
  function studentRows(sv, from, nameCol, hasData) {
    const out = []; let empty = 0, gap = false;
    for (let r = from; r < sv.rows; r++) {
      const v = sv.v(r, nameCol);
      if (v == null || typeof v !== 'string' || !/[a-zа-яё]/i.test(v)) { if (out.length) { empty++; gap = true; if (empty >= 2) break; } continue; }
      empty = 0;
      if (LEGEND.test(low(v))) continue;
      if (gap && hasData && !hasData(r)) continue;
      gap = false;
      out.push({ r, name: v });
    }
    return out;
  }
  function findSheet(wb, key) { return wb.SheetNames.find(n => low(n).includes(key)) || null; }
  function headerCell(sv, re, maxRows) {
    for (let r = 0; r < Math.min(maxRows, sv.rows); r++) for (let c = 0; c < Math.min(sv.cols, 40); c++) { const v = sv.v(r, c); if (typeof v === 'string' && re.test(low(v))) return { r, c }; }
    return null;
  }

  /* ---------- dates in headers ---------- */
  function parseHeaderDate(v, yearHint) {
    if (isDate(v)) return { date: v, text: '' };
    if (typeof v !== 'string') return null;
    const m = /^\s*(\d{1,2})[.\/](\d{1,2})(?:[.\/](\d{2,4}))?/.exec(v);
    if (!m) return null;
    const d = +m[1], mo = +m[2]; if (d < 1 || d > 31 || mo < 1 || mo > 12) return null;
    let y = m[3] ? +m[3] : null; if (y && y < 100) y += 2000;
    return { date: null, d, mo, y, text: v };
  }
  function academicYear(month, startYear) { return month >= 8 ? startYear : startYear + 1; }
  function weekEnd(label, startYear) {
    const all = [...String(label).matchAll(/(\d{1,2})\.(\d{1,2})/g)].map(m => [+m[1], +m[2]]).filter(([d, mo]) => d >= 1 && d <= 31 && mo >= 1 && mo <= 12);
    if (!all.length) return null;
    const [d, mo] = all[all.length - 1];
    return utc(academicYear(mo, startYear), mo, d);
  }

  /* ---------- the parser ---------- */
  function parseWorkbook(wb, opts) {
    opts = opts || {};
    const warnings = [];
    const today = opts.today ? new Date(opts.today + 'T00:00:00Z') : utc(new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate());
    const names = { pos: findSheet(wb, 'посещ'), usp: findSheet(wb, 'успев'), prob: findSheet(wb, 'пробник'), kes: findSheet(wb, 'кэс'), dr: findSheet(wb, 'др') };
    names.dr = wb.SheetNames.find(n => /^\s*др\s*$/i.test(n) || /рожд/i.test(n)) || null;
    const views = {}; for (const k in names) if (names[k]) views[k] = sheetView(wb.Sheets[names[k]]);
    if (!views.pos && !views.usp) return { ok: false, error: 'В файле нет листов «Посещаемость» и «Успеваемость». Это точно таблица группы?' };
    if (!views.usp) warnings.push('Нет листа «Успеваемость» — ДЗ и конспекты не посчитаются.');
    if (!views.prob) warnings.push('Нет листа «Пробники» — входной пробник возьму из «Успеваемости», если он там есть.');
    if (!views.kes) warnings.push('Нет листа «КЭС» — подключение к чатам не посчитается.');
    if (!views.dr) warnings.push('Нет листа «ДР» — дни рождения не покажу.');

    const roster = []; // {name, key, src}
    const claimed = new Set(), typos = [];
    const add = (name, src) => {
      const m = matchName(name, roster, k => roster[k].src !== src && !claimed.has(src + ':' + k));
      if (m) { claimed.add(src + ':' + m.i); if (m.how === 'typo') typos.push([m.i, src, name]); return m.i; }
      roster.push({ name: String(name).replace(/\s*\([^)]*\)\s*/g, ' ').replace(/\s+/g, ' ').trim(), key: normName(name), src });
      claimed.add(src + ':' + (roster.length - 1));
      return roster.length - 1;
    };

    // rows of another sheet → roster: exact / word-order matches first, typos only for what is left; one row per student
    const matchRows = rows => {
      const used = new Set();
      rows.forEach(x => { const m = matchName(x.name, roster); x.m = m && m.how !== 'typo' && !used.has(m.i) ? m : null; if (x.m) used.add(x.m.i); });
      rows.forEach(x => { if (!x.m) { const m = matchName(x.name, roster, k => !used.has(k)); if (m) { x.m = m; used.add(m.i); } } });
      return rows;
    };

    /* attendance */
    const sessions = [];
    let posRows = [];
    if (views.pos) {
      const sv = views.pos;
      const h = headerCell(sv, /ученик|фио/, 5) || { r: 0, c: 0 };
      const years = [];
      for (let c = h.c + 1; c < sv.cols; c++) { const v = sv.v(h.r, c); if (isDate(v)) years.push([c, v]); }
      for (let c = h.c + 1; c < sv.cols; c++) {
        if (sv.cont(h.r, c)) continue;
        const v = sv.v(h.r, c), p = parseHeaderDate(v);
        if (!p) continue;
        let date = p.date;
        if (!date) {
          let y = p.y;
          if (!y && years.length) { // the year that puts this day closest to the nearest date-valued header
            const near = years.reduce((a, b) => Math.abs(b[0] - c) < Math.abs(a[0] - c) ? b : a)[1], y0 = near.getUTCFullYear();
            y = [y0 - 1, y0, y0 + 1].reduce((a, b) => Math.abs(utc(b, p.mo, p.d) - near) < Math.abs(utc(a, p.mo, p.d) - near) ? b : a);
          }
          if (!y) y = academicYear(p.mo, today.getUTCMonth() + 1 >= 8 ? today.getUTCFullYear() : today.getUTCFullYear() - 1);
          date = utc(y, p.mo, p.d);
        }
        const text = typeof v === 'string' ? v : '';
        sessions.push({ c, date: iso(date), kind: /общ/i.test(text) ? 'общее' : 'урок', label: pad(date.getUTCDate()) + '.' + pad(date.getUTCMonth() + 1) });
      }
      // a plain-date header on the weekday that all labelled «общее» sessions share is an «общее» too
      const wd = x => new Date(x.date + 'T00:00:00Z').getUTCDay();
      const gen = new Set(sessions.filter(x => x.kind === 'общее').map(wd));
      const lessonDays = new Set(sessions.filter((x, k) => x.kind === 'урок' && typeof sv.v(h.r, x.c) === 'string').map(wd));
      sessions.forEach(x => { if (x.kind === 'урок' && gen.has(wd(x)) && !lessonDays.has(wd(x)) && sessions.filter(y => y.kind === 'общее' && wd(y) === wd(x)).length >= 2) x.kind = 'общее'; });
      const marked = r => sessions.some(x => sv.v(r, x.c) != null || colorKind(sv.fill(r, x.c)));
      posRows = studentRows(sv, h.r + 1, h.c, marked).map(x => ({ ...x, i: add(x.name, 'pos') }));
      if (!sessions.length) warnings.push('На листе «Посещаемость» не нашлось дат в первой строке.');
      if (!posRows.length) warnings.push('На листе «Посещаемость» нет учеников.');
    } else warnings.push('Нет листа «Посещаемость» — посещаемость не посчитается.');

    const startYear = sessions.length ? (() => { const d = new Date(sessions[0].date + 'T00:00:00Z'); return d.getUTCMonth() + 1 >= 8 ? d.getUTCFullYear() : d.getUTCFullYear() - 1; })()
      : (today.getUTCMonth() + 1 >= 8 ? today.getUTCFullYear() : today.getUTCFullYear() - 1);

    /* Успеваемость: columns */
    const tasks = []; let uspRows = [];
    if (views.usp) {
      const sv = views.usp;
      const KEY = /дз|конспект|задач|правильн|пробник|макс/;
      let itemRow = 0, best = -1;
      for (let r = 0; r < Math.min(6, sv.rows); r++) { let n = 0; for (let c = 0; c < sv.cols; c++) { const v = sv.v(r, c); if (typeof v === 'string' && KEY.test(low(v))) n++; } if (n > best) { best = n; itemRow = r; } }
      const nameH = headerCell(sv, /ученик|фио/, itemRow + 1);
      const nameCol = nameH ? nameH.c : 0;
      // week label per column: a «…неделя…» label covers its merged range and the empty cells after it
      const weekOf = new Array(sv.cols).fill(null);
      for (let r = 0; r < itemRow; r++) {
        let cur = null;
        for (let c = 0; c < sv.cols; c++) {
          const v = sv.v(r, c);
          if (typeof v === 'string' && /недел/i.test(v)) { cur = v; weekOf[c] = v; continue; }
          if (v != null) { cur = null; continue; }
          if (cur && weekOf[c] == null) weekOf[c] = cur;
        }
      }
      uspRows = studentRows(sv, itemRow + 1, nameCol).map(x => ({ ...x, i: add(x.name, 'usp'), goal: ((/\(\s*(?:на|цель)?\s*([2-5](?:\s*[-–\/]\s*[2-5])?\+?)\s*\)/i.exec(x.name) || [])[1] || '').replace(/\s+/g, '').replace('–', '-') || null }));
      for (let c = 0; c < sv.cols; c++) {
        if (c === nameCol || sv.cont(itemRow, c)) continue;
        const head = sv.v(itemRow, c); const h = low(head);
        let type = null;
        if (h) {
          if (/пробник/.test(h)) type = 'mock';
          else if (/^дз|^домашн/.test(h)) type = 'hw';
          else if (/задач|правильн|самостоят|тест|срез/.test(h)) type = 'classwork';
          else if (/конспект/.test(h)) type = 'notes';
        }
        if (!type) { // classify by values
          let notes = 0, filled = 0;
          for (const x of uspRows) { const v = sv.v(x.r, c); if (v == null) continue; filled++; if (typeof v === 'string' && /^(не\s+)?прислал/.test(low(v))) notes++; }
          if (filled && notes / filled >= 0.6) type = 'notes'; else continue;
        }
        const mx = /макс\D{0,3}(\d+(?:[.,]\d+)?)/.exec(h);
        const wl = weekOf[c];
        const we = wl ? weekEnd(wl, startYear) : null;
        tasks.push({ c, type, label: head ? String(head).replace(/\s+/g, ' ').trim() : 'конспект', week: wl ? wl.replace(/\s+/g, ' ').trim() : null, weekEnd: we ? iso(we) : null, max: mx ? +mx[1].replace(',', '.') : null });
      }
      if (!tasks.some(t => t.type === 'hw')) warnings.push('На листе «Успеваемость» не нашлось столбцов с ДЗ (заголовок должен начинаться с «дз»).');
    }

    /* Пробники */
    let mocks = [], topics = [], probRows = [], probNick = null;
    if (views.prob) {
      const sv = views.prob;
      const h = headerCell(sv, /^фио|ученик/, 6) || { r: 0, c: 0 };
      for (let c = 0; c < sv.cols; c++) {
        const v = low(sv.v(h.r, c));
        if (!v || c === h.c) continue;
        if (/пробник/.test(v) && !/итог/.test(v)) mocks.push({ c, label: String(sv.v(h.r, c)).replace(/\s+/g, ' ').trim() });
        else if (probNick == null && /ник|ссылк|tg|вк|телеграм/.test(v)) probNick = c;
      }
      let sub = -1;
      for (let r = 0; r < Math.min(8, sv.rows) && sub < 0; r++) { let n = 0; for (let c = 0; c < sv.cols; c++) if (low(sv.v(r, c)) === 'балл') n++; if (n >= 2) sub = r; }
      if (sub >= 0) {
        let titleRow = -1;
        for (let r = sub; r >= 0 && titleRow < 0; r--) for (let c = 0; c < sv.cols; c++) if (/^тема/.test(low(sv.v(r, c)))) { titleRow = r; break; }
        const titleAt = c => { if (titleRow < 0) return null; for (let k = c; k >= 0; k--) { const v = sv.v(titleRow, k); if (v != null) return String(v); } return null; };
        for (let c = 0; c < sv.cols; c++) {
          if (low(sv.v(sub, c)) !== 'балл') continue;
          const title = titleAt(c);
          if (!title || /итог/i.test(title) || !/тема/i.test(title)) continue;
          const block = { title: title.replace(/\s+/g, ' ').trim(), score: c, max: null, rno: null };
          for (let k = c + 1; k < Math.min(sv.cols, c + 6); k++) { const s = low(sv.v(sub, k)); if (s === 'балл') break; if (/максим/.test(s)) block.max = k; else if (/балл с рно/.test(s)) block.rno = k; }
          topics.push(block);
        }
      }
      probRows = matchRows(studentRows(sv, Math.max(h.r, sub) + 1, h.c));
    }

    /* КЭС */
    let kesSteps = [], kesRows = [], kesMode = null, kesNick = null;
    if (views.kes) {
      const sv = views.kes;
      const stepCols = [];
      for (let c = 0; c < sv.cols; c++) { const v = low(sv.v(0, c)); if (/^(довели|подключил|добавил|провели)/.test(v)) stepCols.push(c); }
      let nameCol = 1, bestN = -1, nickBest = 0;
      for (let c = 0; c < Math.min(sv.cols, 8); c++) {
        let n = 0, at = 0;
        for (let r = 1; r < Math.min(sv.rows, 80); r++) { const v = sv.v(r, c); if (typeof v !== 'string') continue; if (/^@/.test(v)) at++; else if (matchName(v, roster)) n++; }
        if (n > bestN) { bestN = n; nameCol = c; }
        if (at > nickBest) { nickBest = at; kesNick = c; }
      }
      kesSteps = stepCols.map(c => ({ c, label: String(sv.v(0, c)).replace(/\s+/g, ' ').trim() }));
      kesRows = matchRows(studentRows(sv, 1, nameCol)).filter(x => x.m);
      kesMode = kesRows.some(x => stepCols.some(c => colorKind(sv.fill(x.r, c)) === 'green')) ? 'color' : 'value';
    }

    /* ДР */
    let drRows = [];
    if (views.dr) {
      const sv = views.dr;
      let dateCol = -1, bestD = 0;
      for (let c = 0; c < Math.min(sv.cols, 10); c++) { let n = 0; for (let r = 0; r < Math.min(sv.rows, 80); r++) if (isDate(sv.v(r, c))) n++; if (n > bestD) { bestD = n; dateCol = c; } }
      if (dateCol >= 0) {
        let nameCol = 0, bestN = -1;
        for (let c = 0; c < Math.min(sv.cols, 10); c++) { if (c === dateCol) continue; let n = 0; for (let r = 0; r < Math.min(sv.rows, 80); r++) { const v = sv.v(r, c); if (typeof v === 'string' && matchName(v, roster)) n++; } if (n > bestN) { bestN = n; nameCol = c; } }
        const cand = [];
        for (let r = 0; r < sv.rows; r++) { const n = sv.v(r, nameCol), d = sv.v(r, dateCol); if (typeof n === 'string' && isDate(d)) cand.push({ name: n, bd: pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) }); }
        drRows = matchRows(cand).filter(x => x.m).map(x => ({ i: x.m.i, bd: x.bd }));
      }
    }

    /* ---------- assemble students ---------- */
    const students = roster.map(r => ({ name: r.name, goal: null, nick: null, birthday: null, att: '', task: [], mocks: [], topics: [], kes: null, flags: [] }));
    const flag = (i, text) => { if (!students[i].flags.includes(text)) students[i].flags.push(text); };
    for (const x of posRows) {
      const sv = views.pos; let s = '';
      for (const ses of sessions) {
        const v = sv.v(x.r, ses.c); let m = '';
        if (v != null) { const t = low(v); if (/^(был|была|\+|1|да|true|присутств)/.test(t) || v === true || v === 1) m = 'p'; else if (/^(н|нет|0|-|false|отсутств|ув|болел)/.test(t) || v === false || v === 0) m = 'a'; }
        if (!m) { const k = colorKind(sv.fill(x.r, ses.c)); m = k === 'green' ? 'p' : k === 'yellow' ? 'y' : k === 'red' ? 'a' : '.'; }
        s += m;
      }
      students[x.i].att = s;
    }
    for (const st of students) if (st.att.length !== sessions.length) st.att = '.'.repeat(sessions.length);
    for (const x of uspRows) {
      const sv = views.usp; const st = students[x.i];
      if (x.goal) st.goal = x.goal;
      st.task = tasks.map(t => {
        const v = sv.v(x.r, t.c);
        if (v == null) return null;
        if (typeof v === 'number') return v;
        const s = low(v);
        if (/^[—–-]+$/.test(s)) return '-';
        if (t.type === 'notes' || /прислал/.test(s)) return /^прислал/.test(s) ? 's' : /^не\s/.test(s) ? 'n' : null;
        const num = parseFloat(s.replace(',', '.')); return isNaN(num) ? null : num;
      });
      if (roster[x.i].src === 'usp') flag(x.i, 'нет на листе «Посещаемость»');
    }
    for (const st of students) if (st.task.length !== tasks.length) st.task = tasks.map(() => null);
    for (const x of probRows) {
      if (!x.m) continue; const sv = views.prob, st = students[x.m.i];
      if (x.m.how === 'typo') flag(x.m.i, 'имя в «Пробниках» написано иначе: ' + x.name);
      st.mocks = mocks.map(m => { const v = sv.v(x.r, m.c); return typeof v === 'number' ? v : null; });
      st.topics = topics.map(t => { const raw = sv.v(x.r, t.score), rno = t.rno != null ? sv.v(x.r, t.rno) : null, mx = t.max != null ? sv.v(x.r, t.max) : null; const s = typeof rno === 'number' ? rno : typeof raw === 'number' ? raw : null; return s == null && typeof mx !== 'number' ? null : [s, typeof mx === 'number' ? mx : null]; });
      if (probNick != null) { const n = sv.v(x.r, probNick); if (typeof n === 'string' && /^@\w/.test(n.trim())) st.nick = n.trim(); }
    }
    for (const st of students) { if (st.mocks.length !== mocks.length) st.mocks = mocks.map(() => null); if (st.topics.length !== topics.length) st.topics = topics.map(() => null); }
    for (const x of kesRows) {
      const sv = views.kes, st = students[x.m.i];
      if (x.m.how === 'typo') flag(x.m.i, 'имя в «КЭС» написано иначе: ' + x.name);
      st.kes = kesSteps.map(k => {
        if (kesMode === 'color') return colorKind(sv.fill(x.r, k.c)) === 'green' ? 1 : 0;
        const v = sv.v(x.r, k.c); return v === 1 || v === true || /^(1|да|\+)$/.test(low(v)) ? 1 : 0;
      });
      if (kesNick != null && !st.nick) { const n = sv.v(x.r, kesNick); if (typeof n === 'string' && /^@\w/.test(n.trim())) st.nick = n.trim(); }
    }
    for (const x of drRows) students[x.i].birthday = x.bd;
    for (const [i, src, name] of typos) if (src === 'usp') flag(i, 'имя в «Успеваемости» написано иначе: ' + String(name).replace(/\s*\([^)]*\)\s*/g, ' ').trim());
    // entrance mock fallback from «Успеваемость»
    const uspMock = tasks.findIndex(t => t.type === 'mock');
    const mockIdx = mocks.findIndex((m, k) => students.some(s => s.mocks[k] != null));
    students.forEach(st => {
      const fromProb = mockIdx >= 0 ? st.mocks[mockIdx] : null;
      st.entrance = fromProb != null ? fromProb : (uspMock >= 0 && typeof st.task[uspMock] === 'number' ? st.task[uspMock] : null);
    });
    if (views.kes && students.some(s => !s.kes)) students.filter(s => !s.kes).forEach(s => s.flags.push('нет на листе «КЭС»'));

    const held = sessions.map((_, j) => students.some(s => s.att[j] && s.att[j] !== '.'));
    const lastHeld = sessions.filter((_, j) => held[j]).map(s => s.date).pop() || null;
    const ref = lastHeld || iso(today);
    const graceDate = d => { const t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + 3); return iso(t); };
    // A column counts once someone has a result in it. A homework nobody has a score for yet is only "pending"
    // (often not checked yet), so it never pulls an individual student into the risk zone.
    tasks.forEach((t, k) => {
      const any = students.some(s => typeof s.task[k] === 'number' || (t.type === 'notes' && (s.task[k] === 's' || s.task[k] === 'n')));
      t.assigned = any;
      t.pending = !any && t.type === 'hw' && t.weekEnd != null && graceDate(t.weekEnd) < ref;
    });

    return {
      ok: true, version: 1,
      sheets: Object.fromEntries(Object.entries(names).map(([k, v]) => [k, !!v])),
      sessions: sessions.map(({ date, kind, label }) => ({ date, kind, label })),
      tasks: tasks.map(({ type, label, week, weekEnd: we, max, assigned, pending }) => ({ type, label, week, weekEnd: we, max, assigned, pending: !!pending })),
      mocks: mocks.map(m => m.label), topics: topics.map(t => t.title), kesSteps: kesSteps.map(k => k.label.replace(/^довели до\s*/i, '')), kesMode,
      referenceDate: ref, warnings,
      students: students.map(s => ({ name: s.name, goal: s.goal, nick: s.nick, birthday: s.birthday, entrance: s.entrance, att: s.att, task: s.task, mocks: s.mocks, topics: s.topics, kes: s.kes, flags: s.flags })),
    };
  }

  /* ---------- metrics ---------- */
  const DEFAULTS = { riskAtt: 0.7, warnAtt: 0.9, warnHw: 0.5, streak: 2, scale: 'oge' };
  const SCALES = { oge: { name: 'ОГЭ', max: 31, t: [8, 15, 22] }, base: { name: 'база ЕГЭ', max: 21, t: [7, 12, 17] } };
  function grade(score, sc) { return score >= sc.t[2] ? 5 : score >= sc.t[1] ? 4 : score >= sc.t[0] ? 3 : 2; }

  function studentMetrics(model, st, settings) {
    const S = Object.assign({}, DEFAULTS, settings || {});
    const att = st.att || '';
    let present = 0, absent = 0, withNotes = 0, enrolledFrom = null;
    const marked = [];
    for (let j = 0; j < att.length; j++) {
      const m = att[j]; if (m === '.' || !m) continue;
      if (!enrolledFrom) enrolledFrom = model.sessions[j].date;
      marked.push(m);
      if (m === 'p') present++; else { absent++; if (m === 'y') withNotes++; }
    }
    const lastP = marked.lastIndexOf('p');
    const streak = marked.length - (lastP + 1);
    const rate = present + absent ? present / (present + absent) : null;
    let hwDone = 0, hwAll = 0, cwGot = 0, cwMax = 0, cwN = 0, nSent = 0, nMarked = 0;
    model.tasks.forEach((t, k) => {
      const v = st.task[k];
      if (t.type === 'hw') {
        if (!t.assigned || v === '-') return;
        if (t.weekEnd && enrolledFrom && t.weekEnd < enrolledFrom) return;
        hwAll++; if (typeof v === 'number') hwDone++;
      } else if (t.type === 'classwork') {
        if (typeof v === 'number' && t.max) { cwGot += v; cwMax += t.max; cwN++; }
      } else if (t.type === 'notes') {
        if (t.weekEnd && enrolledFrom && t.weekEnd < enrolledFrom) return;
        if (v === 's') { nSent++; nMarked++; } else if (v === 'n') nMarked++;
      }
    });
    const hwRate = hwAll ? hwDone / hwAll : null;
    const kesDone = st.kes ? st.kes.reduce((a, b) => a + b, 0) : null;
    const kesTotal = st.kes ? st.kes.length : null;
    let status = 'ok';
    if ((rate != null && rate < S.riskAtt) || streak >= S.streak || (hwAll >= 2 && hwDone === 0)) status = 'risk';
    else if ((rate != null && rate < S.warnAtt) || (hwRate != null && hwRate < S.warnHw) || st.entrance == null) status = 'attention';
    const sc = SCALES[S.scale] || SCALES.oge;
    const g = st.entrance != null ? grade(st.entrance, sc) : null;
    const goalN = st.goal ? parseInt(st.goal, 10) : null;
    const need = goalN ? (goalN >= 5 ? sc.t[2] : goalN === 4 ? sc.t[1] : sc.t[0]) : null;
    const reasons = [];
    if (rate != null && rate < S.riskAtt) reasons.push('посещаемость ' + Math.round(rate * 100) + '%');
    if (streak >= S.streak) reasons.push(streak + ' ' + plural(streak, 'пропуск', 'пропуска', 'пропусков') + ' подряд');
    if (hwAll >= 2 && hwDone === 0) reasons.push('ни одного ДЗ');
    if (status === 'attention') {
      if (rate != null && rate < S.warnAtt) reasons.push('посещаемость ' + Math.round(rate * 100) + '%');
      if (hwRate != null && hwRate < S.warnHw) reasons.push('ДЗ ' + hwDone + ' из ' + hwAll);
      if (st.entrance == null) reasons.push('нет входного пробника');
    }
    return { present, absent, withNotes, rate, streak, enrolledFrom, hwDone, hwAll, hwRate, cwPct: cwMax ? cwGot / cwMax : null, cwN, nSent, nMarked,
      notesRate: nMarked ? nSent / nMarked : null, kesDone, kesTotal, status, reasons, grade: g, need, gap: need != null && st.entrance != null ? need - st.entrance : null };
  }

  function groupMetrics(model, settings) {
    const ms = model.students.map(st => studentMetrics(model, st, settings));
    const sum = k => ms.reduce((a, m) => a + (m[k] || 0), 0);
    const mean = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
    const cw = ms.map(m => m.cwPct).filter(v => v != null);
    const ent = model.students.map(s => s.entrance).filter(v => v != null);
    const kes = ms.filter(m => m.kesTotal).map(m => m.kesDone / m.kesTotal);
    const kpi = {
      students: model.students.length,
      attendance: sum('present') + sum('absent') ? sum('present') / (sum('present') + sum('absent')) : null,
      absences: sum('absent'),
      hw: sum('hwAll') ? sum('hwDone') / sum('hwAll') : null, hwDone: sum('hwDone'), hwAll: sum('hwAll'),
      classwork: mean(cw), notes: sum('nMarked') ? sum('nSent') / sum('nMarked') : null,
      mockMean: mean(ent), mockCount: ent.length, kes: mean(kes),
      risk: ms.filter(m => m.status === 'risk').length, attention: ms.filter(m => m.status === 'attention').length, ok: ms.filter(m => m.status === 'ok').length,
    };
    // per session
    const sessions = model.sessions.map((s, j) => {
      let p = 0, n = 0; model.students.forEach(st => { const m = st.att[j]; if (m === 'p') { p++; n++; } else if (m === 'a' || m === 'y') n++; });
      return { ...s, present: p, marked: n, rate: n ? p / n : null };
    });
    // per task
    const tasks = model.tasks.map((t, k) => {
      let done = 0, due = 0, got = 0, max = 0;
      model.students.forEach((st, i) => {
        const v = st.task[k], m = ms[i];
        if (t.type === 'hw') { if (!t.assigned || v === '-' || (t.weekEnd && m.enrolledFrom && t.weekEnd < m.enrolledFrom)) return; due++; if (typeof v === 'number') { done++; if (t.max) { got += v; max += t.max; } } }
        else if (t.type === 'notes') { if (t.weekEnd && m.enrolledFrom && t.weekEnd < m.enrolledFrom) return; if (v === 's') { done++; due++; } else if (v === 'n') due++; }
        else if (typeof v === 'number') { done++; due++; if (t.max) { got += v; max += t.max; } }
      });
      return { ...t, done, due, rate: due ? done / due : null, avgPct: max ? got / max : null };
    });
    // per week (from task weeks + session dates)
    const weekMap = new Map();
    model.tasks.forEach((t, k) => { if (!t.week) return; if (!weekMap.has(t.week)) weekMap.set(t.week, { label: t.week, end: t.weekEnd, tasks: [] }); weekMap.get(t.week).tasks.push(k); });
    const weeks = [...weekMap.values()].filter(w => w.end).sort((a, b) => a.end < b.end ? -1 : 1).map(w => {
      const endD = new Date(w.end + 'T00:00:00Z'), start = new Date(endD); start.setUTCDate(start.getUTCDate() - 6);
      let p = 0, n = 0; sessions.forEach(s => { const d = new Date(s.date + 'T00:00:00Z'); if (d >= start && d <= endD) { p += s.present; n += s.marked; } });
      const hw = w.tasks.map(k => tasks[k]).filter(t => t.type === 'hw' && t.assigned && t.due);
      const nt = w.tasks.map(k => tasks[k]).filter(t => t.type === 'notes' && t.due);
      const short = (/\(([^)]*)\)/.exec(w.label) || [])[1] || w.label;
      return { label: w.label, short, end: w.end, attendance: n ? p / n : null,
        hw: hw.reduce((a, t) => a + t.due, 0) ? hw.reduce((a, t) => a + t.done, 0) / hw.reduce((a, t) => a + t.due, 0) : null,
        notes: nt.reduce((a, t) => a + t.due, 0) ? nt.reduce((a, t) => a + t.done, 0) / nt.reduce((a, t) => a + t.due, 0) : null };
    });
    const topics = model.topics.map((title, k) => {
      let done = 0, got = 0, max = 0;
      model.students.forEach(st => { const v = st.topics && st.topics[k]; if (v && v[0] != null) { done++; if (v[1]) { got += v[0]; max += v[1]; } } });
      return { title, done, avgPct: max ? got / max : null };
    });
    const kesSteps = model.kesSteps.map((label, k) => ({ label, done: model.students.filter(st => st.kes && st.kes[k]).length, total: model.students.filter(st => st.kes).length }));
    return { students: ms, kpi, sessions, tasks, weeks, topics, kesSteps };
  }

  const api = { parseWorkbook, studentMetrics, groupMetrics, normName, matchName, colorKind, plural, SCALES, DEFAULTS, grade };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.TutorParser = api;
})(typeof window !== 'undefined' ? window : globalThis);
