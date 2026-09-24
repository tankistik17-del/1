/*
 * «Горячая резина» — shell (window.Arcade).
 * Start screen, main loop, multi-touch input, synthesized audio, storage and overlays.
 * Plain browser JavaScript, no modules. The game registers itself with Arcade.register(def).
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants

  var FONTS = {
    display: '"Unbounded", "Arial Black", system-ui, sans-serif',
    body: '"Golos Text", system-ui, -apple-system, "Segoe UI", sans-serif'
  };
  var DIFFICULTIES = [
    { id: 'easy', label: 'Легко', level: 1 },
    { id: 'normal', label: 'Нормально', level: 2 },
    { id: 'hard', label: 'Сложно', level: 3 }
  ];
  var DIFF_LABEL = { easy: 'Легко', normal: 'Нормально', hard: 'Сложно' };

  var MAX_DPR = 2;
  var MAX_CANVAS_PIXELS = 16000000;
  var MAX_FRAME_DT = 0.25;
  var MAX_STEP = 0.05;
  var MAX_STEPS_PER_FRAME = 4000;

  var PAUSE_SIZE = 56;     // keep in sync with .pause-btn in index.html
  var PAUSE_MARGIN = 12;   // distance from the safe-area edge
  var RESERVED_PAD = 8;    // extra breathing room around the button in api.reserved

  var MASTER_VOLUME = 0.5;
  var SOUND_GAP_MS = 40;
  var FONT_WAIT_MS = 1500;
  // After «Продолжить» the game eases back from a standstill to full speed over this many real
  // seconds (smoothstep; the whole ramp covers half as much game time), so a car paused mid-corner
  // at speed does not hit the barrier before the player's fingers are back on the screen.
  var RESUME_EASE = 1.2;
  // The result card's buttons ignore taps for this long after it appears: players are often still
  // tapping to steer when the finish overlay pops up under their fingers.
  var OVER_TAP_GUARD_MS = 500;

  function noop() {}
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function now() { return (window.performance && performance.now) ? performance.now() : Date.now(); }

  var reducedMq = null;
  try { reducedMq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null; } catch (e) { reducedMq = null; }
  function reducedMotion() { return !!(reducedMq && reducedMq.matches); }

  // ---------------------------------------------------------------------------
  // Error reporting (never let one bad frame kill the loop, but keep errors visible)

  var errorCounts = {};
  function reportError(where, err) {
    var n = errorCounts[where] = (errorCounts[where] || 0) + 1;
    if (n <= 3 || n % 600 === 0) {
      try { console.error('[Arcade] ' + where + (n > 3 ? ' (x' + n + ')' : '') + ':', err); } catch (e) { /* ignore */ }
    }
  }

  // ---------------------------------------------------------------------------
  // Storage: namespaced JSON over localStorage, with an in-memory fallback. Never throws.

  var memoryStore = {};
  var ls = (function () {
    try {
      var s = window.localStorage;
      var probe = '__arcade_probe__';
      s.setItem(probe, '1');
      s.removeItem(probe);
      return s;
    } catch (e) { return null; }
  })();

  function rawGet(key) {
    var v = null;
    if (ls) { try { v = ls.getItem(key); } catch (e) { v = null; } }
    if (v == null && has(memoryStore, key)) v = memoryStore[key];
    return v;
  }
  function rawSet(key, value) {
    if (value == null) {
      delete memoryStore[key];
      if (ls) { try { ls.removeItem(key); } catch (e) { /* ignore */ } }
      return;
    }
    memoryStore[key] = value;
    if (ls) { try { ls.setItem(key, value); } catch (e) { /* quota / private mode: memory copy remains */ } }
  }
  function makeStore(ns) {
    var prefix = 'arcade:' + ns + ':';
    return {
      get: function (key, fallback) {
        try {
          var raw = rawGet(prefix + key);
          if (raw == null) return fallback;
          var v = JSON.parse(raw);
          return v === undefined || v === null ? fallback : v;
        } catch (e) { return fallback; }
      },
      set: function (key, value) {
        try { rawSet(prefix + key, value === undefined ? null : JSON.stringify(value)); } catch (e) { /* ignore */ }
      },
      remove: function (key) {
        try { rawSet(prefix + key, null); } catch (e) { /* ignore */ }
      }
    };
  }
  var shellStore = makeStore('_shell');
  var storesById = {};
  function storeFor(id) { return storesById[id] || (storesById[id] = makeStore(id)); }

  // ---------------------------------------------------------------------------
  // Audio: lazily created inside a user gesture; synthesized SFX; per-game bus.

  var audio = {
    ctx: null,
    master: null,
    sfx: null,
    noise: null,
    enabled: shellStore.get('sound', true) !== false,
    last: {},
    resumeAt: -1e9
  };

  function audioUsable() {
    return !!(audio.enabled && audio.ctx && audio.ctx.state !== 'closed');
  }

  function ensureAudio() {
    if (!audio.enabled) return null;
    if (!audio.ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      var c;
      try { c = new AC(); } catch (e) { return null; }
      audio.ctx = c;
      try {
        var comp = c.createDynamicsCompressor();
        comp.threshold.value = -16;
        comp.knee.value = 14;
        comp.ratio.value = 4;
        comp.attack.value = 0.004;
        comp.release.value = 0.2;
        audio.master = c.createGain();
        audio.master.gain.value = MASTER_VOLUME;
        audio.sfx = c.createGain();
        audio.sfx.gain.value = 1;
        audio.sfx.connect(audio.master);
        audio.master.connect(comp);
        comp.connect(c.destination);
        // one second of white noise, reused by every noisy sound
        var len = Math.floor(c.sampleRate);
        var buf = c.createBuffer(1, len, c.sampleRate);
        var d = buf.getChannelData(0);
        for (var i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
        audio.noise = buf;
        // iOS unlock: play one silent sample inside the gesture
        var silent = c.createBufferSource();
        silent.buffer = c.createBuffer(1, 1, 22050);
        silent.connect(c.destination);
        silent.start(0);
      } catch (e) { reportError('audio init', e); }
    }
    resumeAudio(true);
    return audio.ctx;
  }

  // fromGesture: the resume happens inside a user gesture, so the context is about to run and
  // one-shot sounds may be scheduled right away (see playSound).
  function resumeAudio(fromGesture) {
    var c = audio.ctx;
    if (!c || !audio.enabled) return;
    if (c.state !== 'running' && c.state !== 'closed') {
      if (fromGesture) audio.resumeAt = now();
      try {
        var p = c.resume();
        if (p && p.then) p.then(noop, noop);
      } catch (e) { /* ignore */ }
    }
  }

  function setMasterAudible(on) {
    if (!audio.ctx || !audio.master) return;
    try {
      var t = audio.ctx.currentTime;
      audio.master.gain.cancelScheduledValues(t);
      audio.master.gain.setTargetAtTime(on ? MASTER_VOLUME : 0, t, 0.02);
    } catch (e) { /* ignore */ }
  }

  // --- tiny synth primitives -------------------------------------------------

  function tone(freq, t0, dur, o) {
    var c = audio.ctx;
    var osc = c.createOscillator();
    var g = c.createGain();
    var node = osc;
    osc.type = o.type || 'sine';
    osc.frequency.setValueAtTime(freq, t0);
    if (o.slide) osc.frequency.exponentialRampToValueAtTime(o.slide, t0 + dur);
    if (o.detune) osc.detune.value = o.detune;
    var lp = null;
    if (o.lp) {
      lp = c.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = o.lp;
      osc.connect(lp);
      node = lp;
    }
    var a = o.attack || 0.006;
    var v = Math.max(0.0002, o.vol);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(v, t0 + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    node.connect(g);
    g.connect(o.dest || audio.sfx);
    osc.start(t0);
    osc.stop(t0 + dur + 0.03);
    osc.onended = function () {
      try { osc.disconnect(); g.disconnect(); if (lp) lp.disconnect(); } catch (e) { /* ignore */ }
    };
  }

  function noiseBurst(t0, dur, o) {
    var c = audio.ctx;
    if (!audio.noise) return;
    var src = c.createBufferSource();
    src.buffer = audio.noise;
    var f = c.createBiquadFilter();
    f.type = o.filter || 'lowpass';
    f.frequency.setValueAtTime(o.freq, t0);
    if (o.freqTo) f.frequency.exponentialRampToValueAtTime(o.freqTo, t0 + dur);
    f.Q.value = o.q || 0.8;
    var g = c.createGain();
    var v = Math.max(0.0002, o.vol);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(v, t0 + (o.attack || 0.004));
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(f);
    f.connect(g);
    g.connect(o.dest || audio.sfx);
    src.start(t0, Math.random() * 0.5);
    src.stop(t0 + dur + 0.03);
    src.onended = function () {
      try { src.disconnect(); f.disconnect(); g.disconnect(); } catch (e) { /* ignore */ }
    };
  }

  // --- the named sounds (p = pitch multiplier, v = volume multiplier) --------

  var SOUNDS = {
    tap: function (t, p, v) {
      tone(760 * p, t, 0.08, { type: 'triangle', vol: 0.24 * v, slide: 620 * p });
    },
    select: function (t, p, v) {
      tone(587 * p, t, 0.07, { type: 'triangle', vol: 0.13 * v });
      tone(880 * p, t + 0.045, 0.1, { type: 'triangle', vol: 0.12 * v });
    },
    deny: function (t, p, v) {
      tone(311 * p, t, 0.1, { type: 'triangle', vol: 0.16 * v, slide: 262 * p, lp: 1400 });
      tone(233 * p, t + 0.09, 0.16, { type: 'triangle', vol: 0.16 * v, slide: 196 * p, lp: 1200 });
    },
    countdown: function (t, p, v) {
      tone(587 * p, t, 0.22, { type: 'sine', vol: 0.36 * v });
      tone(1174 * p, t, 0.12, { type: 'triangle', vol: 0.07 * v });
    },
    go: function (t, p, v) {
      tone(880 * p, t, 0.5, { type: 'sine', vol: 0.26 * v, attack: 0.008 });
      tone(1318 * p, t + 0.01, 0.38, { type: 'triangle', vol: 0.07 * v });
      tone(440 * p, t, 0.3, { type: 'triangle', vol: 0.08 * v });
    },
    lap: function (t, p, v) {
      var notes = [659, 831, 988];
      for (var i = 0; i < notes.length; i++) tone(notes[i] * p, t + i * 0.075, 0.16, { type: 'triangle', vol: 0.14 * v });
    },
    bestlap: function (t, p, v) {
      var notes = [880, 1109, 1319, 1760];
      for (var i = 0; i < notes.length; i++) {
        var last = i === notes.length - 1;
        tone(notes[i] * p, t + i * 0.07, last ? 0.42 : 0.14, { type: 'triangle', vol: 0.12 * v });
        tone(notes[i] * 2 * p, t + i * 0.07, last ? 0.3 : 0.1, { type: 'sine', vol: 0.03 * v });
      }
    },
    crash: function (t, p, v) {
      noiseBurst(t, 0.3, { freq: 1400 * p, freqTo: 260, vol: 0.34 * v, q: 0.7 });
      tone(120 * p, t, 0.24, { type: 'sine', vol: 0.34 * v, slide: 48 * p });
    },
    bank: function (t, p, v) {
      tone(988 * p, t, 0.08, { type: 'triangle', vol: 0.13 * v, slide: 1319 * p });
      tone(1976 * p, t + 0.06, 0.16, { type: 'sine', vol: 0.09 * v });
      tone(1319 * p, t + 0.06, 0.14, { type: 'triangle', vol: 0.07 * v });
    },
    fail: function (t, p, v) {
      tone(150 * p, t, 0.28, { type: 'sine', vol: 0.34 * v, slide: 58 * p });
      noiseBurst(t, 0.16, { freq: 420 * p, vol: 0.12 * v });
    },
    finish: function (t, p, v) {
      var notes = [523, 659, 784, 1047];
      for (var i = 0; i < notes.length; i++) {
        var last = i === notes.length - 1;
        tone(notes[i] * p, t + i * 0.09, last ? 0.5 : 0.16, { type: 'triangle', vol: 0.14 * v });
      }
    },
    win: function (t, p, v) {
      var seq = [392, 523, 659];
      for (var i = 0; i < seq.length; i++) tone(seq[i] * p, t + i * 0.11, 0.16, { type: 'triangle', vol: 0.14 * v });
      var t2 = t + 0.34;
      tone(784 * p, t2, 0.7, { type: 'triangle', vol: 0.15 * v });
      tone(1047 * p, t2, 0.7, { type: 'sine', vol: 0.08 * v });
      tone(523 * p, t2, 0.6, { type: 'sine', vol: 0.07 * v });
    },
    lose: function (t, p, v) {
      var seq = [392, 330, 262];
      for (var i = 0; i < seq.length; i++) {
        tone(seq[i] * p, t + i * 0.16, i === 2 ? 0.45 : 0.2, { type: 'triangle', vol: 0.13 * v, lp: 1800 });
      }
    }
  };

  function playSound(name, opts) {
    if (!audioUsable()) return;
    var fn = SOUNDS[name];
    if (!fn) return;
    var c = audio.ctx;
    var tNow = now();
    if (c.state !== 'running') {
      // Sounds scheduled on a suspended context would pile up and fire together on resume.
      // Only allow it right after a gesture asked to resume (the context is about to run).
      if (tNow - audio.resumeAt > 400) return;
    }
    var last = audio.last[name];
    if (last != null && tNow - last < SOUND_GAP_MS) return;
    audio.last[name] = tNow;
    var p = 1, v = 1;
    if (opts) {
      if (typeof opts.pitch === 'number' && opts.pitch > 0) p = Math.min(4, Math.max(0.25, opts.pitch));
      if (typeof opts.volume === 'number') v = Math.min(1, Math.max(0, opts.volume));
    }
    if (v <= 0) return;
    try { fn(c.currentTime + 0.005, p, v); } catch (e) { reportError('sound ' + name, e); }
  }

  // ---------------------------------------------------------------------------
  // DOM + view state

  var el = {};
  var gameCtx = null;
  var previewCtx = null;
  var view = { w: 0, h: 0, dpr: 1 };
  var safe = { top: 0, right: 0, bottom: 0, left: 0 };
  var reserved = { x: 0, y: 0, w: 0, h: 0 };
  var preview = { w: 0, h: 0, dpr: 1, t: 0, active: false };
  var resizePending = true;
  var fontsReady = false;

  // ---------------------------------------------------------------------------
  // Registry + selection + session state

  var registry = {};
  var order = [];
  var booted = false;
  var screen = 'menu';
  var menuDef = null;
  var selection = { difficulty: 'normal', options: {} };
  var session = null;     // the running game (instance + api + flags)
  var pointers = [];      // active pointers on the game canvas: { id, x, y }
  var rafId = 0;
  var lastTs = 0;
  var wake = { sentinel: null, pending: false };

  function validDifficulty(d) { return d === 'easy' || d === 'normal' || d === 'hard'; }

  function normalizeOptions(def, src) {
    var out = {};
    var groups = def.setup || [];
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      var choices = g.choices || [];
      if (!choices.length) continue;
      var want = src ? src[g.id] : undefined;
      var pick = choices[0].id;
      for (var j = 0; j < choices.length; j++) {
        if (choices[j].id === want) { pick = want; break; }
      }
      out[g.id] = pick;
    }
    return out;
  }

  function copyOptions(o) {
    var out = {};
    for (var k in o) if (has(o, k)) out[k] = o[k];
    return out;
  }

  function loadSelection(def) {
    var saved = shellStore.get('last:' + def.id, null) || {};
    selection.difficulty = validDifficulty(saved.difficulty) ? saved.difficulty : 'normal';
    selection.options = normalizeOptions(def, saved.options || {});
  }

  function saveSelection(def) {
    shellStore.set('last:' + def.id, { difficulty: selection.difficulty, options: copyOptions(selection.options) });
  }

  function choiceLabel(def, groupId, choiceId) {
    var groups = def.setup || [];
    for (var i = 0; i < groups.length; i++) {
      if (groups[i].id !== groupId) continue;
      var ch = groups[i].choices || [];
      for (var j = 0; j < ch.length; j++) if (ch[j].id === choiceId) return ch[j].label;
    }
    return '';
  }

  function summaryText(def, difficulty, options) {
    var parts = [];
    var groups = def.setup || [];
    for (var i = 0; i < groups.length; i++) {
      var l = choiceLabel(def, groups[i].id, options[groups[i].id]);
      if (l) parts.push(l);
    }
    parts.push(DIFF_LABEL[difficulty] || '');
    return parts.join(' · ');
  }

  // ---------------------------------------------------------------------------
  // Screens

  function setScreen(name) {
    screen = name;
    if (el.root) el.root.setAttribute('data-screen', name);
    setInert(el.menu, name !== 'menu');
    setInert(el.pause, name !== 'paused');
    setInert(el.over, name !== 'over');
    setInert(el.pauseBtn, name !== 'game');
  }

  function setInert(node, on) {
    if (!node) return;
    if (on) {
      node.setAttribute('inert', '');
      node.setAttribute('aria-hidden', 'true');
    } else {
      node.removeAttribute('inert');
      node.removeAttribute('aria-hidden');
    }
  }

  function focusSoon(node) {
    if (!node) return;
    setTimeout(function () {
      try { node.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
    }, 30);
  }

  // ---------------------------------------------------------------------------
  // Start screen

  function buildMenu(def) {
    menuDef = def;
    loadSelection(def);

    var title = def.title || 'Горячая резина';
    document.title = title;
    var words = String(title).split(/\s+/);
    el.title.textContent = '';
    for (var w = 0; w < words.length; w++) {
      var span = document.createElement('span');
      span.className = 'title-line';
      span.style.setProperty('--i', String(w + 1));
      span.textContent = words[w];
      el.title.appendChild(span);
      if (w < words.length - 1) el.title.appendChild(document.createTextNode(' '));
    }
    el.tagline.textContent = def.tagline || '';

    el.howto.textContent = '';
    var how = def.howTo || [];
    for (var h = 0; h < how.length; h++) {
      var li = document.createElement('li');
      li.textContent = how[h];
      el.howto.appendChild(li);
    }

    el.setup.textContent = '';
    var groups = def.setup || [];
    for (var i = 0; i < groups.length; i++) {
      el.setup.appendChild(buildGroup(groups[i].id, groups[i].label, groups[i].choices || [], false));
    }
    var diffChoices = [];
    for (var d = 0; d < DIFFICULTIES.length; d++) diffChoices.push(DIFFICULTIES[d]);
    el.setup.appendChild(buildGroup('__difficulty', 'Сложность', diffChoices, true));

    refreshSelectionUI();
  }

  function buildGroup(groupId, label, choices, isDifficulty) {
    var wrap = document.createElement('div');
    wrap.className = 'group';
    var labelId = 'grp-' + groupId + '-label';
    var lab = document.createElement('p');
    lab.className = 'group-label';
    lab.id = labelId;
    lab.textContent = label;
    wrap.appendChild(lab);

    var row = document.createElement('div');
    row.className = 'chips';
    row.setAttribute('role', 'radiogroup');
    row.setAttribute('aria-labelledby', labelId);
    row.setAttribute('data-group', groupId);
    for (var i = 0; i < choices.length; i++) {
      var ch = choices[i];
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip';
      b.id = 'chip-' + groupId.replace(/^_+/, '') + '-' + ch.id;
      b.setAttribute('role', 'radio');
      b.setAttribute('aria-checked', 'false');
      b.setAttribute('data-group', groupId);
      b.setAttribute('data-choice', ch.id);
      var txt = document.createElement('span');
      txt.textContent = ch.label;
      b.appendChild(txt);
      if (isDifficulty) {
        var lvl = document.createElement('span');
        lvl.className = 'lvl';
        lvl.setAttribute('aria-hidden', 'true');
        lvl.setAttribute('data-level', String(ch.level));
        lvl.innerHTML = '<i></i><i></i><i></i>';
        b.appendChild(lvl);
      }
      if (ch.note) b.setAttribute('aria-description', ch.note);
      row.appendChild(b);
    }
    row.addEventListener('click', onChipClick);
    row.addEventListener('keydown', onChipKey);
    wrap.appendChild(row);

    if (!isDifficulty) {
      var note = document.createElement('p');
      note.className = 'group-note';
      note.id = 'note-' + groupId;
      note.setAttribute('aria-live', 'polite');
      wrap.appendChild(note);
    }
    return wrap;
  }

  function onChipClick(e) {
    var b = e.target && e.target.closest ? e.target.closest('.chip') : null;
    if (!b || screen !== 'menu') return;
    selectChoice(b.getAttribute('data-group'), b.getAttribute('data-choice'), true);
  }

  function onChipKey(e) {
    var k = e.key;
    var dir = (k === 'ArrowRight' || k === 'ArrowDown') ? 1 : (k === 'ArrowLeft' || k === 'ArrowUp') ? -1 : 0;
    if (!dir) return;
    var row = e.currentTarget;
    var chips = row.querySelectorAll('.chip');
    var idx = -1;
    for (var i = 0; i < chips.length; i++) if (chips[i].getAttribute('aria-checked') === 'true') idx = i;
    var next = chips[(idx + dir + chips.length) % chips.length];
    if (!next) return;
    e.preventDefault();
    selectChoice(next.getAttribute('data-group'), next.getAttribute('data-choice'), true);
    try { next.focus({ preventScroll: false }); } catch (err) { /* ignore */ }
  }

  function selectChoice(groupId, choiceId, withSound) {
    if (!menuDef) return;
    var changed;
    if (groupId === '__difficulty') {
      if (!validDifficulty(choiceId)) return;
      changed = selection.difficulty !== choiceId;
      selection.difficulty = choiceId;
    } else {
      changed = selection.options[groupId] !== choiceId;
      selection.options[groupId] = choiceId;
      selection.options = normalizeOptions(menuDef, selection.options);
    }
    saveSelection(menuDef);
    refreshSelectionUI();
    if (withSound) playSound(changed ? 'select' : 'tap', changed ? null : { volume: 0.6 });
  }

  function refreshSelectionUI() {
    if (!menuDef) return;
    var chips = el.setup.querySelectorAll('.chip');
    for (var i = 0; i < chips.length; i++) {
      var c = chips[i];
      var g = c.getAttribute('data-group');
      var id = c.getAttribute('data-choice');
      var on = g === '__difficulty' ? selection.difficulty === id : selection.options[g] === id;
      c.setAttribute('aria-checked', on ? 'true' : 'false');
      c.tabIndex = on ? 0 : -1;
    }
    var groups = menuDef.setup || [];
    for (var j = 0; j < groups.length; j++) {
      var note = document.getElementById('note-' + groups[j].id);
      if (!note) continue;
      var txt = '';
      var ch = groups[j].choices || [];
      for (var q = 0; q < ch.length; q++) if (ch[q].id === selection.options[groups[j].id]) txt = ch[q].note || '';
      note.textContent = txt;
    }
    refreshBest();
  }

  function refreshBest() {
    if (!menuDef) return;
    var text = null;
    if (typeof menuDef.bestText === 'function') {
      try {
        text = menuDef.bestText(storeFor(menuDef.id), copyOptions(selection.options), selection.difficulty);
      } catch (e) { reportError('bestText', e); text = null; }
    }
    if (text) {
      el.recordText.textContent = String(text);
      el.record.classList.remove('is-empty');
    } else {
      el.recordText.textContent = 'Рекорда пока нет';
      el.record.classList.add('is-empty');
    }
  }

  function showMenuError(msg) {
    el.setup.textContent = '';
    var p = document.createElement('p');
    p.className = 'menu-error';
    p.textContent = msg;
    el.setup.appendChild(p);
    el.play.disabled = true;
    el.play.style.display = 'none';
    el.record.style.display = 'none';
  }

  // ---------------------------------------------------------------------------
  // Sizing

  function readSafe() {
    if (!el.probe) return;
    try {
      var cs = window.getComputedStyle(el.probe);
      safe.top = parseFloat(cs.paddingTop) || 0;
      safe.right = parseFloat(cs.paddingRight) || 0;
      safe.bottom = parseFloat(cs.paddingBottom) || 0;
      safe.left = parseFloat(cs.paddingLeft) || 0;
    } catch (e) { /* keep previous */ }
  }

  function pickDpr(w, h) {
    var dpr = Math.min(MAX_DPR, window.devicePixelRatio || 1);
    if (!(dpr > 0)) dpr = 1;
    var area = w * h;
    if (area * dpr * dpr > MAX_CANVAS_PIXELS) dpr = Math.sqrt(MAX_CANVAS_PIXELS / Math.max(1, area));
    return dpr;
  }

  function layoutPauseButton() {
    var top = Math.round(safe.top + PAUSE_MARGIN);
    var right = Math.round(safe.right + PAUSE_MARGIN);
    el.pauseBtn.style.top = top + 'px';
    el.pauseBtn.style.right = right + 'px';
    var rw = right + PAUSE_SIZE + RESERVED_PAD;
    reserved.x = Math.max(0, view.w - rw);
    reserved.y = 0;
    reserved.w = Math.min(view.w, rw);
    reserved.h = top + PAUSE_SIZE + RESERVED_PAD;
  }

  // Resize the main canvas; returns true when the CSS size or dpr changed.
  function sizeGameCanvas() {
    var r = el.canvas.getBoundingClientRect();
    var w = Math.max(1, Math.round(r.width || window.innerWidth || 1));
    var h = Math.max(1, Math.round(r.height || window.innerHeight || 1));
    var dpr = pickDpr(w, h);
    var bw = Math.max(1, Math.round(w * dpr));
    var bh = Math.max(1, Math.round(h * dpr));
    var changed = w !== view.w || h !== view.h || dpr !== view.dpr;
    view.w = w;
    view.h = h;
    view.dpr = dpr;
    if (el.canvas.width !== bw || el.canvas.height !== bh) {
      el.canvas.width = bw;
      el.canvas.height = bh;
      changed = true;
    }
    resetGameCtx();
    layoutPauseButton();
    return changed;
  }

  function freeGameCanvas() {
    el.canvas.width = 1;
    el.canvas.height = 1;
  }

  function resetGameCtx() {
    if (!gameCtx) return;
    gameCtx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    gameCtx.globalAlpha = 1;
    gameCtx.globalCompositeOperation = 'source-over';
  }

  function sizePreview() {
    if (!el.preview) return;
    var host = el.preview.parentNode;
    var r = host.getBoundingClientRect();
    var w = Math.max(1, Math.round(r.width));
    var h = Math.max(1, Math.round(r.height));
    var dpr = pickDpr(w, h);
    preview.w = w;
    preview.h = h;
    preview.dpr = dpr;
    var bw = Math.max(1, Math.round(w * dpr));
    var bh = Math.max(1, Math.round(h * dpr));
    if (el.preview.width !== bw || el.preview.height !== bh) {
      el.preview.width = bw;
      el.preview.height = bh;
    }
  }

  function freePreview() {
    el.preview.width = 1;
    el.preview.height = 1;
    preview.w = preview.h = 0;
  }

  // Free the hero canvas while playing (iOS canvas memory), after the menu has faded out.
  var previewFreeTimer = 0;
  function schedulePreviewFree() {
    clearTimeout(previewFreeTimer);
    previewFreeTimer = setTimeout(function () {
      if (screen !== 'menu') freePreview();
    }, 400);
  }

  function applyResize() {
    resizePending = false;
    readSafe();
    if (session) {
      var changed = sizeGameCanvas();
      if (changed && session.instance && typeof session.instance.resize === 'function') {
        callGame(session, 'resize', view.w, view.h);
      }
    } else {
      var r = el.canvas.getBoundingClientRect();
      view.w = Math.max(1, Math.round(r.width || window.innerWidth || 1));
      view.h = Math.max(1, Math.round(r.height || window.innerHeight || 1));
      layoutPauseButton();
    }
    if (screen === 'menu') sizePreview();
  }

  function requestResize() {
    resizePending = true;
  }

  // ---------------------------------------------------------------------------
  // Game session

  function callGame(s, method, a, b) {
    var inst = s.instance;
    if (!inst || typeof inst[method] !== 'function') return;
    try { inst[method](a, b); } catch (e) { reportError('game.' + method, e); }
  }

  function makeApi(def, s) {
    var store = storeFor(def.id);
    var api = {
      canvas: el.canvas,
      ctx: gameCtx,
      difficulty: s.difficulty,
      options: copyOptions(s.options),
      fonts: { display: FONTS.display, body: FONTS.body },
      store: store,
      sound: function (name, opts) {
        if (!s.alive) return;
        playSound(name, opts);
      },
      gameOver: function (result) {
        if (!s.alive || s.over || s.pendingOver) return;
        s.pendingOver = result && typeof result === 'object' ? result : {};
      },
      exit: function () {
        if (!s.alive) return;
        s.pendingExit = true;
      }
    };
    Object.defineProperty(api, 'width', { enumerable: true, get: function () { return view.w; } });
    Object.defineProperty(api, 'height', { enumerable: true, get: function () { return view.h; } });
    Object.defineProperty(api, 'dpr', { enumerable: true, get: function () { return view.dpr; } });
    Object.defineProperty(api, 'safe', { enumerable: true, get: function () { return safe; } });
    Object.defineProperty(api, 'reserved', { enumerable: true, get: function () { return reserved; } });
    Object.defineProperty(api, 'reducedMotion', { enumerable: true, get: reducedMotion });
    Object.defineProperty(api, 'audio', { enumerable: true, get: function () { return gameAudio(s); } });
    return api;
  }

  function gameAudio(s) {
    if (!s.alive || !audioUsable() || !audio.master) return null;
    if (!s.bus) {
      try {
        s.bus = audio.ctx.createGain();
        s.bus.gain.value = screen === 'game' ? 1 : 0;
        s.bus.connect(audio.master);
        s.audioHandle = { ctx: audio.ctx, out: s.bus };
      } catch (e) { reportError('audio bus', e); s.bus = null; return null; }
    }
    return s.audioHandle;
  }

  function setBus(s, on, tc) {
    if (!s || !s.bus || !audio.ctx) return;
    try {
      var t = audio.ctx.currentTime;
      s.bus.gain.cancelScheduledValues(t);
      s.bus.gain.setTargetAtTime(on ? 1 : 0, t, tc || 0.02);
    } catch (e) { /* ignore */ }
  }

  function startGame(def, difficulty, options) {
    teardownSession();
    if (!def || typeof def.create !== 'function') return null;
    var s = {
      def: def,
      difficulty: validDifficulty(difficulty) ? difficulty : 'normal',
      options: normalizeOptions(def, options || {}),
      instance: null,
      api: null,
      alive: true,
      over: false,
      pendingOver: null,
      pendingExit: false,
      bus: null,
      audioHandle: null,
      easeT: RESUME_EASE,   // real seconds since the last resume (>= RESUME_EASE: full speed)
      overAt: 0
    };
    session = s;
    setScreen('game');
    schedulePreviewFree();
    readSafe();
    sizeGameCanvas();
    gameCtx.setTransform(1, 0, 0, 1, 0, 0);
    gameCtx.clearRect(0, 0, el.canvas.width, el.canvas.height);
    resetGameCtx();
    s.api = makeApi(def, s);
    try {
      s.instance = def.create(s.api) || null;
    } catch (e) {
      reportError('game.create', e);
      s.instance = null;
    }
    if (!s.instance || session !== s) {
      if (session === s) goMenu();
      return null;
    }
    resizePending = false;
    callGame(s, 'resize', view.w, view.h);
    requestWakeLock();
    return s.instance;
  }

  function teardownSession() {
    var s = session;
    if (!s) return;
    s.alive = false;
    pointers.length = 0;
    session = null;
    callGame(s, 'destroy');
    if (s.bus) {
      var bus = s.bus;
      setBus(s, false, 0.03);
      setTimeout(function () { try { bus.disconnect(); } catch (e) { /* ignore */ } }, 250);
      s.bus = null;
      s.audioHandle = null;
    }
  }

  // Send pointerUp for every pointer still down (no stuck steering).
  function releasePointers(s) {
    if (!pointers.length) return;
    var list = pointers.slice();
    pointers.length = 0;
    if (!s || !s.instance) return;
    for (var i = 0; i < list.length; i++) {
      callGame(s, 'pointerUp', { id: list[i].id, x: list[i].x, y: list[i].y });
    }
  }

  function pauseGame() {
    var s = session;
    if (!s || screen !== 'game') return;
    releasePointers(s);
    setScreen('paused');
    callGame(s, 'pause');
    setBus(s, false);
    releaseWakeLock();
    el.pauseSummary.textContent = summaryText(s.def, s.difficulty, s.options);
    focusSoon(el.resume);
  }

  function resumeGame() {
    var s = session;
    if (!s || screen !== 'paused') return;
    pointers.length = 0;
    s.easeT = 0;
    setScreen('game');
    callGame(s, 'resume');
    setBus(s, true);
    requestWakeLock();
  }

  function restartGame() {
    var s = session;
    var def = s ? s.def : menuDef;
    if (!def) return;
    var diff = s ? s.difficulty : selection.difficulty;
    var opts = s ? copyOptions(s.options) : copyOptions(selection.options);
    startGame(def, diff, opts);
  }

  function goMenu() {
    teardownSession();
    releaseWakeLock();
    freeGameCanvas();
    setScreen('menu');
    if (menuDef) refreshSelectionUI();
    sizePreview();
    focusSoon(el.play);
  }

  function finishOver(s) {
    var result = s.pendingOver || {};
    s.pendingOver = null;
    s.over = true;
    s.overAt = now();
    releasePointers(s);
    setScreen('over');
    setBus(s, false, 0.12);
    releaseWakeLock();
    renderResult(s, result);
    focusSoon(el.again);
  }

  function overTapReady() {
    return screen === 'over' && !!session && now() - session.overAt >= OVER_TAP_GUARD_MS;
  }

  function starSvg(on, i) {
    return '<svg class="star' + (on ? ' is-on' : '') + '" style="--i:' + i + '" viewBox="0 0 48 48" aria-hidden="true">' +
      '<path d="M24 4.5l5.9 12 13.2 1.9-9.6 9.3 2.3 13.2L24 34.7l-11.8 6.2 2.3-13.2-9.6-9.3 13.2-1.9z"/></svg>';
  }

  function renderResult(s, r) {
    var stars = typeof r.stars === 'number' && isFinite(r.stars) ? Math.max(0, Math.min(3, Math.round(r.stars))) : null;
    if (stars == null) {
      el.overStars.innerHTML = '';
      el.overStars.removeAttribute('aria-label');
      el.overStars.removeAttribute('role');
    } else {
      var html = '';
      for (var i = 0; i < 3; i++) html += starSvg(i < stars, i);
      el.overStars.innerHTML = html;
      el.overStars.setAttribute('role', 'img');
      el.overStars.setAttribute('aria-label', 'Звёзды: ' + stars + ' из 3');
    }
    el.overSummary.textContent = summaryText(s.def, s.difficulty, s.options);
    el.overTitle.textContent = r.title ? String(r.title) : (r.win ? 'Победа' : 'Финиш');
    el.overSubtitle.textContent = r.subtitle ? String(r.subtitle) : '';
    el.overRecord.hidden = !r.record;
    el.overCard.classList.toggle('is-win', !!r.win);
    el.overStats.textContent = '';
    var stats = Array.isArray(r.stats) ? r.stats : [];
    for (var k = 0; k < stats.length; k++) {
      var row = stats[k];
      if (!row) continue;
      var div = document.createElement('div');
      div.className = 'stat';
      var dt = document.createElement('dt');
      dt.textContent = row[0] == null ? '' : String(row[0]);
      var dd = document.createElement('dd');
      dd.textContent = row[1] == null ? '' : String(row[1]);
      div.appendChild(dt);
      div.appendChild(dd);
      el.overStats.appendChild(div);
    }
    if (stars) {
      for (var q = 0; q < stars; q++) {
        (function (idx) {
          setTimeout(function () {
            if (screen === 'over' && session === s) playSound('tap', { pitch: 1 + idx * 0.25, volume: 0.7 });
          }, reducedMotion() ? 120 + idx * 120 : 300 + idx * 160);
        })(q);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Main loop

  function frame(ts) {
    rafId = requestAnimationFrame(frame);
    var dt = lastTs ? (ts - lastTs) / 1000 : 1 / 60;
    lastTs = ts;
    if (!(dt >= 0)) dt = 0;
    if (dt > MAX_FRAME_DT) dt = MAX_FRAME_DT;

    if (resizePending) applyResize();

    if (screen === 'menu') {
      drawPreviewFrame(dt);
      return;
    }

    var s = session;
    if (!s) return;

    if (s.pendingExit) { goMenu(); return; }
    if (s.pendingOver && !s.over) finishOver(s);

    if (screen === 'game' && s.instance) {
      var scale = +Arcade.debug.timeScale;
      if (!(scale > 0)) scale = 0;
      var rem = easedDt(s, dt) * scale;
      var steps = 0;
      while (rem > 1e-9 && steps < MAX_STEPS_PER_FRAME) {
        var step = rem > MAX_STEP ? MAX_STEP : rem;
        rem -= step;
        steps++;
        callGame(s, 'update', step);
        if (session !== s || s.pendingOver || s.pendingExit || screen !== 'game') break;
      }
      if (session !== s) return;
      if (s.pendingExit) { goMenu(); return; }
      if (s.pendingOver && !s.over) finishOver(s);
    }

    if (session === s && s.instance && typeof s.instance.render === 'function') {
      resetGameCtx();
      callGame(s, 'render', gameCtx);
    }
  }

  // Game time for a real frame of dt seconds: during the ease-in after a resume the rate follows
  // smoothstep(u) (u = time since resume / RESUME_EASE); integrating it exactly keeps 60 Hz and
  // 120 Hz identical.
  function easeIntegral(u) { return u * u * u - 0.5 * u * u * u * u; }
  function easedDt(s, dt) {
    var a = s.easeT;
    if (!(a < RESUME_EASE)) return dt;
    var b = a + dt;
    s.easeT = b;
    var ua = a / RESUME_EASE;
    var ub = b < RESUME_EASE ? b / RESUME_EASE : 1;
    return RESUME_EASE * (easeIntegral(ub) - easeIntegral(ua)) + (b > RESUME_EASE ? b - RESUME_EASE : 0);
  }

  function drawPreviewFrame(dt) {
    if (!fontsReady || !menuDef || typeof menuDef.drawPreview !== 'function' || !previewCtx) return;
    if (!preview.w) sizePreview();
    preview.t += dt;
    var c = previewCtx;
    c.setTransform(preview.dpr, 0, 0, preview.dpr, 0, 0);
    c.globalAlpha = 1;
    c.globalCompositeOperation = 'source-over';
    c.clearRect(0, 0, preview.w, preview.h);
    c.save();
    try { menuDef.drawPreview(c, preview.w, preview.h, preview.t); } catch (e) { reportError('drawPreview', e); }
    c.restore();
  }

  // ---------------------------------------------------------------------------
  // Input

  function localPoint(e) {
    var r = el.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function findPointer(id) {
    for (var i = 0; i < pointers.length; i++) if (pointers[i].id === id) return i;
    return -1;
  }

  function canForward() {
    return !!(session && session.instance && screen === 'game' && !session.pendingOver && !session.pendingExit && !session.over);
  }

  function onPointerDown(e) {
    if (!canForward()) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    e.preventDefault();
    try { el.canvas.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
    var pt = localPoint(e);
    var idx = findPointer(e.pointerId);
    if (idx >= 0) pointers.splice(idx, 1);
    pointers.push({ id: e.pointerId, x: pt.x, y: pt.y });
    callGame(session, 'pointerDown', { id: e.pointerId, x: pt.x, y: pt.y });
  }

  function onPointerMove(e) {
    var idx = findPointer(e.pointerId);
    if (idx < 0) return;
    if (!canForward()) return;
    var pt = localPoint(e);
    var p = pointers[idx];
    p.x = pt.x;
    p.y = pt.y;
    callGame(session, 'pointerMove', { id: e.pointerId, x: pt.x, y: pt.y });
  }

  function onPointerUp(e) {
    var idx = findPointer(e.pointerId);
    if (idx < 0) return;
    pointers.splice(idx, 1);
    if (!canForward()) return;
    var pt = e.type === 'lostpointercapture' ? null : localPoint(e);
    var p = pt || { x: 0, y: 0 };
    callGame(session, 'pointerUp', { id: e.pointerId, x: p.x, y: p.y });
  }

  function prevent(e) {
    if (e.cancelable) e.preventDefault();
  }

  // ---------------------------------------------------------------------------
  // Wake lock (optional; failures are fine)

  function requestWakeLock() {
    if (wake.sentinel || wake.pending) return;
    if (document.hidden) return;
    var wl = navigator.wakeLock;
    if (!wl || typeof wl.request !== 'function') return;
    wake.pending = true;
    var p;
    try { p = wl.request('screen'); } catch (e) { wake.pending = false; return; }
    if (!p || !p.then) { wake.pending = false; return; }
    p.then(function (sentinel) {
      wake.pending = false;
      if (screen !== 'game') {
        try { sentinel.release().then(noop, noop); } catch (e) { /* ignore */ }
        return;
      }
      wake.sentinel = sentinel;
      try {
        sentinel.addEventListener('release', function () {
          if (wake.sentinel === sentinel) wake.sentinel = null;
        });
      } catch (e) { /* ignore */ }
    }, function () { wake.pending = false; });
  }

  function releaseWakeLock() {
    var s = wake.sentinel;
    wake.sentinel = null;
    if (s) {
      try { s.release().then(noop, noop); } catch (e) { /* ignore */ }
    }
  }

  // ---------------------------------------------------------------------------
  // Sound toggle

  function applySoundUI() {
    el.root.classList.toggle('is-muted', !audio.enabled);
    var label = audio.enabled ? 'Звук включён' : 'Звук выключен';
    el.soundMenu.setAttribute('aria-pressed', audio.enabled ? 'true' : 'false');
    el.soundMenu.setAttribute('aria-label', label);
    el.soundPause.setAttribute('aria-pressed', audio.enabled ? 'true' : 'false');
    el.soundPause.setAttribute('aria-label', label);
  }

  function toggleSound() {
    audio.enabled = !audio.enabled;
    shellStore.set('sound', audio.enabled);
    if (audio.enabled) {
      ensureAudio();
      setMasterAudible(true);
      if (session && screen === 'game') setBus(session, true);
      playSound('select');
    } else {
      setMasterAudible(false);
    }
    applySoundUI();
  }

  // ---------------------------------------------------------------------------
  // Fonts

  // index.html loads the Google Fonts stylesheet without blocking the scripts
  // (media="print", switched to "all" by its onload), so a stalled or captive network can never
  // keep the game from booting. Track that stylesheet here: the font wait below starts only once
  // its @font-face rules exist, and the media switch is repeated in case the inline onload
  // handler was not allowed to run.
  var fontCss = { link: null, state: 'none', waiters: [] };

  function watchFontCss() {
    var link = null;
    try { link = document.querySelector('link[rel~="stylesheet"][href*="fonts.googleapis.com"]'); } catch (e) { link = null; }
    fontCss.link = link;
    if (!link) return;
    if (link.sheet) { fontCssSettled('load'); return; }
    fontCss.state = 'pending';
    link.addEventListener('load', function () { fontCssSettled('load'); });
    link.addEventListener('error', function () { fontCssSettled('error'); });
  }

  function fontCssSettled(state) {
    if (fontCss.state === 'load' || fontCss.state === 'error') return;
    fontCss.state = state;
    var link = fontCss.link;
    if (state === 'load' && link && link.media === 'print') {
      try { link.media = 'all'; } catch (e) { /* ignore */ }
    }
    // flush style so the new @font-face rules are registered before document.fonts.load()
    try { void document.documentElement.offsetWidth; } catch (e) { /* ignore */ }
    var list = fontCss.waiters.splice(0, fontCss.waiters.length);
    for (var i = 0; i < list.length; i++) {
      try { list[i](); } catch (e) { reportError('fonts', e); }
    }
  }

  function whenFontCss(fn) {
    if (fontCss.state === 'pending') fontCss.waiters.push(fn);
    else fn();
  }

  // Calls cb once the fonts are ready, or after FONT_WAIT_MS at most (then the fallbacks show
  // first and the web fonts swap in whenever they arrive).
  function waitForFonts(cb) {
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      cb();
    }
    setTimeout(finish, FONT_WAIT_MS);
    whenFontCss(function () {
      if (done) return;
      try {
        var fs = document.fonts;
        if (!fs || typeof fs.load !== 'function') { finish(); return; }
        var sample = 'Горячая резина 0123456789';
        var specs = ['800 40px "Unbounded"', '600 20px "Unbounded"', '400 16px "Golos Text"', '600 16px "Golos Text"', '700 16px "Golos Text"'];
        var loads = [];
        for (var i = 0; i < specs.length; i++) {
          try { loads.push(fs.load(specs[i], sample).then(noop, noop)); } catch (e) { /* ignore */ }
        }
        Promise.all(loads).then(function () { return fs.ready; }).then(finish, finish);
      } catch (e) { finish(); }
    });
  }
  watchFontCss();

  // ---------------------------------------------------------------------------
  // Boot

  function grabDom() {
    function $(id) { return document.getElementById(id); }
    el.root = $('arcade');
    el.canvas = $('game-canvas');
    el.probe = $('safe-probe');
    el.menu = $('menu');
    el.preview = $('preview');
    el.title = $('menu-title');
    el.tagline = $('menu-tagline');
    el.howto = $('menu-howto');
    el.setup = $('setup');
    el.record = $('record-line');
    el.recordText = $('record-text');
    el.play = $('btn-play');
    el.soundMenu = $('btn-sound-menu');
    el.pauseBtn = $('btn-pause');
    el.pause = $('pause');
    el.pauseSummary = $('pause-summary');
    el.resume = $('btn-resume');
    el.restart = $('btn-restart');
    el.pauseMenu = $('btn-pause-menu');
    el.soundPause = $('btn-sound-pause');
    el.over = $('over');
    el.overCard = $('over-card');
    el.overStars = $('over-stars');
    el.overSummary = $('over-summary');
    el.overTitle = $('over-title');
    el.overSubtitle = $('over-subtitle');
    el.overRecord = $('over-record');
    el.overStats = $('over-stats');
    el.again = $('btn-again');
    el.overMenu = $('btn-over-menu');
    gameCtx = el.canvas.getContext('2d');
    previewCtx = el.preview.getContext('2d');
  }

  function bindEvents() {
    // audio unlock / resume on any user gesture (iOS)
    var unlock = function () { if (audio.enabled) ensureAudio(); };
    document.addEventListener('touchend', unlock, true);
    document.addEventListener('pointerup', unlock, true);
    document.addEventListener('click', unlock, true);
    document.addEventListener('keydown', unlock, true);

    // game surface input
    var c = el.canvas;
    c.addEventListener('pointerdown', onPointerDown);
    c.addEventListener('pointermove', onPointerMove);
    c.addEventListener('pointerup', onPointerUp);
    c.addEventListener('pointercancel', onPointerUp);
    c.addEventListener('lostpointercapture', onPointerUp);

    // iOS gesture suppression on the game layer
    var nonPassive = { passive: false };
    c.addEventListener('touchstart', prevent, nonPassive);
    c.addEventListener('touchmove', prevent, nonPassive);
    c.addEventListener('dblclick', prevent);
    c.addEventListener('contextmenu', prevent);
    el.pauseBtn.addEventListener('touchmove', prevent, nonPassive);
    // pause fires on pointerup; cancel iOS's synthetic click so it can't land on the overlay
    el.pauseBtn.addEventListener('touchend', prevent, nonPassive);
    el.pauseBtn.addEventListener('dblclick', prevent);
    el.pauseBtn.addEventListener('contextmenu', prevent);
    document.addEventListener('gesturestart', prevent, nonPassive);
    document.addEventListener('gesturechange', prevent, nonPassive);
    document.addEventListener('gestureend', prevent, nonPassive);
    el.root.addEventListener('dblclick', function (e) { if (screen !== 'menu') prevent(e); });

    // buttons
    el.play.addEventListener('click', function () {
      if (screen !== 'menu' || !menuDef) return;
      playSound('tap');
      saveSelection(menuDef);
      startGame(menuDef, selection.difficulty, copyOptions(selection.options));
    });
    // pause reacts on pointerup too: iOS may drop the click while another finger steers
    el.pauseBtn.addEventListener('pointerup', function (e) { if (e.pointerType !== 'mouse') pauseGame(); });
    el.pauseBtn.addEventListener('click', function () { pauseGame(); });
    el.resume.addEventListener('click', function () { playSound('tap'); resumeGame(); });
    el.restart.addEventListener('click', function () { if (screen !== 'paused') return; playSound('tap'); restartGame(); });
    el.pauseMenu.addEventListener('click', function () { if (screen !== 'paused') return; playSound('tap'); goMenu(); });
    el.again.addEventListener('click', function () { if (!overTapReady()) return; playSound('tap'); restartGame(); });
    el.overMenu.addEventListener('click', function () { if (!overTapReady()) return; playSound('tap'); goMenu(); });
    el.soundMenu.addEventListener('click', toggleSound);
    el.soundPause.addEventListener('click', toggleSound);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        if (screen === 'game') { e.preventDefault(); pauseGame(); }
        else if (screen === 'paused') { e.preventDefault(); resumeGame(); }
      }
    });

    // lifecycle
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        if (screen === 'game') pauseGame();
      } else {
        if (screen === 'game') requestWakeLock();
        resumeAudio(false);
        requestResize();
      }
    });
    window.addEventListener('pagehide', function () { if (screen === 'game') pauseGame(); });
    // iPad: pulling down Control Center / Notification Center, a system alert or switching to the
    // other app in Split View blurs the window without hiding the page; pause so the car doesn't
    // drive on unattended (the system cancels the touches anyway).
    window.addEventListener('blur', function () { if (screen === 'game') pauseGame(); });
    window.addEventListener('resize', requestResize);
    window.addEventListener('orientationchange', function () {
      requestResize();
      setTimeout(requestResize, 250);
      setTimeout(requestResize, 700);
    });
    if (window.visualViewport) window.visualViewport.addEventListener('resize', requestResize);
    // in the stacked layout the hero's height follows its text (font swap, rotation): keep the
    // preview canvas's backing store matched to it
    if (window.ResizeObserver && el.preview && el.preview.parentNode) {
      try { new ResizeObserver(function () { requestResize(); }).observe(el.preview.parentNode); } catch (e) { /* ignore */ }
    }
  }

  function boot() {
    if (booted) return;
    booted = true;
    grabDom();
    bindEvents();
    applySoundUI();
    readSafe();
    setScreen('menu');
    if (order.length) {
      buildMenu(registry[order[0]]);
    } else {
      showMenuError('Игра не загрузилась. Обнови страницу.');
    }
    applyResize();
    waitForFonts(function () {
      fontsReady = true;
      if (!reducedMotion()) {
        el.root.classList.add('is-intro');
        setTimeout(function () { el.root.classList.remove('is-intro'); }, 1600);
      }
      el.root.classList.add('is-ready');
      requestResize();
    });
    lastTs = 0;
    rafId = requestAnimationFrame(frame);
  }

  function register(def) {
    if (!def || typeof def.id !== 'string' || !def.id) {
      reportError('register', new Error('game definition needs a string id'));
      return;
    }
    if (!has(registry, def.id)) order.push(def.id);
    registry[def.id] = def;
    if (booted && !menuDef) {
      buildMenu(def);
      el.play.disabled = false;
      el.play.style.display = '';
      el.record.style.display = '';
    }
  }

  // ---------------------------------------------------------------------------
  // Public API

  var debug = {
    timeScale: 1,
    start: function (gameId, difficulty, options) {
      if (!booted) boot();
      var def = registry[gameId] || (order.length ? registry[order[0]] : null);
      if (!def) return null;
      var base = def === menuDef ? copyOptions(selection.options) : {};
      if (options) for (var k in options) if (has(options, k)) base[k] = options[k];
      var diff = validDifficulty(difficulty) ? difficulty : (def === menuDef ? selection.difficulty : 'normal');
      return startGame(def, diff, base);
    }
  };
  Object.defineProperty(debug, 'instance', { enumerable: true, get: function () { return session ? session.instance : null; } });
  Object.defineProperty(debug, 'screen', { enumerable: true, get: function () { return screen; } });

  window.Arcade = {
    register: register,
    boot: boot,
    debug: debug
  };
})();
