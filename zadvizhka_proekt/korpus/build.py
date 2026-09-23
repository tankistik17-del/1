# -*- coding: utf-8 -*-
"""
3D-модель сварного корпуса задвижки трубопровода (лист 2 «Корпус», М 1:1,
дипломный проект «Технология сборки-сварки корпуса задвижки трубопровода»).

Состав (по чертежу и технологическому процессу, листы 4, 5):
  поз.1 Патрубок (2 шт.)           — труба Ø111×6, внутренний торец — наклонное седло
  поз.2 Стакан                     — труба Ø130×6 (Ø118 внутр.), 2 отверстия под патрубки
  поз.3 Фланец патрубка (2 шт.)    — Ø210, 8 отв. Ø18 на Ø180, толщина 20, выступ Ø130
  поз.4 Фланец стакана             — Ø210, 8 отв. Ø18H14 на Ø180 (22,5°±1°), расточка Ø118
  поз.5 Направляющая (2 шт.)       — квадрат 14, ширина 14*, зазор между направляющими 90*
  поз.6 Дно                        — штампованное сферическое днище s = 5
  Швы ГОСТ 14771-76-Т1-ИП-◺3: №1 (8 шт., направляющие—стакан),
      №2 (5 шт., стакан—фланец стакана, патрубки—фланцы, патрубки—стакан),
      №3 (дно—стакан, узел Б листа 1).

Система координат: X — ось прохода (трубопровода), Z — ось стакана (шпинделя),
вверх; Y = Z × X. Начало — пересечение оси прохода и оси стакана. Размеры в мм.

API для общей сборки (лист 1):
    sys.path.insert(0, '/home/user/1/zadvizhka_proekt/korpus')
    from build import make_korpus_parts
    parts = make_korpus_parts()   # [(node_key, name_ru, cq.Workplane, cq.Color), ...]

Запуск: python3 build.py  → out/*.step, out/*.glb, out/parts_step, out/parts_stl, out/spec.json
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# ---------------------------------------------------------------------------
# Исходные размеры (лист 2, если не оговорено иное). «*» — справочный размер,
# «*1» — размер обеспечивается приспособлением (ТТ п.1).
# Масштаб PDF: 1 мм чертежа = 8.05 px @200 dpi (калибровка по 224, 214*, 174*,
# Ø210, 130* и по размерам 181*, 286*, 102, 138 листа 1).
# ---------------------------------------------------------------------------
# --- Габарит по фланцам патрубков
L_FACE = 224.0          # 224 — между уплотнительными поверхностями фланцев поз.3
L_PLATE = 214.0         # 214* — между наружными плоскостями тарелок фланцев
L_INNER = 174.0         # 174* — между внутренними плоскостями фланцев поз.3
X_FACE = L_FACE / 2     # 112
X_PLATE = L_PLATE / 2   # 107
X_INNER = L_INNER / 2   # 87

# --- Фланцы поз.3 и поз.4 (одинаковый наружный контур)
FL_D = 210.0            # Ø210 (вид сверху листа 2; Ø210* вид слева листа 1)
FL_T = 20.0             # 20* — толщина тарелки
FL_BC = 180.0           # Ø180 — окружность центров отверстий
FL_HOLE = 18.0          # 8 отв. Ø18H14* (на листе 1 для поз.3 указано Ø17,64 — см. NOTES)
FL_N = 8
FL_HOLE_ANG = 22.5      # 22,5°±1° (лист 2 — фланец стакана; лист 1 и оп.035 — фланец патрубка)
RF_D = 130.0            # Ø130* — торец выступа (уплотнительной поверхности)
RF_H = (L_FACE - L_PLATE) / 2   # 5 — высота выступа
RF_D0 = RF_D + 2 * RF_H         # 140 — основание выступа (фаска 45°, размер «45°»)
CH = 2.0                # 2×45° «3 фаски» — фаски расточек фланцев (2 × поз.3, поз.4)

# --- Патрубок поз.1 (труба)
P_OD = 111.0            # Ø111* (лист 1 и 2)
P_ID = 99.0             # Ø99*  — внутренний диаметр патрубка = расточка фланца поз.3
P_SOCKET = 8.0          # глубина расточки фланца под патрубок (по векторам 7,6 мм)
X_P_OUT = X_INNER + P_SOCKET    # 95 — наружный торец патрубка (упор в уступ фланца)
FIT = 0.1               # радиальный зазор посадок трубы во фланце/стакане (допущение)

# --- Седла (наклонные внутренние торцы патрубков)
SEAT_GAP = 34.0         # 34±0,1*1 — между уплотнительными поверхностями по низу патрубков
SEAT_ANG = 6.2          # угол наклона седла к вертикали, град (по векторам листов 1 и 2: 6,21°)
SEAT_LAYER = 2.0        # толщина наплавки уплотнительной поверхности (по векторам 1,99 мм)

# --- Стакан поз.2 (труба)
ST_OD = 130.0           # 130* (лист 2), Ø130* (А-А листа 1)
ST_ID = 118.0           # Ø118 (расточка фланца стакана = внутр. Ø стакана, лист 1 «Ø118»)
Z_ST_TOP = 140.0        # верхний торец стакана (по векторам 139,7)
Z_ST_BOT = -68.0        # нижний торец стакана (по векторам -68,07)

# --- Фланец стакана поз.4
F4_CBORE = 10.0         # глубина расточки Ø130 под стакан (по векторам 10,2)
Z_F4_BOT = Z_ST_TOP - F4_CBORE      # 130 — нижняя плоскость фланца (по векторам 129,5)
Z_F4_TOP = Z_F4_BOT + FL_T          # 150
Z_F4_HUB = Z_F4_TOP + RF_H          # 155 — торец выступа (160* на листе 2 — см. NOTES)

# --- Направляющие поз.5
GD_W = 14.0             # 14* (лист 2, А-А листа 1)
GD_GAP = 90.0           # 90* — между рабочими гранями направляющих (А-А листа 1)
GD_DEPTH = 13.5         # радиальный размер (квадрат 14 вписывается в Ø118 только на 13,58)
Z_GD_TOP = Z_ST_TOP - 8.0   # 8₋₂*1 — от торца стакана до торца направляющей
Z_GD_BOT = -60.0            # 60⁺⁵*1 — от оси прохода до нижнего торца направляющей
W1_LEN = 40.0               # 40⁺⁴*1 — длина швов №1 (оп.020 «длина швов по шаблону», 40±2)

# --- Дно поз.6 (штамповка из листа s5)
DNO_T = 5.0             # толщина (по векторам 4,9…5,6)
DNO_RO = 102.0          # R наружной сферы (по векторам R101,8)
DNO_RI = DNO_RO - DNO_T
# центр сфер: внутренняя кромка дна опирается на внутреннюю кромку торца стакана (узел Б)
DNO_ZC = Z_ST_BOT + math.sqrt(DNO_RI ** 2 - (ST_ID / 2) ** 2)
DIMPLE_TOP_IN = -82.4   # центральная выштамповка (лунка) — верх внутренней поверхности
DIMPLE_TOP_OUT = -87.4  # верх наружной поверхности лунки
DIMPLE_R_IN = (2.0, 7.5)    # радиусы начала/конца боковой поверхности лунки (внутр.)
DIMPLE_R_OUT = (1.5, 6.5)   # то же, наружная поверхность

# --- Швы ГОСТ 14771-76-Т1-ИП-◺3
K = 3.0                 # катет
W3_OVER = 1.5           # 1,5 — выступание шва №3 за наружную поверхность стакана (узел Б, лист 1)
GAP = 0.05              # технологический зазор швов, выполненных многогранником


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _valid(wp, name):
    s = wp.val()
    assert s.isValid(), "invalid solid: " + name
    assert s.Volume() > 0, "zero volume: " + name
    return wp


def revolve_x(pts):
    """Тело вращения вокруг оси X из контура (x, r)."""
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (1, 0, 0)))


def revolve_z(pts):
    """Тело вращения вокруг оси Z из контура (r, z)."""
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))


def tube_x(x0, x1, r_in, r_out):
    return revolve_x([(x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out)])


def tube_z(z0, z1, r_in, r_out):
    return revolve_z([(r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1)])


def cyl(r, h, pnt, d):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*pnt), cq.Vector(*d)))


def mirror_x(wp):
    return wp.mirror("YZ")


def seat_x(z, u=0.0):
    """x правого седла на высоте z; u — смещение по нормали к плоскости седла."""
    t = math.radians(SEAT_ANG)
    return SEAT_GAP / 2 + (z + P_OD / 2) * math.tan(t) + u / math.cos(t)


def seat_slab(u0, u1):
    """Слой между плоскостями, параллельными плоскости правого седла (u — по нормали)."""
    box = cq.Solid.makeBox(u1 - u0, 400, 400, cq.Vector(u0, -200, -200))
    box = box.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), SEAT_ANG)
    box = box.translate(cq.Vector(SEAT_GAP / 2, 0, -P_OD / 2))
    return cq.Workplane("XY").add(box)


def polyhedron_ring(sections):
    """Замкнутое кольцо из треугольных сечений [(P, A, B), ...] → тело (грани — треугольники)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    n = len(sections)
    faces = []

    def tri(a, b, c):
        faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon(
            [cq.Vector(*a), cq.Vector(*b), cq.Vector(*c)], close=True)))

    for i in range(n):
        j = (i + 1) % n
        (p0, a0, b0), (p1, a1, b1) = sections[i], sections[j]
        tri(p0, a0, a1); tri(p0, a1, p1)      # грань по поверхности 1
        tri(p0, p1, b1); tri(p0, b1, b0)      # грань по поверхности 2
        tri(a0, b0, b1); tri(a0, b1, a1)      # свободная поверхность шва
    sew = BRepBuilderAPI_Sewing(1e-6)
    for f in faces:
        sew.Add(f.wrapped)
    sew.Perform()
    shell = cq.Shell(sew.SewedShape())
    solid = cq.Solid.makeSolid(shell)
    if solid.Volume() < 0:
        solid = cq.Solid(solid.wrapped.Reversed())
    solid = solid.fix()
    return cq.Workplane("XY").add(solid)


