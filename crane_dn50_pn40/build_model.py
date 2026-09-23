# -*- coding: utf-8 -*-
"""
Параметрическая 3D-модель шарового крана DN 50 PN 40 (рисунок 1.1 ВКР).

Система координат: X — ось трубопровода (проход), Z — ось штока (вверх),
начало координат — центр шаровой пробки. Все размеры в миллиметрах.

Запуск:  python build_model.py      (нужен cadquery >= 2.4)
Результат: папка out/ — сборка STEP/GLB, детали STEP/STL.
"""
import math
import os

import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# ---------------------------------------------------------------------------
# Исходные размеры
# ---------------------------------------------------------------------------
# Общие (рисунок 1.1)
L = 180.0            # строительная длина (между уплотнительными поверхностями)
H_HANDLE = 109.0     # от оси прохода до верха рукоятки
L_HANDLE = 330.0     # от левой уплотнительной поверхности до конца рукоятки

# Фланец 12: ГОСТ 33259-2015, тип 01, исполнение B (ряд 2 = ГОСТ 12815-80,
# исполнение 1), DN 50, PN 40
FL_D = 160.0         # наружный диаметр фланца D
FL_D1 = 125.0        # диаметр окружности центров отверстий D1
FL_D2 = 102.0        # диаметр выступа уплотнительной поверхности d2
FL_F = 3.0           # высота выступа f
FL_B = 21.0          # толщина тарелки фланца b
FL_HOLE = 18.0       # диаметр отверстий под шпильки M16
FL_N = 4             # число отверстий

# Патрубок 4: труба 57×4 по ГОСТ 8732-78, сталь 20 (разд. 2.4 ВКР)
P_OD = 57.0
P_S = 4.0
P_ID = P_OD - 2 * P_S          # 49
P_SOCKET = 12.0                # глубина посадки трубы во фланец (рис. 2.6)

# Шаровая пробка 1
BALL_D = 80.0
BALL_BORE = 45.0
BALL_FLAT = 35.0               # лыски сверху/снизу (от центра)
SLOT_W = 6.4                   # паз под поводок штока
SLOT_BOTTOM = 30.0

# Седло 5, втулка 6, пружина 7, шайба 8 (пакет в расточке патрубка)
SEAT_OD = 53.0
SEAT_ID = 45.0
X_SEAT_OUT = 38.0              # наружный торец седла
X_SLEEVE_OUT = 46.0            # наружный торец втулки
X_SPRING_OUT = 49.0            # наружный торец тарельчатой пружины
X_WASHER_OUT = 52.0            # упорный бурт расточки патрубка
X_PIPE_IN = 30.5               # внутренний торец патрубка

# Корпус 3 (листовая сталь 20, s = 4 мм), горловина
B_S = 4.0
B_R_MAX = 47.0                 # наружный радиус средней части
B_X_CYL = 26.0                 # полудлина цилиндрической части
B_X_NECK = 52.0                # начало посадочной манжеты на патрубке
B_X_END = 56.0                 # торец корпуса (сварной шов №2)
NECK_D = 30.0
NECK_TOP = 82.0
STEM_BORE = 16.2
NECK_CBORE = 22.5
NECK_CBORE_TOP = 49.0

# Шток 2
STEM_D = 16.0
COLLAR_D = 22.0
Z_COLLAR = (42.0, 47.0)
Z_GASKET = (47.0, 49.0)        # прокладка штока 9
TANG_T = 6.0
TANG_L = 16.0
Z_SQ = (86.0, 93.0)            # квадрат под рукоятку
SQ = 11.0
THREAD_D = 10.0                # резьба M10
Z_THREAD_TOP = 104.0
ORING_Z = (60.0, 70.0)         # кольца 10: 013-016-19 ГОСТ 9833-73
ORING_D_IN = 12.8
ORING_W = 1.9
PIN_D = 4.0                    # штифт 11: 4×12 ГОСТ 3128-70
PIN_L = 12.0
PIN_Z = 76.0

# Рукоятка 13 и гайка 14 (M10 ГОСТ 5915-70: S = 17, m = 8)
HUB_Z = (88.0, 93.0)
BAR_W = 20.0
BAR_T = 5.0
NUT_S = 17.0
NUT_M = 8.0

