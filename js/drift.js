/* «Горячая резина» — top-down drift racing. Registers itself with window.Arcade. */
(function () {
  'use strict';

  var Arcade = window.Arcade;
  if (!Arcade || typeof Arcade.register !== 'function') return;

  // =====================================================================================
  // Constants
  // =====================================================================================
  var TAU = Math.PI * 2;
  var DEG = Math.PI / 180;
  var STEP = 1 / 120;          // physics substep
  var KMH = 4.5;               // m/s -> displayed km/h (arcade scale)
  var DS = 2;                  // centreline sample spacing, m
  var LAPS = 3;
  var DRIFT_TIME = 90;
  var SKID_CAP = 1500;
  var SMOKE_CAP = 200;
  var SPARK_CAP = 90;
  var CHUNK = 12;              // centreline samples per render chunk
  var KERB_DASH = [1.3, 1.3], NO_DASH = [];

  var UI = {
    night: '#172031', night2: '#202C42', line: '#34435F', paper: '#F4EEDF', muted: '#9BA7BD',
    flame: '#FF5A36', gold: '#E7A93A', good: '#5CC57A', bad: '#E5484D'
  };

  var DIFF = {
    easy: {
      widthCars: 4.6, runoff: 8, grip: 1.12, release: 0, betaAdd: -4 * DEG, lift: 0.96, liftBrake: 5.5, over: 0.95, driftGrip: 1.08,
      offGrip: 0.8, offTop: 0.82, offDrag: 2, offDragV: 0.22, botPace: 0.82, rbBehind: 0.1, rbAhead: 0.04, starMul: 1.08
    },
    normal: {
      widthCars: 4.1, runoff: 7, grip: 1.0, release: 0.3, betaAdd: 0, lift: 1.0, liftBrake: 4.5, over: 1.0, driftGrip: 1.0,
      offGrip: 0.7, offTop: 0.72, offDrag: 3, offDragV: 0.3, botPace: 0.93, rbBehind: 0.1, rbAhead: 0.04, starMul: 1.0
    },
    hard: {
      widthCars: 3.7, runoff: 6, grip: 0.93, release: 0.65, betaAdd: 12 * DEG, lift: 1.1, liftBrake: 0, over: 1.08, driftGrip: 0.95,
      offGrip: 0.58, offTop: 0.6, offDrag: 4, offDragV: 0.34, botPace: 0.97, rbBehind: 0.1, rbAhead: 0.03, starMul: 0.97
    }
  };

  // Physical + visual parameters of the three cars (units: m, s, rad).
  var CARS = {
    hatch: {
      name: 'Хэтчбек', kind: 'hatch', len: 3.9, wid: 1.8, wb: 2.4, color: '#F2C230',
      vtop: 36, accel: 12.5, grip: 22.5, slideK: 1.1, latStiff: 11, lock: 0.62,
      yawMax: 2.5, yawResp: 12, yawRespSlide: 7.5, betaMax: 28 * DEG, betaFlick: 20 * DEG, betaK: 4.0, betaCap: 1.6, carry: 0.2, over: 1.15, slideT: 0.18,
      mass: 1.0, pitch: 1.2
    },
    coupe: {
      name: 'Купе', kind: 'coupe', len: 4.3, wid: 1.9, wb: 2.6, color: '#E5412D',
      vtop: 39, accel: 11.8, grip: 20.5, slideK: 1.12, latStiff: 10, lock: 0.6,
      yawMax: 2.55, yawResp: 11, yawRespSlide: 7, betaMax: 35 * DEG, betaFlick: 24 * DEG, betaK: 3.6, betaCap: 1.5, carry: 0.18, over: 1.3, slideT: 0.1,
      mass: 1.2, pitch: 1.0
    },
    muscle: {
      name: 'Маслкар', kind: 'muscle', len: 4.8, wid: 2.05, wb: 2.9, color: '#2F63D0',
      vtop: 42, accel: 12.2, grip: 19.5, slideK: 1.08, latStiff: 9, lock: 0.56,
      yawMax: 2.35, yawResp: 9, yawRespSlide: 6, betaMax: 38 * DEG, betaFlick: 26 * DEG, betaK: 3.3, betaCap: 1.35, carry: 0.16, over: 1.32, slideT: 0.12,
      mass: 1.6, pitch: 0.78
    }
  };
  var CAR_ORDER = ['hatch', 'coupe', 'muscle'];
  var EXTRA_COLOR = '#2FA36B';

  var THEMES = {
    ring: {
      ground: '#3E6A35', speck: ['#4B7B3F', '#33592D', '#5A8C4A', '#2E5129'],
      verge: '#5A8A45', sand: '#D6BD88', asphalt: '#4A4744', rubber: '#3F3C3A', rubberSoft: '#454240',
      edge: '#ECE6D8', treeA: ['#2E5B2A', '#386B31', '#44793A'], treeHi: 'rgba(255,255,240,0.10)'
    },
    port: {
      ground: '#626A72', speck: ['#6E767E', '#586067', '#7A828A', '#535A61'],
      verge: '#8F897C', sand: '#B4A98F', asphalt: '#434549', rubber: '#393B3F', rubberSoft: '#3E4044',
      edge: '#ECE6D8', sea: '#1D4A66', seaHi: '#2A6386'
    },
    serpent: {
      ground: '#55683A', speck: ['#617641', '#4A5B33', '#6C8248', '#43532E'],
      verge: '#6D8347', sand: '#BCA479', asphalt: '#4A4540', rubber: '#403B37', rubberSoft: '#45403B',
      edge: '#ECE6D8', treeA: ['#22422A', '#2A4F31', '#1C3923'], rock: '#8A8478', rockDark: '#6B665C'
    }
  };

  // bots lose a little time to line-following lag on twisty tracks; this evens out their pace
  var BOT_TRACK_K = { ring: 1.035, port: 1.065, serpent: 1.0 };
  // the loosest car is harder to drive at its limit, so its rivals are paced a touch gentler
  var BOT_CAR_K = { hatch: 1.0, coupe: 0.99, muscle: 0.965 };
  var TRACK_NAMES = { ring: 'Кольцо', port: 'Порт', serpent: 'Серпантин' };
  var MODE_NAMES = { race: 'Гонка', drift: 'Дрифт-зачёт', time: 'На время' };

  // =====================================================================================
  // Small helpers
  // =====================================================================================
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function sgn(v) { return v < 0 ? -1 : 1; }
  function wrapA(a) {
    while (a > Math.PI) a -= TAU;
    while (a < -Math.PI) a += TAU;
    return a;
  }
  function expK(rate, dt) { return 1 - Math.exp(-rate * dt); }
  function smooth01(t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); }
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hash1(n) {
    var x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  }
  function fmtTime(t) {
    if (!(t >= 0) || !isFinite(t)) return '–:––.––';
    var m = Math.floor(t / 60);
    var s = t - m * 60;
    var ss = Math.floor(s);
    var cs = Math.floor((s - ss) * 100);
    return m + ':' + (ss < 10 ? '0' : '') + ss + '.' + (cs < 10 ? '0' : '') + cs;
  }
  function fmtInt(n) {
    n = Math.round(n);
    var neg = n < 0;
    var s = String(Math.abs(n));
    var out = '';
    while (s.length > 3) { out = ' ' + s.slice(-3) + out; s = s.slice(0, -3); }
    return (neg ? '-' : '') + s + out;
  }
  function plural(n, one, few, many) {
    n = Math.abs(Math.round(n)) % 100;
    var n1 = n % 10;
    if (n > 10 && n < 20) return many;
    if (n1 > 1 && n1 < 5) return few;
    if (n1 === 1) return one;
    return many;
  }
  function hexRgb(h) {
    var n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function mixHex(a, b, k) {
    var x = hexRgb(a), y = hexRgb(b);
    return 'rgb(' + Math.round(x[0] + (y[0] - x[0]) * k) + ',' + Math.round(x[1] + (y[1] - x[1]) * k) + ',' +
      Math.round(x[2] + (y[2] - x[2]) * k) + ')';
  }
  function rgba(h, a) {
    var x = hexRgb(h);
    return 'rgba(' + x[0] + ',' + x[1] + ',' + x[2] + ',' + a + ')';
  }
  function rrect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
  function pickOpt(v, list, def) { return list.indexOf(v) >= 0 ? v : def; }
  function normOpts(o) {
    o = o || {};
    return {
      mode: pickOpt(o.mode, ['race', 'drift', 'time'], 'race'),
      track: pickOpt(o.track, ['ring', 'port', 'serpent'], 'ring'),
      car: pickOpt(o.car, CAR_ORDER, 'coupe')
    };
  }
  function normDiff(d) { return pickOpt(d, ['easy', 'normal', 'hard'], 'normal'); }
  function recKey(o, d) { return 'rec:' + o.mode + ':' + o.track + ':' + o.car + ':' + d; }
  // race bests are stored as {p: place, t: total time}; older saves hold just a time (place unknown)
  function raceBest(v) {
    if (typeof v === 'number' && isFinite(v)) return { p: 0, t: v };
    if (v && typeof v === 'object' && typeof v.t === 'number' && isFinite(v.t)) {
      var p = Math.round(+v.p);
      return { p: p >= 1 && p <= 4 ? p : 0, t: v.t };
    }
    return null;
  }

  // =====================================================================================
  // Track shapes (control points, metres; x right, y down)
  // =====================================================================================
  function scalePts(P, k) {
    var o = [];
    for (var i = 0; i < P.length; i++) o.push([P[i][0] * k, P[i][1] * k]);
    return o;
  }
  function rotateToNearest(P, hx, hy) {
    var bi = 0, bd = Infinity;
    for (var i = 0; i < P.length; i++) {
      var dx = P[i][0] - hx, dy = P[i][1] - hy, d = dx * dx + dy * dy;
      if (d < bd) { bd = d; bi = i; }
    }
    return P.slice(bi).concat(P.slice(0, bi));
  }
  // Rectilinear polygon -> control points with rounded corners (radius r) and straight fillers.
  function roundPoly(V, r) {
    var n = V.length, out = [];
    for (var i = 0; i < n; i++) {
      var p = V[(i - 1 + n) % n], v = V[i], q = V[(i + 1) % n];
      var ax = v[0] - p[0], ay = v[1] - p[1], al = Math.sqrt(ax * ax + ay * ay);
      ax /= al; ay /= al;
      var bx = q[0] - v[0], by = q[1] - v[1], bl = Math.sqrt(bx * bx + by * by);
      bx /= bl; by /= bl;
      out.push([v[0] - ax * r, v[1] - ay * r]);
      out.push([v[0] + (bx - ax) * 0.293 * r, v[1] + (by - ay) * 0.293 * r]);
      out.push([v[0] + bx * r, v[1] + by * r]);
      var len = bl - 2 * r;
      var m = Math.floor(len / 34);
      for (var k = 1; k <= m; k++) {
        var t = r + len * k / (m + 1);
        out.push([v[0] + bx * t, v[1] + by * t]);
      }
    }
    return out;
  }

  var TRACK_DEFS = {
    ring: function () {
      var P = [
        [0, -50], [150, -50], [262, -36], [332, 8], [352, 74], [328, 142], [266, 186], [180, 198],
        [95, 180], [25, 140], [-45, 104], [-120, 70], [-185, 30], [-228, 2], [-258, -12],
        [-276, -30], [-266, -50], [-236, -57], [-170, -54], [-85, -52]
      ];
      return scalePts(P, 0.8);
    },
    port: function () {
      var V = [
        [260, 0], [260, 110], [170, 110], [170, 220], [300, 220], [300, 300], [-40, 300], [-40, 190],
        [60, 190], [60, 90], [-60, 90], [-60, 0]
      ];
      var P = roundPoly(scalePts(V, 0.66), 14);
      return rotateToNearest(P, 55, 0);
    },
    serpent: function () {
      var P = [], g = 34, A = 25, lam = 200, X = 200, x, k, f;
      for (x = -260; x < -200; x += 30) P.push([x, -g]);
      for (x = -200; x < X; x += 25) P.push([x, -g + A * Math.cos(TAU * x / lam) - A]);
      for (k = 0; k < 6; k++) { f = k / 6 * Math.PI; P.push([X + g * Math.sin(f), -g * Math.cos(f)]); }
      for (x = X; x > -200; x -= 25) P.push([x, g + A * Math.cos(TAU * x / lam) - A]);
      for (x = -200; x > -260; x -= 30) P.push([x, g]);
      for (k = 0; k < 6; k++) { f = k / 6 * Math.PI; P.push([-260 - g * Math.sin(f), g * Math.cos(f)]); }
      return rotateToNearest(P, -200, -g);
    }
  };

  function catmullClosed(P, per) {
    var n = P.length, out = [];
    function d4(a, b) {
      var dx = b[0] - a[0], dy = b[1] - a[1];
      return Math.max(1e-4, Math.pow(dx * dx + dy * dy, 0.25));
    }
    for (var i = 0; i < n; i++) {
      var p0 = P[(i - 1 + n) % n], p1 = P[i], p2 = P[(i + 1) % n], p3 = P[(i + 2) % n];
      var t0 = 0, t1 = d4(p0, p1), t2 = t1 + d4(p1, p2), t3 = t2 + d4(p2, p3);
      for (var k = 0; k < per; k++) {
        var t = t1 + (t2 - t1) * k / per;
        var a1x = ((t1 - t) * p0[0] + (t - t0) * p1[0]) / (t1 - t0);
        var a1y = ((t1 - t) * p0[1] + (t - t0) * p1[1]) / (t1 - t0);
        var a2x = ((t2 - t) * p1[0] + (t - t1) * p2[0]) / (t2 - t1);
        var a2y = ((t2 - t) * p1[1] + (t - t1) * p2[1]) / (t2 - t1);
        var a3x = ((t3 - t) * p2[0] + (t - t2) * p3[0]) / (t3 - t2);
        var a3y = ((t3 - t) * p2[1] + (t - t2) * p3[1]) / (t3 - t2);
        var b1x = ((t2 - t) * a1x + (t - t0) * a2x) / (t2 - t0);
        var b1y = ((t2 - t) * a1y + (t - t0) * a2y) / (t2 - t0);
        var b2x = ((t3 - t) * a2x + (t - t1) * a3x) / (t3 - t1);
        var b2y = ((t3 - t) * a2y + (t - t1) * a3y) / (t3 - t1);
        out.push([((t2 - t) * b1x + (t - t1) * b2x) / (t2 - t1), ((t2 - t) * b1y + (t - t1) * b2y) / (t2 - t1)]);
      }
    }
    return out;
  }

  // Builds everything static about a track for a given difficulty.
  function buildTrack(key, diffKey) {
    var Dd = DIFF[diffKey];
    var ctrl = TRACK_DEFS[key]();
    var dense = catmullClosed(ctrl, 24);
    var nd = dense.length, cum = new Float64Array(nd + 1), total = 0, i, j, a, b;
    for (i = 0; i < nd; i++) {
      a = dense[i]; b = dense[(i + 1) % nd];
      total += Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]));
      cum[i + 1] = total;
    }
    var N = Math.round(total / DS), ds = total / N;
    var px = new Float64Array(N), py = new Float64Array(N);
    j = 0;
    for (i = 0; i < N; i++) {
      var s = i * ds;
      while (j < nd - 1 && cum[j + 1] < s) j++;
      var seg = cum[j + 1] - cum[j] || 1;
      var t = (s - cum[j]) / seg;
      a = dense[j]; b = dense[(j + 1) % nd];
      px[i] = a[0] + (b[0] - a[0]) * t;
      py[i] = a[1] + (b[1] - a[1]) * t;
    }
    var tx = new Float64Array(N), ty = new Float64Array(N), nx = new Float64Array(N), ny = new Float64Array(N);
    var ang = new Float64Array(N), kRaw = new Float64Array(N), k = new Float64Array(N);
    for (i = 0; i < N; i++) {
      var ip = (i + 1) % N, im = (i - 1 + N) % N;
      var dx = px[ip] - px[im], dy = py[ip] - py[im], l = Math.sqrt(dx * dx + dy * dy) || 1;
      tx[i] = dx / l; ty[i] = dy / l;
      nx[i] = -ty[i]; ny[i] = tx[i];
      ang[i] = Math.atan2(ty[i], tx[i]);
    }
    for (i = 0; i < N; i++) kRaw[i] = wrapA(ang[(i + 1) % N] - ang[(i - 1 + N) % N]) / (2 * ds);
    smoothArr(kRaw, k, N, 3, 2);
    var area = 0;
    for (i = 0; i < N; i++) { j = (i + 1) % N; area += px[i] * py[j] - px[j] * py[i]; }
    var inSide = area > 0 ? 1 : -1;
    var hw = Dd.widthCars * 2.0 / 2;
    var T = {
      key: key, name: TRACK_NAMES[key], theme: THEMES[key], N: N, ds: ds, L: total,
      px: px, py: py, tx: tx, ty: ty, nx: nx, ny: ny, ang: ang, k: k,
      inSide: inSide, outer: -inSide, hw: hw, wallDist: hw + Dd.runoff
    };
    var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (i = 0; i < N; i++) {
      if (px[i] < minx) minx = px[i]; if (px[i] > maxx) maxx = px[i];
      if (py[i] < miny) miny = py[i]; if (py[i] > maxy) maxy = py[i];
    }
    T.minx = minx; T.miny = miny; T.maxx = maxx; T.maxy = maxy;
    // checkpoints
    var NC = Math.max(10, Math.round(total / 60));
    T.NC = NC;
    T.cpS = new Float64Array(NC);
    for (i = 0; i < NC; i++) T.cpS[i] = total * i / NC;
    buildRacingLine(T);
    buildKerbs(T);
    buildChunks(T);
    buildStacks(T);
    T.grid = new Grid(16);
    T.scenery = [];
    buildScenery(T, key);
    return T;
  }

  function smoothArr(src, dst, N, rad, passes) {
    var tmp = new Float64Array(N), i, o, acc;
    for (i = 0; i < N; i++) dst[i] = src[i];
    for (var p = 0; p < passes; p++) {
      for (i = 0; i < N; i++) {
        acc = 0;
        for (o = -rad; o <= rad; o++) acc += dst[(i + o + N) % N];
        tmp[i] = acc / (2 * rad + 1);
      }
      for (i = 0; i < N; i++) dst[i] = tmp[i];
    }
  }

  function buildRacingLine(T) {
    var N = T.N, lim = T.hw - 1.35, i, it;
    var d = new Float64Array(N), lx = new Float64Array(N), ly = new Float64Array(N);
    for (i = 0; i < N; i++) { lx[i] = T.px[i]; ly[i] = T.py[i]; }
    for (it = 0; it < 700; it++) {
      for (i = 0; i < N; i++) {
        var im = (i - 1 + N) % N, ip = (i + 1) % N;
        var mx = (lx[im] + lx[ip]) * 0.5, my = (ly[im] + ly[ip]) * 0.5;
        var nd = (mx - T.px[i]) * T.nx[i] + (my - T.py[i]) * T.ny[i];
        nd = clamp(nd, -lim, lim);
        d[i] = nd;
        lx[i] = T.px[i] + T.nx[i] * nd;
        ly[i] = T.py[i] + T.ny[i] * nd;
      }
    }
    var lk = new Float64Array(N), lkr = new Float64Array(N), lds = new Float64Array(N);
    for (i = 0; i < N; i++) {
      var a = (i - 2 + N) % N, b = (i + 2) % N, c = (i + 1) % N;
      var a1 = Math.atan2(ly[i] - ly[a], lx[i] - lx[a]);
      var a2 = Math.atan2(ly[b] - ly[i], lx[b] - lx[i]);
      var l1 = Math.sqrt((ly[i] - ly[a]) * (ly[i] - ly[a]) + (lx[i] - lx[a]) * (lx[i] - lx[a]));
      var l2 = Math.sqrt((ly[b] - ly[i]) * (ly[b] - ly[i]) + (lx[b] - lx[i]) * (lx[b] - lx[i]));
      lkr[i] = wrapA(a2 - a1) / ((l1 + l2) * 0.5 || 1);
      lds[i] = Math.sqrt((lx[c] - lx[i]) * (lx[c] - lx[i]) + (ly[c] - ly[i]) * (ly[c] - ly[i]));
    }
    smoothArr(lkr, lk, N, 2, 2);
    T.line = d; T.lx = lx; T.ly = ly; T.lineK = lk; T.lineDs = lds;
  }

  function buildKerbs(T) {
    var N = T.N, i, thr = 1 / 72, flag = new Uint8Array(N);
    for (i = 0; i < N; i++) if (Math.abs(T.k[i]) > thr) flag[i] = 1;
    // find runs (handle wrap by starting at a non-corner sample)
    var start = -1;
    for (i = 0; i < N; i++) if (!flag[i]) { start = i; break; }
    T.kerbs = [];
    T.sandFlag = new Uint8Array(N);
    if (start < 0) return;
    var runs = [], cur = null;
    for (var c = 1; c <= N; c++) {
      i = (start + c) % N;
      if (flag[i]) {
        if (!cur) cur = { a: c, b: c };
        else cur.b = c;
      } else if (cur) { runs.push(cur); cur = null; }
    }
    if (cur) runs.push(cur);
    var hw = T.hw;
    for (var r = 0; r < runs.length; r++) {
      var a = runs[r].a + start, b = runs[r].b + start;
      if (b - a < 3) continue;
      var apex = a, km = 0;
      for (i = a; i <= b; i++) { var kk = Math.abs(T.k[i % N]); if (kk > km) { km = kk; apex = i; } }
      var side = sgn(T.k[apex % N]);
      T.kerbs.push(makeKerb(T, a - 3, b + 3, side, hw + 0.3));
      T.kerbs.push(makeKerb(T, apex + 2, b + 10, -side, hw + 0.3));
      if (km > 1 / 58) for (i = a - 8; i <= b + 12; i++) T.sandFlag[(i % N + N) % N] = 1;
    }
  }
  function makeKerb(T, a, b, side, off) {
    var N = T.N, pts = [], minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (var i = a; i <= b; i++) {
      var j = (i % N + N) % N;
      var x = T.px[j] + T.nx[j] * side * off, y = T.py[j] + T.ny[j] * side * off;
      pts.push(x, y);
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
    }
    return { pts: pts, minx: minx - 2, miny: miny - 2, maxx: maxx + 2, maxy: maxy + 2, path: null };
  }

  function buildChunks(T) {
    var N = T.N, m = T.wallDist + 3, chunks = [];
    for (var a = 0; a < N; a += CHUNK) {
      var b = Math.min(N, a + CHUNK);
      var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity, sand = 0;
      for (var i = a; i <= b; i++) {
        var j = i % N;
        if (T.px[j] < minx) minx = T.px[j]; if (T.px[j] > maxx) maxx = T.px[j];
        if (T.py[j] < miny) miny = T.py[j]; if (T.py[j] > maxy) maxy = T.py[j];
        if (T.sandFlag && T.sandFlag[j]) sand++;
      }
      chunks.push({ a: a, b: b, minx: minx - m, miny: miny - m, maxx: maxx + m, maxy: maxy + m, sand: sand > (b - a) * 0.5 });
    }
    T.chunks = chunks;
  }

  // global nearest distance to centreline (brute force, build time only)
  function distCentre(T, x, y) {
    var bd = Infinity;
    for (var i = 0; i < T.N; i++) {
      var dx = T.px[i] - x, dy = T.py[i] - y, d = dx * dx + dy * dy;
      if (d < bd) bd = d;
    }
    return Math.sqrt(bd);
  }
  function insideLoop(T, x, y) {
    var c = false, N = T.N;
    for (var i = 0, j = N - 1; i < N; j = i++) {
      var yi = T.py[i], yj = T.py[j];
      if ((yi > y) !== (yj > y)) {
        var xx = (T.px[j] - T.px[i]) * (y - yi) / (yj - yi) + T.px[i];
        if (x < xx) c = !c;
      }
    }
    return c;
  }

  function buildStacks(T) {
    var N = T.N, off = T.wallDist + 0.6, sx = [], sy = [], acc = 0, lastx = null, lasty = 0;
    for (var i = 0; i < N * 4; i++) {
      var f = i / 4, i0 = Math.floor(f) % N, i1 = (i0 + 1) % N, t = f - Math.floor(f);
      var cx = T.px[i0] + (T.px[i1] - T.px[i0]) * t, cy = T.py[i0] + (T.py[i1] - T.py[i0]) * t;
      var nnx = T.nx[i0] + (T.nx[i1] - T.nx[i0]) * t, nny = T.ny[i0] + (T.ny[i1] - T.ny[i0]) * t;
      var x = cx + nnx * T.outer * off, y = cy + nny * T.outer * off;
      if (lastx !== null) {
        var dx = x - lastx, dy = y - lasty;
        acc += Math.sqrt(dx * dx + dy * dy);
      }
      lastx = x; lasty = y;
      if (acc >= 1.15 || sx.length === 0) {
        acc = 0;
        if (distCentre(T, x, y) >= T.wallDist + 0.25) { sx.push(x); sy.push(y); }
      }
    }
    var n = sx.length;
    T.stackN = n;
    T.stackX = new Float64Array(sx);
    T.stackY = new Float64Array(sy);
    T.stackGroups = [];
    for (var a = 0; a < n; a += 24) {
      var b = Math.min(n, a + 24), minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
      for (var q = a; q < b; q++) {
        if (sx[q] < minx) minx = sx[q]; if (sx[q] > maxx) maxx = sx[q];
        if (sy[q] < miny) miny = sy[q]; if (sy[q] > maxy) maxy = sy[q];
      }
      T.stackGroups.push({ a: a, b: b, minx: minx - 2, miny: miny - 2, maxx: maxx + 2, maxy: maxy + 2 });
    }
  }

  // ---------------------------------------------------------------- spatial grid (static colliders)
  function Grid(cell) { this.cell = cell; this.map = new Map(); this.empty = []; }
  Grid.prototype.key = function (cx, cy) { return (cx + 4096) * 8192 + (cy + 4096); };
  Grid.prototype.add = function (o, minx, miny, maxx, maxy) {
    var c = this.cell;
    for (var cx = Math.floor(minx / c); cx <= Math.floor(maxx / c); cx++) {
      for (var cy = Math.floor(miny / c); cy <= Math.floor(maxy / c); cy++) {
        var k = this.key(cx, cy), arr = this.map.get(k);
        if (!arr) { arr = []; this.map.set(k, arr); }
        arr.push(o);
      }
    }
  };
  Grid.prototype.at = function (x, y) {
    var arr = this.map.get(this.key(Math.floor(x / this.cell), Math.floor(y / this.cell)));
    return arr || this.empty;
  };

  // ---------------------------------------------------------------- scenery
  function addCircleCollider(T, x, y, r) {
    var o = { box: false, x: x, y: y, r: r };
    T.grid.add(o, x - r - 3, y - r - 3, x + r + 3, y + r + 3);
  }
  function addBoxCollider(T, x, y, hx, hy, a) {
    var c = Math.cos(a), s = Math.sin(a);
    var o = { box: true, x: x, y: y, hx: hx, hy: hy, c: c, s: s };
    var e = Math.abs(c) * hx + Math.abs(s) * hy + 3, f = Math.abs(s) * hx + Math.abs(c) * hy + 3;
    T.grid.add(o, x - e, y - f, x + e, y + f);
  }
  function sceneItem(T, it, rad) {
    it.minx = it.x - rad; it.maxx = it.x + rad; it.miny = it.y - rad; it.maxy = it.y + rad;
    T.scenery.push(it);
  }

  function buildScenery(T, key) {
    var R = rng(key === 'ring' ? 11 : key === 'port' ? 23 : 37);
    var hw = T.hw, inMin = hw + 7.5, outMin = T.wallDist + 2.2;
    var i, x, y, d, inside;
    // Grandstand / start furniture next to the start line on the outer side
    var o = T.outer;
    var sx0 = T.px[0], sy0 = T.py[0], ttx = T.tx[0], tty = T.ty[0], onx = T.nx[0] * o, ony = T.ny[0] * o;
    T.gantry = { x: sx0, y: sy0, tx: ttx, ty: tty, nx: T.nx[0], ny: T.ny[0], half: T.wallDist + 1 };
    var standDist = T.wallDist + 4 + 6;
    var stand = {
      type: 'stand', x: sx0 + onx * standDist - ttx * 6, y: sy0 + ony * standDist - tty * 6,
      a: Math.atan2(tty, ttx), len: key === 'serpent' ? 46 : 70, dep: 11, seed: 5, face: 1
    };
    // the crowd faces the track: local +y of the stand must point toward the road
    stand.face = 1;
    var sa = stand.a, lyx = -Math.sin(sa), lyy = Math.cos(sa);
    if (lyx * -onx + lyy * -ony < 0) stand.face = -1;
    sceneItem(T, stand, 45);
    var standBox = stand;

    function clearOfStand(px, py, m) {
      var dx = px - standBox.x, dy = py - standBox.y;
      var c = Math.cos(standBox.a), s = Math.sin(standBox.a);
      var lx = dx * c + dy * s, ly = -dx * s + dy * c;
      return Math.abs(lx) > standBox.len / 2 + m || Math.abs(ly) > standBox.dep / 2 + m;
    }

    var bx0 = T.minx - 70, by0 = T.miny - 70, bx1 = T.maxx + 70, by1 = T.maxy + 70;

    if (key === 'port') {
      buildPort(T, R, inMin, outMin, clearOfStand);
    } else {
      var spacing = key === 'ring' ? 12 : 11;
      for (x = bx0; x < bx1; x += spacing) {
        for (y = by0; y < by1; y += spacing) {
          var jx = x + (R() - 0.5) * spacing * 0.9, jy = y + (R() - 0.5) * spacing * 0.9;
          var dens = 0.5 + 0.5 * Math.sin(jx * 0.021 + 1.3) * Math.cos(jy * 0.017 - 0.4);
          if (R() > 0.12 + 0.7 * dens) continue;
          d = distCentre(T, jx, jy);
          inside = insideLoop(T, jx, jy);
          var rr = key === 'ring' ? 2.2 + R() * 1.8 : 1.8 + R() * 1.6;
          if (d < (inside ? inMin + 3 : outMin + 2) + rr) continue;
          if (d > 95) continue;
          if (!clearOfStand(jx, jy, rr + 3)) continue;
          if (key === 'serpent' && !inside && R() < 0.3 && d < outMin + 16) {
            addRock(T, R, jx, jy, 1.4 + R() * 2.6, inside);
            continue;
          }
          var tree = { type: key === 'ring' ? 'tree' : 'pine', x: jx, y: jy, r: rr, c: Math.floor(R() * 3), rot: R() * TAU };
          sceneItem(T, tree, rr + 3);
          if (inside) addCircleCollider(T, jx, jy, rr * 0.55);
        }
      }
      if (key === 'serpent') {
        // rock clusters just outside the barrier on the outer side of bends
        for (i = 0; i < T.N; i += 9) {
          if (Math.abs(T.k[i]) < 1 / 70 || sgn(T.k[i]) === o) continue;
          for (var q = 0; q < 2; q++) {
            var dd = T.wallDist + 3 + R() * 7;
            x = T.px[i] + T.nx[i] * o * dd + (R() - 0.5) * 6;
            y = T.py[i] + T.ny[i] * o * dd + (R() - 0.5) * 6;
            if (distCentre(T, x, y) < outMin + 2) continue;
            addRock(T, R, x, y, 1.2 + R() * 2.2, false);
          }
        }
      }
    }
    // cones on the inside of the tightest corners
    for (i = 0; i < T.N; i += 3) {
      if (Math.abs(T.k[i]) < 1 / 28) continue;
      var side = sgn(T.k[i]);
      var cd = hw + 3.2;
      x = T.px[i] + T.nx[i] * side * cd; y = T.py[i] + T.ny[i] * side * cd;
      if (distCentre(T, x, y) < cd - 0.5) continue;
      sceneItem(T, { type: 'cone', x: x, y: y }, 1);
    }
  }

  function addRock(T, R, x, y, r, collide) {
    var n = 6 + Math.floor(R() * 3), pts = [];
    for (var k = 0; k < n; k++) {
      var a = k / n * TAU + (R() - 0.5) * 0.5, rr = r * (0.7 + R() * 0.35);
      pts.push(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    sceneItem(T, { type: 'rock', x: x, y: y, r: r, pts: pts }, r + 2);
    if (collide) addCircleCollider(T, x, y, r * 0.85);
  }

  var CONTAINER_COLS = ['#C8452F', '#2E6DA4', '#D39B2A', '#3E8A5A', '#8A8F96', '#B8573A', '#2F7F8C'];
  function buildPort(T, R, inMin, outMin, clearOfStand) {
    var cols = CONTAINER_COLS;
    var CL = 12.2, CW = 2.5, x, y, k;
    // sea beyond the southern edge
    T.seaY = T.maxy + T.wallDist + 26;
    sceneItem(T, { type: 'quay', x: (T.minx + T.maxx) / 2, y: T.seaY, w: (T.maxx - T.minx) + 400 }, 0);
    var sc = T.scenery[T.scenery.length - 1];
    sc.minx = T.minx - 250; sc.maxx = T.maxx + 250; sc.miny = T.seaY - 3; sc.maxy = T.seaY + 400;
    // container blocks on a regular yard grid
    var gx0 = Math.floor((T.minx - 60) / 14) * 14, gy0 = Math.floor((T.miny - 60) / 3.3) * 3.3;
    for (x = gx0; x < T.maxx + 60; x += 13.4) {
      var colBlock = Math.floor((x - gx0) / 13.4);
      if (colBlock % 5 === 4) continue;
      for (y = gy0; y < T.seaY - 8; y += 3.1) {
        var rowBlock = Math.floor((y - gy0) / 3.1);
        if (rowBlock % 6 >= 4) continue;
        var cx = x + CL / 2, cy = y + CW / 2;
        var ok = true, inside = insideLoop(T, cx, cy);
        var pts = [[cx - CL / 2, cy - CW / 2], [cx + CL / 2, cy - CW / 2], [cx - CL / 2, cy + CW / 2], [cx + CL / 2, cy + CW / 2], [cx, cy]];
        for (k = 0; k < pts.length; k++) {
          var dd = distCentre(T, pts[k][0], pts[k][1]);
          if (dd < (inside ? inMin + 1.5 : outMin + 1)) { ok = false; break; }
          if (insideLoop(T, pts[k][0], pts[k][1]) !== inside) { ok = false; break; }
        }
        if (!ok || !clearOfStand(cx, cy, 8)) continue;
        if (R() < 0.12) continue;
        var h = 1 + Math.floor(R() * 2.4), ci = Math.floor(R() * cols.length);
        sceneItem(T, { type: 'box', x: cx, y: cy, w: CL, h: CW, a: 0, ci: ci, col: cols[ci], lv: h }, CL / 2 + 3);
        if (inside) addBoxCollider(T, cx, cy, CL / 2, CW / 2, 0);
      }
    }
    // gantry cranes over some outer container rows
    var placed = 0, tries = 0;
    while (placed < 3 && tries < 400) {
      tries++;
      x = T.minx - 40 + R() * (T.maxx - T.minx + 80);
      y = T.miny - 40 + R() * (T.seaY - T.miny + 30);
      if (insideLoop(T, x, y)) continue;
      if (distCentre(T, x, y) < T.wallDist + 18) continue;
      if (!clearOfStand(x, y, 30)) continue;
      var clash = false;
      for (k = 0; k < T.scenery.length; k++) {
        var s2 = T.scenery[k];
        if (s2.type === 'crane' && Math.abs(s2.x - x) < 60) { clash = true; break; }
      }
      if (clash) continue;
      sceneItem(T, { type: 'crane', x: x, y: y, span: 22, depth: 16 }, 30);
      placed++;
    }
    // bollards along the quay
    for (x = T.minx - 200; x < T.maxx + 200; x += 18) {
      sceneItem(T, { type: 'bollard', x: x, y: T.seaY - 1.2 }, 1);
    }
    // painted yard lines inside and outside
    for (k = 0; k < 26; k++) {
      x = T.minx - 40 + R() * (T.maxx - T.minx + 80);
      y = T.miny - 40 + R() * (T.seaY - T.miny + 20);
      var horiz = R() < 0.5, len = 20 + R() * 40;
      var ex = horiz ? x + len : x, ey = horiz ? y : y + len;
      var okl = true;
      for (var q = 0; q <= 4; q++) {
        var qx = x + (ex - x) * q / 4, qy = y + (ey - y) * q / 4;
        if (distCentre(T, qx, qy) < T.wallDist + 1) { okl = false; break; }
      }
      if (!okl) continue;
      var it = { type: 'paint', x: (x + ex) / 2, y: (y + ey) / 2, x0: x, y0: y, x1: ex, y1: ey };
      sceneItem(T, it, len / 2 + 2);
    }
  }

  // =====================================================================================
  // Speed profile along the racing line
  // =====================================================================================
  function makeProfile(T, grip, vtop, accel, brake, onCentre) {
    var N = T.N, v = new Float64Array(N), i, p;
    var kArr = onCentre ? T.k : T.lineK, dsArr = T.lineDs;
    for (i = 0; i < N; i++) {
      var kk = Math.abs(kArr[i]);
      v[i] = Math.min(vtop, Math.sqrt(grip / Math.max(kk, 1e-5)));
    }
    for (p = 0; p < 3; p++) {
      for (i = N - 1; i >= 0; i--) {
        var nv = v[(i + 1) % N], lim = Math.sqrt(nv * nv + 2 * brake * (onCentre ? T.ds : dsArr[i]));
        if (v[i] > lim) v[i] = lim;
      }
    }
    for (p = 0; p < 3; p++) {
      for (i = 0; i < N; i++) {
        var im = (i - 1 + N) % N, pv = v[im];
        var q = pv / vtop, a = Math.max(0.6, accel * (1 - q * q));
        var lim2 = Math.sqrt(pv * pv + 2 * a * (onCentre ? T.ds : dsArr[im]));
        if (v[i] > lim2) v[i] = lim2;
      }
    }
    return v;
  }
  function profileLapTime(T, v) {
    var t = 0;
    for (var i = 0; i < T.N; i++) t += T.lineDs[i] / Math.max(1, v[i]);
    return t;
  }

  // =====================================================================================
  // Car drawing (local frame: +x forward, +y right, metres)
  // =====================================================================================
  function makeStyle(kind, color) {
    var m = CARS[kind];
    return {
      kind: kind, len: m.len, wid: m.wid, wb: m.wb, body: color,
      dark: mixHex(color, '#000000', 0.38), shade: mixHex(color, '#000000', 0.18),
      light: mixHex(color, '#FFFFFF', 0.32), glass: '#1B2230', glassHi: 'rgba(170,200,235,0.28)',
      roof: kind === 'hatch' ? '#26262A' : mixHex(color, '#FFFFFF', 0.12),
      stripe: kind === 'muscle' ? '#F4EEDF' : (kind === 'coupe' ? '#1E1F24' : '#1E1F24')
    };
  }

  function carBodyPath(ctx, st, i) {
    var hl = st.len / 2 - i, hw = st.wid / 2 - i;
    ctx.beginPath();
    if (st.kind === 'coupe') {
      ctx.moveTo(-hl, -hw + 0.3);
      ctx.quadraticCurveTo(-hl, -hw, -hl + 0.35, -hw);
      ctx.lineTo(hl - 1.0, -hw);
      ctx.quadraticCurveTo(hl - 0.1, -hw + 0.08, hl, -hw + 0.5);
      ctx.lineTo(hl, hw - 0.5);
      ctx.quadraticCurveTo(hl - 0.1, hw - 0.08, hl - 1.0, hw);
      ctx.lineTo(-hl + 0.35, hw);
      ctx.quadraticCurveTo(-hl, hw, -hl, hw - 0.3);
      ctx.closePath();
    } else if (st.kind === 'muscle') {
      rrect(ctx, -hl, -hw, hl * 2, hw * 2, 0.3);
    } else {
      rrect(ctx, -hl, -hw, hl * 2, hw * 2, 0.45);
    }
  }

  function drawWheel(ctx, x, y, a) {
    ctx.save();
    ctx.translate(x, y);
    if (a) ctx.rotate(a);
    ctx.fillRect(-0.34, -0.14, 0.68, 0.28);
    ctx.restore();
  }

  // Draws a car centred at origin, facing +x.
  function drawCarLocal(ctx, st, steerAng, braking, blink) {
    var hl = st.len / 2, hw = st.wid / 2, ax = st.wb / 2;
    var k = st.kind;
    // wheels (front ones turn with steering)
    ctx.fillStyle = '#131316';
    drawWheel(ctx, -ax, -hw + 0.1, 0);
    drawWheel(ctx, -ax, hw - 0.1, 0);
    drawWheel(ctx, ax, -hw + 0.1, steerAng);
    drawWheel(ctx, ax, hw - 0.1, steerAng);
    // body rim + body
    ctx.fillStyle = st.dark;
    carBodyPath(ctx, st, 0);
    ctx.fill();
    ctx.fillStyle = st.body;
    carBodyPath(ctx, st, 0.1);
    ctx.fill();
    // side shading for volume
    ctx.fillStyle = 'rgba(0,0,0,0.16)';
    ctx.fillRect(-hl + 0.3, hw - 0.36, st.len - 0.7, 0.24);
    ctx.fillStyle = 'rgba(255,255,255,0.10)';
    ctx.fillRect(-hl + 0.3, -hw + 0.12, st.len - 0.7, 0.2);

    var wsF, wsB, roofB, rgB, glassHalf;
    if (k === 'hatch') { wsF = 0.72; wsB = 0.2; roofB = -1.08; rgB = -1.52; glassHalf = 0.7; }
    else if (k === 'coupe') { wsF = 0.55; wsB = 0.0; roofB = -0.72; rgB = -1.48; glassHalf = 0.74; }
    else { wsF = 0.42; wsB = -0.08; roofB = -1.0; rgB = -1.36; glassHalf = 0.8; }

    // stripes (under the glass)
    if (k === 'muscle') {
      ctx.fillStyle = st.stripe;
      ctx.fillRect(-hl + 0.12, -0.36, st.len - 0.24, 0.22);
      ctx.fillRect(-hl + 0.12, 0.14, st.len - 0.24, 0.22);
    } else if (k === 'coupe') {
      ctx.fillStyle = 'rgba(20,20,26,0.85)';
      ctx.fillRect(wsF + 0.05, -0.08, hl - wsF - 0.3, 0.16);
    }
    // hood highlight
    ctx.fillStyle = 'rgba(255,255,255,0.12)';
    ctx.fillRect(wsF + 0.1, -hw + 0.35, hl - wsF - 0.4, 0.22);
    // windshield
    ctx.fillStyle = st.glass;
    ctx.beginPath();
    ctx.moveTo(wsF, -glassHalf + 0.12);
    ctx.lineTo(wsF, glassHalf - 0.12);
    ctx.lineTo(wsB, glassHalf);
    ctx.lineTo(wsB, -glassHalf);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = st.glassHi;
    ctx.beginPath();
    ctx.moveTo(wsF - 0.06, -glassHalf + 0.25);
    ctx.lineTo(wsF - 0.06, -glassHalf + 0.5);
    ctx.lineTo(wsB + 0.08, -glassHalf + 0.62);
    ctx.lineTo(wsB + 0.08, -glassHalf + 0.3);
    ctx.closePath();
    ctx.fill();
    // roof
    ctx.fillStyle = st.roof;
    ctx.beginPath();
    rrect(ctx, roofB, -glassHalf, wsB - roofB, glassHalf * 2, 0.14);
    ctx.fill();
    if (k === 'muscle') {
      ctx.fillStyle = st.stripe;
      ctx.fillRect(roofB, -0.36, wsB - roofB, 0.22);
      ctx.fillRect(roofB, 0.14, wsB - roofB, 0.22);
    }
    ctx.fillStyle = 'rgba(255,255,255,0.14)';
    ctx.fillRect(roofB + 0.15, -glassHalf + 0.12, wsB - roofB - 0.3, 0.18);
    // rear glass
    ctx.fillStyle = st.glass;
    ctx.beginPath();
    ctx.moveTo(roofB, -glassHalf);
    ctx.lineTo(roofB, glassHalf);
    ctx.lineTo(rgB, glassHalf - 0.1);
    ctx.lineTo(rgB, -glassHalf + 0.1);
    ctx.closePath();
    ctx.fill();
    // mirrors
    ctx.fillStyle = st.dark;
    ctx.fillRect(wsF - 0.12, -hw - 0.12, 0.2, 0.16);
    ctx.fillRect(wsF - 0.12, hw - 0.04, 0.2, 0.16);
    // bonnet scoop / spoiler
    if (k === 'muscle') {
      ctx.fillStyle = '#17181C';
      ctx.fillRect(0.95, -0.2, 0.62, 0.4);
    } else if (k === 'coupe') {
      ctx.fillStyle = '#17181C';
      ctx.fillRect(-hl + 0.05, -hw - 0.04, 0.22, st.wid + 0.08);
      ctx.fillRect(-hl + 0.22, -hw + 0.18, 0.2, 0.08);
      ctx.fillRect(-hl + 0.22, hw - 0.26, 0.2, 0.08);
    }
    // headlights
    ctx.fillStyle = '#FFF3C4';
    ctx.fillRect(hl - 0.2, -hw + 0.18, 0.16, 0.38);
    ctx.fillRect(hl - 0.2, hw - 0.56, 0.16, 0.38);
    // tail lights
    ctx.fillStyle = braking ? '#FF3B30' : '#A61D22';
    ctx.fillRect(-hl + 0.04, -hw + 0.16, 0.14, 0.36);
    ctx.fillRect(-hl + 0.04, hw - 0.52, 0.14, 0.36);
    if (braking) {
      ctx.fillStyle = 'rgba(255,60,40,0.28)';
      ctx.beginPath();
      ctx.arc(-hl - 0.1, -hw + 0.34, 0.45, 0, TAU);
      ctx.arc(-hl - 0.1, hw - 0.34, 0.45, 0, TAU);
      ctx.fill();
    }
    if (blink) {
      ctx.fillStyle = 'rgba(255,255,255,0.35)';
      carBodyPath(ctx, st, 0);
      ctx.fill();
    }
  }

  function drawCarShadow(ctx, st) {
    var hl = st.len / 2 + 0.1, hw = st.wid / 2 + 0.1;
    ctx.beginPath();
    rrect(ctx, -hl, -hw, hl * 2, hw * 2, 0.5);
    ctx.fill();
  }

  // =====================================================================================
  // Start-screen hero illustration
  // =====================================================================================
  var previewStyles = null;
  var PV = { x: 0, y: 0, a: 0, k: 0 }, PV2 = { x: 0, y: 0, a: 0, k: 0 };
  function drawPreview(ctx, w, h, t) {
    if (!(w > 4 && h > 4)) return;
    if (!previewStyles) previewStyles = [makeStyle('coupe', '#FF5A36'), makeStyle('muscle', '#2F63D0')];
    t = t || 0;
    var horiz = w >= h * 0.9;
    var m = Math.min(w, h), M = Math.max(w, h);
    var sc = m / 35;                              // px per metre: the cars are the heroes
    var R = 10.5;                                 // curve radius (centre line), m
    var hwR = 3.9;                                // road half width
    // keep the action clear of where a title usually sits: high in tall frames, a bit right in wide ones
    var fitM = M, cx = w / 2, cy = h / 2;
    if (h > w * 1.1) { fitM = M * 0.74; cy = h * 0.4; }
    else if (w > h * 1.4) { fitM = M * 0.9; cx = w * 0.55; }
    var halfS = Math.max(3, (fitM / sc) * 0.5 - R - hwR - 2.5);
    var P = 4 * halfS + 2 * Math.PI * R;
    var speed = P / 5.4;

    ctx.save();
    ctx.fillStyle = '#335638';
    ctx.fillRect(0, 0, w, h);
    ctx.translate(cx, cy);
    if (!horiz) ctx.rotate(Math.PI / 2);
    ctx.scale(sc, sc);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'butt';
    var ext = (M / sc) * 0.6 + 4, extY = (m / sc) * 0.6 + 4, q;
    // grass speckle
    ctx.fillStyle = 'rgba(150,200,130,0.08)';
    for (q = 0; q < 220; q++) ctx.fillRect((hash1(q * 3.1) - 0.5) * 2 * ext, (hash1(q * 7.7 + 1) - 0.5) * 2 * extY, 0.45, 0.45);
    ctx.fillStyle = 'rgba(0,0,0,0.08)';
    for (q = 0; q < 160; q++) ctx.fillRect((hash1(q * 5.3 + 2) - 0.5) * 2 * ext, (hash1(q * 2.9 + 4) - 0.5) * 2 * extY, 0.5, 0.5);

    function stadium(off) {
      ctx.beginPath();
      ctx.moveTo(-halfS, -R - off);
      ctx.lineTo(halfS, -R - off);
      ctx.arc(halfS, 0, R + off, -Math.PI / 2, Math.PI / 2);
      ctx.lineTo(-halfS, R + off);
      ctx.arc(-halfS, 0, R + off, Math.PI / 2, Math.PI * 1.5);
      ctx.closePath();
    }
    function curveBand(r0, r1, col) {
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(halfS, 0, r1, -Math.PI / 2, Math.PI / 2); ctx.arc(halfS, 0, r0, Math.PI / 2, -Math.PI / 2, true); ctx.fill();
      ctx.beginPath(); ctx.arc(-halfS, 0, r1, Math.PI / 2, Math.PI * 1.5); ctx.arc(-halfS, 0, r0, Math.PI * 1.5, Math.PI / 2, true); ctx.fill();
    }
    // verge + sand traps on the outside of both curves
    ctx.strokeStyle = '#3E6C3D';
    ctx.lineWidth = (hwR + 2.6) * 2;
    stadium(0); ctx.stroke();
    curveBand(R + hwR, R + hwR + 5.2, '#CDB282');
    // asphalt with a rubbered racing line
    ctx.strokeStyle = '#48454C';
    ctx.lineWidth = hwR * 2;
    stadium(0); ctx.stroke();
    ctx.strokeStyle = '#403D44';
    ctx.lineWidth = 2.6;
    stadium(-0.9); ctx.stroke();
    // painted edges
    ctx.strokeStyle = '#E9E3D5';
    ctx.lineWidth = 0.28;
    stadium(hwR - 0.35); ctx.stroke();
    stadium(-hwR + 0.35); ctx.stroke();
    // kerbs: inside of both curves
    ctx.lineWidth = 0.95;
    for (var side = 0; side < 2; side++) {
      var ccx = side ? -halfS : halfS, a0 = side ? Math.PI / 2 : -Math.PI / 2, a1 = a0 + Math.PI;
      ctx.strokeStyle = '#F1ECE0';
      ctx.beginPath(); ctx.arc(ccx, 0, R - hwR - 0.1, a0, a1); ctx.stroke();
      ctx.strokeStyle = '#D63A2F';
      ctx.setLineDash([1.1, 1.1]);
      ctx.beginPath(); ctx.arc(ccx, 0, R - hwR - 0.1, a0, a1); ctx.stroke();
      ctx.setLineDash([]);
    }
    // start / finish checker on the top straight
    var chx = -halfS * 0.45, cell = hwR * 2 / 7;
    for (var cxq = 0; cxq < 2; cxq++) {
      for (var cyq = 0; cyq < 7; cyq++) {
        ctx.fillStyle = (cxq + cyq) % 2 ? '#1A1A1E' : '#F1ECE0';
        ctx.fillRect(chx + cxq * cell, -R - hwR + cyq * cell, cell, cell);
      }
    }
    // tyre walls around the curves
    for (side = 0; side < 2; side++) {
      var sxc = side ? -halfS : halfS;
      ctx.fillStyle = 'rgba(0,0,0,0.25)';
      ctx.beginPath();
      for (var ti = 0; ti <= 26; ti++) {
        var ta = (side ? Math.PI / 2 : -Math.PI / 2) + Math.PI * ti / 26, tr = R + hwR + 5.8;
        ctx.moveTo(sxc + Math.cos(ta) * tr + 0.8, Math.sin(ta) * tr + 0.25);
        ctx.arc(sxc + Math.cos(ta) * tr + 0.25, Math.sin(ta) * tr + 0.25, 0.55, 0, TAU);
      }
      ctx.fill();
      for (ti = 0; ti <= 26; ti++) {
        ta = (side ? Math.PI / 2 : -Math.PI / 2) + Math.PI * ti / 26; tr = R + hwR + 5.8;
        var txx = sxc + Math.cos(ta) * tr, tyy = Math.sin(ta) * tr, white = ti % 4 === 0;
        ctx.fillStyle = white ? '#E9E4D8' : '#1F2023';
        ctx.beginPath(); ctx.arc(txx, tyy, 0.55, 0, TAU); ctx.fill();
        ctx.strokeStyle = white ? '#B5AEA0' : '#3C3E43';
        ctx.lineWidth = 0.12;
        ctx.beginPath(); ctx.arc(txx, tyy, 0.3, 0, TAU); ctx.stroke();
      }
    }

    function at(u, out) {
      u = ((u % P) + P) % P;
      var s1 = 2 * halfS, s2 = s1 + Math.PI * R, s3 = s2 + 2 * halfS, f;
      if (u < s1) { out.x = -halfS + u; out.y = -R; out.a = 0; }
      else if (u < s2) { f = (u - s1) / R; out.x = halfS + R * Math.sin(f); out.y = -R * Math.cos(f); out.a = f; }
      else if (u < s3) { out.x = halfS - (u - s2); out.y = R; out.a = Math.PI; }
      else { f = (u - s3) / R; out.x = -halfS - R * Math.sin(f); out.y = R * Math.cos(f); out.a = Math.PI + f; }
      return out;
    }
    function slipAt(u) {
      u = ((u % P) + P) % P;
      var s1 = 2 * halfS, s2 = s1 + Math.PI * R, s3 = s2 + 2 * halfS;
      function win(a, b) { return smooth01((u - (a - 7)) / 6) * (1 - smooth01((u - (b - 3)) / 7)); }
      return Math.max(win(s1, s2), win(s3, P), win(s3 - P, 0)) * 36 * DEG;
    }
    var wbH = 1.3, rw = 0.76;
    function rearWheel(u, sideSign, out) {
      at(u, out);
      var hd = out.a + slipAt(u), c = Math.cos(hd), s = Math.sin(hd);
      out.x = out.x - c * wbH - s * rw * sideSign;
      out.y = out.y - s * wbH + c * rw * sideSign;
      return out;
    }
    // old rubber on the curves
    ctx.lineCap = 'round';
    ctx.lineWidth = 0.26;
    ctx.strokeStyle = 'rgba(16,14,14,0.2)';
    var u, s1b = 2 * halfS;
    for (var pass = 0; pass < 2; pass++) {
      var base = pass ? s1b * 2 + Math.PI * R - 9 : s1b - 9;
      for (var sd = -1; sd <= 1; sd += 2) {
        ctx.beginPath();
        for (u = base; u <= base + Math.PI * R + 13; u += 0.8) {
          rearWheel(u, sd, PV);
          if (u === base) ctx.moveTo(PV.x, PV.y); else ctx.lineTo(PV.x, PV.y);
        }
        ctx.stroke();
      }
    }
    var uLead = t * speed, gap = P * 0.17, car;
    // fresh marks behind both cars
    for (car = 0; car < 2; car++) {
      var uc = uLead - car * gap;
      for (var seg = 0; seg < 4; seg++) {
        ctx.strokeStyle = 'rgba(16,14,14,' + (0.55 - seg * 0.12).toFixed(2) + ')';
        for (sd = -1; sd <= 1; sd += 2) {
          ctx.beginPath();
          var started = false;
          for (u = uc - seg * 5; u >= uc - (seg + 1) * 5 - 0.01; u -= 0.7) {
            if (slipAt(u) < 12 * DEG) { started = false; continue; }
            rearWheel(u, sd, PV);
            if (!started) { ctx.moveTo(PV.x, PV.y); started = true; } else ctx.lineTo(PV.x, PV.y);
          }
          ctx.stroke();
        }
      }
    }
    // cars: shadows, then bodies (chaser first)
    for (car = 1; car >= 0; car--) {
      var ucar = uLead - car * gap, sl0 = slipAt(ucar);
      at(ucar, PV);
      var hd = PV.a + sl0;
      ctx.save();
      ctx.translate(PV.x + 0.4, PV.y + 0.55);
      ctx.rotate(hd);
      ctx.fillStyle = 'rgba(0,0,0,0.38)';
      drawCarShadow(ctx, previewStyles[car]);
      ctx.restore();
      ctx.save();
      ctx.translate(PV.x, PV.y);
      ctx.rotate(hd);
      drawCarLocal(ctx, previewStyles[car], -sl0 * 0.6, false, false);
      ctx.restore();
    }
    // tyre smoke: particles emitted in the past, fully determined by t
    var dtE = 0.045, life = 1.3, kNow = Math.floor(t / dtE);
    ctx.fillStyle = '#EEEBE6';
    for (car = 0; car < 2; car++) {
      for (var j = 0; j < life / dtE; j++) {
        var ke = kNow - j, te = ke * dtE, age = t - te;
        if (age < 0 || age > life) continue;
        var ue = te * speed - car * gap, sl = slipAt(ue);
        if (sl < 14 * DEG) continue;
        rearWheel(ue, (ke % 2) ? 1 : -1, PV);
        at(ue, PV2);
        var hr = hash1(ke * 1.37 + car * 17.1), hr2 = hash1(ke * 2.91 + car * 5.3);
        var ox = Math.sin(PV2.a), oy = -Math.cos(PV2.a);          // outward (left of travel)
        var dr = 1.6 + hr * 2.2;
        var sx = PV.x + ox * dr * age - Math.cos(PV2.a) * age * 1.2 + (hr2 - 0.5) * 1.4 * age;
        var sy = PV.y + oy * dr * age - Math.sin(PV2.a) * age * 1.2 + (hr - 0.5) * 1.4 * age;
        var rad = 0.5 + age * (2.2 + hr * 1.2);
        ctx.globalAlpha = (1 - age / life) * (1 - age / life) * 0.42 * (sl / (36 * DEG));
        ctx.beginPath(); ctx.arc(sx, sy, rad, 0, TAU); ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
    // trees (canopies above everything)
    var trees = [[-halfS * 0.35, -1.2, 3.2], [halfS * 0.25, 1.8, 2.7], [-halfS - R - hwR - 11, -R + 2, 3.4],
      [halfS + R + hwR + 11, R - 3, 3.1], [halfS * 0.6, -R - hwR - 8, 3.0], [-halfS * 0.7, R + hwR + 8, 3.3]];
    for (var k2 = 0; k2 < trees.length; k2++) {
      var T0 = trees[k2];
      ctx.fillStyle = 'rgba(0,0,0,0.28)';
      ctx.beginPath(); ctx.arc(T0[0] + 1.0, T0[1] + 1.3, T0[2], 0, TAU); ctx.fill();
      ctx.fillStyle = k2 % 2 ? '#2B5628' : '#356830';
      ctx.beginPath(); ctx.arc(T0[0], T0[1], T0[2], 0, TAU); ctx.fill();
      ctx.fillStyle = k2 % 2 ? '#356830' : '#3F7638';
      ctx.beginPath(); ctx.arc(T0[0] - T0[2] * 0.2, T0[1] - T0[2] * 0.22, T0[2] * 0.66, 0, TAU); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,230,0.10)';
      ctx.beginPath(); ctx.arc(T0[0] - T0[2] * 0.35, T0[1] - T0[2] * 0.38, T0[2] * 0.35, 0, TAU); ctx.fill();
    }
    ctx.restore();
    // vignette blending into the page
    var g = ctx.createRadialGradient(w / 2, h / 2, m * 0.32, w / 2, h / 2, Math.sqrt(w * w + h * h) * 0.6);
    g.addColorStop(0, 'rgba(23,32,49,0)');
    g.addColorStop(1, 'rgba(23,32,49,0.78)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
  }

  // =====================================================================================
  // The game instance
  // =====================================================================================
  function createGame(api) {
    var O = normOpts(api.options);
    var mode = O.mode, trackKey = O.track, carKey = O.car;
    var diffKey = normDiff(api.difficulty);
    var D = DIFF[diffKey];
    var T = buildTrack(trackKey, diffKey);
    var TH = T.theme;
    var N = T.N, L = T.L;
    var reduced = !!api.reducedMotion;

    var vw = api.width || 800, vh = api.height || 600;
    var hudU = 1;

    // ---------------------------------------------------------------- cars
    var PM = CARS[carKey];
    var profile = makeProfile(T, PM.grip * D.grip * 0.98, PM.vtop, PM.accel * 0.85, 13);
    var idealLap = profileLapTime(T, profile);
    // what the automatic throttle aims for (gentler braking than the ideal profile)
    // (players drive near the centre line, so it is computed on the centre line, not the racing line)
    var liftProfile = D.lift > 0 ? makeProfile(T, PM.grip * D.grip * 1.12, PM.vtop, PM.accel, 5, true) : null;

    function newCar(kind, color, isPlayer) {
      var m = CARS[kind];
      return {
        isPlayer: isPlayer, kind: kind, m: m, st: makeStyle(kind, color), color: color,
        x: 0, y: 0, a: 0, vx: 0, vy: 0, w: 0, px: 0, py: 0, pa: 0,
        mass: m.mass, inertia: m.mass * (m.len * m.len + m.wid * m.wid) / 12 * 1.5,
        steer: 0, steerAng: 0, hbF: 0, hb: false, throttle: 0, sliding: false, slip: 0, speed: 0, vf: 0, off: 0,
        omP: 0, velA: 0, prevTs: 0, overT: 0, autoBrake: 0,
        ti: 0, ts: 0, td: 0, lap: 0, nextCp: 0, started: false, finished: false, finishTime: 0,
        lapStart: 0, lapTimes: [], bestLap: Infinity, raceDist: 0, place: 1,
        // bots
        s: 0, d: 0, dd: 0, v: 0, pace: 1, rb: 1, visSlip: 0, react: 0, targetD: 0, avoidT: 0,
        // effects
        mOn: false, mlx: 0, mly: 0, mrx: 0, mry: 0, emit: 0,
        stuckT: 0, wrongT: 0, skipT: 0, ghostT: 0, hitCd: 0, brakeT: 0, blockT: 0
      };
    }

    var cars = [];
    var player = newCar(carKey, PM.color, true);
    cars.push(player);
    if (mode === 'race') {
      var others = CAR_ORDER.filter(function (kk) { return kk !== carKey; });
      var botKinds = [others[0], others[1], carKey];
      var botCols = [CARS[others[0]].color, CARS[others[1]].color, EXTRA_COLOR];
      var paces = [1.0, 0.975, 0.955];
      var R0 = rng(Math.floor(Math.random() * 1e9));
      for (var bi = 0; bi < 3; bi++) {
        var b = newCar(botKinds[bi], botCols[bi], false);
        b.pace = D.botPace * paces[bi] * (0.99 + R0() * 0.02) * BOT_TRACK_K[trackKey] * BOT_CAR_K[carKey];
        b.react = 0.12 + R0() * 0.3;
        cars.push(b);
      }
    }

    // grid: slot k sits (8 + 7k) m behind the line, alternating sides
    function gridPlace(car, slot) {
      var sBack = 8 + 7 * slot;
      var s = L - sBack;
      var side = slot % 2 === 0 ? -1 : 1;
      var dOff = side * Math.min(1.9, T.hw - 1.6);
      var P0 = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
      centreAt(s, P0);
      car.x = P0.x + P0.nx * dOff; car.y = P0.y + P0.ny * dOff;
      car.a = Math.atan2(P0.ty, P0.tx);
      car.px = car.x; car.py = car.y; car.pa = car.a;
      car.s = s; car.d = dOff; car.targetD = dOff;
      car.ti = Math.floor(s / T.ds) % N; car.ts = s; car.td = dOff;
    }
    var slotOrder = mode === 'race' ? [2, 0, 1, 3] : [0];
    for (var ci = 0; ci < cars.length; ci++) gridPlace(cars[ci], slotOrder[ci]);

    // ---------------------------------------------------------------- state
    var phase = 'countdown';
    var cdT = 3.6, lastCount = 4;
    var raceTime = 0, goFlash = 0, clock = 0;
    var timeLeft = DRIFT_TIME;
    var acc = 0;
    var paused = false, over = false, overT = 0, resultSent = false;
    var dbgSteer = null, dbgHb = false, autoPilot = false;
    var respawns = 0, sandbox = false, hitCount = 0, overview = false;
    var totalDrift = 0, bestDrift = 0, maxCombo = 1;
    var dr = { active: false, pts: 0, dir: 0, calm: 0, combo: 1, comboT: 0, t: 0, offT: 0 };
    var popups = [];
    var msg = { text: '', sub: '', t: 0, dur: 0, color: UI.paper, subColor: UI.paper };
    var hintT = 0;
    var wrongShow = 0;
    var shake = 0;
    var cam = { x: player.x, y: player.y, a: player.a, z: 1, lx: 0, ly: 0, init: false };
    var ptrs = [];
    var steerInput = 0, hbInput = false;
    var lastLapFlash = 0;

    // ---------------------------------------------------------------- effects buffers
    var skid = new Float32Array(SKID_CAP * 4), skidHead = 0, skidCount = 0;
    var smk = {
      x: new Float32Array(SMOKE_CAP), y: new Float32Array(SMOKE_CAP), vx: new Float32Array(SMOKE_CAP),
      vy: new Float32Array(SMOKE_CAP), age: new Float32Array(SMOKE_CAP), life: new Float32Array(SMOKE_CAP),
      r: new Float32Array(SMOKE_CAP), g: new Float32Array(SMOKE_CAP), dust: new Uint8Array(SMOKE_CAP), head: 0
    };
    for (var si = 0; si < SMOKE_CAP; si++) smk.life[si] = 0;
    var spk = {
      x: new Float32Array(SPARK_CAP), y: new Float32Array(SPARK_CAP), vx: new Float32Array(SPARK_CAP),
      vy: new Float32Array(SPARK_CAP), age: new Float32Array(SPARK_CAP), life: new Float32Array(SPARK_CAP), head: 0
    };
    var fxR = rng(99);

    // ---------------------------------------------------------------- track queries
    function centreAt(s, out) {
      s = ((s % L) + L) % L;
      var f = s / T.ds, i0 = Math.floor(f) % N, i1 = (i0 + 1) % N, t = f - Math.floor(f);
      out.x = T.px[i0] + (T.px[i1] - T.px[i0]) * t;
      out.y = T.py[i0] + (T.py[i1] - T.py[i0]) * t;
      var tx = T.tx[i0] + (T.tx[i1] - T.tx[i0]) * t, ty = T.ty[i0] + (T.ty[i1] - T.ty[i0]) * t;
      var l = Math.sqrt(tx * tx + ty * ty) || 1;
      out.tx = tx / l; out.ty = ty / l; out.nx = -out.ty; out.ny = out.tx;
      out.k = T.k[i0] + (T.k[i1] - T.k[i0]) * t;
      out.i = i0; out.f = t;
      return out;
    }
    function nearestIdx(x, y, hint, win) {
      var best = 0, bd = Infinity, i, j, dx, dy, d;
      if (hint < 0) {
        for (i = 0; i < N; i++) {
          dx = T.px[i] - x; dy = T.py[i] - y; d = dx * dx + dy * dy;
          if (d < bd) { bd = d; best = i; }
        }
      } else {
        for (var o = -win; o <= win; o++) {
          j = (hint + o + N) % N;
          dx = T.px[j] - x; dy = T.py[j] - y; d = dx * dx + dy * dy;
          if (d < bd) { bd = d; best = j; }
        }
      }
      return best;
    }
    var PR = { i: 0, s: 0, d: 0, dist: 0, nx: 0, ny: 0, tx: 0, ty: 0 };
    function project(x, y, i, out) {
      // best of segments (i-1,i) and (i,i+1)
      var bestD = Infinity;
      for (var q = -1; q <= 0; q++) {
        var a = (i + q + N) % N, b = (a + 1) % N;
        var ax = T.px[a], ay = T.py[a], ux = T.px[b] - ax, uy = T.py[b] - ay;
        var ll = ux * ux + uy * uy || 1;
        var t = clamp(((x - ax) * ux + (y - ay) * uy) / ll, 0, 1);
        var qx = ax + ux * t, qy = ay + uy * t, dx = x - qx, dy = y - qy, dd = dx * dx + dy * dy;
        if (dd < bestD) {
          bestD = dd;
          var nxx = T.nx[a] + (T.nx[b] - T.nx[a]) * t, nyy = T.ny[a] + (T.ny[b] - T.ny[a]) * t;
          var nl = Math.sqrt(nxx * nxx + nyy * nyy) || 1;
          nxx /= nl; nyy /= nl;
          out.i = t > 0.5 ? b : a;
          var sv = (a + t) * T.ds;
          if (sv >= L) sv -= L;
          out.s = sv;
          out.d = dx * nxx + dy * nyy;
          out.nx = nxx; out.ny = nyy; out.tx = nyy; out.ty = -nxx;
        }
      }
      out.dist = Math.sqrt(bestD);
      return out;
    }

    // Updates car.ti/ts/td; returns true if the tracked position jumped (no checkpoint credit)
    var trackCounter = 0;
    function trackCar(car, forceGlobal) {
      var jumped = false;
      var i = nearestIdx(car.x, car.y, forceGlobal ? -1 : car.ti, 5);
      project(car.x, car.y, i, PR);
      if (!forceGlobal && PR.dist > T.hw + 4 && ((trackCounter + (car.isPlayer ? 0 : 7)) % 24 === 0)) {
        var g = nearestIdx(car.x, car.y, -1, 0);
        var gdx = T.px[g] - car.x, gdy = T.py[g] - car.y;
        if (Math.sqrt(gdx * gdx + gdy * gdy) < PR.dist - 3) {
          var jd = Math.abs(g - i);
          if (jd > N / 2) jd = N - jd;
          if (jd > 6) jumped = true;
          i = g;
          project(car.x, car.y, i, PR);
        }
      }
      if (forceGlobal) jumped = true;
      car.ti = i; car.ts = PR.s; car.td = PR.d;
      return jumped;
    }

    // ---------------------------------------------------------------- checkpoints / laps
    function crossed(prev, cur, target) {
      var d = cur - prev;
      if (d < -L / 2) d += L; else if (d > L / 2) d -= L;
      if (d <= 0 || d > 40) return false;
      var t = target - prev;
      if (t < 0) t += L;
      if (t >= L) t -= L;
      return t > 0 && t <= d;
    }
    function onCheckpoint(car) {
      if (car.nextCp === 0) {
        if (!car.started) {
          car.started = true;
          car.lapStart = raceTime;
        } else {
          var lt = raceTime - car.lapStart;
          car.lapStart = raceTime;
          car.lap++;
          car.lapTimes.push(lt);
          var improved = lt < car.bestLap;
          if (improved) car.bestLap = lt;
          if (car.isPlayer) onPlayerLap(lt, improved);
          if (mode !== 'drift' && car.lap >= LAPS && !car.finished) {
            car.finished = true;
            car.finishTime = raceTime;
            if (car.isPlayer) onPlayerFinish();
          }
        }
        car.nextCp = 1;
      } else {
        car.nextCp = (car.nextCp + 1) % T.NC;
      }
    }
    function updateProgress(car, prevS, jumped) {
      if (!jumped) {
        var guard = 0;
        while (guard++ < 3 && crossed(prevS, car.ts, T.cpS[car.nextCp])) onCheckpoint(car);
      }
      var sp = car.ts, rd;
      if (!car.started) rd = sp > L / 2 ? sp - L : sp - L;
      else {
        var lo = car.nextCp === 0 ? T.cpS[T.NC - 1] : T.cpS[car.nextCp - 1];
        var hi = car.nextCp === 0 ? L : T.cpS[car.nextCp];
        var v = (sp >= lo - 5 && sp <= hi) ? sp : lo;
        if (car.nextCp === 1 && sp > L - 30) v = 0;
        rd = car.lap * L + v;
      }
      if (car.finished) rd = LAPS * L + 1000 - car.finishTime;
      car.raceDist = rd;
    }

    // ---------------------------------------------------------------- player events
    function onPlayerLap(lt, improved) {
      var lapNo = player.lap;
      if (mode === 'drift') {
        flash('Круг ' + (lapNo + 1), fmtTime(lt), UI.paper, 1.4);
        api.sound('lap');
        return;
      }
      if (lapNo >= LAPS) return;
      var best = improved && lapNo >= 2;
      api.sound(best ? 'bestlap' : 'lap');
      if (lapNo === LAPS - 1) {
        // the start of the final lap is always announced; a best lap rides along in gold
        flash('Последний круг', best ? 'Лучший круг ' + fmtTime(lt) : fmtTime(lt), UI.paper, 1.8);
        msg.subColor = best ? UI.gold : UI.paper;
      } else if (best) flash('Лучший круг!', fmtTime(lt), UI.gold, 1.8);
      else flash('Круг ' + (lapNo + 1), fmtTime(lt), UI.paper, 1.6);
      lastLapFlash = 1.5;
    }
    function onPlayerFinish() {
      bankDrift(true);
      computePlaces();
      phase = 'finished';
      overT = 0;
      api.sound('finish');
      finalizeResult();
      var place = player.place;
      if (mode === 'race') flash(place === 1 ? 'Победа!' : 'Финиш', place + '-е место', place === 1 ? UI.gold : UI.paper, 3);
      else flash('Финиш', fmtTime(player.finishTime), UI.paper, 3);
    }
    function flash(text, sub, color, dur) {
      msg.text = text; msg.sub = sub || ''; msg.color = color || UI.paper; msg.subColor = UI.paper; msg.t = 0; msg.dur = dur || 1.6;
    }
    function popup(text, color, big) {
      var p = popups.length >= 6 ? popups.shift() : {};
      p.text = text; p.color = color; p.t = 0; p.big = !!big;
      popups.push(p);
    }

    // ---------------------------------------------------------------- drift scoring
    function bankDrift(silent) {
      if (!dr.active) return;
      dr.active = false;
      var gained = Math.round(dr.pts * dr.combo);
      if (gained >= 20) {
        totalDrift += gained;
        if (gained > bestDrift) bestDrift = gained;
        popup('+' + fmtInt(gained) + (dr.combo > 1 ? '  ×' + dr.combo : ''), UI.gold, true);
        if (!silent) api.sound('bank', { pitch: 1 + (dr.combo - 1) * 0.08 });
        dr.comboT = 2.6;
      } else {
        dr.comboT = 0;
      }
      dr.pts = 0;
    }
    function failDrift() {
      if (!dr.active) return;
      var had = dr.pts;
      dr.active = false; dr.pts = 0; dr.combo = 1; dr.comboT = 0;
      if (had > 40) {
        popup('Сорвалось!', UI.bad, true);
        api.sound('fail');
      }
    }
    function driftStep(h) {
      var p = player;
      var aslip = Math.abs(p.slip);
      var ok = phase === 'race' && !p.finished && p.vf > 0 && aslip < 110 * DEG;
      var drifting = ok && aslip > 12 * DEG && p.speed > 11 && p.off < 0.85;
      if (dr.active && p.off > 0.85) { dr.offT += h; if (dr.offT > 0.2) { failDrift(); return; } } else dr.offT = 0;
      if (drifting) {
        if (!dr.active) {
          dr.active = true; dr.pts = 0; dr.calm = 0; dr.t = 0;
          dr.dir = sgn(p.slip);
          dr.combo = dr.comboT > 0 ? Math.min(5, dr.combo + 1) : 1;
        } else if (sgn(p.slip) !== dr.dir && aslip > 15 * DEG) {
          dr.dir = sgn(p.slip);
          if (dr.combo < 5) { dr.combo++; }
        }
        if (dr.combo > maxCombo) maxCombo = dr.combo;
        dr.pts += Math.min(aslip, 70 * DEG) / DEG * p.speed * h * 0.5;
        dr.calm = 0;
        dr.t += h;
      } else if (dr.active) {
        dr.calm += h;
        if (dr.calm > 0.6) bankDrift(false);
      } else if (dr.comboT > 0) {
        dr.comboT -= h;
        if (dr.comboT <= 0) dr.combo = 1;
      }
    }

    // ---------------------------------------------------------------- input
    function sideOf(x) { return x < vw / 2 ? -1 : 1; }
    function pointerDown(p) {
      if (!p) return;
      for (var i = 0; i < ptrs.length; i++) if (ptrs[i].id === p.id) { ptrs.splice(i, 1); break; }
      ptrs.push({ id: p.id, side: sideOf(p.x), t: clock });
      if (ptrs.length > 8) ptrs.shift();
    }
    function pointerMove(p) {
      if (!p) return;
      for (var i = 0; i < ptrs.length; i++) if (ptrs[i].id === p.id) { ptrs[i].side = sideOf(p.x); return; }
    }
    function pointerUp(p) {
      if (!p) return;
      for (var i = 0; i < ptrs.length; i++) if (ptrs[i].id === p.id) { ptrs.splice(i, 1); return; }
    }
    var inL = false, inR = false;
    // Direction for a handbrake started with both thumbs at once: keep the current turn, else kick
    // toward the next bend (positive curvature = right turn = positive steer), else toward the road centre.
    function hbKickDir() {
      if (Math.abs(player.steer) > 0.2) return sgn(player.steer);
      if (Math.abs(player.w) > 0.25) return sgn(player.w);
      var kA = 0;
      for (var kk = 4; kk <= 30; kk += 2) kA += T.k[(player.ti + kk) % N];
      if (Math.abs(kA) > 0.02) return sgn(kA);
      if (Math.abs(player.td) > 0.4) return -sgn(player.td);
      return sgn(kA);
    }
    function readInput() {
      var L0 = null, R0 = null, i;
      for (i = 0; i < ptrs.length; i++) {
        var q = ptrs[i];
        if (q.side < 0) { if (!L0 || q.t < L0.t) L0 = q; }
        else if (!R0 || q.t < R0.t) R0 = q;
      }
      inL = !!L0; inR = !!R0;
      if (L0 && R0) {
        hbInput = true;
        if (Math.abs(L0.t - R0.t) < 0.1) steerInput = hbKickDir();
        else steerInput = L0.t < R0.t ? -1 : 1;
      } else if (ptrs.length >= 2) {
        // two fingers on the same half: handbrake, steering toward that side
        hbInput = true;
        steerInput = L0 ? -1 : 1;
      } else {
        hbInput = false;
        steerInput = L0 ? -1 : (R0 ? 1 : 0);
      }
      if (dbgSteer !== null) { steerInput = dbgSteer; }
      if (dbgHb) hbInput = true;
      if (dbgSteer !== null && !dbgHb && ptrs.length === 0) hbInput = false;
    }

    // simple autopilot (used after the finish and by tests)
    var APt = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
    function autoSteer(car, look) {
      var la = look || (7 + car.speed * 0.45);
      centreAt(car.ts + la, APt);
      var li = APt.i, lineD = T.line[li] * 0.6;
      var tx = APt.x + APt.nx * lineD, ty = APt.y + APt.ny * lineD;
      var want = Math.atan2(ty - car.y, tx - car.x);
      var velA = car.speed > 3 ? Math.atan2(car.vy, car.vx) : car.a;
      var hd = lerp(car.a, car.a - wrapA(car.a - velA), 0.5);
      var err = wrapA(want - hd);
      return clamp(err * 2.6, -1, 1);
    }

    // ---------------------------------------------------------------- physics
    function stepPlayer(car, h) {
      var M = car.m;
      var c = Math.cos(car.a), s = Math.sin(car.a);
      var vf = car.vx * c + car.vy * s;
      var vr = -car.vx * s + car.vy * c;
      var v = Math.sqrt(car.vx * car.vx + car.vy * car.vy);
      var slip = v > 0.8 ? Math.atan2(-vr, vf) : 0;
      car.slip = slip; car.speed = v; car.vf = vf;
      // how fast the direction of travel is turning (feed-forward for the drift controller)
      var va = Math.atan2(car.vy, car.vx);
      if (v > 2) {
        var om = clamp(wrapA(va - car.velA) / h, -4, 4);
        car.omP += (om - car.omP) * expK(18, h);
      } else car.omP = 0;
      car.velA = va;
      var off = car.off;
      var gripMul = D.grip * lerp(1, D.offGrip, off);
      var hb = car.hbF;
      var st = car.steer;
      var aslip = Math.abs(slip);

      // ---- yaw
      var vyaw = Math.max(Math.abs(vf), 3.5);
      // speed-sensitive steering: at speed full lock asks for ~1.5x the available grip, half lock stays gripped
      var yawMax = Math.min(vyaw * M.lock / M.wb * 1.6, M.yawMax, M.over * D.over * M.grip * D.grip / Math.max(v, 1));
      var target;
      if (car.sliding && vf > 2 && aslip < 2.1) {
        // in a slide the steering asks for a drift ANGLE; the controller holds it
        var d = aslip > 2 * DEG ? sgn(slip) : (st !== 0 ? sgn(st) : sgn(slip));
        var u = st * d;                                   // + steering into the slide, - countersteer
        var bmax = (M.betaMax + D.betaAdd) * (1 + 0.35 * hb);
        var brel = Math.min(aslip * D.release, 1.9);       // what the car does with no input
        var bt = u >= 0 ? lerp(brel, bmax, Math.pow(u, 1.5)) : lerp(brel, -M.betaFlick, -u);
        var cap = M.betaCap * (1 + 0.6 * hb);
        target = car.omP + clamp(d * M.betaK * (1 + 0.5 * hb) * (bt - aslip), -cap, cap);
      } else {
        target = st * yawMax * (1 + 0.4 * hb);
      }
      car.w += (target - car.w) * expK(car.sliding ? M.yawRespSlide : M.yawResp, h);

      // ---- lateral tyre force (static -> kinetic friction)
      var gLat = (car.sliding ? M.grip * M.slideK * D.driftGrip : M.grip) * gripMul * (1 - 0.62 * hb);
      var want = -vr * expK(M.latStiff, h);
      var lim = gLat * h;
      var lat = want > lim ? lim : (want < -lim ? -lim : want);
      if (!car.sliding) {
        // the tyres must be over the limit for a moment before the tail lets go (small corrections stay gripped)
        if (Math.abs(want) > lim * 1.001 && v > 12) car.overT += h; else car.overT = Math.max(0, car.overT - 2 * h);
        if (car.overT > M.slideT) { car.sliding = true; car.overT = 0; }
      } else if (hb < 0.05 && aslip < 10 * DEG && Math.abs(vr) < 2.4) {
        car.sliding = false;
      }
      if (hb > 0.5 && v > 5) car.sliding = true;
      var fx = -s * lat, fy = c * lat;
      if (car.sliding && v > 3 && hb < 0.5) {
        // arcade "carry": most of the sideways friction turns the car's path instead of scrubbing speed
        var ux = car.vx / v, uy = car.vy / v;
        var along = fx * ux + fy * uy;
        if (along < 0) {
          var mag = Math.sqrt(fx * fx + fy * fy);
          var prx = fx - along * ux, pry = fy - along * uy;
          var pm = Math.sqrt(prx * prx + pry * pry);
          var along2 = along * (1 - M.carry);
          var pm2 = Math.sqrt(Math.max(0, mag * mag - along2 * along2));
          if (pm > 1e-7) { prx *= pm2 / pm; pry *= pm2 / pm; }
          fx = prx + along2 * ux; fy = pry + along2 * uy;
        }
      }

      // ---- longitudinal
      var vtop = M.vtop * lerp(1, D.offTop, off);
      var thr = car.throttle * (1 - 0.75 * hb);
      var aF;
      if (vf >= 0) {
        var q = vf / vtop;
        aF = thr * M.accel * (1 - q * q);
        if (q > 1) aF = -Math.min(9, (q - 1) * 30 + 1.5);
        aF -= (1 - thr) * (1.2 + 0.03 * vf);
        aF -= hb * 7.5 + (car.autoBrake || 0);
        if (vf + aF * h < 0) aF = -vf / h;
      } else {
        aF = thr * M.accel * 0.8 + 4;
      }
      car.vx += c * aF * h + fx;
      car.vy += s * aF * h + fy;
      // run-off drags the car down (against its whole velocity, so it does not also swing the tail out):
      // cutting a corner through the sand must cost time; deep in it bites much harder than one wheel over
      if (off > 0 && v > 0.5) {
        var dv = off * Math.sqrt(off) * (D.offDrag * (T.sandFlag[car.ti] ? 1.6 : 1) + D.offDragV * v) * h;
        var kd = Math.max(0, 1 - dv / v);
        car.vx *= kd; car.vy *= kd;
      }
      car.a += car.w * h;
      car.x += car.vx * h;
      car.y += car.vy * h;
      car.brakeT = hb > 0.3 || car.throttle < 0.5 ? 0.2 : Math.max(0, car.brakeT - h);
      car.steerAng = st * 0.5 - (car.sliding ? clamp(slip, -0.5, 0.5) * 0.7 : 0);
    }

    // kinematic bots on the racing line
    var BP = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
    function stepBot(b, h) {
      if (!(b.s >= 0 && b.s < L)) b.s = ((b.s % L) + L) % L || 0;
      if (!(b.v >= 0)) b.v = 0;
      var i = Math.floor(b.s / T.ds) % N;
      var tgtV = 0;
      if (phase !== 'countdown' && raceTime > b.react) {
        var la = (i + 3) % N;
        tgtV = Math.min(profile[i], profile[la]) * b.pace * b.rb;
        if (b.finished) tgtV *= 0.65;
      }
      // avoidance: look for cars ahead in the same lane
      var wantD = T.line[(i + 4) % N];
      var lim = T.hw - 1.3, laneLim = T.hw - 1.0, blocked = false;
      for (var j = 0; j < cars.length && b.ghostT <= 0; j++) {
        var o = cars[j];
        if (o === b) continue;
        var gap = o.ts - b.s;
        if (gap < -L / 2) gap += L; else if (gap > L / 2) gap -= L;
        if (gap > 0 && gap < 13) {
          var lat = o.td - b.d;
          if (Math.abs(lat) < 2.7) {
            // pass lanes from the real car widths; the wider side wins when neither is comfortable
            var po = (o.m.wid + b.m.wid) * 0.5 + 0.55;
            var passR = o.td + po, passL = o.td - po;
            var canR = passR < laneLim, canL = passL > -laneLim;
            if (canR && (!canL || Math.abs(passR - wantD) < Math.abs(passL - wantD))) wantD = passR;
            else if (canL) wantD = passL;
            else wantD = o.td > 0 ? -laneLim : laneLim;
            var ov = o.isPlayer ? o.vf : o.v;
            if (gap < 7 && (!canR && !canL || Math.abs(lat) < 1.6)) {
              tgtV = Math.min(tgtV, Math.max(0, ov - 0.5));
              blocked = true;
            }
          }
        }
      }
      b.targetD = clamp(wantD, -laneLim, laneLim);
      // stuck behind a stopped car: after a moment it drives through it (ghosted) instead of waiting forever
      if (blocked && tgtV < 1 && phase === 'race' && !b.finished) b.blockT += h; else b.blockT = Math.max(0, b.blockT - h);
      if (b.blockT > 1.5) { b.blockT = 0; b.ghostT = 1.2; }
      var accel = b.m.accel * 0.95 * (1 - Math.pow(b.v / (b.m.vtop * 1.05), 2));
      var dv = tgtV - b.v;
      b.v += clamp(dv, -14 * h, Math.max(0.3, accel) * h);
      if (b.v < 0) b.v = 0;
      // lateral dynamics
      var ddMax = Math.min(4, b.v * 0.3);                  // no sideways creeping while standing still
      if (blocked && phase === 'race') ddMax = Math.max(1.4, ddMax);   // ...unless it must steer round a stopped car
      var wantDD = clamp((b.targetD - b.d) * 2.2, -ddMax, ddMax);
      b.dd += clamp(wantDD - b.dd, -12 * h, 12 * h);
      b.d += b.dd * h;
      if (b.d > T.hw - 1.0) { b.d = T.hw - 1.0; if (b.dd > 0) b.dd = 0; }
      if (b.d < -T.hw + 1.0) { b.d = -T.hw + 1.0; if (b.dd < 0) b.dd = 0; }
      centreAt(b.s, BP);
      var fac = clamp(1 - BP.k * b.d, 0.6, 1.4);
      b.s += b.v * h / fac;
      if (b.s >= L) b.s -= L;
      centreAt(b.s, BP);
      var nxp = BP.x + BP.nx * b.d, nyp = BP.y + BP.ny * b.d;
      var pathA = Math.atan2(BP.ty, BP.tx) + Math.atan2(b.dd, Math.max(4, b.v));
      // visual slide: tail out when lateral accel approaches the limit
      var lk = T.lineK[i];
      var latA = b.v * b.v * Math.abs(lk);
      var want = clamp((latA / (b.m.grip * D.grip) - 0.5) * 1.3, 0, 0.55) * sgn(lk);
      if (b.v < 10) want = 0;
      b.visSlip += (want - b.visSlip) * expK(3, h);
      b.vx = (nxp - b.x) / h; b.vy = (nyp - b.y) / h;
      b.x = nxp; b.y = nyp;
      b.a = pathA + b.visSlip;
      b.slip = b.visSlip; b.speed = b.v; b.vf = b.v;
      b.sliding = Math.abs(b.visSlip) > 0.14;
      b.steerAng = clamp(lk * 6, -0.45, 0.45) - b.visSlip * 0.5;
      b.ts = b.s; b.td = b.d; b.ti = i;
      b.throttle = tgtV > b.v ? 1 : 0.3;
      b.brakeT = dv < -1.5 ? 0.2 : Math.max(0, b.brakeT - h);
    }

    // ---------------------------------------------------------------- collisions
    var circ = [0, 0, 0, 0, 0, 0];
    function carCircles(car, out) {
      var e = (car.m.len - car.m.wid) / 2 * 0.95, c = Math.cos(car.a), s = Math.sin(car.a);
      out[0] = car.x + c * e; out[1] = car.y + s * e;
      out[2] = car.x; out[3] = car.y;
      out[4] = car.x - c * e; out[5] = car.y - s * e;
      return car.m.wid / 2;
    }
    // impulse between player-like rigid car A and (static | bot B)
    function impulse(A, cxp, cyp, nx, ny, pen, B, e, mu) {
      var rx = cxp - A.x, ry = cyp - A.y;
      var mA = A.mass, iA = A.inertia;
      var invB = B ? 1 / B.mass : 0;
      var vax = A.vx - A.w * ry, vay = A.vy + A.w * rx;
      var vbx = B ? B.vx : 0, vby = B ? B.vy : 0;
      var rvx = vax - vbx, rvy = vay - vby;
      var vn = rvx * nx + rvy * ny;
      // positional correction
      var share = B ? B.mass / (mA + B.mass) : 1;
      A.x += nx * pen * share; A.y += ny * pen * share;
      if (B) {
        var bs = pen * (1 - share);
        B.s -= (nx * BP2tx(B) + ny * BP2ty(B)) * bs;
        if (B.s < 0) B.s += L; else if (B.s >= L) B.s -= L;
        B.d -= (nx * BP2nx(B) + ny * BP2ny(B)) * bs;
      }
      if (vn >= 0) return 0;
      var rn = rx * ny - ry * nx;
      var j = -(1 + e) * vn / (1 / mA + invB + rn * rn / iA);
      A.vx += nx * j / mA; A.vy += ny * j / mA; A.w += rn * j / iA;
      var tx = -ny, ty = nx, vt = rvx * tx + rvy * ty, rt = rx * ty - ry * tx;
      var jt = -vt / (1 / mA + invB + rt * rt / iA);
      jt = clamp(jt, -mu * j, mu * j);
      A.vx += tx * jt / mA; A.vy += ty * jt / mA; A.w += rt * jt / iA;
      if (A.w > 4) A.w = 4; else if (A.w < -4) A.w = -4;
      if (B) {
        var dvx = -(nx * j + tx * jt) * invB, dvy = -(ny * j + ty * jt) * invB;
        B.v = Math.max(0, B.v + dvx * BP2tx(B) + dvy * BP2ty(B));
        B.dd += (dvx * BP2nx(B) + dvy * BP2ny(B)) * 0.8;
      }
      return j / mA;
    }
    var BQ = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
    var bqFor = null;
    function bq(B) { if (bqFor !== B) { centreAt(B.s, BQ); bqFor = B; } return BQ; }
    function BP2tx(B) { return bq(B).tx; }
    function BP2ty(B) { return bq(B).ty; }
    function BP2nx(B) { return bq(B).nx; }
    function BP2ny(B) { return bq(B).ny; }

    var PW = { i: 0, s: 0, d: 0, dist: 0, nx: 0, ny: 0, tx: 0, ty: 0 };
    function collidePlayer(car) {
      var r = carCircles(car, circ);
      var hitMax = 0, k, hx = 0, hy = 0, hnx = 0, hny = 0;
      // outer barrier
      for (k = 0; k < 3; k++) {
        var qx = circ[k * 2], qy = circ[k * 2 + 1];
        var i = nearestIdx(qx, qy, car.ti, 4);
        project(qx, qy, i, PW);
        var dOut = PW.d * T.outer;
        var pen = dOut + r - T.wallDist;
        if (pen > 0) {
          var nX = -PW.nx * T.outer, nY = -PW.ny * T.outer;
          var cxp = qx - nX * r, cyp = qy - nY * r;
          var jv = impulse(car, cxp, cyp, nX, nY, pen, null, 0.3, 0.22);
          if (jv > hitMax) { hitMax = jv; hx = cxp; hy = cyp; hnx = nX; hny = nY; }
          carCircles(car, circ);
        }
      }
      // static scenery colliders
      var list = T.grid.at(car.x, car.y);
      for (var o = 0; o < list.length; o++) {
        var ob = list[o];
        for (k = 0; k < 3; k++) {
          var px = circ[k * 2], py = circ[k * 2 + 1], nx, ny, pn, cpx, cpy;
          if (!ob.box) {
            var dx = px - ob.x, dy = py - ob.y, dd = Math.sqrt(dx * dx + dy * dy);
            pn = r + ob.r - dd;
            if (pn <= 0) continue;
            if (dd < 1e-4) { dx = 1; dy = 0; dd = 1; }
            nx = dx / dd; ny = dy / dd;
            cpx = px - nx * r; cpy = py - ny * r;
          } else {
            var lx0 = px - ob.x, ly0 = py - ob.y;
            var lx = lx0 * ob.c + ly0 * ob.s, ly = -lx0 * ob.s + ly0 * ob.c;
            var qx2 = clamp(lx, -ob.hx, ob.hx), qy2 = clamp(ly, -ob.hy, ob.hy);
            var ddx = lx - qx2, ddy = ly - qy2, dl = Math.sqrt(ddx * ddx + ddy * ddy);
            var lnx, lny;
            if (dl > 1e-4) {
              pn = r - dl;
              if (pn <= 0) continue;
              lnx = ddx / dl; lny = ddy / dl;
            } else {
              var ex = ob.hx - Math.abs(lx), ey = ob.hy - Math.abs(ly);
              if (ex < ey) { lnx = sgn(lx); lny = 0; pn = ex + r; } else { lnx = 0; lny = sgn(ly); pn = ey + r; }
            }
            nx = lnx * ob.c - lny * ob.s; ny = lnx * ob.s + lny * ob.c;
            cpx = px - nx * r; cpy = py - ny * r;
          }
          var jv2 = impulse(car, cpx, cpy, nx, ny, pn, null, 0.25, 0.3);
          if (jv2 > hitMax) { hitMax = jv2; hx = cpx; hy = cpy; hnx = nx; hny = ny; }
          carCircles(car, circ);
        }
      }
      // other cars
      if (car.ghostT <= 0) {
        for (var bj = 1; bj < cars.length; bj++) {
          var B = cars[bj];
          if (B.ghostT > 0) continue;
          var ddx2 = B.x - car.x, ddy2 = B.y - car.y;
          if (ddx2 * ddx2 + ddy2 * ddy2 > 64) continue;
          var rb = carCircles(B, circB);
          bqFor = null;
          for (k = 0; k < 3; k++) {
            for (var kb = 0; kb < 3; kb++) {
              var ax = circ[k * 2], ay = circ[k * 2 + 1], bx = circB[kb * 2], by = circB[kb * 2 + 1];
              var cdx = ax - bx, cdy = ay - by, cd = Math.sqrt(cdx * cdx + cdy * cdy);
              var pp = r + rb - cd;
              if (pp <= 0) continue;
              if (cd < 1e-4) { cdx = 1; cdy = 0; cd = 1; }
              var nnx = cdx / cd, nny = cdy / cd;
              var jv3 = impulse(car, ax - nnx * r, ay - nny * r, nnx, nny, pp, B, 0.35, 0.2);
              if (jv3 > hitMax) { hitMax = jv3; hx = ax - nnx * r; hy = ay - nny * r; hnx = nnx; hny = nny; }
              carCircles(car, circ);
              carCircles(B, circB);
            }
          }
        }
      }
      if (hitMax > 1.5) onHit(car, hitMax, hx, hy, hnx, hny);
    }
    var circB = [0, 0, 0, 0, 0, 0];

    function botSeparation() {
      for (var i = 1; i < cars.length; i++) {
        for (var j = i + 1; j < cars.length; j++) {
          var A = cars[i], B = cars[j];
          if (A.ghostT > 0 || B.ghostT > 0) continue;
          var gap = B.s - A.s;
          if (gap < -L / 2) gap += L; else if (gap > L / 2) gap -= L;
          if (Math.abs(gap) > 6) continue;
          var lat = B.d - A.d;
          if (Math.abs(lat) > 2.7) continue;
          var push = (2.7 - Math.abs(lat)) * 0.5;
          var dir = lat >= 0 ? 1 : -1;
          A.d -= dir * push * 0.5; B.d += dir * push * 0.5;
          var back = gap >= 0 ? A : B, front = gap >= 0 ? B : A;
          if (back.v > front.v - 0.3) back.v = Math.max(0, front.v - 0.3);
        }
      }
    }

    var hitFlash = { x: 0, y: 0, t: 0, s: 0 };
    function onHit(car, jv, x, y, nx, ny) {
      if (car.hitCd > 0) return;
      car.hitCd = 0.25;
      if (jv > 3) hitCount++;
      var strength = clamp(jv / 10, 0.1, 1);
      if (jv > 3.5) api.sound('crash', { volume: clamp(0.25 + strength * 0.75, 0, 1), pitch: 0.9 + fxR() * 0.2 });
      if (!reduced) shake = Math.max(shake, strength * 0.7);
      var n = Math.round((reduced ? 6 : 10) + strength * (reduced ? 10 : 20));
      if (jv > 3.5) { hitFlash.x = x; hitFlash.y = y; hitFlash.t = 0.12; hitFlash.s = strength; }
      for (var k = 0; k < n; k++) {
        var i = spk.head; spk.head = (spk.head + 1) % SPARK_CAP;
        var tx = -ny, ty = nx, sp = 6 + fxR() * 12, side = fxR() < 0.5 ? -1 : 1;
        spk.x[i] = x; spk.y[i] = y;
        spk.vx[i] = tx * sp * side + nx * (2 + fxR() * 5) + car.vx * 0.3;
        spk.vy[i] = ty * sp * side + ny * (2 + fxR() * 5) + car.vy * 0.3;
        spk.age[i] = 0; spk.life[i] = 0.25 + fxR() * 0.35;
      }
      if (jv > 2.2) failDrift();
    }

    // ---------------------------------------------------------------- effects
    function addSkid(x0, y0, x1, y1) {
      var o = skidHead * 4;
      skid[o] = x0; skid[o + 1] = y0; skid[o + 2] = x1; skid[o + 3] = y1;
      skidHead = (skidHead + 1) % SKID_CAP;
      if (skidCount < SKID_CAP) skidCount++;
    }
    function spawnSmoke(x, y, vx, vy, dust, strength) {
      var i = smk.head; smk.head = (smk.head + 1) % SMOKE_CAP;
      smk.x[i] = x; smk.y[i] = y;
      smk.vx[i] = vx * 0.12 + (fxR() - 0.5) * 2.4;
      smk.vy[i] = vy * 0.12 + (fxR() - 0.5) * 2.4;
      smk.age[i] = 0;
      smk.life[i] = (dust ? 0.8 : 1.1) + fxR() * 0.6;
      smk.r[i] = 0.5 + fxR() * 0.3;
      smk.g[i] = (dust ? 1.8 : 2.4) * (0.7 + strength * 0.5);
      smk.dust[i] = dust ? 1 : 0;
    }
    function carEffects(car, h) {
      var c = Math.cos(car.a), s = Math.sin(car.a);
      var ax = -car.m.wb / 2, yw = car.m.wid / 2 - 0.22;
      var lx = car.x + c * ax + s * yw, ly = car.y + s * ax - c * yw;
      var rx = car.x + c * ax - s * yw, ry = car.y + s * ax + c * yw;
      var aslip = Math.abs(car.slip);
      var marking = car.speed > 4 && car.off < 0.5 && (aslip > 9 * DEG || car.hbF > 0.5);
      if (marking) {
        if (!car.mOn) { car.mOn = true; car.mlx = lx; car.mly = ly; car.mrx = rx; car.mry = ry; }
        else {
          var dx = lx - car.mlx, dy = ly - car.mly;
          if (dx * dx + dy * dy > 0.16) {
            addSkid(car.mlx, car.mly, lx, ly);
            addSkid(car.mrx, car.mry, rx, ry);
            car.mlx = lx; car.mly = ly; car.mrx = rx; car.mry = ry;
          }
        }
      } else car.mOn = false;
      // smoke / dust
      var rate = 0, dust = false;
      if (car.off > 0.5 && car.speed > 6) { rate = 10 + car.speed * 0.6; dust = true; }
      else if (car.speed > 7 && (aslip > 14 * DEG || car.hbF > 0.5)) rate = clamp((aslip / DEG - 10) * 1.1, 6, 42) + car.hbF * 10;
      if (reduced) rate *= 0.5;
      if (!car.isPlayer) rate *= 0.6;
      car.emit += rate * h;
      while (car.emit >= 1) {
        car.emit -= 1;
        var left = fxR() < 0.5;
        spawnSmoke(left ? lx : rx, left ? ly : ry, car.vx, car.vy, dust, clamp(aslip / (40 * DEG), 0.3, 1.2));
      }
    }
    function stepParticles(dt) {
      var i;
      if (hitFlash.t > 0) hitFlash.t = Math.max(0, hitFlash.t - dt);
      for (i = 0; i < SMOKE_CAP; i++) {
        if (smk.life[i] <= 0) continue;
        smk.age[i] += dt;
        if (smk.age[i] >= smk.life[i]) { smk.life[i] = 0; continue; }
        var dmp = Math.exp(-1.6 * dt);
        smk.vx[i] *= dmp; smk.vy[i] *= dmp;
        smk.x[i] += smk.vx[i] * dt; smk.y[i] += smk.vy[i] * dt;
        smk.r[i] += smk.g[i] * dt;
      }
      for (i = 0; i < SPARK_CAP; i++) {
        if (spk.life[i] <= 0) continue;
        spk.age[i] += dt;
        if (spk.age[i] >= spk.life[i]) { spk.life[i] = 0; continue; }
        var d2 = Math.exp(-4 * dt);
        spk.vx[i] *= d2; spk.vy[i] *= d2;
        spk.x[i] += spk.vx[i] * dt; spk.y[i] += spk.vy[i] * dt;
      }
    }

    // ---------------------------------------------------------------- respawn
    var RS = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
    // Nearest centreline sample inside the stretch the car is allowed to be on: from just before the
    // last checkpoint it passed up to the next one, so a respawn can never skip a checkpoint.
    function sectionIdx(car) {
      var loS, hiS;
      if (car.started) {
        loS = (car.nextCp === 0 ? T.cpS[T.NC - 1] : T.cpS[car.nextCp - 1]) - 10;
        hiS = car.nextCp === 0 ? L : T.cpS[car.nextCp];
      } else { loS = L - 60; hiS = L; }
      var i0 = Math.floor(loS / T.ds), i1 = Math.floor(hiS / T.ds) - 1, best = -1, bd = Infinity;
      for (var ii = i0; ii <= i1; ii++) {
        var j = ((ii % N) + N) % N, dx = T.px[j] - car.x, dy = T.py[j] - car.y, d = dx * dx + dy * dy;
        if (d < bd) { bd = d; best = j; }
      }
      return best < 0 ? nearestIdx(car.x, car.y, -1, 0) : best;
    }
    function respawn(car, sAt) {
      var s = sAt !== undefined ? sAt : sectionIdx(car) * T.ds - 4;
      centreAt(s, RS);
      car.x = RS.x; car.y = RS.y; car.a = Math.atan2(RS.ty, RS.tx);
      car.vx = RS.tx * 6; car.vy = RS.ty * 6; car.w = 0;
      car.px = car.x; car.py = car.y; car.pa = car.a;
      car.sliding = false; car.steer = 0; car.hbF = 0; car.velA = car.a; car.omP = 0;
      car.ghostT = 1.6; car.stuckT = 0; car.wrongT = 0; car.skipT = 0; car.mOn = false;
      trackCar(car, true);
      respawns++;
      failDrift();
      if (car.isPlayer) cam.init = false;              // clean cut to the new heading, no whip-pan
    }
    // A car that left the road and rejoined further along (skipping a checkpoint) would silently lose
    // a whole lap: put it back at the checkpoint it missed, and say why.
    function checkSkipped(car, h) {
      var ahead = car.ts - T.cpS[car.nextCp];
      if (ahead > L / 2) ahead -= L; else if (ahead <= -L / 2) ahead += L;
      if (ahead > 25 && car.off < 0.5) car.skipT += h; else car.skipT = Math.max(0, car.skipT - 2 * h);
      if (car.skipT < 1.2) return;
      if (mode === 'drift') {
        // laps do not matter here: just resync the checkpoint chain (no lap credit)
        var k = 0;
        while (k++ < T.NC && crossedAhead(car)) car.nextCp = (car.nextCp + 1) % T.NC;
        car.skipT = 0;
        return;
      }
      flash('Пропущена отметка', 'Возврат на трассу', UI.bad, 1.8);
      api.sound('deny');
      respawn(car, T.cpS[car.nextCp] - 8);
    }
    function crossedAhead(car) {
      if (car.nextCp === 0) return false;              // never credit the start/finish line this way
      var a = car.ts - T.cpS[car.nextCp];
      if (a > L / 2) a -= L; else if (a <= -L / 2) a += L;
      return a > 0;
    }

    // ---------------------------------------------------------------- main substep
    function substep(h) {
      var i, car;
      trackCounter++;
      for (i = 0; i < cars.length; i++) {
        car = cars[i];
        car.px = car.x; car.py = car.y; car.pa = car.a; car.prevTs = car.ts;
      }
      // ---- player input & physics
      var p = player;
      var tgtSteer = steerInput, tgtHb = hbInput;
      if (autoPilot || p.finished) { tgtSteer = autoSteer(p); tgtHb = false; }
      var hiSpeed = clamp(p.speed / 38, 0, 1);
      var rise = lerp(8.0, 5.0, hiSpeed), fall = 9;
      if (tgtSteer !== 0 && (p.steer === 0 || sgn(tgtSteer) === sgn(p.steer)) && Math.abs(tgtSteer) > Math.abs(p.steer)) {
        p.steer = Math.min(Math.abs(tgtSteer), Math.abs(p.steer) + rise * h) * sgn(tgtSteer);
      } else {
        var diff = tgtSteer - p.steer;
        var stp = fall * h;
        p.steer += clamp(diff, -stp, stp);
      }
      p.hbF = clamp(p.hbF + (tgtHb ? 7 : -5) * h, 0, 1);
      p.hb = tgtHb;
      p.autoBrake = 0;
      if (phase === 'countdown') { p.throttle = 0; }
      else if (p.finished) p.throttle = 0.45;
      else {
        p.throttle = 1;
        if (liftProfile && p.off < 0.5) {
          // smart auto-throttle: lift (and brake a little on easy) before corners that are too fast
          var lim = liftProfile[p.ti] * D.lift;
          var lim2 = liftProfile[(p.ti + 6) % N] * D.lift;
          if (lim2 < lim) lim = lim2;
          if (p.speed > lim) {
            p.throttle = clamp(1 - (p.speed - lim) / 2.5, 0, 1);
            if (p.speed > lim + 1.5) p.autoBrake = D.liftBrake;
          }
        }
      }
      if (phase === 'countdown') {
        p.vx = 0; p.vy = 0; p.w = 0;
      } else {
        stepPlayer(p, h);
      }
      // ---- bots
      for (i = 1; i < cars.length; i++) stepBot(cars[i], h);
      if (cars.length > 2) botSeparation();
      // ---- collisions
      if (phase !== 'countdown' && !sandbox) collidePlayer(p);
      // ---- tracking & laps
      for (i = 0; i < cars.length; i++) {
        car = cars[i];
        var prevS = car.prevTs;
        var jumped = car.isPlayer ? trackCar(car, false) : false;
        if (!car.isPlayer) { car.ts = car.s; car.td = car.d; car.ti = Math.floor(car.s / T.ds) % N; }
        if (phase !== 'countdown') updateProgress(car, prevS, jumped);
        else updateProgress(car, prevS, true);
        if (car.hitCd > 0) car.hitCd -= h;
        if (car.ghostT > 0) car.ghostT -= h;
      }
      // off-road factor for the player
      var ad = Math.abs(p.td);
      p.off = sandbox ? 0 : clamp((ad - (T.hw + 0.55)) / 1.1, 0, 1);
      // ---- effects
      for (i = 0; i < cars.length; i++) carEffects(cars[i], h);
      // ---- drift, stuck, wrong-way
      if (phase === 'race' && !p.finished) {
        driftStep(h);
        if (p.speed < 1.5 && p.hbF < 0.5) p.stuckT += h; else p.stuckT = Math.max(0, p.stuckT - h * 2);
        if (p.stuckT > 2 && !sandbox) respawn(p);
        else if (!sandbox) checkSkipped(p, h);
        var ti = p.ti;
        var along = p.vx * T.tx[ti] + p.vy * T.ty[ti];
        if (along < -2.5 && p.speed > 3) p.wrongT += h; else p.wrongT = Math.max(0, p.wrongT - h * 2);
      }
      raceTime += phase === 'countdown' ? 0 : h;
      // per substep (not per frame), so 60 Hz and 120 Hz screens give exactly the same run
      rubberBand();
      if (mode === 'drift' && phase === 'race') {
        timeLeft -= h;
        if (timeLeft <= 1e-6) endDriftSession();
      }
    }
    function endDriftSession() {
      timeLeft = 0;
      bankDrift(false);
      phase = 'finished';
      overT = 0;
      player.finished = true;
      player.finishTime = raceTime;
      api.sound('finish');
      finalizeResult();
      flash('Время вышло', fmtInt(totalDrift) + ' ' + plural(totalDrift, 'очко', 'очка', 'очков'), UI.gold, 3);
    }

    function computePlaces() {
      if (cars.length === 1) { player.place = 1; return; }
      for (var i = 0; i < cars.length; i++) {
        var c = cars[i], pl = 1;
        for (var j = 0; j < cars.length; j++) {
          if (i === j) continue;
          var o = cars[j];
          if (o.finished && c.finished) { if (o.finishTime < c.finishTime) pl++; }
          else if (o.finished) pl++;
          else if (!c.finished && o.raceDist > c.raceDist) pl++;
        }
        c.place = pl;
      }
    }

    function rubberBand() {
      if (mode !== 'race' || sandbox) return;
      for (var i = 1; i < cars.length; i++) {
        var b = cars[i];
        // asymmetric: bots ease off harder when the player has fallen behind than they push when he leads
        var gap = player.raceDist - b.raceDist;
        b.rb = 1 + clamp(gap / 700, -D.rbBehind, D.rbAhead);
        if (player.finished) b.rb = 1;
      }
    }

    // ---------------------------------------------------------------- audio
    var au = null, noiseBuf = null;
    function startAudio() {
      var A = api.audio;
      if (!A || !A.ctx || !A.out || au) return;
      try {
        var ac = A.ctx, now = ac.currentTime;
        var eg = ac.createGain(); eg.gain.value = 0;
        var lp = ac.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 900; lp.Q.value = 0.8;
        var o1 = ac.createOscillator(); o1.type = 'sawtooth'; o1.frequency.value = 60;
        var o2 = ac.createOscillator(); o2.type = 'square'; o2.frequency.value = 30;
        var g2 = ac.createGain(); g2.gain.value = 0.45;
        o1.connect(lp); o2.connect(g2); g2.connect(lp); lp.connect(eg); eg.connect(A.out);
        if (!noiseBuf || noiseBuf.ctx !== ac) {
          var len = Math.floor(ac.sampleRate * 1.0);
          var nb = ac.createBuffer(1, len, ac.sampleRate), data = nb.getChannelData(0);
          for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
          noiseBuf = { ctx: ac, buf: nb };
        }
        var buf = noiseBuf.buf;
        var ns = ac.createBufferSource(); ns.buffer = buf; ns.loop = true;
        var bp = ac.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1500; bp.Q.value = 7;
        var sg = ac.createGain(); sg.gain.value = 0;
        ns.connect(bp); bp.connect(sg); sg.connect(A.out);
        var gl = ac.createBiquadFilter(); gl.type = 'lowpass'; gl.frequency.value = 380;
        var gg = ac.createGain(); gg.gain.value = 0;
        ns.connect(gl); gl.connect(gg); gg.connect(A.out);
        o1.start(now); o2.start(now); ns.start(now);
        au = { ac: ac, out: A.out, eg: eg, lp: lp, o1: o1, o2: o2, g2: g2, ns: ns, bp: bp, sg: sg, gl: gl, gg: gg };
      } catch (e) { au = null; }
    }
    function stopAudio() {
      if (!au) return;
      var a = au;
      au = null;
      try {
        var now = a.ac.currentTime;
        a.eg.gain.cancelScheduledValues(now); a.eg.gain.setValueAtTime(0, now);
        a.sg.gain.cancelScheduledValues(now); a.sg.gain.setValueAtTime(0, now);
        a.gg.gain.cancelScheduledValues(now); a.gg.gain.setValueAtTime(0, now);
        a.o1.stop(); a.o2.stop(); a.ns.stop();
      } catch (e) { /* ignore */ }
      try {
        a.o1.disconnect(); a.o2.disconnect(); a.g2.disconnect(); a.lp.disconnect(); a.eg.disconnect();
        a.ns.disconnect(); a.bp.disconnect(); a.sg.disconnect(); a.gl.disconnect(); a.gg.disconnect();
      } catch (e2) { /* ignore */ }
    }
    function updateAudio() {
      var A = api.audio;
      if (!A || over || paused) { if (au) stopAudio(); return; }
      if (au && au.out !== A.out) stopAudio();
      if (!au) startAudio();
      if (!au) return;
      try {
        var p = player, now = au.ac.currentTime;
        var v = p.speed, M = p.m;
        var gears = [0, 9, 17, 25, 33, 60];
        var g = 1;
        while (g < gears.length - 1 && v > gears[g]) g++;
        var lo = gears[g - 1], hi = gears[g];
        var rpm = clamp((v - lo) / (hi - lo), 0, 1);
        if (phase === 'countdown') rpm = 0.25 + 0.2 * Math.sin(clock * 9) * 0.5 + 0.2;
        var base = (46 + rpm * 70 + g * 7) * M.pitch;
        au.o1.frequency.setTargetAtTime(base, now, 0.04);
        au.o2.frequency.setTargetAtTime(base * 0.5, now, 0.04);
        au.lp.frequency.setTargetAtTime(500 + rpm * 900 + p.throttle * 300, now, 0.05);
        var ev = over ? 0 : (0.035 + 0.035 * p.throttle + 0.02 * rpm);
        au.eg.gain.setTargetAtTime(ev, now, 0.06);
        var aslip = Math.abs(p.slip);
        var sq = 0;
        if (p.speed > 5 && p.off < 0.5) sq = clamp((aslip - 8 * DEG) / (30 * DEG), 0, 1) * clamp(p.speed / 20, 0, 1);
        sq = Math.max(sq, p.hbF * clamp(p.speed / 15, 0, 1));
        if (over) sq = 0;
        au.sg.gain.setTargetAtTime(sq * 0.085, now, 0.05);
        au.bp.frequency.setTargetAtTime(1250 + aslip * 500 + Math.sin(clock * 23) * 60, now, 0.05);
        var gv = over ? 0 : p.off * clamp(p.speed / 15, 0, 1) * 0.12;
        au.gg.gain.setTargetAtTime(gv, now, 0.08);
      } catch (e) { /* ignore */ }
    }

    // ---------------------------------------------------------------- update (per frame)
    function update(dt) {
      if (paused || !(dt > 0)) return;
      if (dt > 0.05) dt = 0.05;
      clock += dt;
      readInput();
      if (phase === 'countdown') {
        cdT -= dt;
        var cnt = Math.ceil(cdT);
        if (cnt < lastCount && cnt >= 1 && cnt <= 3) { api.sound('countdown'); }
        lastCount = cnt;
        if (cdT <= 0) {
          phase = 'race';
          goFlash = 1;
          api.sound('go');
          hintT = 3.2;
        }
      } else if (hintT > 0) hintT -= dt;
      if (goFlash > -2) goFlash -= dt;
      acc += dt;
      var guard = 0;
      while (acc >= STEP && guard < 8) {
        substep(STEP);
        acc -= STEP;
        guard++;
      }
      if (acc > STEP) acc = STEP;
      computePlaces();
      stepParticles(dt);
      if (phase === 'finished') {
        overT += dt;
        if (overT > 1.8 && !resultSent) sendResult();
      }
      // messages & popups
      if (msg.t < msg.dur) msg.t += dt;
      for (var i = popups.length - 1; i >= 0; i--) {
        popups[i].t += dt;
        if (popups[i].t > 1.4) popups.splice(i, 1);
      }
      wrongShow = player.wrongT > 0.8 ? Math.min(1, wrongShow + dt * 4) : Math.max(0, wrongShow - dt * 4);
      if (lastLapFlash > 0) lastLapFlash -= dt;
      shake = Math.max(0, shake - dt * 2.5);
      updateCamera(dt);
      updateAudio();
    }

    // The result (and the saved record) is settled the moment the run ends, so leaving or restarting
    // during the finish celebration never loses it; sendResult() only presents it afterwards.
    var lastResult = null;
    var STAR_WORDS = ['', 'одной звезды', 'двух звёзд', 'трёх звёзд'];
    function finalizeResult() {
      if (lastResult) return lastResult;
      computePlaces();
      var res, key = recKey(O, diffKey), prev = api.store.get(key, null), record = false, stars = 0, sub = '';
      var i;
      if (mode === 'race') {
        var place = player.place;
        stars = place === 1 ? 3 : place === 2 ? 2 : place === 3 ? 1 : 0;
        var tot = player.finishTime;
        // best race = best place first, then the faster time; only a podium counts as a record
        var pb = raceBest(prev), pbP = pb && pb.p ? pb.p : 5;
        if (!pb || place < pbP || (place === pbP && tot < pb.t)) {
          api.store.set(key, { p: place, t: tot });
          record = place <= 3;
        }
        if (place > 1) {
          var win = Infinity;
          for (i = 1; i < cars.length; i++) if (cars[i].finished && cars[i].finishTime < win) win = cars[i].finishTime;
          if (isFinite(win)) sub = 'Отставание от победителя: +' + (tot - win).toFixed(2) + ' с';
        } else {
          // lead over the runner-up, estimated from the distance it still has to cover
          var rest = Infinity;
          for (i = 1; i < cars.length; i++) {
            var b = cars[i];
            if (!b.finished && b.v > 3) rest = Math.min(rest, Math.max(0, LAPS * L - b.raceDist) / b.v);
          }
          if (isFinite(rest) && rest > 0.05) sub = 'Отрыв от 2-го места: ~' + rest.toFixed(1) + ' с';
        }
        res = {
          win: place === 1, title: place + '-е место', subtitle: sub,
          stats: [['Общее время', fmtTime(tot)], ['Лучший круг', fmtTime(player.bestLap)], ['Дрифт-очки', fmtInt(totalDrift)]],
          record: record, stars: stars
        };
      } else if (mode === 'time') {
        var bl = player.bestLap, ref = idealLap * D.starMul, lims = [1.32, 1.15, 1.06];
        var r = bl / ref;
        stars = r <= lims[2] ? 3 : r <= lims[1] ? 2 : r <= lims[0] ? 1 : 0;
        if (typeof prev !== 'number' || bl < prev) { api.store.set(key, bl); record = true; }
        sub = stars < 3 ? 'До ' + STAR_WORDS[stars + 1] + ': круг за ' + fmtTime(Math.floor(ref * lims[stars] * 100) / 100) : 'Все три звезды!';
        var st = [['Лучший круг', fmtTime(bl)], ['Общее время', fmtTime(player.finishTime)]];
        for (i = 0; i < player.lapTimes.length; i++) st.push(['Круг ' + (i + 1), fmtTime(player.lapTimes[i])]);
        res = { win: stars >= 1, title: 'Финиш', subtitle: sub, stats: st, record: record, stars: stars };
      } else {
        var sc = Math.round(totalDrift);
        var th = driftThresholds();
        stars = sc >= th[2] ? 3 : sc >= th[1] ? 2 : sc >= th[0] ? 1 : 0;
        if (sc > 0 && (typeof prev !== 'number' || sc > prev)) { api.store.set(key, sc); record = true; }
        sub = stars < 3 ? 'До ' + STAR_WORDS[stars + 1] + ': ' + fmtInt(th[stars]) + ' ' + plural(th[stars], 'очко', 'очка', 'очков') : 'Все три звезды!';
        res = {
          win: stars >= 1, title: 'Время вышло', subtitle: sub,
          stats: [['Очки', fmtInt(sc)], ['Лучший занос', fmtInt(bestDrift)], ['Макс. комбо', '×' + maxCombo]],
          record: record, stars: stars
        };
      }
      lastResult = res;
      return res;
    }
    function sendResult() {
      resultSent = true;
      over = true;
      stopAudio();
      var res = finalizeResult();
      if (res.win) api.sound('win'); else if (mode === 'race' && player.place === cars.length) api.sound('lose');
      api.gameOver(res);
    }
    // Star targets for «Дрифт-зачёт», calibrated per track and difficulty from measured runs of touch-like
    // drivers (1 star for roughly two players in three who try to drift, 3 stars for the best ~10 %),
    // then scaled by how easily each car slides (the grippy hatch scores about half of the coupe).
    var DRIFT_STARS = {
      ring: { easy: [2000, 7000, 16000], normal: [3000, 10000, 22000], hard: [3000, 10000, 20000] },
      port: { easy: [6000, 11500, 18000], normal: [8000, 16000, 24000], hard: [7000, 16000, 25000] },
      serpent: { easy: [6000, 10500, 15000], normal: [10000, 15500, 27000], hard: [9000, 15000, 24000] }
    };
    var DRIFT_CAR_K = { hatch: 0.65, coupe: 1.2, muscle: 1.1 };
    function driftThresholds() {
      var row = (DRIFT_STARS[trackKey] || DRIFT_STARS.port)[diffKey] || DRIFT_STARS.port.normal;
      var k = DRIFT_CAR_K[carKey] || 1;
      return [0, 1, 2].map(function (q) { return Math.max(500, Math.round(row[q] * k / 500) * 500); });
    }

    // ---------------------------------------------------------------- camera
    function baseZoom() { return Math.sqrt(vw * vh) / 64; }
    function updateCamera(dt) {
      var al = acc / STEP;
      var p = player;
      var x = lerp(p.px, p.x, al), y = lerp(p.py, p.y, al);
      var slipC = Math.abs(p.slip) < 1.6 ? p.slip : 0;
      var tA, lx, ly, zt;
      if (reduced) {
        // reduced motion: follow the direction of travel (it turns far more calmly than the drifting
        // body), a fixed look-ahead and a fixed zoom, so the view does not sway or breathe
        tA = p.speed > 3 ? Math.atan2(p.vy, p.vx) + 0.25 * clamp(p.slip, -1.2, 1.2) : p.a;
        lx = Math.cos(tA) * 9; ly = Math.sin(tA) * 9;
        zt = baseZoom() * 0.85;
      } else {
        tA = p.a - slipC * 0.42;
        // look ahead: a fixed bit along the view direction plus more with speed along the travel direction
        // (landscape is short, so it looks further ahead and zooms out a little more at speed)
        var land = vw > vh, lk = land ? 0.4 : 0.3, lcap = land ? 20 : 16;
        lx = Math.cos(tA) * 5 + p.vx * lk; ly = Math.sin(tA) * 5 + p.vy * lk;
        var ll = Math.sqrt(lx * lx + ly * ly);
        if (ll > lcap) { lx *= lcap / ll; ly *= lcap / ll; }
        zt = baseZoom() * (1 - (land ? 0.35 : 0.25) * clamp(p.speed / 40, 0, 1));
      }
      if (!cam.init) {
        cam.init = true; cam.lx = lx; cam.ly = ly; cam.a = tA; cam.z = zt;
      } else {
        cam.lx += (lx - cam.lx) * expK(reduced ? 1.5 : 2.6, dt);
        cam.ly += (ly - cam.ly) * expK(reduced ? 1.5 : 2.6, dt);
        cam.a += wrapA(tA - cam.a) * expK(reduced ? 3.2 : 4.4, dt);
        cam.z += (zt - cam.z) * expK(1.6, dt);
      }
      cam.x = x + cam.lx; cam.y = y + cam.ly;
    }

    // ---------------------------------------------------------------- render resources
    var gfx = null;
    function ensureGfx() {
      if (gfx) return gfx;
      gfx = { ok: typeof Path2D === 'function', canvases: [] };
      var i, k, ch;
      if (gfx.ok) {
        for (k = 0; k < T.chunks.length; k++) {
          ch = T.chunks[k];
          var pc = new Path2D(), pl = new Path2D(), pr = new Path2D(), prl = new Path2D();
          var eo = T.hw - 0.4;
          for (i = ch.a; i <= ch.b; i++) {
            var j = i % N;
            var x = T.px[j], y = T.py[j];
            if (i === ch.a) {
              pc.moveTo(x, y);
              pl.moveTo(x - T.nx[j] * eo, y - T.ny[j] * eo);
              pr.moveTo(x + T.nx[j] * eo, y + T.ny[j] * eo);
              prl.moveTo(T.lx[j], T.ly[j]);
            } else {
              pc.lineTo(x, y);
              pl.lineTo(x - T.nx[j] * eo, y - T.ny[j] * eo);
              pr.lineTo(x + T.nx[j] * eo, y + T.ny[j] * eo);
              prl.lineTo(T.lx[j], T.ly[j]);
            }
          }
          ch.pc = pc; ch.pl = pl; ch.pr = pr; ch.prl = prl;
        }
        for (k = 0; k < T.kerbs.length; k++) {
          var kb = T.kerbs[k], pk = new Path2D();
          for (i = 0; i < kb.pts.length; i += 2) {
            if (i === 0) pk.moveTo(kb.pts[i], kb.pts[i + 1]); else pk.lineTo(kb.pts[i], kb.pts[i + 1]);
          }
          kb.path = pk;
        }
        // start/finish checker + grid slots
        var chk = new Path2D(), chkW = new Path2D(), grid = new Path2D();
        var sx = T.px[0], sy = T.py[0], tx = T.tx[0], ty = T.ty[0], nx = T.nx[0], ny = T.ny[0];
        var cols = Math.max(6, Math.round(T.hw * 2 / 1.0)), cw = T.hw * 2 / cols;
        function quad(p, u0, v0, u1, v1) {
          p.moveTo(sx + tx * u0 + nx * v0, sy + ty * u0 + ny * v0);
          p.lineTo(sx + tx * u1 + nx * v0, sy + ty * u1 + ny * v0);
          p.lineTo(sx + tx * u1 + nx * v1, sy + ty * u1 + ny * v1);
          p.lineTo(sx + tx * u0 + nx * v1, sy + ty * u0 + ny * v1);
          p.closePath();
        }
        quad(chkW, -1.0, -T.hw, 1.0, T.hw);
        for (var r = 0; r < 2; r++) {
          for (var c = 0; c < cols; c++) {
            if ((r + c) % 2) quad(chk, -1.0 + r * 1.0, -T.hw + c * cw, r * 1.0, -T.hw + (c + 1) * cw);
          }
        }
        gfx.chk = chk; gfx.chkW = chkW;
        var GP = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
        for (var slot = 0; slot < 4; slot++) {
          centreAt(L - 8 - 7 * slot + 2.6, GP);
          var side = slot % 2 === 0 ? -1 : 1, dOff = side * Math.min(1.9, T.hw - 1.6);
          var gx = GP.x + GP.nx * dOff, gy = GP.y + GP.ny * dOff;
          var a1x = gx + GP.nx * 1.3, a1y = gy + GP.ny * 1.3, a2x = gx - GP.nx * 1.3, a2y = gy - GP.ny * 1.3;
          grid.moveTo(a1x - GP.tx * 1.4, a1y - GP.ty * 1.4);
          grid.lineTo(a1x, a1y);
          grid.lineTo(a2x, a2y);
          grid.lineTo(a2x - GP.tx * 1.4, a2y - GP.ty * 1.4);
        }
        gfx.grid = grid;
      }
      // textures (small tiles)
      if (typeof document !== 'undefined') {
        gfx.groundPat = null; gfx.roadPat = null;
        try {
          var cg = document.createElement('canvas');
          cg.width = 128; cg.height = 128;
          var g = cg.getContext('2d');
          var R = rng(7);
          for (i = 0; i < 1500; i++) {
            g.fillStyle = TH.speck[i % TH.speck.length];
            g.globalAlpha = 0.25 + R() * 0.4;
            var sz = 1 + Math.floor(R() * 2.5);
            g.fillRect(Math.floor(R() * 128), Math.floor(R() * 128), sz, sz);
          }
          gfx.canvases.push(cg);
          var cr = document.createElement('canvas');
          cr.width = 128; cr.height = 128;
          var g2 = cr.getContext('2d');
          for (i = 0; i < 900; i++) {
            g2.fillStyle = R() < 0.5 ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.16)';
            g2.fillRect(Math.floor(R() * 128), Math.floor(R() * 128), 1 + Math.floor(R() * 2), 1);
          }
          gfx.canvases.push(cr);
          gfx.groundTile = cg; gfx.roadTile = cr;
          gfx.pctx = null;
        } catch (e) { /* ignore */ }
      }
      // minimap path (normalised to unit box)
      if (gfx.ok) {
        var mp = new Path2D(), w = T.maxx - T.minx, hgt = T.maxy - T.miny, s = 1 / Math.max(w, hgt);
        gfx.mapS = s; gfx.mapW = w * s; gfx.mapH = hgt * s;
        for (i = 0; i <= N; i += 2) {
          var jj = i % N, mx = (T.px[jj] - T.minx) * s, my = (T.py[jj] - T.miny) * s;
          if (i === 0) mp.moveTo(mx, my); else mp.lineTo(mx, my);
        }
        mp.closePath();
        gfx.map = mp;
      }
      return gfx;
    }
    function patterns(ctx) {
      if (!gfx || !gfx.groundTile) return;
      if (gfx.pctx === ctx) return;
      gfx.pctx = ctx;
      try {
        gfx.groundPat = ctx.createPattern(gfx.groundTile, 'repeat');
        gfx.roadPat = ctx.createPattern(gfx.roadTile, 'repeat');
        gfx.roadPatOk = false;
        if (gfx.roadPat && typeof gfx.roadPat.setTransform === 'function' && typeof DOMMatrix === 'function') {
          gfx.roadPat.setTransform(new DOMMatrix([1 / 12, 0, 0, 1 / 12, 0, 0]));
          gfx.roadPatOk = true;
        }
      } catch (e) { gfx.roadPatOk = false; }
    }

    // ---------------------------------------------------------------- render
    var view = { minx: 0, miny: 0, maxx: 0, maxy: 0 };
    var markX = 0, markY = 0;
    var visChunks = [];
    function inView(o, m) {
      m = m || 0;
      return o.maxx >= view.minx - m && o.minx <= view.maxx + m && o.maxy >= view.miny - m && o.miny <= view.maxy + m;
    }
    function render(ctx) {
      if (!ctx) return;
      ensureGfx();
      if (!gfx.ok) { ctx.fillStyle = TH.ground; ctx.fillRect(0, 0, vw, vh); return; }
      patterns(ctx);
      var W = vw, Hh = vh;
      if (!cam.init) updateCamera(0);
      if (overview) {
        cam.x = (T.minx + T.maxx) / 2; cam.y = (T.miny + T.maxy) / 2; cam.a = -Math.PI / 2;
        cam.z = Math.min(vw / (T.maxx - T.minx + 90), vh / (T.maxy - T.miny + 90));
      }
      var z = cam.z;
      var ax = W / 2, ay = overview ? Hh / 2 : Hh * (W > Hh ? 0.47 : 0.5);
      var shx = 0, shy = 0;
      if (shake > 0 && !reduced) {
        shx = (Math.sin(clock * 91) + Math.sin(clock * 57)) * shake * 5;
        shy = (Math.cos(clock * 83) + Math.sin(clock * 41)) * shake * 5;
      }
      var rot = -cam.a - Math.PI / 2;
      // view AABB in world space
      var cr = Math.cos(-rot), sr = Math.sin(-rot);
      view.minx = Infinity; view.miny = Infinity; view.maxx = -Infinity; view.maxy = -Infinity;
      for (var q = 0; q < 4; q++) {
        var sx = ((q & 1) ? W : 0) - ax, sy = ((q & 2) ? Hh : 0) - ay;
        var wx = cam.x + (sx * cr - sy * sr) / z, wy = cam.y + (sx * sr + sy * cr) / z;
        if (wx < view.minx) view.minx = wx; if (wx > view.maxx) view.maxx = wx;
        if (wy < view.miny) view.miny = wy; if (wy > view.maxy) view.maxy = wy;
      }
      ctx.save();
      ctx.fillStyle = TH.ground;
      ctx.fillRect(0, 0, W, Hh);
      ctx.translate(ax + shx, ay + shy);
      ctx.rotate(rot);
      ctx.scale(z, z);
      ctx.translate(-cam.x, -cam.y);
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      // ground texture
      if (gfx.groundPat) {
        ctx.save();
        ctx.scale(1 / 10, 1 / 10);
        ctx.fillStyle = gfx.groundPat;
        ctx.fillRect(view.minx * 10, view.miny * 10, (view.maxx - view.minx) * 10, (view.maxy - view.miny) * 10);
        ctx.restore();
      }
      if (trackKey === 'port') drawSea(ctx);

      visChunks.length = 0;
      var ci;
      for (ci = 0; ci < T.chunks.length; ci++) if (inView(T.chunks[ci])) visChunks.push(T.chunks[ci]);
      var ch, k;
      // run-off
      ctx.lineWidth = T.wallDist * 2 + 0.8;
      ctx.strokeStyle = TH.verge;
      for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].pc);
      ctx.strokeStyle = TH.sand;
      for (k = 0; k < visChunks.length; k++) if (visChunks[k].sand) ctx.stroke(visChunks[k].pc);
      // shoulder + asphalt
      ctx.lineWidth = T.hw * 2 + 0.5;
      ctx.strokeStyle = mixCache('sh', TH.asphalt);
      for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].pc);
      ctx.lineWidth = T.hw * 2;
      ctx.strokeStyle = TH.asphalt;
      for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].pc);
      ctx.lineWidth = 3.6;
      ctx.strokeStyle = TH.rubberSoft;
      for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].prl);
      ctx.lineWidth = 1.8;
      ctx.strokeStyle = TH.rubber;
      for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].prl);
      if (gfx.roadPatOk) {
        ctx.lineCap = 'butt';
        ctx.lineWidth = T.hw * 2;
        ctx.strokeStyle = gfx.roadPat;
        for (k = 0; k < visChunks.length; k++) ctx.stroke(visChunks[k].pc);
        ctx.lineCap = 'round';
      }
      // painted edge lines
      ctx.lineWidth = 0.3;
      ctx.strokeStyle = TH.edge;
      for (k = 0; k < visChunks.length; k++) { ctx.stroke(visChunks[k].pl); ctx.stroke(visChunks[k].pr); }
      // kerbs
      ctx.lineCap = 'butt';
      for (k = 0; k < T.kerbs.length; k++) {
        var kb = T.kerbs[k];
        if (!inView(kb)) continue;
        ctx.lineWidth = 1.1;
        ctx.strokeStyle = '#F1ECE0';
        ctx.stroke(kb.path);
        ctx.setLineDash(KERB_DASH);
        ctx.strokeStyle = '#D63A2F';
        ctx.stroke(kb.path);
        ctx.setLineDash(NO_DASH);
      }
      ctx.lineCap = 'round';
      // start line + grid
      ctx.fillStyle = '#F1ECE0';
      ctx.fill(gfx.chkW);
      ctx.fillStyle = '#1B1B1F';
      ctx.fill(gfx.chk);
      ctx.strokeStyle = 'rgba(241,236,224,0.85)';
      ctx.lineWidth = 0.25;
      ctx.stroke(gfx.grid);

      drawSkids(ctx);
      drawScenery(ctx, 0);
      drawStacks(ctx);
      drawCars(ctx);
      drawSmoke(ctx);
      drawSparks(ctx);
      drawScenery(ctx, 1);
      drawGantry(ctx);
      ctx.restore();
      // where the player's car is on screen (for the "you" marker)
      var pal = acc / STEP, pdx = lerp(player.px, player.x, pal) - cam.x, pdy = lerp(player.py, player.y, pal) - cam.y;
      var cr2 = Math.cos(rot), sr2 = Math.sin(rot);
      markX = ax + shx + (pdx * cr2 - pdy * sr2) * z;
      markY = ay + shy + (pdx * sr2 + pdy * cr2) * z;
      drawHUD(ctx);
    }
    var mixMemo = {};
    function mixCache(key, col) {
      var k = key + col;
      if (!mixMemo[k]) mixMemo[k] = mixHex(col, '#D8D2C4', 0.25);
      return mixMemo[k];
    }

    function drawSea(ctx) {
      var y0 = T.seaY;
      if (view.maxy < y0) return;
      ctx.fillStyle = '#5B6167';
      ctx.fillRect(view.minx - 5, y0 - 2.2, view.maxx - view.minx + 10, 2.2);
      ctx.fillStyle = TH.sea;
      ctx.fillRect(view.minx - 5, y0, view.maxx - view.minx + 10, Math.max(0, view.maxy - y0) + 5);
      ctx.strokeStyle = TH.seaHi;
      ctx.lineWidth = 0.35;
      ctx.beginPath();
      var ph = clock * 0.6;
      for (var r = 0; r < 14; r++) {
        var yy = y0 + 5 + r * 7;
        if (yy > view.maxy + 2) break;
        var xs = Math.floor((view.minx - 20) / 30) * 30;
        for (var x = xs; x < view.maxx + 20; x += 30) {
          var off = ((r * 13) % 30) + Math.sin(ph + r) * 3;
          ctx.moveTo(x + off, yy);
          ctx.lineTo(x + off + 8, yy);
        }
      }
      ctx.stroke();
    }

    function drawSkids(ctx) {
      if (!skidCount) return;
      ctx.lineCap = 'round';
      ctx.lineWidth = 0.26;
      var buckets = 5, per = SKID_CAP / buckets;
      for (var b = buckets - 1; b >= 0; b--) {
        ctx.beginPath();
        var any = false;
        for (var a = b * per; a < (b + 1) * per && a < skidCount; a++) {
          var idx = (skidHead - 1 - a + SKID_CAP * 2) % SKID_CAP, o = idx * 4;
          var x0 = skid[o], y0 = skid[o + 1];
          if (x0 < view.minx - 2 || x0 > view.maxx + 2 || y0 < view.miny - 2 || y0 > view.maxy + 2) continue;
          ctx.moveTo(x0, y0);
          ctx.lineTo(skid[o + 2], skid[o + 3]);
          any = true;
        }
        if (any) {
          ctx.strokeStyle = 'rgba(22,18,18,' + (0.5 - b * 0.085).toFixed(3) + ')';
          ctx.stroke();
        }
      }
    }

    function drawStacks(ctx) {
      var gs = T.stackGroups, k, i, x, y;
      // shadow
      ctx.fillStyle = 'rgba(0,0,0,0.25)';
      ctx.beginPath();
      for (k = 0; k < gs.length; k++) {
        if (!inView(gs[k])) continue;
        for (i = gs[k].a; i < gs[k].b; i++) {
          x = T.stackX[i] + 0.25; y = T.stackY[i] + 0.35;
          ctx.moveTo(x + 0.62, y); ctx.arc(x, y, 0.62, 0, TAU);
        }
      }
      ctx.fill();
      for (var pass = 0; pass < 2; pass++) {
        ctx.fillStyle = pass ? '#E9E4D8' : '#1F2023';
        ctx.beginPath();
        for (k = 0; k < gs.length; k++) {
          if (!inView(gs[k])) continue;
          for (i = gs[k].a; i < gs[k].b; i++) {
            if ((i % 5 === 0) !== (pass === 1)) continue;
            x = T.stackX[i]; y = T.stackY[i];
            ctx.moveTo(x + 0.6, y); ctx.arc(x, y, 0.6, 0, TAU);
          }
        }
        ctx.fill();
        ctx.strokeStyle = pass ? '#B5AEA0' : '#3D3F45';
        ctx.lineWidth = 0.13;
        ctx.beginPath();
        for (k = 0; k < gs.length; k++) {
          if (!inView(gs[k])) continue;
          for (i = gs[k].a; i < gs[k].b; i++) {
            if ((i % 5 === 0) !== (pass === 1)) continue;
            x = T.stackX[i]; y = T.stackY[i];
            ctx.moveTo(x + 0.32, y); ctx.arc(x, y, 0.32, 0, TAU);
          }
        }
        ctx.stroke();
      }
    }

    function drawScenery(ctx, layer) {
      var sc = T.scenery, i, it;
      if (layer === 0) {
        // ground-level objects and all shadows
        for (i = 0; i < sc.length; i++) {
          it = sc[i];
          if (!inView(it, 8)) continue;
          if (it.type === 'paint') {
            ctx.strokeStyle = 'rgba(231,186,70,0.55)';
            ctx.lineWidth = 0.3;
            ctx.beginPath(); ctx.moveTo(it.x0, it.y0); ctx.lineTo(it.x1, it.y1); ctx.stroke();
          } else if (it.type === 'tree' || it.type === 'pine') {
            ctx.fillStyle = 'rgba(0,0,0,0.26)';
            ctx.beginPath(); ctx.arc(it.x + it.r * 0.45, it.y + it.r * 0.6, it.r, 0, TAU); ctx.fill();
          } else if (it.type === 'crane') {
            ctx.fillStyle = 'rgba(0,0,0,0.22)';
            ctx.fillRect(it.x - it.span / 2 + 5, it.y - 1.2 + 7, it.span, 2.4);
            ctx.fillRect(it.x - it.span / 2 + 5, it.y + it.depth - 1.2 + 7, it.span, 2.4);
          }
        }
        boxList.length = 0;
        for (i = 0; i < sc.length; i++) {
          it = sc[i];
          if (it.type === 'box') { if (inView(it, 4)) boxList.push(it); }
        }
        if (boxList.length) drawContainers(ctx, boxList);
        for (i = 0; i < sc.length; i++) {
          it = sc[i];
          if (it.type === 'box' || !inView(it, 4)) continue;
          if (it.type === 'rock') drawRock(ctx, it);
          else if (it.type === 'stand') drawStand(ctx, it);
          else if (it.type === 'cone') {
            ctx.fillStyle = 'rgba(0,0,0,0.25)';
            ctx.beginPath(); ctx.arc(it.x + 0.15, it.y + 0.2, 0.38, 0, TAU); ctx.fill();
            ctx.fillStyle = '#F07A2A';
            ctx.beginPath(); ctx.arc(it.x, it.y, 0.36, 0, TAU); ctx.fill();
            ctx.fillStyle = '#F4EEDF';
            ctx.beginPath(); ctx.arc(it.x, it.y, 0.16, 0, TAU); ctx.fill();
          } else if (it.type === 'bollard') {
            ctx.fillStyle = '#2B2F35';
            ctx.beginPath(); ctx.arc(it.x, it.y, 0.45, 0, TAU); ctx.fill();
          }
        }
      } else {
        for (i = 0; i < sc.length; i++) {
          it = sc[i];
          if (!inView(it, 4)) continue;
          if (it.type === 'tree') drawTree(ctx, it);
          else if (it.type === 'pine') drawPine(ctx, it);
          else if (it.type === 'crane') drawCrane(ctx, it);
        }
      }
    }
    function drawTree(ctx, it) {
      var cA = TH.treeA;
      ctx.fillStyle = cA[it.c % cA.length];
      ctx.beginPath(); ctx.arc(it.x, it.y, it.r, 0, TAU); ctx.fill();
      ctx.fillStyle = cA[(it.c + 1) % cA.length];
      ctx.beginPath(); ctx.arc(it.x - it.r * 0.2, it.y - it.r * 0.22, it.r * 0.68, 0, TAU); ctx.fill();
      ctx.fillStyle = TH.treeHi;
      ctx.beginPath(); ctx.arc(it.x - it.r * 0.35, it.y - it.r * 0.38, it.r * 0.36, 0, TAU); ctx.fill();
    }
    function drawPine(ctx, it) {
      var cA = TH.treeA, r = it.r;
      ctx.fillStyle = cA[it.c % cA.length];
      ctx.beginPath();
      for (var k = 0; k < 16; k++) {
        var a = it.rot + k / 16 * TAU, rr = k % 2 ? r * 0.72 : r;
        var x = it.x + Math.cos(a) * rr, y = it.y + Math.sin(a) * rr;
        if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = 'rgba(255,255,230,0.08)';
      ctx.beginPath(); ctx.arc(it.x - r * 0.2, it.y - r * 0.25, r * 0.45, 0, TAU); ctx.fill();
      ctx.fillStyle = 'rgba(0,0,0,0.18)';
      ctx.beginPath(); ctx.arc(it.x, it.y, r * 0.16, 0, TAU); ctx.fill();
    }
    function drawRock(ctx, it) {
      var p = it.pts;
      ctx.fillStyle = 'rgba(0,0,0,0.22)';
      ctx.beginPath();
      for (var k = 0; k < p.length; k += 2) {
        if (k === 0) ctx.moveTo(it.x + p[k] + 0.5, it.y + p[k + 1] + 0.7); else ctx.lineTo(it.x + p[k] + 0.5, it.y + p[k + 1] + 0.7);
      }
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = TH.rockDark;
      ctx.beginPath();
      for (k = 0; k < p.length; k += 2) {
        if (k === 0) ctx.moveTo(it.x + p[k], it.y + p[k + 1]); else ctx.lineTo(it.x + p[k], it.y + p[k + 1]);
      }
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = TH.rock;
      ctx.beginPath();
      for (k = 0; k < p.length; k += 2) {
        var x = it.x + p[k] * 0.78 - it.r * 0.12, y = it.y + p[k + 1] * 0.78 - it.r * 0.14;
        if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath(); ctx.fill();
    }
    // All visible containers in a handful of batched paths (Port has hundreds of them on screen).
    var boxList = [];
    function drawContainers(ctx, list) {
      var i, it, hx, hy, c, x, n = list.length;
      ctx.fillStyle = 'rgba(0,0,0,0.25)';
      ctx.beginPath();
      for (i = 0; i < n; i++) { it = list[i]; ctx.rect(it.x - it.w / 2 + 0.5 * it.lv, it.y - it.h / 2 + 0.7 * it.lv, it.w, it.h); }
      ctx.fill();
      for (c = 0; c < CONTAINER_COLS.length; c++) {
        var any = false;
        ctx.beginPath();
        for (i = 0; i < n; i++) {
          it = list[i];
          if (it.ci !== c) continue;
          ctx.rect(it.x - it.w / 2, it.y - it.h / 2, it.w, it.h);
          any = true;
        }
        if (any) { ctx.fillStyle = CONTAINER_COLS[c]; ctx.fill(); }
      }
      // stacked (taller) containers catch more light
      for (var hi = 0; hi < 2; hi++) {
        ctx.beginPath();
        for (i = 0; i < n; i++) {
          it = list[i];
          if ((it.lv > 1) !== (hi === 1)) continue;
          ctx.rect(it.x - it.w / 2, it.y - it.h / 2, it.w, it.h);
        }
        ctx.fillStyle = hi ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.06)';
        ctx.fill();
      }
      ctx.strokeStyle = 'rgba(0,0,0,0.22)';
      ctx.lineWidth = 0.12;
      ctx.beginPath();
      for (i = 0; i < n; i++) {
        it = list[i]; hx = it.w / 2; hy = it.h / 2;
        for (x = it.x - hx + 0.6; x < it.x + hx - 0.3; x += 0.6) { ctx.moveTo(x, it.y - hy + 0.12); ctx.lineTo(x, it.y + hy - 0.12); }
      }
      ctx.stroke();
      ctx.strokeStyle = 'rgba(0,0,0,0.4)';
      ctx.lineWidth = 0.16;
      ctx.beginPath();
      for (i = 0; i < n; i++) { it = list[i]; ctx.rect(it.x - it.w / 2, it.y - it.h / 2, it.w, it.h); }
      ctx.stroke();
    }
    function drawCrane(ctx, it) {
      var x0 = it.x - it.span / 2, x1 = it.x + it.span / 2, y0 = it.y, y1 = it.y + it.depth;
      ctx.fillStyle = '#D9A92C';
      ctx.fillRect(x0 - 1.2, y0 - 1.2, it.span + 2.4, 2.4);
      ctx.fillRect(x0 - 1.2, y1 - 1.2, it.span + 2.4, 2.4);
      ctx.fillStyle = '#B98C1F';
      ctx.fillRect(x0 - 1.6, y0 - 1.6, 3.2, it.depth + 3.2);
      ctx.fillRect(x1 - 1.6, y0 - 1.6, 3.2, it.depth + 3.2);
      ctx.fillStyle = '#2B2F35';
      ctx.fillRect(it.x - 2.2, y0 - 2, 4.4, it.depth + 4);
      ctx.strokeStyle = 'rgba(0,0,0,0.35)';
      ctx.lineWidth = 0.15;
      ctx.beginPath();
      for (var x = x0; x < x1; x += 2) { ctx.moveTo(x, y0 - 1.1); ctx.lineTo(x + 1, y0 + 1.1); ctx.moveTo(x, y1 - 1.1); ctx.lineTo(x + 1, y1 + 1.1); }
      ctx.stroke();
    }
    var CROWD_COLS = ['#E5412D', '#F2C230', '#F4EEDF', '#2F63D0', '#2FA36B', '#FF5A36', '#9BA7BD'];
    function standCrowd(it) {
      // pre-computed once: dot positions grouped by shirt colour (local frame, front = +y * face)
      var hl = it.len / 2, hd = it.dep / 2, rows = 6, groups = [], c;
      for (c = 0; c < CROWD_COLS.length; c++) groups.push([]);
      var seatDepth = it.dep * 0.62, y0 = -hd, k = 0;
      for (var r = 0; r < rows; r++) {
        var yy = (y0 + 0.9 + r * (seatDepth - 0.9) / (rows - 1)) * -it.face;
        for (var x = -hl + 1.0; x < hl - 0.8; x += 0.85) {
          k++;
          if (hash1(k * 3.7 + it.seed) < 0.28) continue;
          c = Math.floor(hash1(k * 1.9 + 7) * CROWD_COLS.length);
          groups[c].push(x + (hash1(k * 5.1) - 0.5) * 0.3, yy + (hash1(k * 6.3) - 0.5) * 0.25);
        }
      }
      it.crowd = groups;
      it.rows = rows;
    }
    function drawStand(ctx, it) {
      if (!it.crowd) standCrowd(it);
      ctx.save();
      ctx.translate(it.x, it.y);
      ctx.rotate(it.a);
      var hl = it.len / 2, hd = it.dep / 2, f = it.face, c, k;
      ctx.fillStyle = 'rgba(0,0,0,0.28)';
      ctx.fillRect(-hl + 1.5, -hd + 2, it.len, it.dep);
      ctx.fillStyle = '#465063';
      ctx.fillRect(-hl, -hd, it.len, it.dep);
      // seat rows (front part, facing the road)
      var seatDepth = it.dep * 0.62;
      for (var r = 0; r < it.rows; r++) {
        var yb = -hd + r * seatDepth / it.rows;
        ctx.fillStyle = r % 2 ? '#56617A' : '#4E5870';
        ctx.fillRect(-hl + 0.4, f > 0 ? hd - (r + 1) * seatDepth / it.rows : yb, it.len - 0.8, seatDepth / it.rows - 0.15);
      }
      for (c = 0; c < CROWD_COLS.length; c++) {
        var g = it.crowd[c];
        if (!g.length) continue;
        ctx.fillStyle = CROWD_COLS[c];
        ctx.beginPath();
        for (k = 0; k < g.length; k += 2) { ctx.moveTo(g[k] + 0.3, g[k + 1]); ctx.arc(g[k], g[k + 1], 0.3, 0, TAU); }
        ctx.fill();
      }
      // roof over the back part
      var roofD = it.dep - seatDepth + 0.6;
      var ry = f > 0 ? -hd - 0.4 : hd - roofD + 0.4;
      ctx.fillStyle = '#28303F';
      ctx.fillRect(-hl - 0.4, ry, it.len + 0.8, roofD);
      ctx.strokeStyle = 'rgba(255,255,255,0.07)';
      ctx.lineWidth = 0.18;
      ctx.beginPath();
      for (var x = -hl + 2; x < hl; x += 4) { ctx.moveTo(x, ry + 0.2); ctx.lineTo(x, ry + roofD - 0.2); }
      ctx.stroke();
      ctx.fillStyle = UI.flame;
      ctx.fillRect(-hl - 0.4, f > 0 ? ry + roofD - 0.35 : ry, it.len + 0.8, 0.35);
      ctx.restore();
    }
    function drawGantry(ctx) {
      var G = T.gantry;
      if (G.x < view.minx - 20 || G.x > view.maxx + 20 || G.y < view.miny - 20 || G.y > view.maxy + 20) return;
      var hx = G.nx * G.half, hy = G.ny * G.half;
      // shadow
      ctx.strokeStyle = 'rgba(0,0,0,0.22)';
      ctx.lineWidth = 1.2;
      ctx.lineCap = 'butt';
      ctx.beginPath(); ctx.moveTo(G.x - hx + 3, G.y - hy + 4); ctx.lineTo(G.x + hx + 3, G.y + hy + 4); ctx.stroke();
      ctx.strokeStyle = '#2B3344';
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(G.x - hx, G.y - hy); ctx.lineTo(G.x + hx, G.y + hy); ctx.stroke();
      ctx.strokeStyle = UI.flame;
      ctx.lineWidth = 0.35;
      ctx.beginPath(); ctx.moveTo(G.x - hx, G.y - hy); ctx.lineTo(G.x + hx, G.y + hy); ctx.stroke();
      ctx.fillStyle = '#1D2331';
      ctx.fillRect(G.x - hx - 0.7, G.y - hy - 0.7, 1.4, 1.4);
      ctx.fillRect(G.x + hx - 0.7, G.y + hy - 0.7, 1.4, 1.4);
      // start lights during the countdown
      if (phase === 'countdown' || goFlash > 0) {
        var lit = phase === 'countdown' ? Math.max(0, 3 - Math.ceil(cdT)) : 3;
        for (var q = 0; q < 3; q++) {
          var f = (q - 1) * 1.2;
          var lx = G.x + G.nx * f, ly = G.y + G.ny * f;
          ctx.fillStyle = phase !== 'countdown' ? '#5CC57A' : (q < lit ? '#FF3B30' : '#3A2226');
          ctx.beginPath(); ctx.arc(lx, ly, 0.45, 0, TAU); ctx.fill();
        }
      }
      ctx.lineCap = 'round';
    }

    function drawCars(ctx) {
      var al = acc / STEP, i, c, x, y, a;
      // shadows
      ctx.fillStyle = 'rgba(0,0,0,0.32)';
      for (i = 0; i < cars.length; i++) {
        c = cars[i];
        x = lerp(c.px, c.x, al); y = lerp(c.py, c.y, al); a = c.pa + wrapA(c.a - c.pa) * al;
        if (x < view.minx - 6 || x > view.maxx + 6 || y < view.miny - 6 || y > view.maxy + 6) continue;
        ctx.save();
        ctx.translate(x + 0.4, y + 0.55);
        ctx.rotate(a);
        drawCarShadow(ctx, c.st);
        ctx.restore();
      }
      for (i = cars.length - 1; i >= 0; i--) {
        c = cars[i];
        x = lerp(c.px, c.x, al); y = lerp(c.py, c.y, al); a = c.pa + wrapA(c.a - c.pa) * al;
        if (x < view.minx - 6 || x > view.maxx + 6 || y < view.miny - 6 || y > view.maxy + 6) continue;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(a);
        var blink = c.ghostT > 0 && Math.floor(c.ghostT * 10) % 2 === 0;
        if (c.ghostT > 0) ctx.globalAlpha = 0.6;
        drawCarLocal(ctx, c.st, c.steerAng, c.brakeT > 0 || c.hbF > 0.3, blink);
        ctx.globalAlpha = 1;
        ctx.restore();
      }
    }
    function drawSmoke(ctx) {
      var i, dustCol = TH.sand;
      for (var pass = 0; pass < 2; pass++) {
        ctx.fillStyle = pass ? dustCol : '#ECE9E4';
        for (i = 0; i < SMOKE_CAP; i++) {
          if (smk.life[i] <= 0 || smk.dust[i] !== pass) continue;
          var x = smk.x[i], y = smk.y[i], r = smk.r[i];
          if (x + r < view.minx || x - r > view.maxx || y + r < view.miny || y - r > view.maxy) continue;
          var f = smk.age[i] / smk.life[i];
          ctx.globalAlpha = (1 - f) * (1 - f) * (pass ? 0.45 : 0.4);
          ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
    }
    function drawSparks(ctx) {
      // contact flash: a short additive burst of light where the car hit
      if (hitFlash.t > 0) {
        var fr = hitFlash.t / 0.12, rr = 0.7 + 0.8 * hitFlash.s + (1 - fr) * 0.6;
        ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = 0.85 * fr;
        ctx.fillStyle = '#FFB547';
        ctx.beginPath(); ctx.arc(hitFlash.x, hitFlash.y, rr, 0, TAU); ctx.fill();
        ctx.fillStyle = '#FFF4D6';
        ctx.beginPath(); ctx.arc(hitFlash.x, hitFlash.y, rr * 0.5, 0, TAU); ctx.fill();
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = 'source-over';
      }
      ctx.lineCap = 'round';
      var any = false, i;
      // warm outer streaks, then bright cores on top
      for (var pass = 0; pass < 2; pass++) {
        ctx.lineWidth = pass ? 0.13 : 0.3;
        ctx.strokeStyle = pass ? '#FFF6DA' : '#FFB030';
        ctx.beginPath();
        any = false;
        for (i = 0; i < SPARK_CAP; i++) {
          if (spk.life[i] <= 0) continue;
          var x = spk.x[i], y = spk.y[i];
          if (x < view.minx - 3 || x > view.maxx + 3 || y < view.miny - 3 || y > view.maxy + 3) continue;
          var k = pass ? 0.04 : 0.07;
          ctx.moveTo(x, y);
          ctx.lineTo(x - spk.vx[i] * k, y - spk.vy[i] * k);
          any = true;
        }
        if (any) ctx.stroke();
      }
    }

    // ---------------------------------------------------------------- HUD
    function panel(ctx, x, y, w, h, r) {
      ctx.fillStyle = 'rgba(32,44,66,0.86)';
      ctx.beginPath(); rrect(ctx, x, y, w, h, r); ctx.fill();
      ctx.strokeStyle = 'rgba(52,67,95,0.9)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    var FONTS = api.fonts || {};
    var FONT_D = FONTS.display || '"Unbounded", "Arial Black", system-ui, sans-serif';
    var FONT_B = FONTS.body || '"Golos Text", system-ui, -apple-system, "Segoe UI", sans-serif';
    function fontD(px, wgt) { return (wgt || 800) + ' ' + Math.round(px) + 'px ' + FONT_D; }
    function fontB(px, wgt) { return (wgt || 600) + ' ' + Math.round(px) + 'px ' + FONT_B; }

    function drawHUD(ctx) {
      var W = vw, Hh = vh, sf = api.safe || { top: 0, right: 0, bottom: 0, left: 0 }, u = hudU;
      var rs = api.reserved || { x: W - 72, y: 0, w: 72, h: 72 };
      var pad = Math.round(12 * u);
      var x0 = sf.left + pad, y0 = sf.top + pad;
      ctx.save();
      ctx.textBaseline = 'alphabetic';
      ctx.lineJoin = 'round';
      // ---- left panel
      var pw = Math.round(176 * u), ph = Math.round(96 * u);
      panel(ctx, x0, y0, pw, ph, 14 * u);
      ctx.textAlign = 'left';
      if (mode === 'drift') {
        ctx.fillStyle = UI.muted; ctx.font = fontB(12 * u, 700);
        ctx.fillText('ОСТАЛОСЬ', x0 + 14 * u, y0 + 22 * u);
        var tl = Math.ceil(timeLeft);
        ctx.fillStyle = timeLeft < 10 && phase === 'race' ? UI.bad : UI.paper;
        ctx.font = fontD(30 * u);
        ctx.fillText(Math.floor(tl / 60) + ':' + (tl % 60 < 10 ? '0' : '') + (tl % 60), x0 + 14 * u, y0 + 56 * u);
        ctx.fillStyle = UI.muted; ctx.font = fontB(13 * u, 600);
        ctx.fillText('Лучший занос ' + fmtInt(bestDrift), x0 + 14 * u, y0 + 82 * u);
      } else {
        ctx.fillStyle = UI.muted; ctx.font = fontB(12 * u, 700);
        ctx.fillText('КРУГ', x0 + 14 * u, y0 + 22 * u);
        var lapShow = Math.min(LAPS, player.lap + 1);
        ctx.fillStyle = UI.paper; ctx.font = fontD(26 * u);
        ctx.fillText(lapShow + '/' + LAPS, x0 + 14 * u, y0 + 52 * u);
        var cur = player.started && !player.finished ? raceTime - player.lapStart : (player.finished ? player.lapTimes[player.lapTimes.length - 1] : 0);
        ctx.font = fontB(16 * u, 700);
        ctx.textAlign = 'right';
        ctx.fillText(fmtTime(cur), x0 + pw - 14 * u, y0 + 50 * u);
        ctx.textAlign = 'left';
        ctx.font = fontB(13 * u, 600);
        ctx.fillStyle = isFinite(player.bestLap) ? UI.gold : UI.muted;
        ctx.fillText('Лучший ' + (isFinite(player.bestLap) ? fmtTime(player.bestLap) : '–:––.––'), x0 + 14 * u, y0 + 80 * u);
      }
      // ---- score / position panel next to the reserved pause area
      var rightEdge = Math.min(W - sf.right - pad, rs.x - pad);
      if (mode === 'race') {
        var bw = Math.round(104 * u), bh = ph;
        var bx = rightEdge - bw;
        panel(ctx, bx, y0, bw, bh, 14 * u);
        ctx.textAlign = 'center';
        ctx.fillStyle = UI.muted; ctx.font = fontB(12 * u, 700);
        ctx.fillText('МЕСТО', bx + bw / 2, y0 + 22 * u);
        ctx.fillStyle = player.place === 1 ? UI.gold : UI.paper;
        ctx.font = fontD(34 * u);
        ctx.fillText(String(player.place), bx + bw / 2 - 10 * u, y0 + 66 * u);
        ctx.fillStyle = UI.muted; ctx.font = fontD(15 * u, 600);
        ctx.fillText('/' + cars.length, bx + bw / 2 + 20 * u, y0 + 66 * u);
      }
      // drift total (top centre)
      var cx = W / 2;
      var topCW = Math.round(170 * u);
      var leftLimit = x0 + pw + pad, rightLimit = (mode === 'race' ? rightEdge - 104 * u : rightEdge) - pad;
      if (rightLimit - leftLimit >= topCW) {
        cx = clamp(W / 2, leftLimit + topCW / 2, rightLimit - topCW / 2);
        panel(ctx, cx - topCW / 2, y0, topCW, Math.round(58 * u), 14 * u);
        ctx.textAlign = 'center';
        ctx.fillStyle = UI.muted; ctx.font = fontB(11 * u, 700);
        ctx.fillText(mode === 'drift' ? 'ОЧКИ' : 'ДРИФТ-ОЧКИ', cx, y0 + 19 * u);
        ctx.fillStyle = UI.paper; ctx.font = fontD(22 * u);
        ctx.fillText(fmtInt(totalDrift), cx, y0 + 46 * u);
      } else {
        // narrow screens: a compact panel under the left panel (label above the value, as in the wide layout)
        var nby = y0 + ph + Math.round(8 * u), nbw = Math.round(Math.max(96, 112 * u)), nbh = Math.round(Math.max(42, 48 * u));
        var nbp = Math.max(9, 12 * u);
        panel(ctx, x0, nby, nbw, nbh, 12 * u);
        ctx.textAlign = 'left';
        ctx.fillStyle = UI.muted; ctx.font = fontB(Math.max(9, 11 * u), 700);
        ctx.fillText(mode === 'drift' ? 'ОЧКИ' : 'ДРИФТ-ОЧКИ', x0 + nbp, nby + nbh * 0.37);
        ctx.fillStyle = UI.paper; ctx.font = fontD(Math.max(15, 18 * u));
        ctx.fillText(fmtInt(totalDrift), x0 + nbp, nby + nbh * 0.83);
      }
      // live drift counter
      var dy0 = y0 + Math.round(58 * u) + 44 * u;
      if (dr.active && dr.pts > 5) {
        ctx.textAlign = 'center';
        ctx.font = fontD(28 * u);
        ctx.lineWidth = 5 * u; ctx.strokeStyle = 'rgba(23,32,49,0.7)';
        var live = fmtInt(dr.pts * dr.combo);
        ctx.strokeText(live, W / 2, dy0);
        ctx.fillStyle = UI.gold;
        ctx.fillText(live, W / 2, dy0);
        if (dr.combo > 1) {
          ctx.font = fontD(18 * u);
          ctx.strokeText('×' + dr.combo, W / 2, dy0 + 24 * u);
          ctx.fillStyle = UI.flame;
          ctx.fillText('×' + dr.combo, W / 2, dy0 + 24 * u);
        }
      } else if (dr.comboT > 0 && dr.combo >= 1 && phase === 'race') {
        ctx.textAlign = 'center';
        ctx.globalAlpha = clamp(dr.comboT / 0.6, 0, 1) * 0.9;
        ctx.font = fontB(15 * u, 700);
        ctx.lineWidth = 4 * u; ctx.strokeStyle = 'rgba(23,32,49,0.75)';
        var ctext = 'Серия ×' + Math.min(5, dr.combo + 1) + ' — следующий занос!';
        ctx.strokeText(ctext, W / 2, dy0);
        ctx.fillStyle = UI.flame;
        ctx.fillText(ctext, W / 2, dy0);
        ctx.globalAlpha = 1;
      }
      // popups (banked / failed)
      for (var pi = 0; pi < popups.length; pi++) {
        var pp = popups[pi], f = pp.t / 1.4;
        ctx.globalAlpha = f < 0.75 ? 1 : 1 - (f - 0.75) / 0.25;
        ctx.textAlign = 'center';
        ctx.fillStyle = pp.color;
        ctx.font = fontD((pp.big ? 26 : 18) * u);
        var yy = Hh * 0.36 - f * 40 * u - (popups.length - 1 - pi) * 30 * u;
        ctx.lineWidth = 4 * u; ctx.strokeStyle = 'rgba(23,32,49,0.7)';
        ctx.strokeText(pp.text, W / 2, yy);
        ctx.fillText(pp.text, W / 2, yy);
      }
      ctx.globalAlpha = 1;
      // ---- minimap
      drawMinimap(ctx, rs, sf, pad, u);
      // ---- steering zones
      var zr = Math.round(46 * u);
      var zy = Hh - sf.bottom - pad - zr - 4 * u;
      var zlx = sf.left + pad + zr + 4 * u, zrx = W - sf.right - pad - zr - 4 * u;
      drawZone(ctx, zlx, zy, zr, -1, inL || (dbgSteer !== null && dbgSteer < -0.3));
      drawZone(ctx, zrx, zy, zr, 1, inR || (dbgSteer !== null && dbgSteer > 0.3));
      // ---- speed
      var kmh = Math.round(player.speed * KMH);
      ctx.textAlign = 'center';
      ctx.fillStyle = UI.paper;
      ctx.font = fontD(34 * u);
      ctx.lineWidth = 5 * u; ctx.strokeStyle = 'rgba(23,32,49,0.55)';
      var sy = Hh - sf.bottom - pad - 22 * u;
      ctx.strokeText(String(kmh), W / 2, sy);
      ctx.fillText(String(kmh), W / 2, sy);
      ctx.fillStyle = UI.muted; ctx.font = fontB(12 * u, 700);
      ctx.strokeText('КМ/Ч', W / 2, sy + 17 * u);
      ctx.fillText('КМ/Ч', W / 2, sy + 17 * u);
      if (player.hbF > 0.5 && phase === 'race') {
        ctx.fillStyle = UI.flame; ctx.font = fontB(13 * u, 700);
        ctx.fillText('РУЧНИК', W / 2, sy - 40 * u);
      }
      // ---- wrong way
      if (wrongShow > 0) {
        ctx.globalAlpha = wrongShow;
        var ww = 230 * u, wh = 64 * u, wx = W / 2 - ww / 2, wy = Hh * 0.22;
        ctx.fillStyle = 'rgba(229,72,77,0.92)';
        ctx.beginPath(); rrect(ctx, wx, wy, ww, wh, 16 * u); ctx.fill();
        // u-turn arrow icon
        ctx.strokeStyle = UI.paper; ctx.lineWidth = 4 * u; ctx.lineCap = 'round';
        var ix = wx + 34 * u, iy = wy + wh / 2;
        ctx.beginPath();
        ctx.moveTo(ix + 8 * u, iy + 12 * u); ctx.lineTo(ix + 8 * u, iy - 4 * u);
        ctx.arc(ix, iy - 4 * u, 8 * u, 0, Math.PI, true);
        ctx.lineTo(ix - 8 * u, iy + 8 * u);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(ix - 14 * u, iy + 3 * u); ctx.lineTo(ix - 8 * u, iy + 11 * u); ctx.lineTo(ix - 2 * u, iy + 3 * u);
        ctx.stroke();
        ctx.fillStyle = UI.paper; ctx.font = fontD(24 * u); ctx.textAlign = 'left';
        ctx.fillText('Не туда!', wx + 62 * u, wy + wh / 2 + 9 * u);
        ctx.globalAlpha = 1;
      }
      // ---- flash message (laps, finish)
      if (msg.t < msg.dur && msg.text) {
        var fa = msg.t < 0.15 ? msg.t / 0.15 : (msg.t > msg.dur - 0.4 ? (msg.dur - msg.t) / 0.4 : 1);
        ctx.globalAlpha = clamp(fa, 0, 1);
        ctx.textAlign = 'center';
        ctx.font = fontD(34 * u);
        ctx.lineWidth = 6 * u; ctx.strokeStyle = 'rgba(23,32,49,0.75)';
        var my = Hh * 0.27;
        ctx.strokeText(msg.text, W / 2, my);
        ctx.fillStyle = msg.color;
        ctx.fillText(msg.text, W / 2, my);
        if (msg.sub) {
          ctx.font = fontB(18 * u, 700);
          ctx.strokeText(msg.sub, W / 2, my + 28 * u);
          ctx.fillStyle = msg.subColor || UI.paper;
          ctx.fillText(msg.sub, W / 2, my + 28 * u);
        }
        ctx.globalAlpha = 1;
      }
      // ---- "you" marker over the player's car at the start
      if ((phase === 'countdown' || goFlash > -1.5) && mode === 'race') {
        var ma = phase === 'countdown' ? 1 : clamp((goFlash + 1.5) / 0.6, 0, 1);
        if (ma > 0) {
          ctx.globalAlpha = ma;
          var bob = reduced ? 0 : Math.sin(clock * 6) * 3 * u;
          var my0 = markY - 50 * u + bob;
          ctx.fillStyle = UI.flame;
          ctx.beginPath();
          ctx.moveTo(markX - 9 * u, my0 - 4 * u); ctx.lineTo(markX + 9 * u, my0 - 4 * u); ctx.lineTo(markX, my0 + 7 * u);
          ctx.closePath(); ctx.fill();
          ctx.font = fontD(14 * u);
          ctx.textAlign = 'center';
          ctx.lineWidth = 4 * u; ctx.strokeStyle = 'rgba(23,32,49,0.8)';
          ctx.strokeText('ТЫ', markX, my0 - 9 * u);
          ctx.fillStyle = UI.paper;
          ctx.fillText('ТЫ', markX, my0 - 9 * u);
          ctx.globalAlpha = 1;
        }
      }
      // ---- countdown
      if (phase === 'countdown' && cdT <= 3) {
        var n = Math.ceil(cdT), fr = n - cdT;
        ctx.globalAlpha = 1 - fr * 0.5;
        ctx.textAlign = 'center';
        ctx.font = fontD((110 + fr * 30) * u);
        ctx.lineWidth = 8 * u; ctx.strokeStyle = 'rgba(23,32,49,0.7)';
        ctx.strokeText(String(n), W / 2, Hh * 0.34);
        ctx.fillStyle = UI.paper;
        ctx.fillText(String(n), W / 2, Hh * 0.34);
        ctx.globalAlpha = 1;
      } else if (goFlash > 0) {
        ctx.globalAlpha = clamp(goFlash / 0.4, 0, 1);
        ctx.textAlign = 'center';
        ctx.font = fontD(84 * u);
        ctx.lineWidth = 8 * u; ctx.strokeStyle = 'rgba(23,32,49,0.7)';
        ctx.strokeText('Старт!', W / 2, Hh * 0.34);
        ctx.fillStyle = UI.flame;
        ctx.fillText('Старт!', W / 2, Hh * 0.34);
        ctx.globalAlpha = 1;
      }
      // ---- control hint
      if (phase === 'countdown' || hintT > 0) {
        var ha = phase === 'countdown' ? 1 : clamp(hintT / 0.6, 0, 1);
        ctx.globalAlpha = ha;
        var hwid = Math.min(W - 2 * pad - sf.left - sf.right, 470 * u), hh = 66 * u;
        // low on the screen, just above the chevron zones it explains: the car never goes down there
        var hx = W / 2 - hwid / 2, hy = Hh - sf.bottom - pad - 2 * zr - 20 * u - hh;
        if (hy < Hh * 0.74) hy = Hh * 0.36;              // very short screens: above the car instead
        ctx.fillStyle = 'rgba(23,32,49,0.84)';
        ctx.beginPath(); rrect(ctx, hx, hy, hwid, hh, 16 * u); ctx.fill();
        ctx.textAlign = 'center';
        ctx.fillStyle = UI.paper;
        var hf = Math.min(16 * u, hwid / 25);
        ctx.font = fontB(hf, 600);
        ctx.fillText('Держи слева — влево, справа — вправо.', W / 2, hy + hh / 2 - 4 * u);
        ctx.fillStyle = UI.flame;
        ctx.font = fontB(hf, 700);
        ctx.fillText('Двумя пальцами — ручник', W / 2, hy + hh / 2 + 18 * u);
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    }
    function drawZone(ctx, x, y, r, dir, on) {
      ctx.fillStyle = on ? 'rgba(255,90,54,0.45)' : 'rgba(23,32,49,0.35)';
      ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
      ctx.strokeStyle = on ? 'rgba(255,90,54,0.95)' : 'rgba(244,238,223,0.35)';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.strokeStyle = on ? UI.paper : 'rgba(244,238,223,0.75)';
      ctx.lineWidth = Math.max(3, r * 0.14);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      var s = r * 0.32, tipX = x + dir * s * 0.55, backX = x - dir * s * 0.35;
      ctx.beginPath();
      ctx.moveTo(backX, y - s);
      ctx.lineTo(tipX, y);
      ctx.lineTo(backX, y + s);
      ctx.stroke();
    }
    function drawMinimap(ctx, rs, sf, pad, u) {
      if (!gfx.map) return;
      var W = vw, Hh = vh;
      var size = Math.round(clamp(Math.min(W, Hh) * 0.18, 80, 150));
      var mw = gfx.mapW * size, mh = gfx.mapH * size;
      var bw = mw + 20 * u, bh = mh + 20 * u;
      var x = W - sf.right - pad - bw;
      var y = Math.max(rs.y + rs.h + 8, sf.top + pad);
      if (mode === 'race' || y < sf.top + pad + 96 * u + 8) y = Math.max(y, sf.top + pad + 96 * u + 10);
      panel(ctx, x, y, bw, bh, 12 * u);
      var ox = x + 10 * u, oy = y + 10 * u;
      ctx.save();
      ctx.translate(ox, oy);
      ctx.scale(size, size);
      ctx.lineJoin = 'round';
      ctx.strokeStyle = 'rgba(244,238,223,0.25)';
      ctx.lineWidth = 7 / size;
      ctx.stroke(gfx.map);
      ctx.strokeStyle = UI.paper;
      ctx.lineWidth = 2.4 / size;
      ctx.stroke(gfx.map);
      ctx.restore();
      var s = gfx.mapS * size;
      // start line tick
      ctx.fillStyle = UI.gold;
      ctx.fillRect(ox + (T.px[0] - T.minx) * s - 2, oy + (T.py[0] - T.miny) * s - 2, 4, 4);
      for (var i = cars.length - 1; i >= 0; i--) {
        var c = cars[i];
        var mx = ox + (c.x - T.minx) * s, my = oy + (c.y - T.miny) * s;
        ctx.fillStyle = c.color;
        ctx.strokeStyle = c.isPlayer ? UI.paper : UI.night;
        ctx.lineWidth = c.isPlayer ? 2 : 1.5;
        ctx.beginPath(); ctx.arc(mx, my, c.isPlayer ? 5 * u + 1 : 3.5 * u + 1, 0, TAU); ctx.fill(); ctx.stroke();
      }
    }

    // ---------------------------------------------------------------- lifecycle
    function resize(w, h) {
      vw = w || api.width || vw;
      vh = h || api.height || vh;
      hudU = clamp(Math.min(vw, vh) / 800, 0.62, 1.25);
      if (!cam.init) updateCamera(0);
    }
    function pause() {
      paused = true;
      ptrs.length = 0;
      stopAudio();
    }
    function resume() {
      paused = false;
      ptrs.length = 0;
    }
    function destroy() {
      stopAudio();
      noiseBuf = null;
      paused = true;
      if (gfx && gfx.canvases) {
        for (var i = 0; i < gfx.canvases.length; i++) {
          try { gfx.canvases[i].width = 0; gfx.canvases[i].height = 0; } catch (e) { /* ignore */ }
        }
        gfx.canvases.length = 0;
        gfx.groundPat = null; gfx.roadPat = null; gfx.groundTile = null; gfx.roadTile = null;
      }
      ptrs.length = 0;
    }

    var DP = { x: 0, y: 0, tx: 0, ty: 0, nx: 0, ny: 0, k: 0 };
    var debug = {
      state: function () {
        var p = player;
        return {
          mode: mode, track: trackKey, car: carKey, difficulty: diffKey,
          lap: Math.min(LAPS, p.lap + 1), lapsDone: p.lap, laps: mode === 'drift' ? 0 : LAPS,
          place: p.place, speedKmh: Math.round(p.speed * KMH), x: p.x, y: p.y, heading: p.a,
          velHeading: p.speed > 1 ? Math.atan2(p.vy, p.vx) : p.a,
          progress: p.raceDist / L, driftScore: Math.round(totalDrift), finished: p.finished, phase: over ? 'over' : phase,
          slipDeg: p.slip / DEG, sliding: p.sliding, offroad: p.off, nextCp: p.nextCp, checkpoints: T.NC,
          bestLap: isFinite(p.bestLap) ? p.bestLap : null, lapTimes: p.lapTimes.slice(), raceTime: raceTime,
          wrongWay: wrongShow > 0.5, respawns: respawns, hits: hitCount, throttle: p.throttle, timeLeft: timeLeft, steer: p.steer, handbrake: p.hbF,
          yawRate: p.w, driftActive: dr.active, driftPending: Math.round(dr.pts), combo: dr.combo,
          trackLength: L, halfWidth: T.hw, idealLap: idealLap,
          bots: cars.slice(1).map(function (b) { return { lap: b.lap, finished: b.finished, finishTime: b.finishTime, place: b.place, speed: b.v, raceDist: b.raceDist }; }),
          result: lastResult
        };
      },
      setSteer: function (v) { dbgSteer = (v === null || v === undefined) ? null : clamp(+v || 0, -1, 1); },
      setHandbrake: function (on) { dbgHb = !!on; },
      setAutopilot: function (on) { autoPilot = !!on; },
      teleportToCheckpoint: function (i) {
        i = ((Math.floor(i) % T.NC) + T.NC) % T.NC;
        var p = player;
        centreAt(T.cpS[i] + 0.5, DP);
        var sp = Math.max(8, p.speed);
        p.x = DP.x; p.y = DP.y; p.a = Math.atan2(DP.ty, DP.tx);
        p.vx = DP.tx * sp; p.vy = DP.ty * sp; p.w = 0; p.sliding = false; p.velA = p.a; p.omP = 0;
        p.px = p.x; p.py = p.y; p.pa = p.a;
        trackCar(p, true);
        updateProgress(p, p.ts, true);
        p.stuckT = 0; p.wrongT = 0; p.skipT = 0; p.mOn = false;
        cam.init = false;
      },
      pointAhead: function (m) {
        centreAt(player.ts + (m || 10), DP);
        return { x: DP.x, y: DP.y, tx: DP.tx, ty: DP.ty, lineX: DP.x + DP.nx * T.line[DP.i], lineY: DP.y + DP.ny * T.line[DP.i] };
      },
      trackInfo: function () {
        return { N: N, L: L, hw: T.hw, wallDist: T.wallDist, outer: T.outer, NC: T.NC, stacks: T.stackN, scenery: T.scenery.length };
      },
      centre: function () {
        var out = [];
        for (var i = 0; i < N; i += 2) out.push([T.px[i], T.py[i]]);
        return out;
      },
      setPosition: function (x, y, a, speed) {
        var p = player;
        p.x = x; p.y = y; p.a = a; p.vx = Math.cos(a) * (speed || 0); p.vy = Math.sin(a) * (speed || 0); p.w = 0;
        p.velA = a; p.omP = 0; p.sliding = false;
        p.px = x; p.py = y; p.pa = a;
        trackCar(p, true);
        cam.init = false;
      },
      setSandbox: function (on) { sandbox = !!on; },
      audioActive: function () { return !!au; },
      setOverview: function (on) { overview = !!on; if (!on) cam.init = false; },
      finishNow: function () { if (mode === 'drift') timeLeft = 0.01; }
    };

    resize(vw, vh);

    return {
      update: update,
      render: render,
      resize: resize,
      pointerDown: pointerDown,
      pointerMove: pointerMove,
      pointerUp: pointerUp,
      pause: pause,
      resume: resume,
      destroy: destroy,
      debug: debug
    };
  }

  // =====================================================================================
  // Registration
  // =====================================================================================
  Arcade.register({
    id: 'drift',
    title: 'Горячая резина',
    tagline: 'Дрифт-гонки',
    accent: '#FF5A36',
    howTo: [
      'Газ автоматический — ты только рулишь.',
      'Держи палец слева — влево, справа — вправо.',
      'Коснись двумя пальцами — ручник и занос.',
      'Длинный занос приносит очки, серия — множитель.'
    ],
    setup: [
      {
        id: 'mode', label: 'Режим', choices: [
          { id: 'race', label: 'Гонка', note: '3 круга против 3 соперников' },
          { id: 'drift', label: 'Дрифт-зачёт', note: '90 секунд, очки за заносы' },
          { id: 'time', label: 'На время', note: '3 круга, лучший круг' }
        ]
      },
      {
        id: 'track', label: 'Трасса', choices: [
          { id: 'ring', label: 'Кольцо', note: 'Быстрая, одна шпилька' },
          { id: 'port', label: 'Порт', note: 'Тесные повороты между контейнерами' },
          { id: 'serpent', label: 'Серпантин', note: 'Длинные связки S-поворотов' }
        ]
      },
      {
        id: 'car', label: 'Машина', choices: [
          { id: 'hatch', label: 'Хэтчбек', note: 'Лёгкий и цепкий, прощает ошибки' },
          { id: 'coupe', label: 'Купе', note: 'Баланс, проще всего дрифтить' },
          { id: 'muscle', label: 'Маслкар', note: 'Мощный и тяжёлый, любит скользить' }
        ]
      }
    ],
    drawPreview: function (ctx, w, h, t) {
      try { drawPreview(ctx, w, h, t); } catch (e) { /* never break the menu */ }
    },
    bestText: function (store, options, difficulty) {
      var o = normOpts(options), d = normDiff(difficulty);
      var v = store && typeof store.get === 'function' ? store.get(recKey(o, d), null) : null;
      if (o.mode === 'race') {
        var rb = raceBest(v);
        if (!rb) return null;
        return rb.p > 0 ? 'Лучшее: ' + rb.p + '-е место, ' + fmtTime(rb.t) : 'Рекорд: ' + fmtTime(rb.t);
      }
      if (typeof v !== 'number' || !isFinite(v)) return null;
      if (o.mode === 'drift') return 'Рекорд: ' + fmtInt(v) + ' ' + plural(v, 'очко', 'очка', 'очков');
      if (o.mode === 'time') return 'Лучший круг: ' + fmtTime(v);
      return 'Рекорд: ' + fmtTime(v);
    },
    create: function (api) { return createGame(api); }
  });
})();