def _unit(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Детали
# ---------------------------------------------------------------------------
def _flange_holes_x(wp, x0, x1):
    for k in range(FL_N):
        a = math.radians(FL_HOLE_ANG + 45.0 * k)      # от вертикали (оси Z), симметрично
        y, z = FL_BC / 2 * math.sin(a), FL_BC / 2 * math.cos(a)
        wp = wp.cut(cyl(FL_HOLE / 2, x1 - x0 + 2, (x0 - 1, y, z), (1, 0, 0)))
    return wp


def make_patrubok(side=1):
    """поз.1 Патрубок: труба Ø111×6 от наружного торца x=95 до наклонной плоскости седла."""
    tube = tube_x(5.0, X_P_OUT, P_ID / 2, P_OD / 2)
    p = tube.intersect(seat_slab(SEAT_LAYER, 300.0))
    p = _valid(p, "patrubok")
    return mirror_x(p) if side < 0 else p


def make_naplavka(side=1):
    """Наплавка уплотнительной поверхности седла (на чертеже — узкая полоса с частой штриховкой)."""
    tube = tube_x(5.0, X_P_OUT, P_ID / 2, P_OD / 2)
    s = tube.intersect(seat_slab(0.0, SEAT_LAYER))
    s = _valid(s, "naplavka")
    return mirror_x(s) if side < 0 else s


def make_stakan():
    """поз.2 Стакан: труба Ø130×6, два отверстия Ø111 под патрубки."""
    st = tube_z(Z_ST_BOT, Z_ST_TOP, ST_ID / 2, ST_OD / 2)
    st = st.cut(cyl(P_OD / 2 + FIT, 200, (-100, 0, 0), (1, 0, 0)))
    return _valid(st, "stakan")


def make_flanec_patrubka(side=1):
    """поз.3 Фланец патрубка: Ø210×20, выступ Ø130/Ø140 h5 (45°), расточка Ø111 под патрубок,
    отверстие Ø99 с фаской 2×45°, 8 отв. Ø18 на Ø180 (22,5° от вертикали)."""
    rc = P_OD / 2 + FIT
    pts = [(X_INNER, rc), (X_INNER, FL_D / 2), (X_PLATE, FL_D / 2), (X_PLATE, RF_D0 / 2),
           (X_FACE, RF_D / 2), (X_FACE, P_ID / 2 + CH), (X_FACE - CH, P_ID / 2),
           (X_P_OUT, P_ID / 2), (X_P_OUT, rc)]
    f = revolve_x(pts)
    f = _flange_holes_x(f, X_INNER, X_FACE)
    f = _valid(f, "flanec_patrubka")
    return mirror_x(f) if side < 0 else f


def make_flanec_stakana():
    """поз.4 Фланец стакана: Ø210×20, выступ Ø130/Ø140 h5, отверстие Ø118 с фаской 2×45°,
    расточка Ø130 глубиной 10 под стакан, 8 отв. Ø18H14 на Ø180 (22,5°±1° от оси прохода)."""
    rc = ST_OD / 2 + FIT
    pts = [(rc, Z_F4_BOT), (FL_D / 2, Z_F4_BOT), (FL_D / 2, Z_F4_TOP), (RF_D0 / 2, Z_F4_TOP),
           (RF_D / 2, Z_F4_HUB), (ST_ID / 2 + CH, Z_F4_HUB), (ST_ID / 2, Z_F4_HUB - CH),
           (ST_ID / 2, Z_ST_TOP), (rc, Z_ST_TOP)]
    f = revolve_z(pts)
    for k in range(FL_N):
        a = math.radians(FL_HOLE_ANG + 45.0 * k)      # от оси X (вид сверху листа 2)
        x, y = FL_BC / 2 * math.cos(a), FL_BC / 2 * math.sin(a)
        f = f.cut(cyl(FL_HOLE / 2, 40, (x, y, Z_F4_BOT - 5), (0, 0, 1)))
    return _valid(f, "flanec_stakana")


def make_napravlyayushchaya(sy=1):
    """поз.5 Направляющая: брус 14×13,5, рабочая грань на |Y| = 45, z = −60…132."""
    y0 = GD_GAP / 2
    g = cq.Workplane("XY").add(cq.Solid.makeBox(
        GD_W, GD_DEPTH, Z_GD_TOP - Z_GD_BOT, cq.Vector(-GD_W / 2, y0, Z_GD_BOT)))
    if sy < 0:
        g = g.mirror("XZ")
    return _valid(g, "napravlyayushchaya")


def _dno_profile():
    """Контур (r, z) дна: сферический сегмент s5 с конической (радиальной) кромкой и лункой."""
    zc, ro, ri = DNO_ZC, DNO_RO, DNO_RI
    zo = lambda r: zc - math.sqrt(ro ** 2 - r ** 2)
    zi = lambda r: zc - math.sqrt(ri ** 2 - r ** 2)
    r_in_rim = ST_ID / 2
    k = ro / ri
    p_in = (r_in_rim, zi(r_in_rim))                              # = (59, -68)
    p_out = (r_in_rim * k, zc + (p_in[1] - zc) * k)              # по лучу из центра сферы
    rm = 35.0
    wp = (cq.Workplane("XZ").moveTo(*p_in).lineTo(*p_out)
          .threePointArc((rm, zo(rm)), (DIMPLE_R_OUT[1], zo(DIMPLE_R_OUT[1])))
          .lineTo(DIMPLE_R_OUT[0], DIMPLE_TOP_OUT).lineTo(0, DIMPLE_TOP_OUT)
          .lineTo(0, DIMPLE_TOP_IN).lineTo(DIMPLE_R_IN[0], DIMPLE_TOP_IN)
          .lineTo(DIMPLE_R_IN[1], zi(DIMPLE_R_IN[1]))
          .threePointArc((rm, zi(rm)), p_in).close())
    return wp, p_in, p_out


def make_dno():
    """поз.6 Дно: штампованное сферическое днище R102 (наружн.), s5, лунка в центре."""
    wp, _, _ = _dno_profile()
    d = wp.revolve(360, (0, 0, 0), (0, 1, 0))
    return _valid(d, "dno")


# ---------------------------------------------------------------------------
# Сварные швы (ГОСТ 14771-76-Т1-ИП-◺3, катет 3)
# ---------------------------------------------------------------------------
def make_shov_1(sy, sx, top):
    """Шов №1: направляющая — стакан (угловой, K3, длина 40), 8 шт.: 2 направл. × 2 стороны
    × (верхний, нижний участок)."""
    rw = ST_ID / 2 - GAP
    x0 = GD_W / 2
    pts = [(x0, GD_GAP / 2 + GD_DEPTH - K), (x0, math.sqrt(rw ** 2 - x0 ** 2)),
           (x0 + K, math.sqrt(rw ** 2 - (x0 + K) ** 2))]
    z0 = Z_GD_TOP - W1_LEN if top else Z_GD_BOT
    w = cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(W1_LEN)
    if sx < 0:
        w = w.mirror("YZ")
    if sy < 0:
        w = w.mirror("XZ")
    return _valid(w, "shov_1")


def make_shov_2_stakan_flanec():
    """Шов №2: стакан — фланец стакана (по замкнутому контуру, K3)."""
    r = ST_OD / 2
    return _valid(revolve_z([(r, Z_F4_BOT), (r, Z_F4_BOT - K), (r + K, Z_F4_BOT)]), "shov_2_sf")


def make_shov_2_patrubok_flanec(side=1):
    """Шов №2: патрубок — фланец патрубка (по замкнутому контуру, K3)."""
    r = P_OD / 2
    w = revolve_x([(X_INNER, r), (X_INNER - K, r), (X_INNER, r + K)])
    w = _valid(w, "shov_2_pf")
    return mirror_x(w) if side < 0 else w


def make_shov_2_patrubok_stakan(side=1, n=120):
    """Шов №2: патрубок — стакан, угловой по линии пересечения цилиндров Ø111 и Ø130 (K3)."""
    rp, rs = P_OD / 2 + GAP, ST_OD / 2 + GAP
    secs = []
    for i in range(n):
        f = 2 * math.pi * i / n
        y, z = rp * math.sin(f), rp * math.cos(f)
        x = math.sqrt(rs ** 2 - y ** 2)
        P = (x, y, z)
        Np = (0.0, math.sin(f), math.cos(f))
        Ns = (x / rs, y / rs, 0.0)
        T = _unit(_cross(Np, Ns))
        dp = _unit(_cross(T, Np))
        if _dot(dp, Ns) < 0:
            dp = tuple(-c for c in dp)
        ds = _unit(_cross(T, Ns))
        if _dot(ds, Np) < 0:
            ds = tuple(-c for c in ds)
        A = [P[c] + K * dp[c] for c in range(3)]
        m = rp / math.hypot(A[1], A[2]); A = (A[0], A[1] * m, A[2] * m)
        B = [P[c] + K * ds[c] for c in range(3)]
        m = rs / math.hypot(B[0], B[1]); B = (B[0] * m, B[1] * m, B[2])
        secs.append((P, A, B))
    w = _valid(polyhedron_ring(secs), "shov_2_ps")
    return mirror_x(w) if side < 0 else w


def make_shov_3():
    """Шов №3: дно — стакан (по замкнутому контуру), узел Б листа 1: заполняет угол между
    торцом стакана и кромкой дна, выступает на 1,5 за наружную поверхность стакана."""
    _, p_in, p_out = _dno_profile()
    r_o = ST_OD / 2
    pts = [(p_in[0] + 0.02, Z_ST_BOT), (r_o, Z_ST_BOT),
           (r_o + W3_OVER, Z_ST_BOT - 2.5),
           (p_out[0] + 1.2, p_out[1] - 0.6), p_out]
    return _valid(revolve_z(pts), "shov_3")


# ---------------------------------------------------------------------------
# Состав корпуса
# ---------------------------------------------------------------------------
C_PIPE = cq.Color(0.55, 0.58, 0.62)
C_STAKAN = cq.Color(0.42, 0.52, 0.64)
C_FLANGE = cq.Color(0.22, 0.40, 0.66)
C_GUIDE = cq.Color(0.70, 0.66, 0.50)
C_DNO = cq.Color(0.36, 0.46, 0.58)
C_SEAT = cq.Color(0.80, 0.62, 0.30)
C_WELD = cq.Color(0.28, 0.22, 0.18)

MAT = "Сталь 20 ГОСТ 1050-2013 (на листе: ГОСТ 1050-88)"
WELD_STD = "ГОСТ 14771-76-Т1-ИП-◺3 (проволока Св-08Г2С ГОСТ 2246-70, Ar 75% + CO2 25%)"

# (key, name_ru, fn, color, pos, standard, note)
PARTS = [
    ("01_patrubok_L", "Патрубок (лев.)", lambda: make_patrubok(-1), C_PIPE, "1",
     "Труба Ø111×6 (нестандартный размер, ближайшие по ГОСТ 8732-78: 108×6, 114×6)",
     "наружный торец x=±95 в расточке фланца, внутренний торец — седло 6,2°"),
    ("01_patrubok_R", "Патрубок (прав.)", lambda: make_patrubok(1), C_PIPE, "1",
     "Труба Ø111×6 (нестандартный размер, ближайшие по ГОСТ 8732-78: 108×6, 114×6)", ""),
    ("naplavka_sedla_L", "Наплавка уплотнительной поверхности седла (лев.)",
     lambda: make_naplavka(-1), C_SEAT, "", "", "на чертеже выделена штриховкой, позиции нет"),
    ("naplavka_sedla_R", "Наплавка уплотнительной поверхности седла (прав.)",
     lambda: make_naplavka(1), C_SEAT, "", "", "на чертеже выделена штриховкой, позиции нет"),
    ("02_stakan", "Стакан", make_stakan, C_STAKAN, "2",
     "Труба Ø130×6 (нестандартный размер, ближайшие по ГОСТ 8732-78: 127×6, 133×6)",
     "z = −68…+140, 2 отв. Ø111 под патрубки"),
    ("03_flanec_patrubka_L", "Фланец патрубка (лев.)", lambda: make_flanec_patrubka(-1),
     C_FLANGE, "3", "по типу ГОСТ 12820-80 Ду100 Ру1,6 (размеры по чертежу: Ø210, Ø180, 8×Ø18, b=20)",
     "выступ Ø130/Ø140 h5"),
    ("03_flanec_patrubka_R", "Фланец патрубка (прав.)", lambda: make_flanec_patrubka(1),
     C_FLANGE, "3", "по типу ГОСТ 12820-80 Ду100 Ру1,6 (размеры по чертежу: Ø210, Ø180, 8×Ø18, b=20)", ""),
    ("04_flanec_stakana", "Фланец стакана", make_flanec_stakana, C_FLANGE, "4",
     "по типу ГОСТ 12820-80 (размеры по чертежу)", "торец выступа z=155"),
    ("05_napravlyayushchaya_1", "Направляющая (Y+)", lambda: make_napravlyayushchaya(1),
     C_GUIDE, "5", "Квадрат 14 ГОСТ 2591-2006", "14×13,5, z = −60…132"),
    ("05_napravlyayushchaya_2", "Направляющая (Y−)", lambda: make_napravlyayushchaya(-1),
     C_GUIDE, "5", "Квадрат 14 ГОСТ 2591-2006", ""),
    ("06_dno", "Дно", make_dno, C_DNO, "6", "Лист 5 ГОСТ 19903-2015, штамповка",
     "сфера R102/R97, низ z=−93"),
]
_i = 0
for _sy, _sn in ((1, "Y+"), (-1, "Y-")):
    for _sx, _xn in ((-1, "L"), (1, "R")):
        for _top, _tn in ((True, "verh"), (False, "niz")):
            _i += 1
            PARTS.append(("shov_1_%d" % _i,
                          "Шов №1 направляющая—стакан (%s, %s, %s)" % (
                              _sn, "лев." if _xn == "L" else "прав.",
                              "верх" if _top else "низ"),
                          (lambda a=_sy, b=_sx, c=_top: make_shov_1(a, b, c)), C_WELD, "",
                          WELD_STD, "угловой K3, L=40"))
PARTS += [
    ("shov_2_1_stakan_flanec", "Шов №2 стакан—фланец стакана", make_shov_2_stakan_flanec,
     C_WELD, "", WELD_STD, "по замкнутому контуру"),
    ("shov_2_2_patrubok_flanec_L", "Шов №2 патрубок—фланец (лев.)",
     lambda: make_shov_2_patrubok_flanec(-1), C_WELD, "", WELD_STD, "по замкнутому контуру"),
    ("shov_2_3_patrubok_flanec_R", "Шов №2 патрубок—фланец (прав.)",
     lambda: make_shov_2_patrubok_flanec(1), C_WELD, "", WELD_STD, "по замкнутому контуру"),
    ("shov_2_4_patrubok_stakan_L", "Шов №2 патрубок—стакан (лев.)",
     lambda: make_shov_2_patrubok_stakan(-1), C_WELD, "", WELD_STD, "по линии пересечения"),
    ("shov_2_5_patrubok_stakan_R", "Шов №2 патрубок—стакан (прав.)",
     lambda: make_shov_2_patrubok_stakan(1), C_WELD, "", WELD_STD, "по линии пересечения"),
    ("shov_3_dno_stakan", "Шов №3 дно—стакан", make_shov_3, C_WELD, "",
     "ГОСТ 14771-76-Т1-ИП-◺3 (оп.030: сварка в CO2)", "по замкнутому контуру, узел Б"),
]


def make_korpus_parts():
    """Все детали и швы корпуса в системе координат задвижки:
    [(node_key, name_ru, cq.Workplane, cq.Color), ...]"""
    return [(key, name, fn(), color) for key, name, fn, color, *_ in PARTS]


# Присоединительные/сопрягаемые размеры корпуса для общей сборки (лист 1)
INTERFACE = {
    "z_flanec_stakana_niz": Z_F4_BOT,        # 130 — нижняя плоскость фланца поз.4 (под гайки)
    "z_flanec_stakana_tarelka": Z_F4_TOP,    # 150 — верх тарелки фланца поз.4
    "z_flanec_stakana_vystup": Z_F4_HUB,     # 155 — торец выступа Ø130 (под прокладку/крышку)
    "flanec_D": FL_D, "flanec_Dbc": FL_BC, "flanec_hole": FL_HOLE, "flanec_n": FL_N,
    "flanec_stakana_hole_ang_from_X": FL_HOLE_ANG,     # отверстия фланца поз.4: 22,5°+45°k от оси X
    "flanec_patrubka_hole_ang_from_Z": FL_HOLE_ANG,    # отверстия фланцев поз.3: 22,5°+45°k от оси Z
    "vystup_D": RF_D, "vystup_D0": RF_D0, "vystup_h": RF_H,
    "x_uplotn_poverkhnost": X_FACE,          # ±112 — уплотнительные поверхности фланцев поз.3
    "x_tarelka_naruzh": X_PLATE,             # ±107
    "x_flanec_vnutr": X_INNER,               # ±87
    "stakan_ID": ST_ID, "stakan_OD": ST_OD, "z_stakan": (Z_ST_BOT, Z_ST_TOP),
    "patrubok_OD": P_OD, "patrubok_ID": P_ID,
    # седла: плоскость правого седла x = SEAT_GAP/2 + (z + P_OD/2)·tg(SEAT_ANG), левое — зеркально
    "seat_gap_at_z": (SEAT_GAP, -P_OD / 2), "seat_angle_deg": SEAT_ANG,
    "seat_gap_at_axis": 2 * seat_x(0.0),
    "napravl_y_face": GD_GAP / 2, "napravl_w": GD_W, "napravl_z": (Z_GD_BOT, Z_GD_TOP),
    "dno_z_min": DNO_ZC - DNO_RO,
}


# ---------------------------------------------------------------------------
# Экспорт и проверки
# ---------------------------------------------------------------------------
def build(parts):
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="Korpus_zadvizhki")
    for key, name, wp, color in parts:
        assy.add(wp, name=key, color=color)
        cq.exporters.export(wp, os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(wp, os.path.join(OUT, "parts_stl", key + ".stl"),
                            tolerance=0.05, angularTolerance=0.1)
    assy.save(os.path.join(OUT, "korpus.step"))
    assy.save(os.path.join(OUT, "korpus.glb"), tolerance=0.08, angularTolerance=0.15)
    return assy


def check(parts):
    solids = {k: wp.val() for k, _, wp, _ in parts}
    bb_all = None
    for k, s in solids.items():
        assert s.isValid(), k
        bb = s.BoundingBox()
        bb_all = bb if bb_all is None else bb_all.add(bb)
    print("Габарит: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (
        bb_all.xmin, bb_all.xmax, bb_all.ymin, bb_all.ymax, bb_all.zmin, bb_all.zmax))
    keys = list(solids)
    bad = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = solids[keys[i]], solids[keys[j]]
            ba, bb = a.BoundingBox(), b.BoundingBox()
            if (ba.xmin > bb.xmax or bb.xmin > ba.xmax or ba.ymin > bb.ymax
                    or bb.ymin > ba.ymax or ba.zmin > bb.zmax or bb.zmin > ba.zmax):
                continue
            v = a.intersect(b).Volume()
            if v > 0.01:
                bad.append((keys[i], keys[j], v))
    for k1, k2, v in bad:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.3f мм3" % (k1, k2, v))
    if not bad:
        print("Пересечений нет (порог 0,01 мм3)")
    tot = 0.0
    for k, s in solids.items():
        m = s.Volume() * 7.85e-6
        tot += m
        print("%-30s V=%10.0f мм3  m=%.3f кг" % (k, s.Volume(), m))
    print("Масса корпуса (сталь 7850 кг/м3): %.2f кг" % tot)
    return bad, bb_all, tot