X_FACE = -L / 2                         # левая уплотнительная поверхность
X_FL_BACK = L / 2 - FL_F - FL_B         # 66: тыльная сторона тарелки фланца
X_PIPE_OUT = X_FL_BACK + P_SOCKET       # 78: торец патрубка во фланце


def revolve_x(pts):
    """Тело вращения вокруг оси X из замкнутого контура (x, r)."""
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (1, 0, 0)))


def ring_x(x0, x1, r_in, r_out):
    return revolve_x([(x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out)])


def mirror_x(wp):
    return wp.mirror("YZ")


# ---------------------------------------------------------------------------
# Детали
# ---------------------------------------------------------------------------
def make_ball():
    ball = cq.Workplane("XY").sphere(BALL_D / 2)
    bore = cq.Workplane("YZ").circle(BALL_BORE / 2).extrude(BALL_D, both=True)
    ball = ball.cut(bore)
    cut = cq.Workplane("XY").box(2 * BALL_D, 2 * BALL_D, BALL_D)
    ball = ball.cut(cut.translate((0, 0, BALL_FLAT + BALL_D / 2)))
    ball = ball.cut(cut.translate((0, 0, -BALL_FLAT - BALL_D / 2)))
    slot = cq.Workplane("XY").box(2 * BALL_D, SLOT_W, 20).translate(
        (0, 0, SLOT_BOTTOM + 10))
    return ball.cut(slot)


def body_profiles(n=60):
    """Наружный контур корпуса (x, r) и эквидистанта внутрь на B_S."""
    def r_out(x):
        ax = abs(x)
        if ax <= B_X_CYL:
            return B_R_MAX
        if ax >= B_X_NECK:
            return P_OD / 2 + B_S
        t = (ax - B_X_CYL) / (B_X_NECK - B_X_CYL)
        return B_R_MAX - (B_R_MAX - P_OD / 2 - B_S) * (1 - math.cos(math.pi * t)) / 2

    xs = [-B_X_END] + [-B_X_NECK + i * (2 * B_X_NECK) / n for i in range(n + 1)] + [B_X_END]
    outer = [(x, r_out(x)) for x in xs]
    inner = []
    for i, (x, r) in enumerate(outer):
        if abs(x) >= B_X_NECK - 1e-9:
            inner.append((x, r - B_S))
            continue
        h = 1e-3
        dr = (r_out(x + h) - r_out(x - h)) / (2 * h)
        nx, nr = -dr, 1.0
        k = math.hypot(nx, nr)
        inner.append((x - B_S * nx / k, r - B_S * nr / k))
    return outer, inner


def make_body():
    outer, inner = body_profiles()
    shell = revolve_x(outer + inner[::-1])
    neck = (cq.Workplane("XY").workplane(offset=30).circle(NECK_D / 2)
            .extrude(NECK_TOP - 30))
    body = shell.union(neck)
    cavity = revolve_x([(inner[0][0], 0)] + inner + [(inner[-1][0], 0)])
    body = body.cut(cavity)
    body = body.cut(cq.Workplane("XY").circle(STEM_BORE / 2).extrude(NECK_TOP + 1))
    body = body.cut(cq.Workplane("XY").circle(NECK_CBORE / 2).extrude(NECK_CBORE_TOP))
    # отверстие под штифт 11
    body = body.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        PIN_D / 2, NECK_D, cq.Vector(0, -STEM_BORE / 2 - 1, PIN_Z), cq.Vector(0, -1, 0))))
    return body


def make_pipe(side):
    """Патрубок 4 (side = -1 — левый, +1 — правый)."""
    pts = [(X_PIPE_IN, SEAT_OD / 2), (X_WASHER_OUT, SEAT_OD / 2),
           (X_WASHER_OUT, P_ID / 2), (X_PIPE_OUT, P_ID / 2),
           (X_PIPE_OUT, P_OD / 2), (X_PIPE_IN, P_OD / 2)]
    wp = revolve_x(pts)
    return mirror_x(wp) if side < 0 else wp


