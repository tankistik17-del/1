// Пульт удержания — клиентская логика.
// Портировано из прототипа-артефакта: расчёты индекса сохранены 1-в-1,
// хранилище заменено с IndexedDB/localStorage на API сервера.
import { extractGroupsFromSheets } from '/shared/grouping.mjs';

async function api(path, body) {
  const opts = body !== undefined
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : {};
  const r = await fetch(path, opts);
  if (r.status === 401) { location.href = '/login.html'; throw new Error('unauthorized'); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}

Vue.createApp({
  data() {
    return {
      state: {
        booted: false,
        me: { username: '', role: '', displayName: '' },
        screen: 'overview', groupCode: 'БГ-3', studentId: 's-04',
        groupSort: 'risk', studentSort: 'index', studentSortDir: 'asc',
        zoneFilter: 'all', timelineFilter: 'all',
        clock: '—:—', calledStudents: {}, theme: 'light',
        loadedGroups: [], groupDeltas: {}, demo: true, uploading: false,
        gsUrl: '', gsModal: false, gsSyncing: false, gsLastSync: null,
      },
    };
  },
  computed: {
    R() { return this.renderVals(); },
  },
  created() { this._sCache = {}; },
  watch: {
    'state.theme'(t) {
      document.documentElement.dataset.theme = t;
      try { localStorage.setItem('retention.theme', t); } catch (e) {}
    },
    'state.screen'() { window.scrollTo({ top: 0, behavior: 'smooth' }); },
  },
  async mounted() {
    try {
      const theme = localStorage.getItem('retention.theme') || 'light';
      this.state.theme = theme;
      document.documentElement.dataset.theme = theme;
    } catch (e) { document.documentElement.dataset.theme = 'light'; }
    const tick = () => {
      const d = new Date();
      this.state.clock = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
    };
    tick();
    this._tick = setInterval(tick, 30000);
    this._fileInput = document.createElement('input');
    this._fileInput.type = 'file'; this._fileInput.accept = '.xlsx,.xls'; this._fileInput.multiple = true; this._fileInput.style.display = 'none';
    document.body.appendChild(this._fileInput);
    this._fileInput.addEventListener('change', e => { if (e.target.files && e.target.files.length) this._handleFiles(e.target.files); e.target.value = ''; });
    document.addEventListener('dragover', e => e.preventDefault());
    document.addEventListener('drop', e => { e.preventDefault(); if (e.dataTransfer.files && e.dataTransfer.files.length) this._handleFiles(e.dataTransfer.files); });
    await this._refreshFromServer();
    this.state.booted = true;
    // периодически подтягиваем данные с сервера (автообновление без перезагрузки)
    this._poll = setInterval(() => this._refreshFromServer().catch(() => {}), 5 * 60 * 1000);
  },
  beforeUnmount() { clearInterval(this._tick); clearInterval(this._poll); if (this._fileInput) this._fileInput.remove(); },

  methods: {
    setState(patch) { Object.assign(this.state, patch); },

    /* ===== СЕРВЕР ===== */
    async _refreshFromServer() {
      const data = await api('/api/state');
      const lg = data.groups.map(g => {
        const M = this._buildModel(g.journal);
        if (!M) return null;
        const MK = g.mocks ? this._parseMocks(g.mocks) : null;
        return { id: 'g-' + g.name, name: g.name, M, MK };
      }).filter(Boolean);

      const snapsByGroup = {};
      for (const s of data.snapshots) (snapsByGroup[s.groupName] = snapsByGroup[s.groupName] || []).push(s);
      const gd = {};
      const toPush = [];
      for (const g of lg) {
        const comp = this._computeStudents(g.M, g.MK, this._cfg());
        const n = comp.length; if (!n) continue;
        const ai = Math.round(comp.reduce((s, o) => s + (100 - o.a.score), 0) / n);
        const wk = this._cwk(g.M);
        const snaps = (snapsByGroup[g.name] || []).sort((a, b) => a.weekKey - b.weekKey);
        const prev = [...snaps].reverse().find(s => s.weekKey !== wk);
        if (prev && prev.kpi && prev.kpi.avgIndex != null) {
          const d = ai - prev.kpi.avgIndex;
          gd[g.name] = d === 0 ? '0' : (d > 0 ? '+' + d : '−' + Math.abs(d));
        }
        toPush.push({
          groupName: g.name, weekKey: wk,
          perStudent: comp.map(o => ({ name: o.s.name, score: o.a.score, level: o.a.level, recent: o.a.recent, drop: o.a.drop, ghost: o.a.ghost })),
          kpi: { green: comp.filter(o => o.a.level === 'green').length, amber: comp.filter(o => o.a.level === 'amber').length, red: comp.filter(o => o.a.level === 'red').length, avgIndex: ai },
        });
      }
      this._sCache = {};
      const groupCode = lg.length && !lg.some(g => g.name === this.state.groupCode) ? lg[0].name : this.state.groupCode;
      this.setState({
        me: data.me, loadedGroups: lg, demo: lg.length === 0, groupDeltas: gd, groupCode,
        calledStudents: data.called, gsUrl: data.gs.url, gsLastSync: data.gs.lastSync,
      });
      for (const p of toPush) api('/api/snapshots', p).catch(() => {});
    },

    async _logout() {
      try { await api('/api/logout', {}); } catch (e) {}
      location.href = '/login.html';
    },

    /* ===== ДЕМО-ДАННЫЕ (пока не загружен ни один журнал) ===== */
    _demoGroups() {
      return [
        { code: 'БГ-1', level: '9 класс · базовый', size: 18, index: 82, delta: '+4', atRisk: 1, schedule: 'Пн / Ср · 18:00' },
        { code: 'БГ-2', level: '9 класс · продвинутый', size: 22, index: 76, delta: '+1', atRisk: 2, schedule: 'Вт / Чт · 17:00' },
        { code: 'БГ-3', level: '9 класс · базовый', size: 14, index: 38, delta: '−9', atRisk: 6, schedule: 'Пн / Ср / Пт · 20:00' },
        { code: 'БГ-4', level: '8 класс · ранний старт', size: 12, index: 88, delta: '+2', atRisk: 0, schedule: 'Сб · 11:00' },
        { code: 'БГ-5', level: '9 класс · профильный', size: 16, index: 54, delta: '−3', atRisk: 4, schedule: 'Вт / Сб · 16:00' },
        { code: 'БГ-6', level: '9 класс · мини-группа', size: 19, index: 79, delta: '0', atRisk: 1, schedule: 'Ср / Пт · 17:30' },
        { code: 'БГ-7', level: '9 класс · повторение', size: 24, index: 63, delta: '−5', atRisk: 4, schedule: 'Пн / Чт · 19:00' },
        { code: 'БГ-8', level: '8 класс · интенсив', size: 22, index: 84, delta: '+6', atRisk: 1, schedule: 'Сб · 14:00' },
      ];
    },
    _demoStudents(groupCode) {
      const byGroup = {
        'БГ-1': [
          { id: 's-1-1', name: 'Артём Соколов', years: 15, school: 1567, tenure: '8 мес', index: 84, hw: 8, hwTotal: 8, attended: [1, 1, 1, 1, 1, 1], contact: '12 ноя', contactBy: 'чат', signal: 'всё ровно', signalIcon: '○' },
          { id: 's-1-2', name: 'Полина Грач', years: 14, school: 1234, tenure: 'год 2 мес', index: 91, hw: 8, hwTotal: 8, attended: [1, 1, 1, 1, 1, 1], contact: '8 ноя', contactBy: 'чат', signal: 'отличник', signalIcon: '★' },
          { id: 's-1-3', name: 'Денис Бабич', years: 15, school: 1567, tenure: '4 мес', index: 35, hw: 3, hwTotal: 8, attended: [1, 0, 0, 1, 0, 1], contact: '5 ноя', contactBy: 'звонок', signal: 'пропускает', signalIcon: '⚠' },
        ],
        'БГ-3': [
          { id: 's-3-1', name: 'Юля Барсова', years: 15, school: 1234, tenure: '3 мес', index: 22, hw: 1, hwTotal: 8, attended: [1, 0, 0, 0, 0, 0], contact: '4 дня', contactBy: 'чат', signal: 'не была 3 раза', signalIcon: '◆' },
          { id: 's-3-2', name: 'Ваня Малеев', years: 15, school: 627, tenure: '5 мес', index: 31, hw: 2, hwTotal: 8, attended: [1, 1, 0, 0, 0, 1], contact: '10 дней', contactBy: '—', signal: 'оплата задерживается', signalIcon: '⚠' },
          { id: 's-3-3', name: 'Никита Огарёв', years: 14, school: 1567, tenure: '2 мес', index: 28, hw: 1, hwTotal: 8, attended: [1, 0, 1, 0, 0, 0], contact: 'нет контакта', contactBy: '—', signal: 'не отвечает в чате', signalIcon: '◆' },
          { id: 's-04', name: 'Маша Захарова', years: 15, school: 1234, tenure: '7 мес', index: 34, hw: 2, hwTotal: 8, attended: [1, 1, 0, 0, 1, 0], contact: '6 дней', contactBy: 'чат', signal: 'просила перерыв', signalIcon: '⚠' },
          { id: 's-3-5', name: 'Лёша Зенин', years: 15, school: 627, tenure: 'год', index: 41, hw: 3, hwTotal: 8, attended: [1, 1, 1, 0, 0, 1], contact: '2 дня', contactBy: 'звонок', signal: 'на грани', signalIcon: '◐' },
          { id: 's-3-6', name: 'Артур Поляков', years: 15, school: 1567, tenure: '4 мес', index: 39, hw: 2, hwTotal: 8, attended: [1, 1, 0, 1, 0, 0], contact: '5 дней', contactBy: 'чат', signal: 'оплата задерживается', signalIcon: '⚠' },
          { id: 's-3-7', name: 'Кира Лю', years: 14, school: 1234, tenure: '8 мес', index: 58, hw: 5, hwTotal: 8, attended: [1, 1, 1, 1, 0, 1], contact: 'вчера', contactBy: 'чат', signal: 'стабилизируется', signalIcon: '◐' },
          { id: 's-3-8', name: 'Витя Гладков', years: 15, school: 627, tenure: '6 мес', index: 64, hw: 6, hwTotal: 8, attended: [1, 1, 1, 0, 1, 1], contact: '3 дня', contactBy: 'чат', signal: 'возвращается', signalIcon: '◐' },
          { id: 's-3-9', name: 'Аня Ким', years: 14, school: 1234, tenure: '11 мес', index: 78, hw: 8, hwTotal: 8, attended: [1, 1, 1, 1, 1, 1], contact: 'неделя', contactBy: 'чат', signal: 'всё ровно', signalIcon: '○' },
          { id: 's-3-10', name: 'Миша Решетников', years: 15, school: 1567, tenure: 'год 3 мес', index: 85, hw: 8, hwTotal: 8, attended: [1, 1, 1, 1, 1, 1], contact: '2 нед', contactBy: 'чат', signal: 'отличник', signalIcon: '★' },
        ],
      };
      if (byGroup[groupCode]) return byGroup[groupCode];
      const g = this._demoGroups().find(x => x.code === groupCode); if (!g) return [];
      const out = [];
      const firsts = ['Алиса', 'Богдан', 'Вера', 'Глеб', 'Дина', 'Егор', 'Жанна', 'Зоя', 'Илья', 'Ким', 'Лиза', 'Марк', 'Нина', 'Олег', 'Пётр', 'Рита', 'Соня', 'Тима', 'Уля', 'Федя', 'Хая', 'Цой', 'Шура', 'Юра', 'Яна'];
      const lasts = ['Тер', 'Чу', 'Минин', 'Ивин', 'Лак', 'Сник', 'Рост', 'Грач', 'Винц', 'Лоу', 'Морч', 'Кон', 'Або', 'Сан', 'Жук', 'Лом', 'Ким', 'Чи', 'Ган', 'Хр', 'Сан', 'Лин', 'Бах', 'Юн', 'Кра'];
      for (let i = 0; i < g.size; i++) {
        const idx = Math.max(8, Math.min(98, Math.round(g.index + Math.sin(i * 1.7) * 22)));
        const hw = Math.max(0, Math.min(8, Math.round(idx / 13)));
        out.push({ id: g.code + '-' + i, name: firsts[i % firsts.length] + ' ' + lasts[(i * 3) % lasts.length], years: 14 + (i % 2), school: [1234, 1567, 627, 444][i % 4], tenure: (3 + (i % 18)) + ' мес', index: idx, hw, hwTotal: 8, attended: [0, 1, 2, 3, 4, 5].map(j => ((i + j) % 5 === 0 || (idx < 35 && j > 2)) ? 0 : 1), contact: ['вчера', '2 дня', '3 дня', 'неделя', '2 нед'][i % 5], contactBy: ['чат', 'звонок', '—', 'чат', 'чат'][i % 5], signal: idx < 40 ? 'требует внимания' : idx < 70 ? 'на грани' : 'всё ровно', signalIcon: idx < 40 ? '⚠' : idx < 70 ? '◐' : '○' });
      }
      return out;
    },

    /* ===== РАЗБОР ЖУРНАЛА И РАСЧЁТ ИНДЕКСА (без изменений) ===== */
    _cv(x) { return String(x == null ? '' : x).trim(); },
    _tok(s) { return String(s).toLowerCase().replace(/[^а-яёa-z ]/g, ' ').split(/\s+/).filter(Boolean).sort().join(' '); },
    _wc(c, W) { for (let i = 0; i < W.length; i++) if (c >= W[i].s && c <= W[i].e) return i; return W.length - 1; },
    _cfg() { return { recentWeeks: 4, low: 60, ghostW: 2, wLow: 55, wDrop: 45, red: 50, amber: 24, price: 6400, recentMocks: 3, mockLow: 60, mockWeight: 40 }; },

    _buildModel(rows) {
      if (!rows || rows.length < 2) return null;
      const maxc = Math.max(...rows.map(r => r.length));
      let nc = 0;
      outer: for (let r = 0; r < Math.min(3, rows.length); r++) for (let c = 0; c < rows[r].length; c++) if (/учен|фио/i.test(this._cv(rows[r][c]))) { nc = c; break outer; }
      const si = []; for (let r = 0; r < rows.length; r++) { const n = this._cv(rows[r][nc]); if (n && !/учен|фио/i.test(n)) si.push(r); }
      if (!si.length) return null;
      const a0 = nc + 1, a1 = maxc - 1; if (a1 < a0) return null;
      let ws = [];
      for (let c = a0; c <= a1; c++) for (let r = 0; r < Math.min(3, rows.length); r++) if (/недел/i.test(this._cv(rows[r][c]))) { ws.push(c); break; }
      let weeks;
      if (ws.length >= 2) weeks = ws.map((s, i) => ({ s, e: i + 1 < ws.length ? ws[i + 1] - 1 : a1 }));
      else { weeks = []; for (let s = a0; s <= a1; s += 3) weeks.push({ s, e: Math.min(s + 2, a1) }); }
      const active = {};
      for (let c = a0; c <= a1; c++) active[c] = si.some(r => this._cv(rows[r][c]) !== '');
      const hwRe = /(?:^|[^а-яё])дз(?:[^а-яё]|$)|д\/з|домаш/i;
      const hwOnly = {}; let anyHW = false;
      for (let c = a0; c <= a1; c++) {
        let hdr = ''; for (let r = 0; r < Math.min(3, rows.length); r++) hdr += ' ' + this._cv(rows[r][c]);
        hwOnly[c] = hwRe.test(hdr);
        if (hwOnly[c]) anyHW = true;
      }
      if (!anyHW) { const skipRe = /пробник|конспект|контрольн|итог|средн|процент|сумм|общ|%/i; for (let c = a0; c <= a1; c++) { let hdr = ''; for (let r = 0; r < Math.min(3, rows.length); r++) hdr += ' ' + this._cv(rows[r][c]); hwOnly[c] = !skipRe.test(hdr); } }
      const colMax = {};
      for (let c = a0; c <= a1; c++) {
        if (!hwOnly[c]) { colMax[c] = 0; continue; }
        let hdr = ''; for (let r = 0; r < Math.min(3, rows.length); r++) hdr += ' ' + this._cv(rows[r][c]);
        const m = hdr.match(/макс[\s.:]*?(\d+(?:[.,]\d+)?)/i);
        if (m) { colMax[c] = parseFloat(m[1].replace(',', '.')); continue; }
        let mx = 0;
        for (const sr of si) { const v = this._cv(rows[sr][c]); const n = parseFloat(String(v).replace(',', '.')); if (!isNaN(n) && n > mx) mx = n; }
        colMax[c] = mx;
      }
      return { nc, a0, a1, weeks, active, hwOnly, colMax, students: si.map(r => ({ name: this._cv(rows[r][nc]), row: rows[r] })) };
    },

    _parseMocks(rows) {
      if (!rows || rows.length < 2) return null;
      let hr = 0; for (let r = 0; r < Math.min(5, rows.length); r++) { if (rows[r].some(x => /фио|пробник/i.test(this._cv(x)))) { hr = r; break; } }
      const hdr = rows[hr];
      let nc = hdr.findIndex(x => /фио|учен/i.test(this._cv(x))); if (nc < 0) nc = 0;
      const pc = hdr.findIndex(x => /процент/i.test(this._cv(x)));
      const mc = []; hdr.forEach((x, i) => { if (/^\s*пробник\s*\d+/i.test(this._cv(x)) && (pc < 0 || i < pc)) mc.push(i); });
      if (!mc.length) return null;
      const students = [];
      for (let r = hr + 1; r < rows.length; r++) { const n = this._cv(rows[r][nc]); if (!n || /фио|групп|куратор|учен/i.test(n)) continue; students.push({ name: n, mocks: mc.map(c => this._cv(rows[r][c])), pct: pc >= 0 ? this._cv(rows[r][pc]) : '' }); }
      if (!students.length) return null;
      const NM = mc.length, active = [];
      for (let i = 0; i < NM; i++) active[i] = students.some(s => this._cv(s.mocks[i]) !== '');
      const byTok = {}; students.forEach(s => byTok[this._tok(s.name)] = s);
      return { students, NM, active, byTok };
    },

    _assess(row, M, cfg) {
      const { a0, a1, weeks: W, active } = M;
      const data = []; for (let c = a0; c <= a1; c++) if (this._cv(row[c]) !== '') data.push(c);
      if (!data.length) return { score: 0, level: 'green', none: true, reasons: [] };
      const fW = this._wc(Math.min(...data), W), lW = this._wc(Math.max(...data), W);
      let lcW = 0; for (let c = a0; c <= a1; c++) if (active[c]) lcW = Math.max(lcW, this._wc(c, W));
      const tot = W.length, rf = Math.max(fW, tot - cfg.recentWeeks);
      const rate = (lo, hi) => { const cl = []; for (let c = a0; c <= a1; c++) { if (!active[c]) continue; if (M.hwOnly && !M.hwOnly[c]) continue; const w = this._wc(c, W); if (w < lo || w > hi || w < fW) continue; const v = this._cv(row[c]); cl.push(v === '' ? 0 : (/не\s*присл/i.test(v) ? 0 : 1)); } return cl.length ? cl.reduce((a, b) => a + b, 0) / cl.length : null; };
      const recent = rate(rf, tot - 1), earlier = rate(fW, rf - 1), overall = rate(fW, tot - 1);
      const gap = lcW - lW, ghost = gap >= cfg.ghostW;
      const lt = cfg.low / 100, rfs = recent != null ? recent : overall != null ? overall : 0.5;
      const ls = Math.max(0, Math.min(1, (lt - rfs) / lt));
      const drop = (earlier != null && recent != null) ? Math.max(0, earlier - recent) : 0;
      const ds = Math.max(0, Math.min(1, drop / 0.4));
      let score = cfg.wLow * ls + cfg.wDrop * ds + (ghost ? 15 : 0);
      score = Math.max(0, Math.min(100, Math.round(score)));
      const level = score >= cfg.red ? 'red' : score >= cfg.amber ? 'amber' : 'green';
      const reasons = [];
      if (ghost) reasons.push({ c: 'c-ghost', t: `Пропал(а) ${gap} нед` });
      if (drop >= 0.12) reasons.push({ c: 'c-drop', t: `Спад −${Math.round(drop * 100)} п.п.` });
      if (recent != null && recent < lt && !ghost) reasons.push({ c: 'c-fresh', t: `Свежая ${Math.round(recent * 100)}%` });
      if (overall != null && overall < lt) reasons.push({ c: 'c-course', t: `За курс ${Math.round(overall * 100)}%` });
      return { score, level, recent, earlier, overall, drop, ghost, gap, reasons };
    },

    _mockAssess(rec, MK, cfg) {
      if (!rec || !rec.mocks || !rec.mocks.some(x => this._cv(x) !== '')) return null;
      const { NM, active } = MK, mocks = rec.mocks;
      const data = []; for (let i = 0; i < NM; i++) if (this._cv(mocks[i]) !== '') data.push(i);
      const first = Math.min(...data), rf = Math.max(first, NM - cfg.recentMocks);
      const rate = (lo, hi) => { const cl = []; for (let i = 0; i < NM; i++) { if (!active[i] || i < lo || i > hi || i < first) continue; const v = this._cv(mocks[i]); cl.push(v === '' ? 0 : (/не\s*сдан/i.test(v) ? 0 : 1)); } return cl.length ? cl.reduce((a, b) => a + b, 0) / cl.length : null; };
      const recent = rate(rf, NM - 1), earlier = rate(first, rf - 1);
      let mr = 0; for (let i = rf; i < NM; i++) { if (!active[i]) continue; const v = this._cv(mocks[i]); if (v === '' || /не\s*сдан/i.test(v)) mr++; }
      const lt = cfg.mockLow / 100, rfs = recent != null ? recent : 0.5;
      const ls = Math.max(0, Math.min(1, (lt - rfs) / lt));
      const drop = (earlier != null && recent != null) ? Math.max(0, earlier - recent) : 0;
      let score = cfg.wLow * ls + cfg.wDrop * Math.max(0, Math.min(1, drop / 0.4));
      score = Math.max(0, Math.min(100, Math.round(score)));
      return { score, recent, earlier, drop, missedRecent: mr };
    },

    _computeStudents(M, MK, c) {
      const all = M.students.map(s => {
        const hw = this._assess(s.row, M, c); if (hw.none) return null;
        const mk = MK ? this._mockAssess(MK.byTok[this._tok(s.name)], MK, c) : null;
        const mw = MK ? Math.max(0, Math.min(100, c.mockWeight)) : 0;
        let score = hw.score; if (mk) score = Math.round(((100 - mw) * hw.score + mw * mk.score) / 100);
        const level = score >= c.red ? 'red' : score >= c.amber ? 'amber' : 'green';
        const reasons = hw.reasons.slice();
        if (mk) { if (mk.missedRecent > 0) reasons.push({ c: 'c-mock', t: `Пробники: пропустил ${mk.missedRecent}` }); else if (mk.recent != null && mk.recent < c.mockLow / 100) reasons.push({ c: 'c-mock', t: `Пробники ${Math.round(mk.recent * 100)}%` }); }
        return { s, a: { score, level, recent: hw.recent, earlier: hw.earlier, overall: hw.overall, drop: hw.drop, ghost: hw.ghost, gap: hw.gap, reasons }, mk };
      }).filter(Boolean);
      all.sort((x, y) => y.a.score - x.a.score);
      return all;
    },

    _groupStats(g) {
      const all = this._computeStudents(g.M, g.MK, this._cfg());
      return { all, red: all.filter(o => o.a.level === 'red'), amber: all.filter(o => o.a.level === 'amber'), green: all.filter(o => o.a.level === 'green') };
    },

    _cwk(M) { let l = 0; for (let c = M.a0; c <= M.a1; c++) if (M.active[c]) l = Math.max(l, this._wc(c, M.weeks)); return l; },

    _wkAtt(s, M, n) {
      const { a0, a1, weeks, active } = M, row = s.row;
      let fc = a1 + 1; for (let c = a0; c <= a1; c++) { if (this._cv(row[c]) !== '') { fc = c; break; } }
      return weeks.slice(-n).map(w => {
        for (let c = w.s; c <= w.e; c++) { if (!active[c]) continue; if (M.hwOnly && !M.hwOnly[c]) continue; if (c < fc) return 'var(--bar-bg)'; const v = this._cv(row[c]); return (v && !/не\s*присл/i.test(v)) ? '#6FA86B' : 'rgba(194,101,76,.5)'; }
        return 'var(--bar-bg)';
      });
    },

    _calcHWStats(s, M) {
      const { a0, a1, active, hwOnly, colMax } = M, row = s.row;
      let fc = a1 + 1; for (let c = a0; c <= a1; c++) { if (this._cv(row[c]) !== '') { fc = c; break; } }
      let total = 0, done = 0, missed = 0, pcts = [], scores = [];
      for (let c = a0; c <= a1; c++) {
        if (!active[c] || c < fc) continue;
        if (hwOnly && !hwOnly[c]) continue;
        total++;
        const v = this._cv(row[c]);
        if (v === '' || /не\s*присл/i.test(v)) { missed++; continue; }
        done++;
        const n = parseFloat(String(v).replace(',', '.'));
        if (!isNaN(n) && n > 0) {
          scores.push(n);
          const mx = colMax && colMax[c] > 0 ? colMax[c] : 0;
          if (mx > 0) pcts.push(Math.min(100, n / mx * 100));
        }
      }
      const pD = total > 0 ? Math.round(done / total * 100) : 0, pM = total > 0 ? Math.round(missed / total * 100) : 0;
      const avg = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10 : null;
      const avgPct = pcts.length > 0 ? Math.round(pcts.reduce((a, b) => a + b, 0) / pcts.length) : null;
      return { total, done, missed, pD, pM, avg, avgPct, hasScores: pcts.length > 0 };
    },

    _calcMockStats(rec, MK) {
      if (!rec || !MK) return null;
      const { NM, active } = MK; let total = 0, done = 0, missed = 0, scores = [];
      for (let i = 0; i < NM; i++) { if (!active[i]) continue; total++; const v = this._cv(rec.mocks[i]); if (v === '' || /не\s*сдан/i.test(v)) { missed++; } else { done++; const n = parseFloat(v.replace(',', '.')); if (!isNaN(n)) scores.push({ i, n }); } }
      const avg = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b.n, 0) / scores.length * 10) / 10 : null;
      const h = Math.ceil(scores.length / 2), sl = scores.slice(0, h), sr = scores.slice(h);
      const aA = sl.length ? sl.reduce((a, b) => a + b.n, 0) / sl.length : null, aB = sr.length ? sr.reduce((a, b) => a + b.n, 0) / sr.length : null;
      const trend = (aA != null && aB != null) ? Math.round((aB - aA) * 10) / 10 : null;
      return { total, done, missed, pD: total > 0 ? Math.round(done / total * 100) : 0, avg, trend, hasScores: scores.length > 0 };
    },

    /* ===== ЗАГРУЗКА .XLSX (разбор в браузере, хранение на сервере) ===== */
    _sr(ws) { return XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: false }); },

    async _handleFiles(fl) {
      if (typeof XLSX === 'undefined') { alert('Библиотека XLSX не загружена. Обновите страницу.'); return; }
      this.setState({ uploading: true });
      const collected = [];
      for (const f of [...fl]) {
        try {
          const buf = await f.arrayBuffer();
          const wb = XLSX.read(new Uint8Array(buf), { type: 'array' });
          const sheets = wb.SheetNames.map(n => ({ name: n, rows: this._sr(wb.Sheets[n]) }));
          for (const g of extractGroupsFromSheets(sheets, f.name)) collected.push(g);
        } catch (e) { console.error(e); }
      }
      try {
        if (collected.length) {
          await api('/api/groups/ingest', { groups: collected });
          await this._refreshFromServer();
          this.setState({ screen: 'overview' });
        } else {
          alert('Не удалось распознать журнал в файле: нужны колонки «ученик» и «неделя».');
        }
      } catch (e) {
        alert('Не удалось сохранить данные на сервере:\n' + e.message);
      }
      this.setState({ uploading: false });
    },

    /* ===== GOOGLE SHEETS (синхронизация выполняется сервером) ===== */
    async _syncGoogle() {
      if (!this.state.gsUrl) { this.setState({ gsModal: true }); return; }
      this.setState({ gsSyncing: true });
      try {
        await api('/api/sync', {});
        await this._refreshFromServer();
        this.setState({ screen: 'overview', gsModal: false });
      } catch (e) {
        alert('Не удалось синхронизировать с Google Sheets:\n\n' + e.message + '\n\nПроверь URL веб-приложения и токен.');
      }
      this.setState({ gsSyncing: false });
    },

    async _saveGsConfig(url, token) {
      try { await api('/api/gs-config', { url, token }); } catch (e) { alert('Не удалось сохранить настройки: ' + e.message); }
      this.setState({ gsUrl: url || '' });
    },

    async _renameGroup(oldName, newName) {
      newName = String(newName || '').trim();
      if (!newName || newName === oldName) return;
      try {
        await api('/api/groups/rename', { oldName, newName });
        if (this.state.groupCode === oldName) this.setState({ groupCode: newName });
        await this._refreshFromServer();
      } catch (e) { alert(e.message); }
    },

    /* ===== ДАННЫЕ ДЛЯ ЭКРАНОВ ===== */
    groups() {
      if (this.state.demo || !this.state.loadedGroups.length) return this._demoGroups();
      return this.state.loadedGroups.map(g => {
        const st = this._groupStats(g), n = st.all.length;
        const ai = n > 0 ? Math.round(st.all.reduce((s, o) => s + (100 - o.a.score), 0) / n) : 100;
        return { code: g.name, level: `${n} уч.${g.MK ? ' · с пробниками' : ''}`, size: n, index: ai, delta: this.state.groupDeltas[g.name] || '—', atRisk: st.red.length + st.amber.length, schedule: '' };
      });
    },

    students(gc) {
      if (this.state.demo || !this.state.loadedGroups.length) return this._demoStudents(gc);
      if (this._sCache[gc]) return this._sCache[gc];
      const g = this.state.loadedGroups.find(x => x.name === gc); if (!g) return [];
      const comp = this._computeStudents(g.M, g.MK, this._cfg());
      const res = comp.map(o => {
        const { a, s, mk } = o, idx = Math.max(0, 100 - a.score);
        const mkRec = g.MK ? g.MK.byTok[this._tok(s.name)] : null;
        return { id: gc + '|' + s.name, name: s.name, years: null, school: null, tenure: null, index: idx, hw: a.recent != null ? Math.round(a.recent * 8) : 0, hwTotal: 8, attended: this._wkAtt(s, g.M, 6), contact: '—', contactBy: '—', signal: a.reasons.length > 0 ? a.reasons[0].t : 'всё ровно', signalIcon: a.level === 'red' ? '◆' : a.level === 'amber' ? '⚠' : '○', _real: true, _level: a.level, _reasons: a.reasons, _recent: a.recent, _earlier: a.earlier, _overall: a.overall, _drop: a.drop, _ghost: a.ghost, _gap: a.gap, _mk: mk, _mkRec: mkRec, _MK: g.MK, _row: s.row, _M: g.M, _groupCode: gc };
      });
      this._sCache[gc] = res;
      return res;
    },

    /* ===== ХЕЛПЕРЫ ===== */
    zoneColor(idx) { return idx < 40 ? '#C2654C' : idx < 70 ? '#D9A24A' : '#6FA86B'; },
    zoneSoft(idx) { return idx < 40 ? 'rgba(194,101,76,.16)' : idx < 70 ? 'rgba(217,162,74,.18)' : 'rgba(111,168,107,.18)'; },
    zoneText(idx) { return this.state.theme === 'dark' ? (idx < 40 ? '#E68B6E' : idx < 70 ? '#E8B36A' : '#85C27F') : (idx < 40 ? '#A53F2A' : idx < 70 ? '#8C6315' : '#4E8C4A'); },
    zoneOf(idx) { return idx < 40 ? 'red' : idx < 70 ? 'amber' : 'green'; },
    avatarColor(name) { const p = ['#C2956B', '#7B8E5C', '#8B6F9C', '#5F8AA8', '#C26B6B', '#6BA09C', '#B07A4A', '#7B7BA8']; let h = 0; for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff; return p[h % p.length]; },
    initials(name) { return String(name || '?').split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase(); },
    _nw(n, one, few, many) { const a = Math.abs(n), m = a % 10, h = a % 100; if (h >= 11 && h <= 19) return n + ' ' + many; if (m === 1) return n + ' ' + one; if (m >= 2 && m <= 4) return n + ' ' + few; return n + ' ' + many; },
    go(sc, ex) { this.setState({ screen: sc, ...(ex || {}) }); },

    /* ===== ЗНАЧЕНИЯ ДЛЯ ШАБЛОНА ===== */
    renderVals() {
      const s = this.state, isDark = s.theme === 'dark', isReal = !s.demo && s.loadedGroups.length > 0;
      const groups = this.groups();

      const tabs = [{ num: '01', label: 'Обзор', key: 'overview' }, { num: '02', label: 'Группа', key: 'group' }, { num: '03', label: 'Карточка ученика', key: 'student' }]
        .map(t => ({ ...t, bg: s.screen === t.key ? 'var(--invert-bg)' : 'transparent', color: s.screen === t.key ? 'var(--invert-fg)' : 'var(--text-soft)', hoverClass: s.screen === t.key ? '' : 'hov-strong', onClick: () => this.go(t.key) }));

      const [themeLightBg, themeLightFg, themeDarkBg, themeDarkFg] = [!isDark ? '#F4EFE6' : 'transparent', !isDark ? '#1F1B16' : 'var(--text-muted)', isDark ? '#1F1B16' : 'transparent', isDark ? '#F4EFE6' : 'var(--text-muted)'];

      const totalStudents = groups.reduce((s2, g) => s2 + g.size, 0);
      const totalRisk = groups.reduce((s2, g) => s2 + g.atRisk, 0);
      const avgIndex = groups.length > 0 ? Math.round(groups.reduce((s2, g) => s2 + g.index * g.size, 0) / Math.max(totalStudents, 1)) : (isReal ? 0 : 71);

      const headlineMain = isReal ? this._nw(groups.length, 'группа', 'группы', 'групп') + ',' : 'Восемь групп,';
      const headlineSub = isReal ? (totalRisk === 0 ? 'все активны.' : this._nw(totalRisk, 'просит', 'просят', 'просят') + ' внимания.') : 'три просят внимания.';

      const weekLabel = isReal
        ? new Date().toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
        : 'неделя 18–24 ноя · демо';

      const histogram = (() => {
        if (!isReal) { const h = [4, 6, 8, 12, 15, 18, 16, 12, 10, 8, 12, 18, 22, 28, 32, 30, 26, 20, 14, 10, 8, 7, 9, 12, 16, 22, 30, 36, 40, 44, 46, 44, 40, 36, 30, 26, 22, 18, 14, 10, 8, 6, 5, 4, 3, 3, 3, 4, 5, 6]; return h.map((v, i) => { const val = (i / (h.length - 1)) * 100; return { h: Math.max(3, v * 1.6) + 'px', color: this.zoneColor(val), tip: `Индекс ≈${Math.round(val)} · ${this._nw(v, 'ученик', 'ученика', 'учеников')}` }; }); }
        const b = new Array(50).fill(0); groups.forEach(g => this.students(g.code).forEach(st => { b[Math.min(49, Math.floor(st.index / 2))]++; }));
        const mx = Math.max(...b, 1); return b.map((v, i) => ({ h: Math.max(v > 0 ? 3 : 0, Math.round(v / mx * 76)) + 'px', color: this.zoneColor((i / 49) * 100), tip: `Индекс ${i * 2}–${i * 2 + 2} · ${this._nw(v, 'ученик', 'ученика', 'учеников')}` }));
      })();

      const sf = { risk: (a, b) => b.atRisk - a.atRisk || a.index - b.index, index: (a, b) => a.index - b.index, size: (a, b) => b.size - a.size };
      const groupSorts = [{ key: 'risk', label: 'риск' }, { key: 'index', label: 'индекс' }, { key: 'size', label: 'размер' }]
        .map(g => ({ ...g, bg: s.groupSort === g.key ? 'var(--invert-bg)' : 'var(--chip)', color: s.groupSort === g.key ? 'var(--invert-fg)' : 'var(--text-soft)', onClick: () => this.setState({ groupSort: g.key }) }));
      const groupRows = [...groups].sort(sf[s.groupSort]).map(g => ({ ...g, indexPct: g.index + '%', indexColor: this.zoneColor(g.index), deltaColor: String(g.delta).startsWith('−') || String(g.delta).startsWith('-') ? '#C2654C' : g.delta === '0' || g.delta === '—' ? 'var(--text-faint)' : '#4E8C4A', riskBg: g.atRisk === 0 ? 'rgba(111,168,107,.18)' : g.atRisk <= 2 ? 'rgba(217,162,74,.18)' : 'rgba(194,101,76,.18)', riskColor: g.atRisk === 0 ? (isDark ? '#85C27F' : '#4E8C4A') : g.atRisk <= 2 ? (isDark ? '#E8B36A' : '#8C6315') : (isDark ? '#E68B6E' : '#A53F2A'), onClick: () => this.go('group', { groupCode: g.code }) }));

      const cg = groups.find(g => g.code === s.groupCode) || groups[0] || { code: '—', level: '—', size: 0, index: 0, delta: '—', atRisk: 0, schedule: '' };
      const currentGroup = { ...cg, indexColor: this.zoneColor(cg.index) };
      const groupChips = groups.map(g => ({ code: g.code, bg: g.code === s.groupCode ? 'var(--invert-bg)' : 'transparent', color: g.code === s.groupCode ? 'var(--invert-fg)' : 'var(--text-soft)', onClick: () => this.setState({ groupCode: g.code }) }));

      const groupSubline = isReal
        ? `журнал загружен · ведёт ${s.me.displayName || '—'}`
        : 'Математика ОГЭ · до пробника 18 занятий · ведёт Марина Кравченко';

      const raw = this.students(s.groupCode);
      const sm = { index: (a, b) => a.index - b.index, name: (a, b) => a.name.localeCompare(b.name), hw: (a, b) => a.hw - b.hw };
      const sorted = [...raw].sort(sm[s.studentSort]); if (s.studentSortDir === 'desc') sorted.reverse();
      const zc = { all: raw.length, red: 0, amber: 0, green: 0 }; raw.forEach(st => zc[this.zoneOf(st.index)]++);
      const zoneFilters = [{ key: 'all', label: 'все', dot: 'var(--text)' }, { key: 'red', label: 'уходит', dot: '#C2654C' }, { key: 'amber', label: 'шатко', dot: '#D9A24A' }, { key: 'green', label: 'держится', dot: '#6FA86B' }]
        .map(f => { const a = s.zoneFilter === f.key; return { ...f, count: zc[f.key], bg: a ? 'var(--invert-bg)' : 'transparent', color: a ? 'var(--invert-fg)' : 'var(--text-soft)', border: a ? 'var(--invert-bg)' : 'var(--border-faint)', onClick: () => this.setState({ zoneFilter: f.key }) }; });
      const studentSorts = [{ key: 'index', label: 'индекс' }, { key: 'name', label: 'имя' }, { key: 'hw', label: 'домашка' }]
        .map(o => { const a = s.studentSort === o.key; return { ...o, arrow: a ? (s.studentSortDir === 'asc' ? '↑' : '↓') : '', bg: a ? 'var(--invert-bg)' : 'var(--chip)', color: a ? 'var(--invert-fg)' : 'var(--text-soft)', onClick: () => { if (s.studentSort === o.key) this.setState({ studentSortDir: s.studentSortDir === 'asc' ? 'desc' : 'asc' }); else this.setState({ studentSort: o.key, studentSortDir: 'asc' }); } }; });
      const fr = s.zoneFilter === 'all' ? sorted : sorted.filter(st => this.zoneOf(st.index) === s.zoneFilter);
      const filteredStudents = fr.map(st => ({ ...st, initials: this.initials(st.name), avatarBg: this.avatarColor(st.name), indexPct: st.index + '%', indexColor: this.zoneSoft(st.index), signalColor: this.zoneText(st.index), attendance: st.attended.map(a => typeof a === 'number' ? (a ? '#6FA86B' : 'rgba(194,101,76,.5)') : a), meta: st.years ? `${st.years} лет · школа №${st.school} · ${st.tenure}` : st._level ? `риск: ${st._level}` : '', hw: st.hw != null ? st.hw : '—', hwTotal: st.hwTotal || 8, onClick: () => this.go('student', { studentId: st.id, groupCode: s.groupCode }) }));

      const all = groups.flatMap(g => this.students(g.code).map(st => ({ ...st, groupCode: g.code })));
      const cs = all.find(x => x.id === s.studentId) || all.find(x => x.id === 's-04') || all[0] || { name: '—', index: 50, years: null, school: null, tenure: null, _real: false, groupCode: '—' };
      const ce = s.calledStudents[cs.id];

      const signals = cs._real ? ((rns => rns.length ? rns : [{ icon: '✓', title: 'Сигналов нет', body: 'Ходит, сдаёт, на связи. Поддерживайте темп.', bg: 'rgba(111,168,107,.12)', accent: '#6FA86B' }])((cs._reasons || []).map(r => { const red = ['c-ghost', 'c-drop'].includes(r.c), amb = ['c-fresh', 'c-course'].includes(r.c); return { icon: r.c === 'c-ghost' ? '◆' : r.c === 'c-drop' ? '↘' : r.c === 'c-fresh' ? '◐' : '☆', title: r.t, body: r.c === 'c-ghost' ? `Нет активности ${cs._gap} нед — позвони первым.` : r.c === 'c-drop' ? `Свежая ${Math.round((cs._recent || 0) * 100)}% против ${Math.round((cs._earlier || 0) * 100)}% в начале.` : r.c === 'c-fresh' ? `Сдаёт ${Math.round((cs._recent || 0) * 100)}% из последних заданий.` : r.c === 'c-course' ? `Средняя за курс — ${Math.round((cs._overall || 0) * 100)}%.` : 'Проблемы с пробниками.', bg: red ? 'rgba(194,101,76,.12)' : amb ? 'rgba(217,162,74,.14)' : 'var(--chip-soft)', accent: red ? '#C2654C' : amb ? '#D9A24A' : '#6FA86B' }; })))
        : cs.index < 40 ? [{ icon: '⚠', title: 'Пропустила 3 занятия подряд', body: '13, 15 и 18 ноября — без предупреждения.', bg: 'rgba(194,101,76,.12)', accent: '#C2654C' }, { icon: '⚠', title: 'Оплата не прошла', body: 'Списание 17 ноября не выполнено. Уточнить карту.', bg: 'rgba(217,162,74,.14)', accent: '#D9A24A' }, { icon: '◐', title: 'В чате тишина с 12 ноября', body: 'Раньше отвечала ежедневно.', bg: 'var(--chip-soft)', accent: 'var(--text-dim)' }]
          : [{ icon: '✓', title: 'Сигналов нет', body: 'Ходит, сдаёт, на связи. Поддерживайте темп.', bg: 'rgba(111,168,107,.12)', accent: '#6FA86B' }];

      const factors = cs._real ? [
        { label: 'Свежая сдача дз', value: cs._recent != null ? Math.round(cs._recent * 100) + '%' : '—', pct: (cs._recent || 0) * 100 + '%', color: this.zoneColor((cs._recent || 0) * 100) },
        { label: 'Средняя за курс', value: cs._overall != null ? Math.round(cs._overall * 100) + '%' : '—', pct: (cs._overall || 0) * 100 + '%', color: this.zoneColor((cs._overall || 0) * 100) },
        ...(cs._mk ? [{ label: 'Пробники', value: cs._mk.missedRecent > 0 ? 'пропустил ' + cs._mk.missedRecent : (cs._mk.recent != null ? Math.round(cs._mk.recent * 100) + '%' : '—'), pct: (cs._mk.recent || 0) * 100 + '%', color: this.zoneColor((cs._mk.recent || 0) * 100) }] : []),
        { label: 'Спад активности', value: cs._drop > 0.1 ? '−' + Math.round(cs._drop * 100) + ' п.п.' : 'нет', pct: Math.max(0, 1 - cs._drop * 3) * 100 + '%', color: cs._drop > 0.2 ? '#C2654C' : '#6FA86B' },
      ] : [
        { label: 'Посещаемость (4 нед)', value: cs.index < 40 ? '38%' : cs.index < 70 ? '72%' : '94%', pct: (cs.index < 40 ? 38 : cs.index < 70 ? 72 : 94) + '%', color: this.zoneColor(cs.index < 40 ? 30 : cs.index < 70 ? 65 : 90) },
        { label: 'Сданные домашки', value: (cs.hw || 0) + ' / ' + (cs.hwTotal || 8), pct: ((cs.hw || 0) / (cs.hwTotal || 8) * 100) + '%', color: this.zoneColor((cs.hw || 0) / (cs.hwTotal || 8) * 100) },
        { label: 'Активность в чате', value: cs.index < 40 ? 'низкая' : cs.index < 70 ? 'средняя' : 'высокая', pct: (cs.index < 40 ? 18 : cs.index < 70 ? 55 : 88) + '%', color: this.zoneColor(cs.index < 40 ? 18 : cs.index < 70 ? 55 : 88) },
        { label: 'Оплата', value: cs.index < 40 ? 'просрочка' : 'в срок', pct: cs.index < 40 ? '20%' : '100%', color: this.zoneColor(cs.index < 40 ? 20 : 100) },
      ];

      const _hwStats = cs._real && cs._M ? this._calcHWStats({ row: cs._row }, cs._M) : null;
      const _mockStats = cs._real && cs._mkRec && cs._MK ? this._calcMockStats(cs._mkRec, cs._MK) : null;
      const _gradeColor = (n) => n >= 4.5 ? '#4E8C4A' : n >= 3.5 ? (isDark ? '#E8B36A' : '#8C6315') : (isDark ? '#E68B6E' : '#A53F2A');
      const _statBoxes = [];
      if (_hwStats && _hwStats.total > 0) {
        _statBoxes.push({ val: _hwStats.done + '/' + _hwStats.total, label: 'ДЗ решено', color: this.zoneColor(_hwStats.pD), hasPct: true, pct: _hwStats.pD + '%' });
        if (_hwStats.hasScores && _hwStats.avgPct != null) _statBoxes.push({ val: _hwStats.avgPct + '%', label: 'Средний % правильности', color: this.zoneColor(_hwStats.avgPct), hasPct: true, pct: _hwStats.avgPct + '%' });
        else if (_hwStats.missed > 0) _statBoxes.push({ val: String(_hwStats.missed), label: 'Пропущено ДЗ', color: '#C2654C', hasPct: false });
      }
      if (_mockStats && _mockStats.total > 0) {
        _statBoxes.push({ val: _mockStats.done + '/' + _mockStats.total, label: 'Пробников сдано', color: this.zoneColor(_mockStats.pD), hasPct: true, pct: _mockStats.pD + '%' });
        if (_mockStats.hasScores && _mockStats.avg != null) {
          const _tA = _mockStats.trend > 0 ? ' ↑' : _mockStats.trend < 0 ? ' ↓' : '';
          _statBoxes.push({ val: String(_mockStats.avg) + _tA, label: 'Средний балл пробников', color: _gradeColor(_mockStats.avg), hasPct: false });
        }
      }
      let _mockHistory = [], _hasMockHistory = false;
      if (cs._real && cs._mkRec && cs._MK) {
        const _mks = cs._mkRec.mocks, _NM = cs._MK.NM, _actv = cs._MK.active, _items = [];
        for (let i = 0; i < _NM; i++) { if (!_actv[i]) continue; const v = this._cv(_mks[i]); const missed = v === '' || /не\s*сдан/i.test(v); const n = missed ? null : parseFloat(String(v).replace(',', '.')); _items.push({ i, v, n: (n != null && !isNaN(n)) ? n : null, missed }); }
        const _lastN = _items.slice(-5), _allN = _items.filter(x => x.n != null).map(x => x.n);
        const _sMax = _allN.length ? Math.max(..._allN) : 0;
        const _norm = (n) => _sMax <= 5 ? n * 20 : _sMax <= 50 ? n / _sMax * 100 : Math.min(100, n);
        _mockHistory = _lastN.map(it => {
          if (it.missed) return { label: 'Пробник ' + (it.i + 1), val: '—', pct: '0%', color: '#C2654C' };
          if (it.n == null) return { label: 'Пробник ' + (it.i + 1), val: String(it.v), pct: '0%', color: 'var(--text-dim)' };
          const p = _norm(it.n);
          return { label: 'Пробник ' + (it.i + 1), val: String(it.n), pct: Math.max(4, Math.min(100, p)) + '%', color: this.zoneColor(p) };
        });
        _hasMockHistory = _mockHistory.length > 0;
      }
      const _showStats = _statBoxes.length > 0 || _hasMockHistory;

      const updatedText = isReal
        ? (s.gsLastSync ? 'синк ' + new Date(s.gsLastSync).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : 'по данным журнала')
        : 'обновлено 4 мин назад';

      const currentStudent = { ...cs, initials: this.initials(cs.name), avatarBg: this.avatarColor(cs.name), indexColor: this.zoneColor(cs.index), indexPct: cs.index + '%', trend: cs.index < 50 ? '−12' : cs.index < 70 ? '−4' : '+5', trendColor: cs.index < 50 ? '#E2A24C' : cs.index < 70 ? '#D9A24A' : '#6FA86B', calledRecently: !!ce, lastCallText: ce ? (ce.date === new Date().toISOString().slice(0, 10) ? 'Сегодня, ' + ce.time : ce.date + ', ' + ce.time) + (ce.by ? ' · ' + ce.by : '') : '', signals, signalCountText: signals.some(sig => sig.accent === '#C2654C' || sig.accent === '#D9A24A') ? `${signals.filter(sig => sig.accent !== '#6FA86B').length} сигнала активны` : 'Все показатели в норме', factors, timeline: this.buildTimeline(cs, ce), metaLine: cs.years ? `${cs.years} лет · школа №${cs.school} · занимается ${cs.tenure}` : '', showStats: _showStats, statBoxes: _statBoxes, mockHistory: _mockHistory, hasMockHistory: _hasMockHistory };

      const tlFilters = [{ key: 'all', label: 'всё' }, { key: 'attend', label: 'занятия' }, { key: 'pay', label: 'оплаты' }, { key: 'chat', label: 'контакты' }]
        .map(t => ({ ...t, bg: s.timelineFilter === t.key ? 'var(--invert-bg)' : 'transparent', color: s.timelineFilter === t.key ? 'var(--invert-fg)' : 'var(--text-soft)', onClick: () => this.setState({ timelineFilter: t.key }) }));

      const markCalled = () => {
        const d = new Date(), t = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
        const next = { ...s.calledStudents, [cs.id]: { time: t, date: d.toISOString().slice(0, 10), by: s.me.displayName } };
        this.setState({ calledStudents: next });
        api('/api/called', { studentId: cs.id }).then(r => this.setState({ calledStudents: r.called })).catch(() => {});
      };

      return {
        tabs, clock: s.clock, isOverview: s.screen === 'overview', isGroup: s.screen === 'group', isStudent: s.screen === 'student',
        toggleTheme: () => this.setState({ theme: isDark ? 'light' : 'dark' }), themeTitle: isDark ? 'Включить светлую тему' : 'Включить тёмную тему',
        themeLightBg, themeLightFg, themeDarkBg, themeDarkFg,
        headlineMain, headlineSub, weekLabel, groupSubline, updatedText,
        meName: s.me.displayName || '—', meInitials: this.initials(s.me.displayName || '?'), meRole: s.me.role === 'admin' ? 'админ' : 'репетитор',
        logout: () => this._logout(),
        totalStudents: isReal ? String(totalStudents) : '147', studentsDelta: isReal ? groups.length + ' групп загружено' : '+4 за месяц',
        avgIndex: isReal ? String(avgIndex) : '71', avgIndexDelta: isReal ? '' : '↑ 3 за неделю',
        atRiskCount: isReal ? String(totalRisk) : '19', atRiskOf: `из ${isReal ? totalStudents : 147} учеников`,
        uploadBtnLabel: s.uploading ? 'Загружаю…' : isReal ? 'Добавить файл' : 'Загрузить .xlsx',
        openFilePicker: () => this._fileInput && this._fileInput.click(),
        histogram, groupSorts, groupRows, currentGroup, groupChips, zoneFilters, studentSorts, filteredStudents,
        noStudents: filteredStudents.length === 0, goOverview: () => this.go('overview'),
        renameCurrentGroup: () => { const old = cg.code; if (!old || old === '—') return; const next = window.prompt('Новое имя группы:', old); if (next && next.trim() && next.trim() !== old) this._renameGroup(old, next.trim()); },
        currentStudent, timelineFilters: tlFilters,
        callBtnText: currentStudent.calledRecently ? 'Перезвонить' : 'Позвонила, отметить',
        markCalled, goGroupFromStudent: () => this.go('group', { groupCode: cs.groupCode || s.groupCode }),
        ...this._gsValues(s, isDark),
      };
    },

    _gsValues(s, isDark) {
      const gsHasConfig = !!s.gsUrl;
      const gsButton = {
        label: s.gsSyncing ? 'Синхрон…' : gsHasConfig ? '⟳ Sheets' : '⊕ Sheets',
        title: gsHasConfig ? 'Синхронизировать с Google Sheets (Shift+клик — настройки)' : 'Подключить Google Sheets',
        bg: gsHasConfig ? 'rgba(111,168,107,.15)' : 'var(--chip)',
        fg: gsHasConfig ? (isDark ? '#85C27F' : '#4E8C4A') : 'var(--text)',
        onClick: (e) => { if (!gsHasConfig || (e && e.shiftKey)) { this.setState({ gsModal: true }); return; } this._syncGoogle(); },
      };
      const gsLastSyncText = s.gsLastSync ? 'Обновлено ' + new Date(s.gsLastSync).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : '';
      const saveAndSync = () => {
        const u = document.getElementById('gs-url-input'), t = document.getElementById('gs-token-input');
        const url = u ? u.value.trim() : '', token = t ? t.value.trim() : '';
        this._saveGsConfig(url, token).then(() => this._syncGoogle());
      };
      const disconnectGs = () => { this._saveGsConfig('', ''); this.setState({ gsLastSync: null, gsModal: false }); };
      return {
        gsButton, gsModal: s.gsModal, closeGsModal: () => this.setState({ gsModal: false }), openGsModal: () => this.setState({ gsModal: true }),
        gsUrl: s.gsUrl, gsHasConfig, gsLastSyncText, gsSyncBtnLabel: s.gsSyncing ? 'Синхронизирую…' : 'Синхронизировать',
        gsTokenPlaceholder: gsHasConfig ? 'токен сохранён — оставьте пустым, чтобы не менять' : 'придумай любую строку, тот же токен впиши в скрипт',
        saveAndSync, disconnectGs,
      };
    },

    buildTimeline(cs, ce) {
      const f = this.state.timelineFilter;
      let base;
      if (cs._real) {
        base = [];
        if (cs._ghost) base.push({ type: 'attend', title: `Нет активности ${cs._gap} нед.`, when: 'последние занятия', body: 'Нет ни ДЗ, ни посещений — требуется звонок.', dotColor: '#C2654C' });
        if (cs._drop > 0.15) base.push({ type: 'attend', title: 'Снижение активности', when: 'последние недели', body: `Свежая сдача упала с ${Math.round((cs._earlier || 0) * 100)}% до ${Math.round((cs._recent || 0) * 100)}%.`, dotColor: '#D9A24A' });
        if (cs._mk && cs._mk.missedRecent > 0) base.push({ type: 'attend', title: `Пропустил ${cs._mk.missedRecent} пробника`, when: 'последние пробники', body: 'Не сдавал последние контрольные точки.', dotColor: '#C2654C' });
        if (!base.length) base.push({ type: 'attend', title: 'Активно занимается', when: 'последние недели', body: `Свежая сдача: ${Math.round((cs._recent || 0) * 100)}%. Сигналов нет.`, dotColor: '#6FA86B' });
      } else {
        base = cs.index < 40 ? [
          { type: 'attend', title: 'Пропуск занятия', when: 'вчера · 20:00', body: 'Не пришла, не предупредила. Тема: задачи 21 из второй части.', dotColor: '#C2654C' },
          { type: 'pay', title: 'Списание не прошло', when: '17 ноя · 09:14', body: 'Карта *4421 отклонила платёж 8 900 ₽.', dotColor: '#D9A24A' },
          { type: 'attend', title: 'Пропуск занятия', when: '15 ноя · 20:00', body: 'Не пришла. Накануне в чате тишина.', dotColor: '#C2654C' },
          { type: 'chat', title: 'Последнее сообщение в чате', when: '12 ноя · 21:42', body: '«Я не успеваю с заданием 22, можно завтра прислать?»', dotColor: 'var(--text-dim)' },
          { type: 'attend', title: 'Пришла на занятие', when: '11 ноя · 20:00', body: 'Активно работала с доски, разбирала текстовую задачу.', dotColor: '#6FA86B' },
          { type: 'pay', title: 'Оплата прошла', when: '17 окт · 09:00', body: '8 900 ₽ за ноябрь.', dotColor: '#6FA86B' },
        ] : [
          { type: 'attend', title: 'Пришла на занятие', when: 'вчера · 20:00', body: 'Без замечаний, активно работала в парах над геометрией.', dotColor: '#6FA86B' },
          { type: 'chat', title: 'Ответила в чате', when: '17 ноя · 18:30', body: 'Прислала вопрос по № 19, получила разбор.', dotColor: 'var(--text-dim)' },
          { type: 'attend', title: 'Сдала домашку', when: '16 ноя · 22:10', body: '8 из 8 заданий, средний балл 4.7.', dotColor: '#6FA86B' },
          { type: 'pay', title: 'Оплата прошла', when: '14 ноя · 09:00', body: '8 900 ₽ за ноябрь.', dotColor: '#6FA86B' },
        ];
      }
      const e = ce ? [{ type: 'chat', title: 'Звонок' + (ce.by ? ' · ' + ce.by : ''), when: (ce.date === new Date().toISOString().slice(0, 10) ? 'сегодня' : ce.date) + ' · ' + ce.time, body: 'Контакт отмечен вручную. Запишите краткий итог в заметку.', dotColor: '#4E8C4A' }, ...base] : base;
      return f === 'all' ? e : e.filter(x => x.type === f);
    },
  },
}).mount('#app');