def _group(key):
    if key.startswith("shov_1_"):
        return "shov_1"
    if key.startswith("shov_2_"):
        return "shov_2"
    if (key[:2].isdigit() or key.startswith("naplavka")) and key[-2:] in ("_L", "_R", "_1", "_2"):
        return key[:-2]
    return key


GROUP_INFO = {
    "shov_1": ("Шов №1 направляющая—стакан (8№1)",
               "8 швов: 2 направляющие × 2 стороны × (верхний 40 мм от торца, нижний 40 мм от "
               "нижнего торца); длина «по шаблону» (оп.020), 40⁺⁴*1"),
    "shov_2": ("Шов №2 (стакан—фланец стакана, патрубки—фланцы, патрубки—стакан)",
               "5№2 по листу 1 (на листе 2 у шва стакан—фланец написано «5№1»); все — по "
               "замкнутому контуру; шов патрубок—стакан — по линии пересечения Ø111/Ø130"),
}


def write_spec(total_mass=None):
    groups = {}
    order = []
    for key, name, fn, color, pos, std, note in PARTS:
        g = _group(key)
        if g not in groups:
            base = name.split(" (")[0]
            groups[g] = {"key": g, "pos": pos, "name_ru": base, "qty": 0, "material": MAT,
                         "standard": std, "note": note, "nodes": []}
            order.append(g)
        groups[g]["qty"] += 1
        groups[g]["nodes"].append(key)
    for g, (nm, nt) in GROUP_INFO.items():
        groups[g]["name_ru"], groups[g]["note"] = nm, nt
    groups["naplavka_sedla"]["material"] = "наплавка (материал на чертеже не указан)"
    for g in order:
        if g.startswith("shov"):
            groups[g]["material"] = "металл шва, проволока Св-08Г2С ГОСТ 2246-70"
    spec = [groups[g] for g in order]
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return spec