def make_flange(side):
    x_face = L / 2
    pts = [(x_face, P_ID / 2), (x_face, FL_D2 / 2), (x_face - FL_F, FL_D2 / 2),
           (x_face - FL_F, FL_D / 2), (X_FL_BACK, FL_D / 2),
           (X_FL_BACK, P_OD / 2 + 0.25), (X_PIPE_OUT, P_OD / 2 + 0.25),
           (X_PIPE_OUT, P_ID / 2)]
    fl = revolve_x(pts)
    for i in range(FL_N):
        a = math.radians(45 + i * 360 / FL_N)   # отверстия вне вертикальной оси
        hole = (cq.Workplane("YZ").workplane(offset=X_FL_BACK - 1)
                .center(FL_D1 / 2 * math.cos(a), FL_D1 / 2 * math.sin(a))
                .circle(FL_HOLE / 2).extrude(FL_B + FL_F + 2))
        fl = fl.cut(hole)
    return mirror_x(fl) if side < 0 else fl


def make_seat(side):
    """Седло: наружный торец плоский, внутренний — сфера R = BALL_D/2."""
    R = BALL_D / 2
    r1, r2 = SEAT_ID / 2, SEAT_OD / 2 - 0.05
    xs = lambda r: math.sqrt(R * R - r * r)
    rm = (r1 + r2) / 2
    seat = (cq.Workplane("XZ").moveTo(X_SEAT_OUT, r1).lineTo(X_SEAT_OUT, r2)
            .lineTo(xs(r2), r2).threePointArc((xs(rm), rm), (xs(r1), r1)).close()
            .revolve(360, (0, 0, 0), (1, 0, 0)))
    return mirror_x(seat) if side < 0 else seat


def make_sleeve(side):
    s = ring_x(X_SEAT_OUT, X_SLEEVE_OUT, SEAT_ID / 2, SEAT_OD / 2 - 0.05)
    return mirror_x(s) if side < 0 else s


def make_spring(side):
    t = 1.2
    x0, x1 = X_SLEEVE_OUT, X_SPRING_OUT
    pts = [(x0, SEAT_ID / 2), (x0 + t, SEAT_ID / 2),
           (x1, SEAT_OD / 2 - 0.3), (x1 - t, SEAT_OD / 2 - 0.3)]
    s = revolve_x(pts)
    return mirror_x(s) if side < 0 else s


def make_washer(side):
    s = ring_x(X_SPRING_OUT, X_WASHER_OUT, SEAT_ID / 2, SEAT_OD / 2 - 0.05)
    return mirror_x(s) if side < 0 else s


def make_stem():
    tang = cq.Workplane("XY").box(TANG_L, TANG_T, Z_COLLAR[0] - SLOT_BOTTOM - 0.5).translate(
        (0, 0, (Z_COLLAR[0] + SLOT_BOTTOM + 0.5) / 2))
    collar = cq.Workplane("XY").workplane(offset=Z_COLLAR[0]).circle(COLLAR_D / 2).extrude(
        Z_COLLAR[1] - Z_COLLAR[0])
    shaft = cq.Workplane("XY").workplane(offset=Z_COLLAR[1]).circle(STEM_D / 2).extrude(
        Z_SQ[0] - Z_COLLAR[1])
    square = (cq.Workplane("XY").workplane(offset=Z_SQ[0]).rect(SQ, SQ).extrude(Z_SQ[1] - Z_SQ[0])
              .edges("|Z").chamfer(0.8))
    thread = cq.Workplane("XY").workplane(offset=Z_SQ[1]).circle(THREAD_D / 2).extrude(
        Z_THREAD_TOP - Z_SQ[1]).faces(">Z").chamfer(1.0)
    stem = tang.union(collar).union(shaft).union(square).union(thread)
    for z in ORING_Z:   # канавки под кольца 10
        g = (cq.Workplane("XY").workplane(offset=z - 1.3).circle(STEM_D / 2 + 1)
             .circle(ORING_D_IN / 2 + 0.1).extrude(2.6))
        stem = stem.cut(g)
    return stem


def make_gasket():
    return (cq.Workplane("XY").workplane(offset=Z_GASKET[0]).circle(COLLAR_D / 2)
            .circle(STEM_D / 2 + 0.1).extrude(Z_GASKET[1] - Z_GASKET[0]))


def make_oring(z):
    rc = ORING_D_IN / 2 + ORING_W / 2
    return cq.Workplane(obj=cq.Solid.makeTorus(rc, ORING_W / 2, cq.Vector(0, 0, z),
                                               cq.Vector(0, 0, 1)))


