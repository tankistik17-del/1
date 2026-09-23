# -*- coding: utf-8 -*-
"""
3D-модель листа 8 «Общий вид сварочного оборудования» (М 1:5) дипломного проекта
«Технология сборки-сварки корпуса задвижки трубопровода».

Состав (спецификация на поле листа):
  1 Газовый баллон с редуктором (2 шт.)      — баллон 40 л ГОСТ 949-73, вентиль, редуктор с 2 манометрами
  2 Источник питания ВС-300Б                 — шкаф на колёсах, элементы лицевой панели, рым-проушины
  3 Механизм подачи проволоки ПДГ-312-5      — корпус на роликах, кассета с проволокой, разъёмы
  4 Горелка сварочная на 300 А               — рукоятка, курок, изогнутая шейка, сопло, кабель-шланг
  5 Свариваемое изделие                      — корпус задвижки (импорт модели ../korpus/build.py)
  6 Рабочий стол сварщика                    — 601×(600)×800
  7 Воздухоприёмник (зонт)
  8 Шибер
  9 Воздуховод
  + газовые рукава и сварочные/управляющие кабели по трассам чертежа (без номера позиции).

Размеры: на листе проставлены размеры в мм БУМАГИ (М 1:5), реальный размер = значение × 5:
  254,21→1271,05 (высота баллона с вентилем); 40→200 (башмак); 148→740 (ВС-300Б до верха
  проушин); 84→420 (ВС-300Б по колёсам); 50→250 (ПДГ ширина); 90→450 (ПДГ до верха ручки);
  160→800 (высота стола); 120,22→601,1 (ширина стола); 84,19→420,95 (наклонная кромка зонта).
Неразмеренная геометрия снята с векторов PDF (1 pt = 0,35278 мм бумаги = 1,7639 мм натуры).
Вертикальные размеры векторов на листе в среднем на 0,53 % меньше проставленных (795,8 против
800 у стола, 736,1 против 740 у ВС-300Б, 447,8 против 450 у ПДГ) — все отметки Z, снятые
с векторов, умножены на ZS = 800/795,8; баллон — на ZC = 1271,05/1268,2 (его собственный размер).

Система координат: Z вверх, пол Z = 0; X вправо как на листе, начало X — ось левого баллона;
Y — в глубину (от наблюдателя, вид спереди листа смотрит вдоль +Y); лицевые панели — в сторону −Y.
Запуск: python3 build.py → out/*.step, out/*.glb, out/parts_step, out/parts_stl, out/spec.json
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
KORPUS_DIR = os.path.join(os.path.dirname(HERE), "korpus")

# ---------------------------------------------------------------------------
# Масштабы и привязка (все координаты X ниже — «чертёжные» в мм натуры от левого поля листа,
# пересчитываются функцией X(); Z — функцией Z() / ZCYL())
# ---------------------------------------------------------------------------
SCALE = 5.0
X0 = 641.4                      # ось левого баллона (середина 557,1…725,6) → X = 0
ZS = 800.0 / 795.8              # 160×5 = 800 (стол) / 795,8 по векторам
ZC = 1271.05 / 1268.2           # 254,21×5 = 1271,05 / 1268,2 по векторам (баллон)


def X(x):
    return x - X0


def Z(z):
    return z * ZS


def ZCYL(z):
    return z * ZC


# ---------------------------------------------------------------------------
# Поз.1 Баллон 40 л ГОСТ 949-73 с вентилем и редуктором
# ---------------------------------------------------------------------------
CYL_D = 219.0                   # ГОСТ 949-73, баллон 40 л: наружный Ø219 (на листе баллон
#                                 изображён условно Ø168,5 — см. NOTES)
CYL_R = CYL_D / 2
CYL_PITCH = 292.3               # шаг осей баллонов (933,7 − 641,4 по векторам)
CYL_X = [0.0, CYL_PITCH]        # оси баллонов
CYL_Z_BOT = 25.0                # низ выпуклого днища внутри башмака (допущение)
CYL_Z_TOP = ZCYL(1201.8)        # верх горловины (вектор 1201,8)
CYL_TOP_FLAT = 50.0             # площадка под фланец вентиля Ø48
# верхнее днище — полусфера R = CYL_R (на листе — полуокружность, h = R); центр сферы опущен так,
# чтобы площадка Ø50 была на CYL_Z_TOP; общая высота 1271,05 сохранена, обечайка укорочена
CYL_Z_HEAD_C = CYL_Z_TOP - math.sqrt(CYL_R ** 2 - (CYL_TOP_FLAT / 2) ** 2)
CYL_Z_SHELL = CYL_Z_HEAD_C      # переход обечайки в днище
SHOE_H = ZCYL(98.6)             # высота башмака (вектор 98,6)
SHOE_D = 235.0                  # башмак: наружный Ø (размер 40 листа = 200 мм меньше ГОСТ-баллона
#                                 Ø219 — принят Ø235, см. NOTES)
SHOE_ID = CYL_D + 0.2           # посадка башмака с зазором 0,1 на сторону
SHOE_LEDGE_ID = 120.0           # отверстие в опорной полке башмака (допущение)
# вентиль (по векторам, мм натуры относительно оси баллона)
V_FL_D, V_FL_Z = 48.0, (1201.8, 1206.4)     # опорный фланец 617,6…665,5
V_BODY_W, V_BODY_Z = 29.7, (1206.4, 1256.4)  # корпус вентиля 626,5…656,2
V_WH_D, V_WH_Z = 48.0, (1256.4, 1268.2)     # маховик 617,6…665,5, верх = 254,21×5
V_OUT_X = (656.2 - 641.4, 673.5 - 641.4)    # штуцер вентиля Ø12,7 (1226,7…1239,4)
V_OUT_D = 12.7
V_OUTZ = 1233.05
# редуктор
R_NUT_X, R_NUT_D = (673.5 - 641.4, 684.5 - 641.4), 30.0   # накидная гайка 1217,9…1247,9
R_IN_X = (684.5 - 641.4, 691.7 - 641.4)                   # входной штуцер Ø12,7
R_BODY_C, R_BODY_D = (719.8 - 641.4, 1233.1), 56.2        # корпус Ø56 (691,7…747,6 / 1204,3…1261,5)
R_BODY_T = 40.0                                           # толщина корпуса по Y (допущение)
R_OUT_X = (747.6 - 641.4, 756.5 - 641.4)                  # выходной ниппель Ø12,7
GAUGE_D, GAUGE_T = 29.6, 18.0                             # манометры Ø29,6 (1269,9…1300,0)
GAUGE_C = [(698.3 - 641.4, 1285.0), (743.8 - 641.4, 1285.0)]
GAUGE_NECK_D = 7.0                                        # штуцеры манометров (наклонные, к центрам)

# ---------------------------------------------------------------------------
# Поз.2 Источник питания ВС-300Б
# ---------------------------------------------------------------------------
PS_X = (1290.3, 1575.6)         # шкаф (вектор, ширина 285)
PS_XC = (PS_X[0] + PS_X[1]) / 2
PS_Z = (Z(96.9), Z(671.8))      # низ/верх шкафа
PS_D = 520.0                    # глубина шкафа (допущение, на листе нет)
PS_Y = (-PS_D / 2, PS_D / 2)
PS_H_TOTAL = 740.0              # 148×5 — до верха рым-проушин
PS_W_WHEELS = 420.0             # 84×5 — по наружным плоскостям больших колёс
LUG_X = [(1315.3, 1364.4), (1501.6, 1550.7)]   # проушины (вектор), отверстие Ø28
LUG_T, LUG_HOLE_D, LUG_HOLE_Z = 10.0, 28.0, Z(708.0)
BW_D, BW_W = Z(147.2), 51.7     # большие колёса (задние): Ø148, ширина 51,7
BW_XC = [PS_XC - PS_W_WHEELS / 2 + BW_W / 2, PS_XC + PS_W_WHEELS / 2 - BW_W / 2]
BW_Y = 170.0
AXLE_D = 20.0
CW_D, CW_W = Z(79.9), 50.0      # ролики (передние) Ø80, ширина 1306…1357 по векторам
CW_XC = [1331.6, 2 * PS_XC - 1331.6]
CW_Y = -170.0
FORK_T = 9.5                    # щёки вилки 1296,2…1306 / 1357,2…1366,5
FORK_Z = (Z(38.5), PS_Z[0])
CW_AXLE_D = 12.0
FRONT_Y = PS_Y[0]               # лицевая панель

# ---------------------------------------------------------------------------
# Поз.3 ПДГ-312-5
# ---------------------------------------------------------------------------
PDG_X = (1816.9, 2066.9)        # 50×5 = 250
PDG_Z = (Z(68.1), Z(390.7))
PDG_D = 450.0                   # глубина (допущение)
PDG_Y = (-PDG_D / 2, PDG_D / 2)
PDG_WALL = 2.0
PDG_H_TOTAL = 450.0             # 90×5 — до верха ручки
PDG_DIV_Z = Z(240.0)            # линия разъёма кассетного отсека
HANDLE_X_BOT = (1924.9, 1959.2)
HANDLE_X_TOP = (1930.4, 1953.7)
HANDLE_L = 160.0                # длина ручки по Y (допущение)
CASTOR_XC = [(1830.5 + 1855.9) / 2, (2027.8 + 2053.6) / 2]
CASTOR_WD, CASTOR_WW = Z(48.2), 25.4          # колесо Ø48, ширина 25,4
CASTOR_FORK = 35.2                            # вилка 1825,8…1861,0
CASTOR_Y = [-185.0, 185.0]
SPOOL_D, SPOOL_W = 200.0, 55.0  # кассета проволоки Ø200 (ГОСТ 2246-70, К200) — внутри корпуса
SPOOL_C = (1942.0, 60.0, 230.0)
EURO_C, EURO_D = (1999.6, Z(136.5)), 38.0     # евроразъём горелки
PDG_SOCKETS = [(1896.7, Z(347.3), 25.0), (1987.5, Z(347.3), 25.0)]
PDG_SMALL = [(1843.0, Z(350.0), 10.0), (2036.4, Z(350.5), 10.0),
             (1838.4, Z(96.5), 10.0), (1873.3, Z(96.5), 10.0)]

# ---------------------------------------------------------------------------
# Поз.4 Горелка на 300 А (Z всех точек горелки сдвинуты на dz = 885,5·(ZS−1))
# ---------------------------------------------------------------------------
TZ = 885.5 * (ZS - 1)
TH_X = (3090.8, 3285.9)         # рукоятка Ø36,4 (867,3…903,7)
TH_D, TH_ZC = 36.4, 885.5 + TZ
TN_X = (3285.9, 3353.2)         # шейка Ø22,8 (877,1…899,9)
TN_D, TN_ZC = 22.8, 888.5 + TZ
TB_R, TB_ANG = 50.0, 48.0       # гиб шейки R50 на 48° (по векторам сопла)
NOZ_D, NOZ_L = 18.0, 46.0       # сопло Ø18 × 46
TRIG = [(3207.6, 867.2), (3214.4, 860.1), (3256.7, 857.6), (3260.5, 867.2)]
HOSE_T_D = 32.0                 # кабель-шланг Ø32 (871,6…903,7)

# ---------------------------------------------------------------------------
# Поз.5 изделие, поз.6 стол
# ---------------------------------------------------------------------------
TABLE_X = (3305.8, 3305.8 + 601.1)   # 120,22×5
TABLE_H = 800.0                      # 160×5
TABLE_D = 600.0                      # глубина (допущение)
TABLE_TOP_T = 800.0 - Z(745.8)       # столешница 50
TABLE_LEG = 50.8                     # опоры 3305,8…3356,6
TABLE_LEG_H = Z(97.7)
PROD_XC = 3491.0 + 10.0              # ось изделия (середина 3415…3567) +10 — зазор до сопла

# ---------------------------------------------------------------------------
# Поз.7…9 вытяжка
# ---------------------------------------------------------------------------
HOOD_P2 = (3905.3, Z(1226.7))        # правая нижняя точка кромки раструба (вектор)
_p1 = (3520.0, Z(1398.2))            # левая нижняя точка (вектор); длина кромки приводится к 84,19×5
_k = 84.19 * SCALE / math.hypot(_p1[0] - HOOD_P2[0], _p1[1] - HOOD_P2[1])
HOOD_P1 = (HOOD_P2[0] + (_p1[0] - HOOD_P2[0]) * _k, HOOD_P2[1] + (_p1[1] - HOOD_P2[1]) * _k)
HOOD_TOP_Z = Z(1693.7)
HOOD_W = 500.0                       # ширина раструба по Y (допущение)
HOOD_T = 1.5                         # лист (допущение)
DUCT_D = 143.1                       # воздуховод/шибер 3762,2…3905,3
DUCT_XC = (3762.2 + 3905.3) / 2
DUCT_T = 1.5
SHIB_Z = (HOOD_TOP_Z, Z(1744.5))
DUCT_Z_TOP = Z(2011.6)               # линия обрыва

# ---------------------------------------------------------------------------
# Рукава и кабели (центральные линии сняты с векторов: середина между контурами)
# ---------------------------------------------------------------------------
GAS_HOSE_D = 14.0      # рукав III-6,3 ГОСТ 9356-75 (Ø наружн. ≈ 14; по чертежу 13,9…14,5)
FLOOR_CABLE_D = 12.6   # обратный провод (по чертежу 0…12,6 над полом)

C_CYL = [cq.Color(0.55, 0.57, 0.60), cq.Color(0.10, 0.10, 0.11)]   # аргон — серый, CO2 — чёрный
C_BRASS = cq.Color(0.80, 0.65, 0.30)
C_GAUGE = cq.Color(0.90, 0.90, 0.88)
C_SHOE = cq.Color(0.25, 0.25, 0.27)
C_PS = cq.Color(0.20, 0.42, 0.62)
C_PDG = cq.Color(0.85, 0.55, 0.15)
C_BLACK = cq.Color(0.08, 0.08, 0.08)
C_RUBBER = cq.Color(0.12, 0.12, 0.12)
C_STEEL = cq.Color(0.62, 0.64, 0.66)
C_RED = cq.Color(0.75, 0.15, 0.12)
C_BLUE_HOSE = cq.Color(0.15, 0.25, 0.70)
C_TABLE = cq.Color(0.35, 0.40, 0.35)
C_TOP = cq.Color(0.45, 0.45, 0.47)
C_HOOD = cq.Color(0.72, 0.74, 0.76)
C_WIRE = cq.Color(0.72, 0.45, 0.20)

NODES = []   # (key, pos, name_ru, cq.Shape, color, standard, note)


def add(key, pos, name, shape, color, std="", note=""):
    if isinstance(shape, cq.Workplane):
        shape = shape.val()
    shape = shape.clean() if hasattr(shape, "clean") else shape
    assert shape.isValid(), key
    assert shape.Volume() > 1.0, key
    NODES.append((key, pos, name, shape, color, std, note))


# ---------------------------------------------------------------------------
# Геометрические помощники
# ---------------------------------------------------------------------------
V = cq.Vector


def cyl(d, h, pnt, dirn):
    return cq.Solid.makeCylinder(d / 2, h, V(*pnt), V(*dirn))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def fuse(*shapes):
    s = shapes[0]
    for o in shapes[1:]:
        s = s.fuse(o)
    return s.clean()


def tube(pts, d, t0=None, t1=None, R=None):
    """Рукав/кабель Ø d: ломаная через 3D-точки трассы, углы скруглены дугами R (≈3d),
    по ней протягивается окружность — получаются точные цилиндры и торы (лёгкая сетка GLB).
    t0/t1 — направления выхода/входа: добавляется прямой участок 1,5d, перпендикулярный стенке."""
    P = [V(*q) for q in pts]
    R = R or 3.0 * d
    L = 1.5 * d
    if t0 is not None:
        P = [P[0]] + [q for q in P[1:] if (q - P[0]).Length > 2.2 * L]
    if t1 is not None:
        P = [q for q in P[:-1] if (q - P[-1]).Length > 2.2 * L] + [P[-1]]
    if t0 is not None:        # прямой участок, перпендикулярный присоединительной плоскости
        P.insert(1, P[0] + V(*t0).normalized() * L)
    if t1 is not None:
        P.insert(len(P) - 1, P[-1] - V(*t1).normalized() * L)
    # убрать почти коллинеарные точки (изломы < 4°) — иначе протяжка даёт вырожденные торы
    changed = True
    while changed and len(P) > 2:
        changed = False
        for i in range(1, len(P) - 1):
            a, b = (P[i] - P[i - 1]).normalized(), (P[i + 1] - P[i]).normalized()
            if math.acos(max(-1.0, min(1.0, a.dot(b)))) < math.radians(4.0) and not (
                    (t0 is not None and i == 1) or (t1 is not None and i == len(P) - 2)):
                del P[i]
                changed = True
                break
    edges, cur = [], P[0]
    for i in range(1, len(P) - 1):
        a, b = P[i] - P[i - 1], P[i + 1] - P[i]
        la, lb = a.Length, b.Length
        a, b = a.normalized(), b.normalized()
        th = math.acos(max(-1.0, min(1.0, a.dot(b))))
        if th < 0.01:
            continue
        t = min(R * math.tan(th / 2), 0.45 * la, 0.45 * lb)
        p1, p2 = P[i] - a * t, P[i] + b * t
        r = t / math.tan(th / 2)
        if r < 2.0 * d:
            print("  ! tube Ø%.0f: радиус изгиба %.1f < 2d в точке (%.0f, %.0f, %.0f)" % (d, r, P[i].x, P[i].y, P[i].z))
        if r < 0.55 * d:        # слишком крутой изгиб — острый угол (переход «right» при протяжке)
            edges.append(cq.Edge.makeLine(cur, P[i]))
            cur = P[i]
            continue
        c = P[i] + (b - a).normalized() * (r / math.cos(th / 2))
        m = c + (P[i] - c).normalized() * r
        if (p1 - cur).Length > 1e-6:
            edges.append(cq.Edge.makeLine(cur, p1))
        edges.append(cq.Edge.makeThreePointArc(p1, m, p2))
        cur = p2
    edges.append(cq.Edge.makeLine(cur, P[-1]))
    path = cq.Wire.assembleEdges(edges)
    prof = cq.Wire.makeCircle(d / 2, P[0], (P[1] - P[0]).normalized())
    s = cq.Solid.sweep(prof, [], path, True, False, transitionMode="right")
    return cq.Solid(s.wrapped) if not isinstance(s, cq.Solid) else s


def route(pts2d, y_of, zf=Z):
    """Точки трассы (x, z) чертежа + закон y(t), t — доля длины по трассе."""
    L = [0.0]
    for a, b in zip(pts2d[:-1], pts2d[1:]):
        L.append(L[-1] + math.dist(a, b))
    return [(X(x), y_of(l / L[-1]), zf(z)) for (x, z), l in zip(pts2d, L)]


def lin(a, b):
    return lambda t: a + (b - a) * t


def wheel(d, w, xc, y, zc, bore, fillet):
    """Колесо с осью вдоль X: шина со скруглёнными кромками и отверстием под ось."""
    w_ = cq.Workplane("YZ").workplane(offset=xc - w / 2).center(y, zc).circle(d / 2).extrude(w)
    w_ = w_.edges().fillet(fillet)
    w_ = w_.cut(cq.Workplane("YZ").workplane(offset=xc - w).center(y, zc).circle(bore / 2).extrude(2 * w))
    return w_.val()


# ---------------------------------------------------------------------------
# Поз.1
# ---------------------------------------------------------------------------
def make_cylinder_body(xc):
    """Баллон Ø219: плоское опорное днище со скруглением R30 (стоит на полке башмака),
    цилиндрическая обечайка, полусферическое верхнее днище R = 109,5 (истинная дуга),
    срезанное площадкой Ø50 под фланец вентиля на отметке CYL_Z_TOP."""
    r, rb = CYL_R, 30.0
    zs, a = CYL_Z_HEAD_C, CYL_TOP_FLAT / 2
    ang = math.asin(a / r)                      # угол площадки от оси
    mid = math.radians(45.0)
    wp = (cq.Workplane("XZ").moveTo(0, CYL_Z_BOT).lineTo(r - rb, CYL_Z_BOT)
          .threePointArc((r - rb + rb * math.sin(math.pi / 4), CYL_Z_BOT + rb - rb * math.cos(math.pi / 4)),
                         (r, CYL_Z_BOT + rb))
          .lineTo(r, zs)
          .threePointArc((r * math.sin(mid), zs + r * math.cos(mid)), (a, zs + r * math.cos(ang)))
          .lineTo(0, CYL_Z_TOP).close())
    s = wp.revolve(360, (0, 0, 0), (0, 1, 0)).val()
    assert s.isValid()
    return s.translate(V(xc, 0, 0))


def make_shoe(xc):
    s = (cq.Workplane("XY").circle(SHOE_D / 2).circle(SHOE_ID / 2).extrude(SHOE_H)).val()
    # опорная полка (дно) башмака: кольцо Ø(SHOE_ID)/Ø120 высотой CYL_Z_BOT — на её верх
    # плоскостью опирается днище баллона (контакт по плоскости Z = CYL_Z_BOT)
    ledge = (cq.Workplane("XY").circle(SHOE_ID / 2 + 0.5).circle(SHOE_LEDGE_ID / 2).extrude(CYL_Z_BOT)).val()
    s = s.fuse(ledge).clean()
    assert s.isValid()
    return s.translate(V(xc, 0, 0))


def make_valve(xc):
    z = ZCYL
    fl = cyl(V_FL_D, z(V_FL_Z[1]) - z(V_FL_Z[0]), (xc, 0, z(V_FL_Z[0])), (0, 0, 1))
    body = box(xc - V_BODY_W / 2, xc + V_BODY_W / 2, -V_BODY_W / 2, V_BODY_W / 2, z(V_BODY_Z[0]), z(V_BODY_Z[1]))
    wh = cyl(V_WH_D, 1271.05 - z(V_WH_Z[0]), (xc, 0, z(V_WH_Z[0])), (0, 0, 1))
    out = cyl(V_OUT_D, V_OUT_X[1] - (V_BODY_W / 2 - 1), (xc + V_BODY_W / 2 - 1, 0, z(V_OUTZ)), (1, 0, 0))
    return fuse(fl, body, wh, out)


def make_regulator(xc):
    z = ZCYL
    zc = z(R_BODY_C[1])
    nut = cq.Workplane("YZ").workplane(offset=xc + R_NUT_X[0] + 0.05).center(0, zc).polygon(6, R_NUT_D / math.cos(math.pi / 6)).extrude(R_NUT_X[1] - R_NUT_X[0] - 0.05).val()
    stub = cyl(V_OUT_D, R_IN_X[1] - R_IN_X[0] + 4, (xc + R_IN_X[0], 0, zc), (1, 0, 0))
    bodyc = cyl(R_BODY_D, R_BODY_T, (xc + R_BODY_C[0], -R_BODY_T / 2, zc), (0, 1, 0))
    outn = cyl(V_OUT_D, R_OUT_X[1] - R_OUT_X[0] + 4, (xc + R_OUT_X[0] - 4, 0, zc), (1, 0, 0))
    return fuse(nut, stub, bodyc, outn)


def make_gauge(xc, i):
    gx, gz = GAUGE_C[i]
    g = cyl(GAUGE_D, GAUGE_T, (xc + gx, -GAUGE_T / 2, ZCYL(gz)), (0, 1, 0))
    glass = cyl(GAUGE_D - 5, 1.0, (xc + gx, -GAUGE_T / 2 - 1.0, ZCYL(gz)), (0, 1, 0))
    # штуцер манометра: от поверхности корпуса редуктора (зазор 0,05) к центру манометра
    c = V(xc + R_BODY_C[0], 0, ZCYL(R_BODY_C[1]))
    gc = V(xc + gx, 0, ZCYL(gz))
    d = (gc - c).normalized()
    pa = c + d * (R_BODY_D / 2 + 0.05)
    neck = cq.Solid.makeCylinder(GAUGE_NECK_D / 2, (gc - pa).Length, pa, d)
    return fuse(g, glass, neck)


def build_pos1():
    for i, xc in enumerate(CYL_X):
        gas = ["аргон", "CO2"][i]
        k = "poz1_ballon_%d" % (i + 1)
        add(k + "_korpus", "1", "Баллон 40 л (%s)" % gas, make_cylinder_body(xc), C_CYL[i],
            "ГОСТ 949-73 (40 л, Ø219)", "окраска по ГОСТ 949-73: аргон — серый, углекислота — чёрный")
        add(k + "_bashmak", "1", "Башмак баллона", make_shoe(xc), C_SHOE, "ГОСТ 949-73")
        add(k + "_ventil", "1", "Вентиль баллонный", make_valve(xc), C_BRASS, "",
            "габариты по векторам листа")
        add(k + "_reduktor", "1", "Редуктор баллонный", make_regulator(xc), C_BRASS, "",
            "корпус Ø56, накидная гайка S30, по векторам листа")
        for j in range(2):
            add(k + "_manometr_%d" % (j + 1), "1", "Манометр редуктора", make_gauge(xc, j), C_GAUGE,
                "", "Ø30 по векторам листа")


# ---------------------------------------------------------------------------
# Поз.2 ВС-300Б
# ---------------------------------------------------------------------------
def fx(x0, x1, z0, z1, t, y=None):
    """Выступающий элемент лицевой панели (прямоугольник x0..x1 × z0..z1, выступ t)."""
    y = FRONT_Y if y is None else y
    return box(X(x0), X(x1), y - t, y, Z(z0), Z(z1))


def fc(xc, zc, d, t, y=None):
    y = FRONT_Y if y is None else y
    return cyl(d, t, (X(xc), y - t, Z(zc)), (0, 1, 0))


def build_pos2():
    k = "poz2_istochnik"
    body = box(X(PS_X[0]), X(PS_X[1]), PS_Y[0], PS_Y[1], PS_Z[0], PS_Z[1])
    add(k + "_korpus", "2", "Источник питания ВС-300Б — шкаф", body, C_PS, "ТУ на ВС-300Б",
        "285 (ширина шкафа по векторам) × 520 (глубина — допущение) × 575")
    # рым-проушины
    for i, (a, b) in enumerate(LUG_X):
        lug = (cq.Workplane("XZ")
               .polyline([(X(a), PS_Z[1]), (X(b), PS_Z[1]), (X(b), PS_H_TOTAL - 8), (X(b) - 8, PS_H_TOTAL),
                          (X(a) + 8, PS_H_TOTAL), (X(a), PS_H_TOTAL - 8)]).close()
               .extrude(LUG_T / 2, both=True))
        lug = lug.cut(cq.Workplane("XZ").center((X(a) + X(b)) / 2, LUG_HOLE_Z)
                      .circle(LUG_HOLE_D / 2).extrude(LUG_T, both=True))
        add(k + "_proushina_%d" % (i + 1), "2", "Рым-проушина ВС-300Б", lug, C_PS, "",
            "верх = 148×5 = 740")
    # элементы лицевой панели
    parts = [
        fx(1369.5, 1496.5, 654.0, 666.3, 6),     # ручка-планка у верха
        fx(1384.3, 1460.1, 491.0, 591.3, 3),     # окно прибора
        fx(1314.9, 1365.3, 526.1, 552.4, 3),     # табличка
        fx(1314.9, 1365.3, 565.1, 591.3, 3),     # табличка
        fx(1520.6, 1570.6, 558.3, 608.3, 8),     # автомат (корпус)
        fx(1327.6, 1378.0, 235.7, 262.0, 12),    # клеммная колодка
        fx(1509.6, 1549.4, 439.3, 479.1, 10),    # розетка управления (фланец)
    ]
    panel = fuse(*parts)
    lever = box(X(1531.6), X(1561.7), FRONT_Y - 8 - 12, FRONT_Y - 8, Z(608.3), Z(617.6))
    lever = lever.fuse(box(X(1541.6), X(1551.7), FRONT_Y - 8 - 12, FRONT_Y - 8, Z(582.9), Z(608.3)))
    panel = panel.fuse(lever)
    sock = fc(1529.5, 459.2, 22.0, 10.0, FRONT_Y - 10)
    panel = panel.fuse(sock)
    for (xc, zc, horiz) in [(1344.0, 358.8, True), (1529.5, 358.8, False)]:
        kn = fc(xc, zc, 32.0, 10.0)
        bar = (fx(xc - 15.8, xc + 15.8, zc - 5.7, zc + 5.7, 8, FRONT_Y - 10) if horiz
               else fx(xc - 5.5, xc + 5.5, zc - 15.7, zc + 15.7, 8, FRONT_Y - 10))
        panel = panel.fuse(kn).fuse(bar)
    # кабельный ввод / вилка (наклонный элемент 1340…1379 × 145…194)
    p0, p1 = V(X(1352.0), FRONT_Y - 9, Z(181.5)), V(X(1376.0), FRONT_Y - 9, Z(149.0))
    plug = cq.Solid.makeCylinder(8.0, (p1 - p0).Length, p0, p1 - p0).fuse(fc(1352.0, 181.5, 24.0, 18.0))
    panel = panel.fuse(plug).clean()
    add(k + "_panel", "2", "Органы управления на лицевой панели ВС-300Б", panel, C_BLACK, "",
        "по векторам листа: прибор, таблички, автомат, ручки, колодка, розетка")
    # силовые клеммы: «+» (1526,8; 248,8), нижние (1470,4 / 1526,8; 181,5)
    for i, (xc, zc) in enumerate([(1526.8, 248.8), (1526.8, 181.5), (1470.4, 181.5)]):
        base = fc(xc, zc, 40.0, 8.0)
        hexp = (cq.Workplane("XZ").workplane(offset=-(FRONT_Y - 8)).center(X(xc), Z(zc))
                .polygon(6, 30.0).extrude(12.0)).val()
        add(k + "_klemma_%d" % (i + 1), "2", "Силовая клемма ВС-300Б", fuse(base, hexp), C_BRASS, "",
            "Ø40 по векторам (кольцо), шестигранник 26")
    add(k + "_peremychka", "2", "Перемычка клемм ВС-300Б",
        box(X(1470.4) + 15.1, X(1526.8) - 15.1, FRONT_Y - 14, FRONT_Y - 8.05, Z(181.5) - 3, Z(181.5) + 3), C_BRASS)
    # ходовая часть
    zc_b = BW_D / 2
    for i, xc in enumerate(BW_XC):
        add(k + "_koleso_%d" % (i + 1), "2", "Колесо ВС-300Б (заднее)",
            wheel(BW_D, BW_W, X(xc), BW_Y, zc_b, AXLE_D + 0.2, 10.0), C_RUBBER, "",
            "Ø148 × 52; размер 84×5 = 420 — по наружным плоскостям колёс")
    ax = cyl(AXLE_D, (BW_XC[1] + BW_W / 2 - 3) - (BW_XC[0] - BW_W / 2 + 3), (X(BW_XC[0] - BW_W / 2 + 3), BW_Y, zc_b), (1, 0, 0))
    brk = []
    for xb in (PS_X[0] + 3, PS_X[1] - 3 - 12):
        brk.append(box(X(xb), X(xb) + 12, BW_Y - 20, BW_Y + 20, zc_b, PS_Z[0]))
    ax = fuse(ax, *brk)
    add(k + "_os", "2", "Ось задних колёс с кронштейнами", ax, C_STEEL)
    zc_c = CW_D / 2
    for i, xc in enumerate(CW_XC):
        add(k + "_rolik_%d" % (i + 1), "2", "Ролик ВС-300Б (передний)",
            wheel(CW_D, CW_W - 0.2, X(xc), CW_Y, zc_c, CW_AXLE_D + 0.2, 8.0), C_RUBBER, "", "Ø80 × 50")
        x0, x1 = X(xc) - CW_W / 2 - 0.1, X(xc) + CW_W / 2 + 0.1
        cheeks = [box(x0 - FORK_T, x0, CW_Y - 25, CW_Y + 25, FORK_Z[0], FORK_Z[1] - 5),
                  box(x1, x1 + FORK_T, CW_Y - 25, CW_Y + 25, FORK_Z[0], FORK_Z[1] - 5),
                  box(x0 - FORK_T, x1 + FORK_T, CW_Y - 25, CW_Y + 25, FORK_Z[1] - 5, FORK_Z[1]),
                  cyl(CW_AXLE_D, CW_W + 2 * FORK_T, (x0 - FORK_T, CW_Y, zc_c), (1, 0, 0))]
        add(k + "_vilka_%d" % (i + 1), "2", "Вилка ролика ВС-300Б", fuse(*cheeks), C_STEEL)
    # поперечина между вилками (линия 1366,5…1499,4 на Z 60,9)
    xa = X(CW_XC[0]) + CW_W / 2 + 0.1 + FORK_T
    xb = X(CW_XC[1]) - CW_W / 2 - 0.1 - FORK_T
    add(k + "_poperechina", "2", "Поперечина передних роликов", cyl(16.0, xb - xa, (xa, CW_Y, Z(60.9) + 8), (1, 0, 0)), C_STEEL)


# ---------------------------------------------------------------------------
# Поз.3 ПДГ-312-5
# ---------------------------------------------------------------------------
def build_pos3():
    k = "poz3_pdg"
    x0, x1 = X(PDG_X[0]), X(PDG_X[1])
    outer = box(x0, x1, PDG_Y[0], PDG_Y[1], PDG_Z[0], PDG_Z[1])
    inner = box(x0 + PDG_WALL, x1 - PDG_WALL, PDG_Y[0] + PDG_WALL, PDG_Y[1] - PDG_WALL,
                PDG_Z[0] + PDG_WALL, PDG_Z[1] - PDG_WALL)
    shell = outer.cut(inner)
    # линия разъёма кассетного отсека (паз 1 мм на лицевой стенке)
    groove = box(x0 - 1, x1 + 1, PDG_Y[0] - 0.1, PDG_Y[0] + 1.0, PDG_DIV_Z - 1.0, PDG_DIV_Z + 1.0)
    shell = shell.cut(groove)
    add(k + "_korpus", "3", "Механизм подачи ПДГ-312-5 — корпус (кожух)", shell, C_PDG, "ТУ на ПДГ-312-5",
        "250 (50×5) × 450 (глубина — допущение) × 322; лист 2 мм")
    # ручка (трапеция на крышке, верх = 90×5 = 450)
    hz0 = PDG_Z[1]
    handle = (cq.Workplane("XZ")
              .polyline([(X(HANDLE_X_BOT[0]), hz0), (X(HANDLE_X_BOT[1]), hz0),
                         (X(HANDLE_X_TOP[1]), PDG_H_TOTAL), (X(HANDLE_X_TOP[0]), PDG_H_TOTAL)]).close()
              .extrude(HANDLE_L / 2, both=True))
    add(k + "_ruchka", "3", "Ручка ПДГ-312-5", handle, C_BLACK, "", "верх = 90×5 = 450 мм")
    # кассета с проволокой внутри
    sx, sy, sz = X(SPOOL_C[0]), SPOOL_C[1], SPOOL_C[2]
    spool = fuse(cyl(SPOOL_D, 4, (sx - SPOOL_W / 2, sy, sz), (1, 0, 0)),
                 cyl(SPOOL_D, 4, (sx + SPOOL_W / 2 - 4, sy, sz), (1, 0, 0)),
                 cyl(SPOOL_D - 30, SPOOL_W - 8, (sx - SPOOL_W / 2 + 4, sy, sz), (1, 0, 0)))
    spool = spool.cut(cyl(20.4, SPOOL_W + 2, (sx - SPOOL_W / 2 - 1, sy, sz), (1, 0, 0)))
    add(k + "_kasseta", "3", "Кассета с электродной проволокой Св-08Г2С", spool, C_WIRE,
        "проволока Св-08Г2С ГОСТ 2246-70, кассета Ø200", "внутри кожуха")
    spindle = cyl(20.0, (sx + SPOOL_W / 2 + 5) - (x0 + PDG_WALL), (x0 + PDG_WALL, sy, sz), (1, 0, 0))
    add(k + "_os_kassety", "3", "Ось кассеты", spindle, C_STEEL)
    # разъёмы на лицевой панели
    yf = PDG_Y[0]
    items = []
    for xc, zc, d in PDG_SOCKETS:
        items.append(cyl(d, 15.0, (X(xc), yf - 15.0, zc), (0, 1, 0)))
    for xc, zc, d in PDG_SMALL:
        items.append(cyl(d, 6.0, (X(xc), yf - 6.0, zc), (0, 1, 0)))
    add(k + "_razemy", "3", "Разъёмы и индикаторы ПДГ-312-5", fuse(*items), C_BLACK)
    eu = fuse(cyl(EURO_D, 8.0, (X(EURO_C[0]), yf - 8.0, EURO_C[1]), (0, 1, 0)),
              cyl(EURO_D - 8, 20.0, (X(EURO_C[0]), yf - 20.0, EURO_C[1]), (0, 1, 0)))
    add(k + "_evrorazem", "3", "Евроразъём горелки", eu, C_BRASS)
    # поворотные ролики
    for i, xc in enumerate(CASTOR_XC):
        for j, yc in enumerate(CASTOR_Y):
            n = "%d%d" % (i + 1, j + 1)
            zc = CASTOR_WD / 2
            add(k + "_rolik_%s" % n, "3", "Ролик ПДГ-312-5",
                wheel(CASTOR_WD, CASTOR_WW, X(xc), yc, zc, 8.2, 5.0), C_RUBBER, "", "Ø48 × 25")
            xa, xb = X(xc) - CASTOR_WW / 2 - 0.1, X(xc) + CASTOR_WW / 2 + 0.1
            ft = (CASTOR_FORK - CASTOR_WW - 0.2) / 2
            fork = fuse(box(xa - ft, xa, yc - 15, yc + 15, zc - 5, Z(62.2)),
                        box(xb, xb + ft, yc - 15, yc + 15, zc - 5, Z(62.2)),
                        box(xa - ft, xb + ft, yc - 15, yc + 15, Z(62.2) - 4, Z(62.2)),
                        cyl(25.0, PDG_Z[0] - Z(62.2), (X(xc), yc, Z(62.2)), (0, 0, 1)),
                        cyl(8.0, CASTOR_FORK, (xa - ft, yc, zc), (1, 0, 0)))
            add(k + "_vilka_%s" % n, "3", "Вилка ролика ПДГ-312-5", fork, C_STEEL)


# ---------------------------------------------------------------------------
# Поз.4 горелка
# ---------------------------------------------------------------------------
def torch_bend_end():
    a = math.radians(TB_ANG)
    sx, sz = X(TN_X[1]), TN_ZC
    return (sx + TB_R * math.sin(a), sz - TB_R + TB_R * math.cos(a)), a


def build_pos4():
    k = "poz4_gorelka"
    x0, x1 = X(TH_X[0]), X(TH_X[1])
    h = cq.Workplane("YZ").workplane(offset=x0).center(0, TH_ZC).circle(TH_D / 2).extrude(x1 - x0)
    h = h.faces("<X").edges().fillet(4.0)
    add(k + "_rukoyatka", "4", "Рукоятка горелки", h, C_BLACK, "", "Ø36,4 × 195 по векторам")
    trig = (cq.Workplane("XZ")
            .polyline([(X(x), z + TZ) for x, z in TRIG]).close().extrude(6.0, both=True))
    add(k + "_kurok", "4", "Курок горелки", trig, C_RED)
    # шейка: прямой участок + гиб R50 на 48°
    (ex, ez), a = torch_bend_end()
    sx = X(TN_X[1])
    mid = (sx + TB_R * math.sin(a / 2), TN_ZC - TB_R + TB_R * math.cos(a / 2))
    path = (cq.Workplane("XZ").moveTo(x1, TN_ZC).lineTo(sx, TN_ZC).threePointArc(mid, (ex, ez))).wire().val()
    prof = cq.Wire.makeCircle(TN_D / 2, V(x1, 0, TN_ZC), V(1, 0, 0))
    neck = cq.Solid.sweep(prof, [], path, True, False, transitionMode="right")
    add(k + "_sheyka", "4", "Шейка (гусак) горелки", neck, C_STEEL, "", "Ø22,8, гиб R50/48°")
    d = V(math.cos(a), 0, -math.sin(a))
    noz = cq.Solid.makeCylinder(NOZ_D / 2, NOZ_L, V(ex, 0, ez), d)
    noz = noz.cut(cq.Solid.makeCylinder(NOZ_D / 2 - 2, NOZ_L - 10, V(ex, 0, ez) + d * 10.01, d))
    add(k + "_soplo", "4", "Сопло горелки", noz, C_BRASS, "", "Ø18 × 46")
    # кабель-шланг от евроразъёма ПДГ до рукоятки (средняя линия по векторам)
    mids = [(2115.8, 119.2), (2181.0, 114.5), (2246.4, 114.0), (2311.6, 119.2), (2376.3, 129.1),
            (2439.9, 144.3), (2500.9, 167.5), (2555.5, 203.1), (2600.8, 249.9), (2637.1, 304.2),
            (2666.4, 362.7), (2692.4, 422.7), (2716.9, 483.4), (2740.6, 544.4), (2765.0, 605.1),
            (2791.9, 664.7), (2822.6, 722.5), (2860.0, 776.1), (2908.1, 820.2), (2965.4, 851.3),
            (3027.3, 872.0)]
    y0 = PDG_Y[0] - 20.0
    pts = [(X(EURO_C[0]), y0 - 0.05, EURO_C[1]), (X(2040.0), y0 - 110, Z(125.0))]
    body = route(mids, lambda t: y0 - 130 + (130 - y0) * t ** 0.8)
    pts += body[::2] + [(x0 - 40, 0.0, TH_ZC), (x0 - 0.05, 0.0, TH_ZC)]
    hose = tube(pts, HOSE_T_D, (0, -1, 0), (1, 0, 0))
    add(k + "_kabel_shlang", "4", "Кабель-шланг горелки", hose, C_BLACK, "",
        "Ø32 по векторам; трасса — средняя линия контуров чертежа, в глубину уходит от евроразъёма")


# ---------------------------------------------------------------------------
# Поз.5 изделие (корпус задвижки, импорт модели листа 2)
# ---------------------------------------------------------------------------
def build_pos5():
    import importlib.util
    spec = importlib.util.spec_from_file_location("korpus_build", os.path.join(KORPUS_DIR, "build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    parts = mod.make_korpus_parts()
    # изделие установлено фланцем стакана (поз.4 корпуса) на стол: поворот 180° вокруг оси X
    # и 90° вокруг Z (ось прохода — вдоль Y, чтобы фланцы патрубков не мешали горелке)
    z_hub = 155.0
    for key, name, wp, color in parts:
        s = wp.val().rotate(V(0, 0, 0), V(1, 0, 0), 180).rotate(V(0, 0, 0), V(0, 0, 1), 90)
        s = s.translate(V(X(PROD_XC), 0, TABLE_H + z_hub))
        add("poz5_izdelie_" + key, "5", "Свариваемое изделие (корпус задвижки): " + name, s, color,
            "лист 2 проекта", "модель ../korpus/build.py; изделие перевёрнуто фланцем стакана вниз")


# ---------------------------------------------------------------------------
# Поз.6 стол
# ---------------------------------------------------------------------------
def build_pos6():
    k = "poz6_stol"
    x0, x1 = X(TABLE_X[0]), X(TABLE_X[1])
    y0, y1 = -TABLE_D / 2, TABLE_D / 2
    add(k + "_stoleshnica", "6", "Столешница стола сварщика",
        box(x0, x1, y0, y1, TABLE_H - TABLE_TOP_T, TABLE_H), C_TOP, "", "601,1 (120,22×5), толщина 50")
    tumba = box(x0, x1, y0, y1, TABLE_LEG_H, TABLE_H - TABLE_TOP_T)
    tumba = tumba.cut(box(x0 + 2, x1 - 2, y0 + 2, y1 - 2, TABLE_LEG_H + 2, TABLE_H - TABLE_TOP_T + 1))
    add(k + "_tumba", "6", "Тумба (каркас с обшивкой) стола", tumba, C_TABLE, "", "лист 2 мм")
    n = 0
    for xa in (x0, x1 - TABLE_LEG):
        for ya in (y0, y1 - TABLE_LEG):
            n += 1
            add(k + "_opora_%d" % n, "6", "Опора стола", box(xa, xa + TABLE_LEG, ya, ya + TABLE_LEG, 0, TABLE_LEG_H),
                C_TABLE, "", "50,8 × 50,8 × 98")


# ---------------------------------------------------------------------------
# Поз.7…9
# ---------------------------------------------------------------------------
def _hood_loft(inset, dz_bot, dz_top):
    (xa, za), (xb, zb) = HOOD_P1, HOOD_P2
    ux, uz = xb - xa, zb - za
    L = math.hypot(ux, uz)
    ux, uz = ux / L, uz / L
    nx, nz = uz, -ux          # нормаль к кромке «вниз-наружу» (-Z сторона)
    if nz > 0:
        nx, nz = -nx, -nz
    pa = (X(xa) + ux * inset + nx * dz_bot, za + uz * inset + nz * dz_bot)
    pb = (X(xb) - ux * inset + nx * dz_bot, zb - uz * inset + nz * dz_bot)
    w = HOOD_W / 2 - inset
    rect = cq.Wire.makePolygon([V(pa[0], -w, pa[1]), V(pb[0], -w, pb[1]), V(pb[0], w, pb[1]),
                                V(pa[0], w, pa[1])], close=True)
    r = DUCT_D / 2 - inset
    circ = cq.Wire.makeCircle(r, V(X(DUCT_XC), 0, HOOD_TOP_Z + dz_top), V(0, 0, 1))
    return cq.Solid.makeLoft([rect, circ], True)


def build_pos789():
    outer = _hood_loft(0.0, 0.0, 0.0)
    inner = _hood_loft(HOOD_T, 1.0, 1.0)
    hood = outer.cut(inner)
    add("poz7_vozduhopriemnik", "7", "Воздухоприёмник (зонт)", hood, C_HOOD, "",
        "наклонная кромка 84,19×5 = 421; ширина по Y 500 — допущение; переход на Ø143")
    zc = X(DUCT_XC)
    ring = (cq.Workplane("XY").workplane(offset=SHIB_Z[0]).center(zc, 0)
            .circle(DUCT_D / 2 + 3).circle(DUCT_D / 2 - DUCT_T).extrude(SHIB_Z[1] - SHIB_Z[0])).val()
    ring = ring.cut(cyl(8.4, DUCT_D + 20, (zc, -DUCT_D / 2 - 10, (SHIB_Z[0] + SHIB_Z[1]) / 2), (0, 1, 0)))
    add("poz8_shiber_korpus", "8", "Шибер — корпус (обечайка)", ring, C_STEEL, "",
        "Ø143 × 51 по векторам (1693,7…1744,5)")
    zm = (SHIB_Z[0] + SHIB_Z[1]) / 2
    disk = cq.Solid.makeCylinder(DUCT_D / 2 - DUCT_T - 1.5, 2.0, V(zc, 0, zm) - V(0, 0, 1), V(0, 0, 1))
    disk = disk.rotate(V(zc, 0, zm), V(zc, 1, zm), 30)
    spindle = cyl(8.0, DUCT_D + 40, (zc, -DUCT_D / 2 - 30, zm), (0, 1, 0))
    handle = box(zc - 4, zc + 60, -DUCT_D / 2 - 30, -DUCT_D / 2 - 24, zm - 4, zm + 4)
    add("poz8_shiber_zaslonka", "8", "Шибер — заслонка с осью и рукояткой", fuse(disk, spindle, handle), C_RED,
        "", "заслонка повёрнута на 30° (частично открыта)")
    duct = (cq.Workplane("XY").workplane(offset=SHIB_Z[1] + 0.05).center(zc, 0)
            .circle(DUCT_D / 2).circle(DUCT_D / 2 - DUCT_T).extrude(DUCT_Z_TOP - SHIB_Z[1] - 0.05)).val()
    add("poz9_vozduhovod", "9", "Воздуховод", duct, C_HOOD, "", "Ø143, показан до линии обрыва чертежа")


# ---------------------------------------------------------------------------
# Рукава и кабели
# ---------------------------------------------------------------------------
def build_hoses():
    zr = ZCYL(V_OUTZ)
    # рукав от редуктора баллона 1 — за баллоном 2 — к левой стенке ВС-300Б
    x_out1 = CYL_X[0] + R_OUT_X[1]
    p = [(x_out1 + 0.05, 0.0, zr), (x_out1 + 30, 0.0, zr - 4), (X(835.0), 40.0, Z(1198.0)),
         (X(880.0), 115.0, Z(1120.0)), (X(940.0), 135.0, Z(960.0)), (X(1000.0), 130.0, Z(790.0)),
         (X(1018.1), 115.0, Z(664.5)), (X(1031.6), 108.0, Z(620.3)), (X(1041.2), 95.0, Z(575.0)),
         (X(1050.1), 80.0, Z(529.5)), (X(1061.6), 65.0, Z(484.7)), (X(1078.4), 50.0, Z(441.8)),
         (X(1102.9), 38.0, Z(402.6)), (X(1133.1), 28.0, Z(367.7)), (X(1168.4), 18.0, Z(337.7)),
         (X(1206.7), 10.0, Z(311.7)), (X(1247.4), 3.0, Z(289.7)), (X(PS_X[0]) - 0.05, 0.0, Z(272.4))]
    add("shlang_gaz_1", "", "Рукав газовый (баллон 1 → ВС-300Б)", tube(p, GAS_HOSE_D, (1, 0, 0), (1, 0, 0)),
        C_BLUE_HOSE, "ГОСТ 9356-75 (III-6,3)", "трасса по чертежу; скрытый участок — за баллоном 2")
    # рукав от редуктора баллона 2 к верху ВС-300Б
    x_out2 = CYL_X[1] + R_OUT_X[1]
    mids = [(1091.3, 1228.5), (1130.3, 1210.5), (1160.1, 1179.8), (1178.0, 1140.4), (1193.0, 1099.9),
            (1208.3, 1059.4), (1224.6, 1019.4), (1241.1, 979.4), (1256.8, 939.1), (1270.5, 898.1),
            (1281.4, 856.2), (1290.3, 813.9), (1297.3, 771.2), (1303.4, 728.3)]
    body = route(mids, lambda t: -35.0 * t)
    p = [(x_out2 + 0.05, 0.0, zr)] + body + [(X(1308.0), -40.0, PS_Z[1] + 0.05)]
    add("shlang_gaz_2", "", "Рукав газовый (баллон 2 → ВС-300Б)", tube(p, GAS_HOSE_D, (1, 0, 0), (0, 0, -1)),
        C_BLUE_HOSE, "ГОСТ 9356-75 (III-6,3)", "трасса по чертежу")
    # кабели ВС-300Б → ПДГ
    xe = X(PDG_X[0]) - 0.05
    yt = FRONT_Y - 20.0          # торец клемм / розетки
    CAB_EXIT = 150.0
    cables = [
        ("kabel_1", "Сварочный кабель (клемма → ПДГ)", 24.0, (1526.8, 181.5),
         [(1567.2, 183.1), (1599.7, 183.1), (1632.1, 181.6), (1664.3, 177.5), (1696.0, 170.6),
          (1727.2, 161.7), (1757.9, 151.3), (1787.8, 138.8)], (1816.9, 124.4), -150.0),
        ("kabel_2", "Сварочный кабель («+» → ПДГ)", 21.0, (1526.8, 248.8),
         [(1590.9, 242.1), (1629.1, 238.4), (1667.1, 232.7), (1704.9, 225.4), (1742.3, 216.5),
          (1779.6, 207.1)], (1816.9, 197.8), -90.0),
        ("kabel_5", "Кабель управления (розетка → ПДГ)", 20.0, (1529.5, 459.2),
         [(1604.4, 444.7), (1641.2, 435.5), (1677.5, 424.5), (1713.2, 411.8), (1748.4, 397.4),
          (1782.9, 381.6)], (1816.9, 364.9), -190.0),
    ]
    y_out = yt - CAB_EXIT       # кабель выходит из клеммы прямо вперёд на CAB_EXIT, затем плавно
    #                            (R ≥ 2d) поворачивает к ПДГ; точки трассы ближе 110 мм по X к клемме
    #                            отброшены (на виде спереди они лежат на той же высоте, что и клемма)
    for key, name, d, (sx, sz), mids, (exx, ez), ye in cables:
        mids = [q for q in mids if q[0] - sx > 110.0 and exx - q[0] > 60.0]
        body = route(mids, lambda t, ye=ye: y_out + (ye - y_out) * t)
        p = [(X(sx), yt - 0.05, Z(sz)), (X(sx), y_out, Z(sz))] + body + [(xe, ye, Z(ez))]
        add(key, "", name, tube(p, d, (0, -1, 0), (1, 0, 0)), C_BLACK, "КГ ГОСТ 24334-80 / ТУ", "трасса по чертежу")
    side = [
        ("kabel_3", "Кабель (правая стенка ВС-300Б → ПДГ)", 16.0, (1575.6, 272.8),
         [(1610.2, 271.6), (1644.8, 272.9), (1679.3, 276.2), (1713.6, 280.9), (1747.8, 285.9),
          (1782.3, 289.2)], (1816.9, 288.5), -100.0, -50.0),
        ("kabel_4", "Кабель управления (правая стенка ВС-300Б → ПДГ)", 13.0, (1575.6, 426.1),
         [(1605.3, 402.8), (1636.4, 381.5), (1669.3, 363.1), (1704.5, 349.8), (1741.6, 343.4),
          (1779.2, 341.3)], (1816.9, 341.1), 0.0, 0.0),
    ]
    for key, name, d, (sx, sz), mids, (exx, ez), ys, ye in side:
        body = route(mids, lambda t, ys=ys, ye=ye: ys + (ye - ys) * t)
        p = [(X(sx) + 0.05, ys, Z(sz))] + body + [(xe, ye, Z(ez))]
        add(key, "", name, tube(p, d, (1, 0, 0), (1, 0, 0)), C_BLACK, "КГ ГОСТ 24334-80 / ТУ", "трасса по чертежу")
    # обратный провод: из-под ПДГ по полу к столу, вверх к днищу тумбы
    r = FLOOR_CABLE_D / 2 + 0.1
    p = [(X(1890.0), 0.0, PDG_Z[0] - 0.05), (X(1890.0), 0.0, 45.0), (X(1935.0), 0.0, 20.0),
         (X(2000.0), 0.0, r), (X(3350.0), 0.0, r), (X(3395.0), 0.0, 30.0), (X(3400.0), 0.0, 60.0),
         (X(3400.0), 0.0, TABLE_LEG_H - 0.05)]
    fc_ = tube(p, FLOOR_CABLE_D, (0, 0, -1), (0, 0, 1), R=40.0)
    add("kabel_obratnyi", "", "Обратный (заземляющий) провод к столу", fc_,
        C_BLACK, "КГ ГОСТ 24334-80", "по полу (линия 12,6 над полом на чертеже)")


# ---------------------------------------------------------------------------
# Сборка, проверки, экспорт
# ---------------------------------------------------------------------------
def build_all():
    NODES.clear()
    build_pos1()
    build_pos2()
    build_pos3()
    build_pos4()
    build_pos5()
    build_pos6()
    build_pos789()
    build_hoses()
    return NODES


def check(nodes):
    bb_all = None
    for key, *_ in nodes:
        pass
    solids = [(n[0], n[3]) for n in nodes]
    for k, s in solids:
        assert s.isValid(), k
        bb = s.BoundingBox()
        bb_all = bb if bb_all is None else bb_all.add(bb)
    print("Габарит: X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f" % (
        bb_all.xmin, bb_all.xmax, bb_all.ymin, bb_all.ymax, bb_all.zmin, bb_all.zmax))
    bad = []
    bbs = [s.BoundingBox() for _, s in solids]
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            ka, kb = solids[i][0], solids[j][0]
            if ka.startswith("poz5_") and kb.startswith("poz5_"):
                continue          # внутренняя проверка изделия — в модели ../korpus
            a, b = bbs[i], bbs[j]
            if (a.xmin > b.xmax or b.xmin > a.xmax or a.ymin > b.ymax or b.ymin > a.ymax
                    or a.zmin > b.zmax or b.zmin > a.zmax):
                continue
            v = solids[i][1].intersect(solids[j][1]).Volume()
            if v > 0.01:
                bad.append((ka, kb, v))
    for ka, kb, v in bad:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.2f мм3" % (ka, kb, v))
    if not bad:
        print("Пересечений нет (порог 0,01 мм3)")
    zmin = min(s.BoundingBox().zmin for _, s in solids)
    print("Мин. Z = %.3f (пол = 0)" % zmin)
    return bad, bb_all


def export(nodes):
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="svarochnoe_oborudovanie")
    for key, pos, name, s, color, std, note in nodes:
        assy.add(s, name=key, color=color)
        cq.exporters.export(s, os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(s, os.path.join(OUT, "parts_stl", key + ".stl"), tolerance=0.8, angularTolerance=0.5)
    assy.save(os.path.join(OUT, "oborudovanie.step"))
    assy.save(os.path.join(OUT, "oborudovanie.glb"), tolerance=1.5, angularTolerance=0.6)
    print("GLB %.2f МБ" % (os.path.getsize(os.path.join(OUT, "oborudovanie.glb")) / 1e6))


MATERIAL = {
    "poz1": "сталь 45 (баллон), латунь ЛС59-1 (вентиль, редуктор)",
    "poz2": "сталь листовая (шкаф), резина (колёса)",
    "poz3": "сталь листовая (кожух), резина/сталь (ролики)",
    "poz4": "пластмасса (рукоятка), медь/латунь (шейка, сопло)",
    "poz5": "Сталь 20 ГОСТ 1050-2013",
    "poz6": "сталь Ст3 ГОСТ 380-2005",
    "poz7": "сталь оцинкованная, лист 1,5",
    "poz8": "сталь оцинкованная",
    "poz9": "сталь оцинкованная, лист 1,5",
    "shla": "резина (рукав)",
    "kabe": "медь + резиновая изоляция",
}


def group_key(key):
    import re
    if key.startswith("poz5_izdelie_"):
        return "poz5_izdelie"
    if key.startswith("poz1_ballon_"):
        g = re.sub(r"^poz1_ballon_\d+_", "poz1_ballon_*_", key)
        return re.sub(r"_\d+$", "_*", g)
    if re.fullmatch(r"kabel_\d+", key):
        return "kabel_[1-5]"
    return re.sub(r"_\d+$", "_*", key)


GROUP_NAMES = {
    "poz5_izdelie": "Свариваемое изделие — корпус задвижки в сборе (детали поз.1–6 листа 2 и швы №1–3, 25 тел)",
    "poz1_ballon_*_korpus": "Баллон 40 л (№1 — аргон, серый; №2 — CO2, чёрный)",
    "shlang_gaz_*": "Рукав газовый (баллон → ВС-300Б)",
    "kabel_[1-5]": "Кабели ВС-300Б → ПДГ-312-5 (сварочные Ø24/Ø21/Ø16 и управления Ø20/Ø13)",
}


def write_spec(nodes):
    groups, order = {}, []
    for key, pos, name, s, color, std, note in nodes:
        g = group_key(key)
        if g not in groups:
            nm = GROUP_NAMES.get(g, name)
            groups[g] = {"key": g, "pos": pos, "name_ru": nm, "qty": 0,
                         "material": MATERIAL.get(key[:4], ""), "standard": std, "note": note, "nodes": []}
            order.append(g)
        groups[g]["qty"] += 1
        groups[g]["nodes"].append(key)
    spec = [groups[g] for g in order]
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    return spec


def report_dims(nodes):
    d = {n[0]: n[3].BoundingBox() for n in nodes}
    rows = [
        ("254,21×5 высота баллона с вентилем", 1271.05, d["poz1_ballon_1_ventil"].zmax),
        ("40×5 башмак (ширина)", 200.0, d["poz1_ballon_2_bashmak"].xlen),
        ("148×5 ВС-300Б до верха проушин", 740.0, d["poz2_istochnik_proushina_1"].zmax),
        ("84×5 ВС-300Б по колёсам", 420.0, d["poz2_istochnik_koleso_2"].xmax - d["poz2_istochnik_koleso_1"].xmin),
        ("50×5 ширина ПДГ", 250.0, d["poz3_pdg_korpus"].xlen),
        ("90×5 ПДГ до верха ручки", 450.0, d["poz3_pdg_ruchka"].zmax),
        ("160×5 высота стола", 800.0, d["poz6_stol_stoleshnica"].zmax),
        ("120,22×5 ширина стола", 601.1, d["poz6_stol_stoleshnica"].xlen),
        ("84,19×5 наклонная кромка зонта", 420.95,
         math.hypot(HOOD_P2[0] - HOOD_P1[0], HOOD_P2[1] - HOOD_P1[1])),
        ("Ø воздуховода (вектор 143,1)", 143.1, d["poz9_vozduhovod"].xlen),
        ("Ø баллона ГОСТ 949-73", 219.0, d["poz1_ballon_1_korpus"].xlen),
    ]
    for n, a, b in rows:
        print("%-40s чертёж %8.2f  модель %8.2f" % (n, a, b))
    return rows


if __name__ == "__main__":
    nodes = build_all()
    print("Узлов:", len(nodes))
    bad, bb = check(nodes)
    report_dims(nodes)
    export(nodes)
    write_spec(nodes)