def report_dims(parts):
    """Контрольные размеры модели (сравнение с чертежом)."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    S = {k: wp.val() for k, _, wp, _ in parts}

    class _BB:
        def __init__(self, s):
            b = Bnd_Box()
            BRepBndLib.AddOptimal_s(s.wrapped, b, False, False)
            (self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax) = b.Get()
            self.xlen, self.ylen, self.zlen = (self.xmax - self.xmin, self.ymax - self.ymin,
                                               self.zmax - self.zmin)

    bb = lambda k: _BB(S[k])
    out = []
    out.append(("224 (между уплотн. поверхностями)", 224, bb("03_flanec_patrubka_R").xmax - bb("03_flanec_patrubka_L").xmin))
    out.append(("Ø210 фланец поз.3", 210, bb("03_flanec_patrubka_R").zlen))
    out.append(("Ø210 фланец поз.4", 210, bb("04_flanec_stakana").xlen))
    out.append(("130* стакан", 130, bb("02_stakan").xlen))
    out.append(("Ø111* патрубок", 111, bb("01_patrubok_R").zlen))
    out.append(("20* фланец (тарелка)", 20, X_PLATE - X_INNER))
    out.append(("174*", 174, 2 * bb("03_flanec_patrubka_R").xmin))
    out.append(("14* направляющая", 14, bb("05_napravlyayushchaya_1").xlen))
    out.append(("90* между направляющими", 90, bb("05_napravlyayushchaya_1").ymin - bb("05_napravlyayushchaya_2").ymax))
    out.append(("60⁺⁵ ось — низ направляющей", 60, -bb("05_napravlyayushchaya_1").zmin))
    out.append(("8₋₂ торец стакана — направляющая", 8, bb("02_stakan").zmax - bb("05_napravlyayushchaya_1").zmax))
    out.append(("40⁺⁴ длина шва №1", 40, bb("shov_1_1").zlen))
    # 34 между седлами по низу патрубков (z = −55.5): точка плоскости седла
    out.append(("34±0,1 между седлами (низ)", 34, 2 * seat_x(-P_OD / 2)))
    out.append(("Ø118 отверстие фланца поз.4", 118, ST_ID))
    out.append(("160* ось — торец фланца поз.4", 160, bb("04_flanec_stakana").zmax))
    out.append(("268* торец фл.4 — низ фл.3", 268, bb("04_flanec_stakana").zmax - bb("03_flanec_patrubka_R").zmin))
    for n, d, m in out:
        print("  %-36s чертёж %7.2f  модель %7.2f" % (n, d, m))
    return out


if __name__ == "__main__":
    parts = make_korpus_parts()
    build(parts)
    bad, bb, mass = check(parts)
    dims = report_dims(parts)
    write_spec(mass)
    print("GLB: %.2f МБ" % (os.path.getsize(os.path.join(OUT, "korpus.glb")) / 1e6))
    sys.exit(1 if bad else 0)