def make_pin():
    # Штифт 4×12 ГОСТ 3128-70 — упор ограничения поворота рукоятки
    return cq.Workplane(obj=cq.Solid.makeCylinder(
        PIN_D / 2, PIN_L, cq.Vector(0, -NECK_D / 2 + 5, PIN_Z), cq.Vector(0, -1, 0)))


def make_handle():
    z_hub = (HUB_Z[0] + HUB_Z[1]) / 2
    z_bar = H_HANDLE - BAR_T / 2
    x_end = L_HANDLE - L / 2
    hub = (cq.Workplane("XY").workplane(offset=HUB_Z[0]).center(5, 0)
           .rect(40, 26).extrude(HUB_Z[1] - HUB_Z[0]).edges("|Z").fillet(6))
    hub = hub.cut(cq.Workplane("XY").workplane(offset=HUB_Z[0] - 1).rect(SQ + 0.2, SQ + 0.2)
                  .extrude(10))
    x0, x1 = 25.0, 60.0
    ln = math.hypot(x1 - x0, z_bar - z_hub)
    ang = math.degrees(math.atan2(z_bar - z_hub, x1 - x0))
    slope = (cq.Workplane("XY").box(ln + BAR_T, BAR_W, BAR_T)
             .rotate((0, 0, 0), (0, 1, 0), -ang)
             .translate(((x0 + x1) / 2, 0, (z_hub + z_bar) / 2)))
    bar = (cq.Workplane("XY").box(x_end - x1, BAR_W, BAR_T)
           .edges("|Z and >X").fillet(BAR_W / 2 - 0.01)
           .translate(((x1 + x_end) / 2, 0, z_bar)))
    handle = hub.union(slope).union(bar)
    # обрезка «выступов» наклонного участка над и под полосой
    handle = handle.cut(cq.Workplane("XY").box(400, 100, 50).translate((0, 0, H_HANDLE + 25)))
    return handle


def make_nut():
    e = NUT_S / math.cos(math.pi / 6)
    nut = (cq.Workplane("XY").workplane(offset=HUB_Z[1]).polygon(6, e).extrude(NUT_M)
           .faces(">Z").edges().chamfer(0.8)
           .faces("<Z").workplane().hole(THREAD_D))
    return nut


def make_weld_flange(side):
    """Шов №1: угловой, катет 4, патрубок — фланец (тыльная сторона)."""
    k = 4.0
    pts = [(X_FL_BACK, P_OD / 2), (X_FL_BACK - k, P_OD / 2), (X_FL_BACK, P_OD / 2 + k)]
    w = revolve_x(pts)
    return mirror_x(w) if side < 0 else w


def make_weld_body(side):
    """Шов №2: корпус — патрубок, катет 4."""
    k = 4.0
    r0 = P_OD / 2
    pts = [(B_X_END, r0), (B_X_END + k, r0), (B_X_END, r0 + k)]
    w = revolve_x(pts)
    return mirror_x(w) if side < 0 else w


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------
STEEL = cq.Color(0.62, 0.64, 0.68)
STEEL_DARK = cq.Color(0.45, 0.47, 0.50)
BODY = cq.Color(0.16, 0.36, 0.62)
FLANGE = cq.Color(0.20, 0.42, 0.70)
PTFE = cq.Color(0.95, 0.95, 0.92)
RUBBER = cq.Color(0.08, 0.08, 0.08)
HANDLE = cq.Color(0.85, 0.15, 0.12)
WELD = cq.Color(0.25, 0.20, 0.18)
CHROME = cq.Color(0.82, 0.84, 0.86)

