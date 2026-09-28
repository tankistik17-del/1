#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лист 9 «Планировка участка сборки-сварки корпуса задвижки трубопровода»
(план 1:50, разрез А-А 1:100, кабина 1:30) — 3D-модель планировки, мм.

Система координат:
  X — вдоль пролёта (длина 36000, оси колонн X = 0/12000/24000/36000, слева направо по плану);
  Y — поперёк пролёта (18000), направлена вверх по листу: Y = 18000 — ось верхнего (по плану) ряда
      колонн со стеной и окнами; Y = 0 — ось нижнего ряда колонн (план за линией обрыва — по разрезу А-А).
  ВНИМАНИЕ: функции make_* ниже строят детали во «внутренней» системе Yi (Yi = 0 у стены, растёт вниз
  по листу), при сборке все детали зеркалируются: Y = 18000 - Yi.
  Z — вверх, пол Z = 0.
Пересчёт координат с плана:  X = (x_pt - 210.2)*S50,  Y = (y_pt - 201.1)*S50,
  S50 = 36000 / (2248.8 - 210.2) = 17.659 мм/pt (калибровка по размеру 12000х3=36000).
Разрез А-А: Y = (x_pt - 114.2)*S100, Z = (1569.1 - y_pt)*S100, S100 = 18000/511.0 = 35.23 мм/pt.
Кабина 1:30: u = (x_pt-1169.5)*3000/283.9, v = (y_pt-1300.6)*2500/243.8.
"""
import json
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
NAME = "planirovka_uchastka"

# ---------------------------------------------------------------- масштабы
S50 = 36000.0 / (2248.8 - 210.2)   # план 1:50, калибровка по «12000х3=36000»
S100 = 18000.0 / (625.2 - 114.2)   # разрез А-А 1:100, калибровка по «18000»

# ---------------------------------------------------------------- здание
L_BAY = 36000.0          # «12000х3=36000» (план)
PITCH = 12000.0          # «12000» шаг колонн (план)
SPAN = 18000.0           # «18000» пролёт (разрез А-А)
AXES_X = [0.0, 12000.0, 24000.0, 36000.0]
COL_X = 800.0            # колонна по плану: 865.2..910.6 pt = 45.4 pt*S50 = 802 -> 800
COL_Y0, COL_Y1 = -424.0, 178.0   # колонна по плану 177.1..211.2 pt при оси 201.1 -> -424..+178 (600)
COLB_IN, COLB_OUT = 237.0, 364.0  # нижний ряд: 976.6..1010.6 pt при оси 990.0 -> 237 внутрь / 364 наружу
H_TRUSS = 10800.0        # «10800» — низ стропильной фермы (разрез А-А)
WALL_Y0 = -842.0         # наружная грань стены: y=153.4 pt -> (153.4-201.1)*S50
WALL_Y1 = -245.0         # внутренняя грань стены: y=187.2 pt  (от неё размер «2000» до кабин)
PIER_HALF = 1000.0       # простенок (штриховка) 832.6..946.1 pt = 2004 мм -> ±1000 от оси
PIER_Y1 = COL_Y0         # простенок 153.4..177.1 pt -> -842..-424
SILL_Z = 1200.0          # низ ленточного остекления (принято)
WIN_TOP_Z = 7200.0       # верх остекления (принято)
WALL_TOP_Z = 11950.0     # верх стены — под кровельной плитой (Z кровли на Y=-842 = 11964)
FLOOR_T = 200.0

# ферма (разрез А-А, вершины по векторам)
TR_T = 250.0             # толщина фермы вдоль X (принято)
TR_W = 150.0             # сечение элемента в плоскости фермы (принято)
TR_SUP_Z = 12080.0       # верх верхнего пояса на опоре: y=1226.2 pt -> (1569.1-1226.2)*S100
TR_RIDGE_Z = 13080.0     # верх пояса в коньке:          y=1197.8 pt -> 13081
TR_SUP_Y = 180.0         # опорный узел x=119.5 pt -> (119.5-114.2)*S100 = 187 -> 180 (симм.)
TR_SLOPE = (TR_RIDGE_Z - TR_SUP_Z) / (SPAN / 2 - TR_SUP_Y)
TR_BOT_NODES = [180.0, 2930.0, 5650.0, 12350.0, 15070.0, 17820.0]  # x=119.5,197.5,274.8,464.9,542.2,620.2 pt
TR_TOP_NODES = [1580.0, 4300.0, 9000.0, 13700.0, 16420.0]          # x=159.1,236.2,369.8,503.3,580.6 pt
ROOF_T = 150.0           # кровельная плита (двойная линия ~4 pt*S100 = 141)
# фонарь
LANT_Y0, LANT_Y1 = 4300.0, 13700.0   # стойки фонаря x=236.2/503.3 pt -> 4298/13708
LANT_EAVE_Z = 14483.0    # низ кровли фонаря у стойки: y=1158.0 pt
LANT_RIDGE_Z = 15632.0   # конёк фонаря: y=1125.4 pt
LANT_WALL_T = 100.0

# подкрановые конструкции / кран (разрез А-А)
RAIL_TOP_Z = 7525.0      # уровень головки рельса: консоль y=1355.5 pt -> 7525
RAIL_H = 120.0           # рельс КР70 ГОСТ 4121-96: h=120, B=120 (подошва), b=70 (головка)
RB_H = 600.0             # подкрановая балка (принято)
CONS_H = 500.0           # консоль колонны (принято)
LAMBDA = 750.0           # привязка оси рельса к оси колонн (ГОСТ 25711-83: Lк = 18000-2*750 = 16500)
CR_SPAN = SPAN - 2 * LAMBDA          # пролёт крана 16500
CR_X = (2093.55 - 210.2) * S50       # ось крана по плану (2056.1..2131.0 pt) = 33258
ET_L = (2178.2 - 2008.1) * S50       # концевая балка по плану 3004
ET_W = (208.3 - 194.2) * S50         # ширина концевой балки 249
GIRD_W = (2074.1 - 2056.1) * S50     # ширина главной балки 318
GIRD_C = (2122.2 - 2065.1) * S50     # межосевое расстояние главных балок 1008
GIRD_BOT_Z = 7990.0      # низ главной балки y=1342.3 pt
GIRD_END_BOT_Z = 8260.0  # низ балки у концевой балки (подъём 598.3,1342.3 -> 606,1334.6 pt)
GIRD_TAPER = (2300.0, 2600.0)  # зона подъёма низа балки от оси пути Yi (принято)
GIRD_TOP_Z = 8853.0      # верх главной балки y=1317.8 pt
TROL_TOP_Z = 9600.0      # «1200» от низа фермы: 10800-1200 = 9600 (верх тележки)
TROL_X = (2124.2 - 2064.7) * S50     # тележка по плану 1051
TROL_Y = (625.9 - 560.6) * S50       # 1153
TROL_YC = ((560.6 + 625.9) / 2 - 201.1) * S50   # положение тележки по плану 6924
LEVEL_8150 = TROL_TOP_Z - 1450.0     # «1450» -> 8150 (верх кабины крановщика)
HOOK_Z = LEVEL_8150 - 1500.0         # «1500» -> 6650 (зев крюка)
LOAD_TOP_Z = HOOK_Z - 1200.0         # «1200» -> 5450 (стропы)
LOAD_BOT_Z = LOAD_TOP_Z - 1000.0     # «1000» груз -> 4450
OBST_H = 1500.0                      # «1500» габарит оборудования на полу; «2950» = 4450-1500
LOAD_Y = (563.0 - 495.8) * S100      # груз по разрезу 2367
LOAD_X = 1500.0                      # принято

# ---------------------------------------------------------------- кабины (1:30 + план)
CAB_W, CAB_D = 3000.0, 2500.0        # «3000», «2500» (кабина 1:30)
CAB_WALL_T = 40.0                    # ширмы кабины (принято)
CAB_H = 2000.0                       # высота ширм (принято, ≥1.8 м)
CAB_X0 = ((681.1 + 1274.2) / 2 - 210.2) * S50 - 1.5 * CAB_W   # центр блока по плану -> 9053
CAB_X0 = round(CAB_X0 / 10.0) * 10.0
CAB_Y0 = WALL_Y1 + 2000.0            # «2000» от внутренней грани стены -> 1755
DOOR_U0, DOOR_U1 = 1081.0, 1893.0    # проём со шторой: 1271.8..1348.6 pt (1:30)
# позиции внутри кабины (u — от левой стенки, v — от стенки, противоположной проёму)
P7 = (560.0, 1607.0, 139.0, 721.0)   # стол сварщика 1222.3..1321.4 x 1314.2..1370.9 pt
P9 = (1709.0, 2100.0, 139.0, 431.0)  # источник питания 1331.5..1368.5 x 1314.2..1342.6 pt
P8_C = (1865.0, 319.0, 105.0)        # установка (круг «М» Ø20 pt) центр, радиус
P6 = (30.0, 761.0, 1756.0, 2470.0)   # бункер для заготовок 1169.5..1241.5 x 1471.9..1544.4 pt
P5 = (2425.0, 2902.0, 2020.0, 2470.0)  # бункер для отходов 1399.0..1444.1 x 1497.6..1544.4 pt
H_TABLE = 800.0; H_SRC = 700.0; H_FEED = 350.0; H_BUNK = 600.0


def PX(x):
    return (x - 210.2) * S50


def PY(y):
    return (y - 201.1) * S50


# ---------------------------------------------------------------- помощники
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").add(
        cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))


def prism_yz(pts, x0, x1):
    """Многоугольник в плоскости YZ (pts=(Y,Z)), вытянутый по X от x0 до x1."""
    return cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(x1 - x0)


def bar_yz(p1, p2, w, x0, x1):
    import math
    (y1, z1), (y2, z2) = p1, p2
    L = math.hypot(y2 - y1, z2 - z1)
    ny, nz = -(z2 - z1) / L * w / 2, (y2 - y1) / L * w / 2
    return prism_yz([(y1 + ny, z1 + nz), (y2 + ny, z2 + nz), (y2 - ny, z2 - nz), (y1 - ny, z1 - nz)], x0, x1)


def union(parts):
    r = parts[0]
    for p in parts[1:]:
        r = r.union(p)
    return r.clean() if hasattr(r, "clean") else r


def shell_box(x0, x1, y0, y1, z0, z1, t=5.0):
    """Бункер — открытый сверху ящик с толщиной стенки t."""
    return box(x0, x1, y0, y1, z0, z1).cut(box(x0 + t, x1 - t, y0 + t, y1 - t, z0 + t, z1 + 1))


def table(x0, x1, y0, y1, h, top=40.0, leg=50.0):
    parts = [box(x0, x1, y0, y1, h - top, h)]
    for lx in (x0 + 20, x1 - 20 - leg):
        for ly in (y0 + 20, y1 - 20 - leg):
            parts.append(box(lx, lx + leg, ly, ly + leg, 0, h - top))
    return union(parts)


def mirY(y):
    return SPAN - y


def z_top(y):
    """Верх верхнего пояса фермы в точке Y."""
    yy = y if y <= SPAN / 2 else SPAN - y
    return TR_SUP_Z + (yy - TR_SUP_Y) * TR_SLOPE


# ---------------------------------------------------------------- здание
def make_floor():
    return box(-1000, L_BAY + 1000, WALL_Y0, SPAN - WALL_Y0, -FLOOR_T, 0)


def make_column(ax, row):
    if row == 0:
        return box(ax - COL_X / 2, ax + COL_X / 2, COL_Y0, COL_Y1, 0, H_TRUSS)
    return box(ax - COL_X / 2, ax + COL_X / 2, SPAN - COLB_IN, SPAN + COLB_OUT, 0, H_TRUSS)


def make_console(ax, row):
    z1 = RAIL_TOP_Z - RAIL_H - RB_H
    y0, y1 = COL_Y1, LAMBDA + 200
    if row:
        y0, y1 = mirY(y1), SPAN - COLB_IN
    return box(ax - COL_X / 2, ax + COL_X / 2, y0, y1, z1 - CONS_H, z1)


def make_runway_beam(row):
    z1 = RAIL_TOP_Z - RAIL_H
    yc = LAMBDA if row == 0 else mirY(LAMBDA)
    return box(-COL_X / 2, L_BAY + COL_X / 2, yc - 150, yc + 150, z1 - RB_H, z1)


def make_rail(row):
    yc = LAMBDA if row == 0 else mirY(LAMBDA)
    z0 = RAIL_TOP_Z - RAIL_H
    return box(-COL_X / 2, L_BAY + COL_X / 2, yc - 60, yc + 60, z0, z0 + 25).union(
        box(-COL_X / 2, L_BAY + COL_X / 2, yc - 35, yc + 35, z0 + 25, RAIL_TOP_Z))


def make_pier(ax):
    return box(ax - PIER_HALF, ax + PIER_HALF, WALL_Y0, PIER_Y1, 0, WALL_TOP_Z)


def make_wall_bay(i):
    x0, x1 = AXES_X[i] + COL_X / 2, AXES_X[i + 1] - COL_X / 2
    w = box(x0, x1, WALL_Y0, WALL_Y1, 0, WALL_TOP_Z)
    # вырезы под простенки и оконный проём (ленточное остекление)
    w = w.cut(box(AXES_X[i], AXES_X[i] + PIER_HALF, WALL_Y0 - 1, PIER_Y1, -1, WALL_TOP_Z + 1))
    w = w.cut(box(AXES_X[i + 1] - PIER_HALF, AXES_X[i + 1], WALL_Y0 - 1, PIER_Y1, -1, WALL_TOP_Z + 1))
    w = w.cut(box(AXES_X[i] + PIER_HALF, AXES_X[i + 1] - PIER_HALF, WALL_Y0 - 1, WALL_Y1 + 1, SILL_Z, WIN_TOP_Z))
    return w


def make_glazing(i):
    # остекление между линиями 161.5 и 179.0 pt -> ось Y = -545
    x0, x1 = AXES_X[i] + PIER_HALF, AXES_X[i + 1] - PIER_HALF
    return box(x0, x1, -560, -530, SILL_Z, WIN_TOP_Z)


def make_truss(ax):
    x0, x1 = ax - TR_T / 2, ax + TR_T / 2
    parts = []
    yb0, yb1 = -300.0, SPAN + 300.0
    zb = H_TRUSS + TR_W / 2
    parts.append(box(x0, x1, yb0, yb1, H_TRUSS, H_TRUSS + TR_W))           # нижний пояс
    for ya, yb in ((yb0, SPAN / 2), (SPAN / 2, yb1)):                      # верхний пояс
        parts.append(prism_yz([(ya, z_top(ya)), (yb, z_top(yb)),
                               (yb, z_top(yb) - TR_W), (ya, z_top(ya) - TR_W)], x0, x1))
    for ye in (yb0, yb1 - TR_W):                                           # торцевые стойки
        parts.append(box(x0, x1, ye, ye + TR_W, H_TRUSS + TR_W - 1, min(z_top(ye), z_top(ye + TR_W)) - 1))
    seq = [TR_BOT_NODES[0], TR_TOP_NODES[0], TR_BOT_NODES[1], TR_TOP_NODES[1], TR_BOT_NODES[2],
           TR_TOP_NODES[2], TR_BOT_NODES[3], TR_TOP_NODES[3], TR_BOT_NODES[4], TR_TOP_NODES[4],
           TR_BOT_NODES[5]]
    for k in range(len(seq) - 1):
        a, b = seq[k], seq[k + 1]
        pa = (a, zb) if k % 2 == 0 else (a, z_top(a) - TR_W / 2)
        pb = (b, zb) if k % 2 == 1 else (b, z_top(b) - TR_W / 2)
        parts.append(bar_yz(pa, pb, TR_W * 0.8, x0, x1))
    for yv in (TR_BOT_NODES[2], TR_BOT_NODES[3], TR_TOP_NODES[1], TR_TOP_NODES[3]):   # стойки
        parts.append(box(x0, x1, yv - TR_W * 0.4, yv + TR_W * 0.4, H_TRUSS + 1, z_top(yv) - 1))
    tr = union(parts)
    # срез выступающих углов раскосов над верхним поясом
    cap = prism_yz([(yb0 - 10, z_top(yb0 - 10)), (SPAN / 2, z_top(SPAN / 2)), (yb1 + 10, z_top(yb1 + 10)),
                    (yb1 + 10, 20000), (yb0 - 10, 20000)], x0 - 1, x1 + 1)
    return tr.cut(cap)


def make_roof(side):
    x0, x1 = -PIER_HALF, L_BAY + PIER_HALF
    if side == 0:
        ya, yb = WALL_Y0, LANT_Y0
    else:
        ya, yb = LANT_Y1, SPAN - WALL_Y0
    return prism_yz([(ya, z_top(ya)), (yb, z_top(yb)), (yb, z_top(yb) + ROOF_T), (ya, z_top(ya) + ROOF_T)],
                    x0, x1)


def make_lantern_wall(side):
    y0 = LANT_Y0 if side == 0 else LANT_Y1 - LANT_WALL_T
    zb = max(z_top(LANT_Y0 + LANT_WALL_T), z_top(LANT_Y0)) + 2
    return box(0, L_BAY, y0, y0 + LANT_WALL_T, zb, LANT_EAVE_Z)


def make_lantern_roof():
    k = (LANT_RIDGE_Z - LANT_EAVE_Z) / (SPAN / 2 - LANT_Y0)

    def zl(y):
        return LANT_EAVE_Z + (min(y, SPAN - y) - LANT_Y0) * k
    ya, yb, yc = LANT_Y0 - 150, SPAN / 2, LANT_Y1 + 150
    return prism_yz([(ya, zl(ya) + 30), (yb, zl(yb)), (yc, zl(yc) + 30),
                     (yc, zl(yc) + 30 + ROOF_T), (yb, zl(yb) + ROOF_T), (ya, zl(ya) + 30 + ROOF_T)],
                    0, L_BAY)


def make_aisle_marking():
    # «Проезд»: надпись y≈862 pt -> Y≈11670; разметка полосами 100 мм (принято 10000..13000)
    return union([box(0, L_BAY, 10000, 10100, 0, 5), box(0, L_BAY, 12900, 13000, 0, 5)])


# ---------------------------------------------------------------- кабины
def cab_origin(n):
    """Пост №n: (x0, y_top, y_bot, flip). Верхний ряд №1,3,5 (проём к стене), нижний №2,4,6."""
    col = (n - 1) // 2
    row = (n - 1) % 2
    x0 = CAB_X0 + col * CAB_W
    y0 = CAB_Y0 + row * CAB_D
    return x0, y0, y0 + CAB_D, row == 0


def cab_rect(n, u0, u1, v0, v1):
    x0, ya, yb, flip = cab_origin(n)
    if flip:   # проём сверху (к стене): v отсчитывается от нижней стороны
        return x0 + u0, x0 + u1, yb - v1, yb - v0
    return x0 + u0, x0 + u1, ya + v0, ya + v1


def make_cab_walls(n):
    t = CAB_WALL_T / 2
    x0, ya, yb, flip = cab_origin(n)
    X = [CAB_X0 + i * CAB_W for i in range(4)]
    Y = [CAB_Y0, CAB_Y0 + CAB_D, CAB_Y0 + 2 * CAB_D]
    grid = []
    for xx in X:
        grid.append(box(xx - t, xx + t, Y[0] - t, Y[2] + t, 0, CAB_H))
    for yy in Y:
        grid.append(box(X[0] - t, X[3] + t, yy - t, yy + t, 0, CAB_H))
    g = union(grid)
    # вырезы проёмов со шторами
    for m in range(1, 7):
        mx0, mya, myb, mflip = cab_origin(m)
        yd = mya if mflip else myb
        g = g.cut(box(mx0 + DOOR_U0, mx0 + DOOR_U1, yd - t - 1, yd + t + 1, -1, CAB_H + 1))
    # доля ширм, принадлежащая кабине n (общие перегородки делятся по оси)
    ex = 100.0
    rx0 = x0 - (ex if x0 == X[0] else 0)
    rx1 = x0 + CAB_W + (ex if x0 + CAB_W == X[3] else 0)
    ry0 = ya - (ex if flip else 0)
    ry1 = yb + (0 if flip else ex)
    return g.intersect(box(rx0, rx1, ry0, ry1, -1, CAB_H + 1))


def make_curtain(n):
    x0, ya, yb, flip = cab_origin(n)
    t = CAB_WALL_T / 2
    if flip:
        return box(x0 + DOOR_U0, x0 + DOOR_U1, ya - t - 15, ya - t - 5, 100, CAB_H)
    return box(x0 + DOOR_U0, x0 + DOOR_U1, yb + t + 5, yb + t + 15, 100, CAB_H)


def make_p7(n):
    x0, x1, y0, y1 = cab_rect(n, *P7)
    return table(x0, x1, y0, y1, H_TABLE)


def make_p9(n):
    x0, x1, y0, y1 = cab_rect(n, *P9)
    return box(x0, x1, y0, y1, 0, H_SRC)


def make_p8(n):
    u, v, r = P8_C
    x0, x1, y0, y1 = cab_rect(n, u, u, v, v)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, H_FEED, cq.Vector(x0, y0, H_SRC)))


def make_p6(n):
    x0, x1, y0, y1 = cab_rect(n, *P6)
    return shell_box(x0, x1, y0, y1, 0, H_BUNK)


def make_p5(n):
    x0, x1, y0, y1 = cab_rect(n, *P5)
    return shell_box(x0, x1, y0, y1, 0, H_BUNK)


# ---------------------------------------------------------------- оборудование участка (план)
def make_p1(part):
    # стол мастера и распреда 1748.9..1805.5 x 341.0..414.7 (Р) / 414.7..488.4 (СМ)
    y0, y1 = (341.0, 414.7) if part == "R" else (414.7, 488.4)
    return table(PX(1748.9), PX(1805.5), PY(y0) + 5, PY(y1) - 5, 750)


def make_p2():
    return table(PX(1462.1), PX(1518.5), PY(388.1), PY(487.2), 750)


def make_p2_zone():
    x0, x1, y0, y1 = PX(1441.9), PX(1595.0), PY(372.7), PY(505.9)
    return box(x0, x1, y0, y1, 0, 5).cut(box(x0 + 50, x1 - 50, y0 + 50, y1 - 50, -1, 6))


def make_p3():
    return shell_box(PX(1462.1), PX(1516.1), PY(306.5), PY(360.2), 0, 800, 8)


def make_p4():
    xc, yc = PX(265.3), PY(230.75)       # центр окружности Ø17 pt = 300 мм
    ped = cq.Solid.makeCylinder(100, 800, cq.Vector(xc, yc, 0))
    bowl = cq.Solid.makeCylinder(150, 150, cq.Vector(xc, yc, 800))
    noz = cq.Solid.makeCylinder(48, 60, cq.Vector(xc, yc, 950))
    return cq.Workplane("XY").add(ped).union(cq.Workplane("XY").add(bowl)).union(cq.Workplane("XY").add(noz))


def make_p10(k):
    if k == 1:
        x0, x1, y0, y1 = PX(361.9), PX(503.5), PY(432.2), PY(454.8)
    else:
        x0, x1, y0, y1 = PX(1631.8), PX(1773.6), PY(607.7), PY(630.2)
    base = box(x0, x1, y0, y1, 0, 150)
    board = box(x0, x1, (y0 + y1) / 2 - 40, (y0 + y1) / 2 + 40, 150, 1800)
    return base.union(board)


# ---------------------------------------------------------------- кран поз. 11
def make_end_truck(row):
    yc = LAMBDA if row == 0 else mirY(LAMBDA)
    body = box(CR_X - ET_L / 2, CR_X + ET_L / 2, yc - ET_W / 2, yc + ET_W / 2, 7700, GIRD_END_BOT_Z)
    for dx in (-1100, 1100):
        w = cq.Solid.makeCylinder(200, 100, cq.Vector(CR_X + dx, yc - 50, RAIL_TOP_Z + 200), cq.Vector(0, 1, 0))
        body = body.union(cq.Workplane("XY").add(w))
    return body


def make_girder(k):
    xc = CR_X + (k - 0.5) * GIRD_C
    # низ балки: 7990 в пролёте, у концевых балок поднят до 8260 (как на разрезе А-А)
    ya, yb = LAMBDA - ET_W / 2, mirY(LAMBDA) + ET_W / 2
    t0, t1 = GIRD_TAPER
    pts = [(ya, GIRD_TOP_Z), (ya, GIRD_END_BOT_Z), (t0, GIRD_END_BOT_Z), (t1, GIRD_BOT_Z),
           (mirY(t1), GIRD_BOT_Z), (mirY(t0), GIRD_END_BOT_Z), (yb, GIRD_END_BOT_Z), (yb, GIRD_TOP_Z)]
    return prism_yz(pts, xc - GIRD_W / 2, xc + GIRD_W / 2)


def make_trolley():
    fr = box(CR_X - TROL_X / 2, CR_X + TROL_X / 2, TROL_YC - TROL_Y / 2, TROL_YC + TROL_Y / 2,
             GIRD_TOP_Z, 9150)
    mech = box(CR_X - 360, CR_X + 360, TROL_YC - 425, TROL_YC + 425, 9150, TROL_TOP_Z)
    return fr.union(mech)


def make_ropes():
    parts = []
    for dx in (-100, 100):
        parts.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(12, GIRD_TOP_Z - 7350, cq.Vector(CR_X + dx, TROL_YC, 7350))))
    return union(parts)


def make_hook():
    blk = box(CR_X - 150, CR_X + 150, TROL_YC - 75, TROL_YC + 75, 7000, 7350)
    sh = cq.Workplane("XY").add(cq.Solid.makeCylinder(30, 110, cq.Vector(CR_X, TROL_YC, 6900)))
    tor = cq.Workplane("XY").add(cq.Solid.makeTorus(120, 30, cq.Vector(CR_X, TROL_YC, HOOK_Z + 150), cq.Vector(0, 1, 0)))
    return blk.union(sh).union(tor)


def make_slings():
    import math
    top = cq.Vector(CR_X, TROL_YC, HOOK_Z - 2)   # от зева крюка (зазор 2 мм до тора)
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = cq.Vector(CR_X + sx * (LOAD_X / 2 - 60), TROL_YC + sy * (LOAD_Y / 2 - 60), LOAD_TOP_Z + 5)
            d = p - top
            parts.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(10, d.Length, top, d.normalized())))
    # концы строп подрезаны по телу крюка и груза: касание без взаимного проникновения
    return union(parts).cut(make_hook()).cut(make_load())


def make_load():
    return box(CR_X - LOAD_X / 2, CR_X + LOAD_X / 2, TROL_YC - LOAD_Y / 2, TROL_YC + LOAD_Y / 2,
               LOAD_BOT_Z, LOAD_TOP_Z)


def make_cab():
    # кабина управления: x=591.1 pt (разрез) у правого подкранового пути; высота «1500»: 6650..8150,
    # подвешена к концевому участку главных балок (низ 8260) через подвесную раму 8150..8260
    y0, y1 = 15800.0, 16900.0
    cab = box(CR_X - 650, CR_X + 650, y0, y1, HOOK_Z, LEVEL_8150)
    hang = [box(xc - 60, xc + 60, y, y + 120, LEVEL_8150, GIRD_END_BOT_Z)
            for xc in (CR_X - GIRD_C / 2, CR_X + GIRD_C / 2) for y in (y0 + 50, y1 - 170)]
    return union([cab] + hang)


def make_obstacle():
    # габарит оборудования высотой «1500» под грузом (разрез: 486.2..572.2 pt, ширина 3030,
    # центр груза 529.4 pt) — поставлен прямо под грузом (тележка по плану), зазор 2950 по вертикали
    y0, y1 = TROL_YC - 1515.0, TROL_YC + 1515.0
    return union([box(CR_X - 750, CR_X + 750, y0, y1, 0, 490),
                  box(CR_X - 750, CR_X + 750, y0, y1, 500, 990),
                  box(CR_X - 750, CR_X + 750, y0, y1, 1000, OBST_H)])


PL_Y0, PL_Y1 = (167.5 - 114.2) * S100, (245.5 - 114.2) * S100
PL_Z0, PL_Z1 = (1569.1 - 1366.3) * S100, (1569.1 - 1351.4) * S100
PL_X0, PL_X1 = CR_X + GIRD_C / 2 - 100, CR_X + GIRD_C / 2 + 1300   # под балкой 2 (принято)


def make_platform():
    # посадочная площадка (разрез: x=167.5..245.5 pt, y=1351.4..1366.3 pt)
    # Площадка — неподвижная конструкция здания у места стоянки крана (не часть моста): на разрезе
    # она показана под мостом с подкосом, но жёсткая связь с мостом не дала бы крану двигаться.
    # Опирается на 2 стойки 120x120 до пола у кромки со стороны стены; до низа главной балки
    # остаётся зазор 7990 - 7668 = 322 мм, мост проходит над площадкой.
    y0, y1 = PL_Y0, PL_Y1
    deck = box(PL_X0, PL_X1, y0, y1, PL_Z0, PL_Z1)
    posts = [box(xc - 60, xc + 60, y0, y0 + 120, 0, PL_Z0) for xc in (PL_X0 + 60, PL_X1 - 60)]
    return union([deck] + posts)


def make_ladder():
    # тетива от кромки площадки (верх — в касание с низом настила) до пола (Z=0), по разрезу
    y2 = (296.6 - 114.2) * S100
    p1, p2 = (PL_Y1 - 150, PL_Z0 + 300), (y2 + 60, -300)
    bar = bar_yz(p1, p2, 150, PL_X1 - 650, PL_X1 - 50)
    return bar.intersect(box(PL_X1 - 700, PL_X1, 0, 20000, 0, PL_Z0))


# ---------------------------------------------------------------- цвета
C_CONC = cq.Color(0.72, 0.72, 0.70)
C_FLOOR = cq.Color(0.55, 0.55, 0.53)
C_BRICK = cq.Color(0.70, 0.45, 0.35)
C_GLASS = cq.Color(0.55, 0.75, 0.90, 0.5)
C_STEEL = cq.Color(0.45, 0.48, 0.52)
C_ROOF = cq.Color(0.50, 0.52, 0.55)
C_CRANE = cq.Color(0.95, 0.75, 0.10)
C_HOOK = cq.Color(0.20, 0.20, 0.20)
C_MARK = cq.Color(0.95, 0.85, 0.10)
C_CAB = cq.Color(0.30, 0.55, 0.40)
C_CURT = cq.Color(0.85, 0.35, 0.15, 0.8)
C_TABLE = cq.Color(0.55, 0.40, 0.25)
C_EQ = cq.Color(0.20, 0.40, 0.75)
C_BUNK = cq.Color(0.40, 0.45, 0.35)
C_FIRE = cq.Color(0.85, 0.10, 0.10)
C_LOAD = cq.Color(0.35, 0.30, 0.28)
C_WHITE = cq.Color(0.92, 0.92, 0.92)

S = "ГОСТ 2.428-84 (условные изображения на планировках); ГОСТ 21.101-97"
PARTS = []   # (key, pos, name_ru, fn, color, material, standard, note)


def P(key, pos, name, fn, color, mat="", std="", note=""):
    PARTS.append((key, pos, name, fn, color, mat, std, note))


P("pol", "", "Пол цеха (бетон)", make_floor, C_FLOOR, "бетон", "", "Z=-200..0")
for r in (0, 1):
    for i, ax in enumerate(AXES_X):
        P("kolonna_%s%d" % ("AB"[r], i + 1), "", "Колонна ж/б 800×600 (ряд %s, ось %d)" % ("АБ"[r], i + 1),
          (lambda ax=ax, r=r: make_column(ax, r)), C_CONC, "железобетон", "",
          "Сечение по плану 1:50 (45.4×34.1 pt → 802×602)")
        P("konsol_%s%d" % ("AB"[r], i + 1), "", "Консоль колонны под подкрановую балку",
          (lambda ax=ax, r=r: make_console(ax, r)), C_CONC, "железобетон", "", "размеры приняты")
    P("podkran_balka_%s" % "AB"[r], "", "Подкрановая балка", (lambda r=r: make_runway_beam(r)), C_STEEL,
      "сталь", "", "сечение 300×600 принято")
    P("rels_%s" % "AB"[r], "", "Крановый рельс КР70", (lambda r=r: make_rail(r)), C_HOOK, "сталь",
      "ГОСТ 4121-96", "h=120, подошва 120, головка 70; головка рельса Z=7525 (разрез А-А)")
for i, ax in enumerate(AXES_X):
    P("prostenok_%d" % (i + 1), "", "Простенок кирпичный (штриховка на плане)", (lambda ax=ax: make_pier(ax)),
      C_BRICK, "кирпич", "", "2000×418 по плану")
for i in range(3):
    P("stena_%d" % (i + 1), "", "Стена наружная с ленточным проёмом (пролёт %d)" % (i + 1),
      (lambda i=i: make_wall_bay(i)), C_BRICK, "кирпич", "", "толщина 597 по плану (153.4..187.2 pt)")
    P("osteklenie_%d" % (i + 1), "", "Ленточное остекление", (lambda i=i: make_glazing(i)), C_GLASS,
      "стекло", "", "высота 1200..7200 принята")
for i, ax in enumerate(AXES_X):
    P("ferma_%d" % (i + 1), "", "Стропильная ферма 18 м", (lambda ax=ax: make_truss(ax)), C_STEEL, "сталь",
      "", "геометрия по разрезу А-А (узлы по векторам)")
P("krovlya_1", "", "Кровельная плита (скат 1)", lambda: make_roof(0), C_ROOF, "ж/б плита", "", "")
P("krovlya_2", "", "Кровельная плита (скат 2)", lambda: make_roof(1), C_ROOF, "ж/б плита", "", "")
P("fonar_stena_1", "", "Фонарь — остеклённая стенка", lambda: make_lantern_wall(0), C_GLASS, "стекло", "", "")
P("fonar_stena_2", "", "Фонарь — остеклённая стенка", lambda: make_lantern_wall(1), C_GLASS, "стекло", "", "")
P("fonar_krovlya", "", "Фонарь — кровля", make_lantern_roof, C_ROOF, "сталь", "", "конёк Z=15632")
P("proezd_razmetka", "", "Проезд — разметка на полу", make_aisle_marking, C_MARK, "краска", "", "ширина 3000 принята")
P("poz02_zona_kontrolya", "", "Зона контролёра (штриховой контур на плане)", make_p2_zone, C_MARK, "краска", "", "2704×2352; разметка зоны поз.2 (не отдельное изделие)")

for n in range(1, 7):
    P("post_%d_shirmy" % n, "", "ПОСТ №%d — ширмы кабины 3000×2500" % n, (lambda n=n: make_cab_walls(n)),
      C_CAB, "сталь листовая", "ГОСТ 12.3.003-86", "h=2000, t=40 приняты; общие перегородки поделены по оси")
    P("post_%d_shtora" % n, "", "ПОСТ №%d — защитная штора в проёме" % n, (lambda n=n: make_curtain(n)),
      C_CURT, "брезент/ПВХ", "ГОСТ 12.4.023", "проём 812 мм (1:30)")
    P("poz05_bunker_othodov_post%d" % n, "5", "Бункер для отходов", (lambda n=n: make_p5(n)), C_BUNK, "сталь", "", "477×450×600")
    P("poz06_bunker_zagotovok_post%d" % n, "6", "Бункер для заготовок", (lambda n=n: make_p6(n)), C_BUNK, "сталь", "", "731×714×600")
    P("poz07_stol_svarshchika_post%d" % n, "7", "Стол сварщика", (lambda n=n: make_p7(n)), C_TABLE, "сталь", "", "1047×582×800")
    P("poz08_ustanovka_pa_post%d" % n, "8", "Установка для полуавтоматической сварки (подающий механизм)",
      (lambda n=n: make_p8(n)), C_EQ, "сталь (корпус)", "", "Ø210 по кругу «М» (1:30)")
    P("poz09_istochnik_pitaniya_post%d" % n, "9", "Источник питания", (lambda n=n: make_p9(n)), C_EQ, "сталь (корпус)", "",
      "391×291×700")

P("poz01_stol_mastera_R", "1", "Стол мастера и распреда (Р)", lambda: make_p1("R"), C_TABLE, "сталь/ДСП", "", "1000×1291")
P("poz01_stol_mastera_SM", "1", "Стол мастера и распреда (СМ)", lambda: make_p1("SM"), C_TABLE, "сталь/ДСП", "", "1000×1291")
P("poz02_stol_kontrolera", "2", "Стол контролёра (К)", make_p2, C_TABLE, "сталь/ДСП", "", "996×1750")
P("poz03_bunker_gotovyh", "3", "Бункер для готовых деталей", make_p3, C_BUNK, "сталь", "", "954×948×800")
P("poz04_fontanchik", "4", "Фонтанчик питьевой воды", make_p4, C_WHITE, "сталь нерж./керамика", "", "Ø300 по плану")
P("poz10_pozharny_shchit_1", "10", "Пожарный щит", lambda: make_p10(1), C_FIRE, "сталь", "ГОСТ 12.4.009-83", "2500×400 по плану")
P("poz10_pozharny_shchit_2", "10", "Пожарный щит", lambda: make_p10(2), C_FIRE, "сталь", "ГОСТ 12.4.009-83", "2500×400 по плану")

P("poz11_kran_koncevaya_balka_A", "11", "Кран мостовой Q=10 т — концевая балка с колёсами", lambda: make_end_truck(0), C_CRANE, "сталь", "ГОСТ 25711-83", "")
P("poz11_kran_koncevaya_balka_B", "11", "Кран мостовой Q=10 т — концевая балка с колёсами", lambda: make_end_truck(1), C_CRANE, "сталь", "ГОСТ 25711-83", "")
P("poz11_kran_glavnaya_balka_1", "11", "Кран мостовой Q=10 т — главная балка", lambda: make_girder(0), C_CRANE, "сталь", "ГОСТ 25711-83", "Lк=16500")
P("poz11_kran_glavnaya_balka_2", "11", "Кран мостовой Q=10 т — главная балка", lambda: make_girder(1), C_CRANE, "сталь", "ГОСТ 25711-83", "Lк=16500")
P("poz11_kran_telezhka", "11", "Кран — грузовая тележка", make_trolley, C_CRANE, "сталь", "", "верх Z=9600")
P("poz11_kran_kanaty", "11", "Кран — канаты", make_ropes, C_HOOK, "сталь", "ГОСТ 2688-80", "")
P("poz11_kran_kryuk", "11", "Кран — крюковая подвеска", make_hook, C_HOOK, "сталь", "ГОСТ 6627-74", "зев Z=6650")
P("poz11_kran_kabina", "11", "Кран — кабина управления", make_cab, C_CRANE, "сталь", "", "6650..8150 (h=1500), подвес к балкам 8150..8260")
P("gruz_stropy", "", "Стропы (4-ветвевой строп)", make_slings, C_HOOK, "сталь", "ГОСТ 25573-82", "1200 по разрезу; концы подрезаны по крюку и грузу (касание)")
P("gruz", "", "Груз на крюке (по разрезу А-А)", make_load, C_LOAD, "сталь (условно)", "", "h=1000, низ Z=4450")
P("gabarit_oborudovaniya", "", "Габарит оборудования под грузом (по разрезу А-А)", make_obstacle, C_LOAD, "условный габарит", "", "h=1500, под грузом, зазор 2950")
P("ploshchadka_posadochnaya", "", "Посадочная площадка крана (по разрезу А-А)", make_platform, C_STEEL, "сталь", "", "неподвижная, на 2 стойках у места стоянки крана; зазор 322 до моста")
P("lestnica", "", "Лестница на посадочную площадку", make_ladder, C_STEEL, "сталь", "", "")


# ---------------------------------------------------------------- сборка
def build():
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="Planirovka_uchastka")
    solids = {}
    for key, pos, title, fn, color, *_ in PARTS:
        # зеркалирование Y -> 18000 - Y: вид сверху совпадает с листом (стена с окнами вверху)
        wp = fn().mirror("XZ", basePointVector=(0, SPAN / 2, 0))
        solids[key] = wp
        assy.add(wp, name=key, color=color)
        cq.exporters.export(wp, os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(wp, os.path.join(OUT, "parts_stl", key + ".stl"), tolerance=2.0, angularTolerance=0.3)
    assy.save(os.path.join(OUT, NAME + ".step"))
    assy.save(os.path.join(OUT, NAME + ".glb"), tolerance=5.0, angularTolerance=0.4)
    spec = []
    for key, pos, title, fn, color, mat, std, note in PARTS:
        spec.append({"key": key, "pos": pos, "name_ru": title, "qty": 1, "material": mat,
                     "standard": std, "note": note})
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    return solids


def check(solids):
    all_bb = None
    for key, wp in solids.items():
        v = wp.val()
        assert v.isValid(), key
        assert v.Volume() > 0, key
        bb = v.BoundingBox()
        all_bb = bb if all_bb is None else all_bb.add(bb)
    print("Габарит: X %.0f..%.0f  Y %.0f..%.0f  Z %.0f..%.0f" % (
        all_bb.xmin, all_bb.xmax, all_bb.ymin, all_bb.ymax, all_bb.zmin, all_bb.zmax))
    keys = list(solids)
    bad = []
    for i in range(len(keys)):
        a = solids[keys[i]].val(); ba = a.BoundingBox()
        for j in range(i + 1, len(keys)):
            b = solids[keys[j]].val(); bb_ = b.BoundingBox()
            if (ba.xmin >= bb_.xmax or bb_.xmin >= ba.xmax or ba.ymin >= bb_.ymax
                    or bb_.ymin >= ba.ymax or ba.zmin >= bb_.zmax or bb_.zmin >= ba.zmax):
                continue
            v = a.intersect(b).Volume()
            if v > 1.0:   # > 1 мм3 (касания по граням не считаются)
                bad.append((keys[i], keys[j], v))
    for k1, k2, v in bad:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.0f мм3" % (k1, k2, v))
    print("деталей:", len(keys), " пересечений:", len(bad))
    return bad


if __name__ == "__main__":
    s = build()
    check(s)
    print("GLB, байт:", os.path.getsize(os.path.join(OUT, NAME + ".glb")))