PARTS = [
    # (обозначение, наименование, функция, цвет)
    ("01_probka_sharovaya", "1 Пробка шаровая", make_ball, CHROME),
    ("02_shtok", "2 Шток", make_stem, STEEL),
    ("03_korpus", "3 Корпус", make_body, BODY),
    ("04_patrubok_L", "4 Патрубок (лев.)", lambda: make_pipe(-1), STEEL_DARK),
    ("04_patrubok_R", "4 Патрубок (прав.)", lambda: make_pipe(1), STEEL_DARK),
    ("05_koltso_upl_shara_L", "5 Кольцо уплотнительное шара (лев.)", lambda: make_seat(-1), PTFE),
    ("05_koltso_upl_shara_R", "5 Кольцо уплотнительное шара (прав.)", lambda: make_seat(1), PTFE),
    ("06_vtulka_L", "6 Втулка крепёжная (лев.)", lambda: make_sleeve(-1), STEEL),
    ("06_vtulka_R", "6 Втулка крепёжная (прав.)", lambda: make_sleeve(1), STEEL),
    ("07_pruzhina_L", "7 Пружина тарельчатая (лев.)", lambda: make_spring(-1), STEEL_DARK),
    ("07_pruzhina_R", "7 Пружина тарельчатая (прав.)", lambda: make_spring(1), STEEL_DARK),
    ("08_shaiba_L", "8 Шайба упорная (лев.)", lambda: make_washer(-1), STEEL),
    ("08_shaiba_R", "8 Шайба упорная (прав.)", lambda: make_washer(1), STEEL),
    ("09_prokladka_shtoka", "9 Прокладка штока", make_gasket, PTFE),
    ("10_koltso_shtoka_1", "10 Кольцо 013-016-19 ГОСТ 9833-73", lambda: make_oring(ORING_Z[0]), RUBBER),
    ("10_koltso_shtoka_2", "10 Кольцо 013-016-19 ГОСТ 9833-73", lambda: make_oring(ORING_Z[1]), RUBBER),
    ("11_shtift", "11 Штифт 4×12 ГОСТ 3128-70", make_pin, STEEL),
    ("12_flanets_L", "12 Фланец 01-50-40-B ГОСТ 33259-2015 (лев.)", lambda: make_flange(-1), FLANGE),
    ("12_flanets_R", "12 Фланец 01-50-40-B ГОСТ 33259-2015 (прав.)", lambda: make_flange(1), FLANGE),
    ("13_rukoyatka", "13 Рукоятка", make_handle, HANDLE),
    ("14_gaika", "14 Гайка M10 ГОСТ 5915-70", make_nut, STEEL),
    ("shov_1_L", "Шов №1 ГОСТ 14771-76 (лев.)", lambda: make_weld_flange(-1), WELD),
    ("shov_1_R", "Шов №1 ГОСТ 14771-76 (прав.)", lambda: make_weld_flange(1), WELD),
    ("shov_2_L", "Шов №2 ГОСТ 14771-76 (лев.)", lambda: make_weld_body(-1), WELD),
    ("shov_2_R", "Шов №2 ГОСТ 14771-76 (прав.)", lambda: make_weld_body(1), WELD),
]


def build():
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="Kran_sharovoy_DN50_PN40")
    solids = {}
    for key, title, fn, color in PARTS:
        wp = fn()
        solids[key] = wp
        assy.add(wp, name=key, color=color)
        cq.exporters.export(wp, os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(wp, os.path.join(OUT, "parts_stl", key + ".stl"),
                            tolerance=0.05, angularTolerance=0.1)
    assy.save(os.path.join(OUT, "kran_DN50_PN40_sborka.step"))
    assy.save(os.path.join(OUT, "kran_DN50_PN40_sborka.glb"), tolerance=0.05,
              angularTolerance=0.1)
    return solids


def check(solids):
    """Проверка габаритов и взаимных пересечений деталей."""
    all_bb = None
    for key, wp in solids.items():
        bb = wp.val().BoundingBox()
        all_bb = bb if all_bb is None else all_bb.add(bb)
        assert wp.val().isValid(), key
    print("Габарит сборки: X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f" % (
        all_bb.xmin, all_bb.xmax, all_bb.ymin, all_bb.ymax, all_bb.zmin, all_bb.zmax))
    keys = list(solids)
    bad = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = solids[keys[i]].val(), solids[keys[j]].val()
            ba, bb_ = a.BoundingBox(), b.BoundingBox()
            if (ba.xmin > bb_.xmax or bb_.xmin > ba.xmax or ba.ymin > bb_.ymax
                    or bb_.ymin > ba.ymax or ba.zmin > bb_.zmax or bb_.zmin > ba.zmax):
                continue
            v = a.intersect(b).Volume()
            if v > 0.5:
                bad.append((keys[i], keys[j], v))
    for k1, k2, v in bad:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.2f мм3" % (k1, k2, v))
    for key, wp in solids.items():
        print("%-26s V = %9.0f мм3  m(сталь) = %.3f кг" % (key, wp.val().Volume(),
                                                          wp.val().Volume() * 7.85e-6))
    return bad


if __name__ == "__main__":
    s = build()
    check(s)
