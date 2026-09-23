# -*- coding: utf-8 -*-
"""
3D-модель: "Приспособление сварочное №1" (лист 6 дипломного проекта
"Технология сборки-сварки корпуса задвижки трубопровода", М 1:1).

Назначение (маршрутный техпроцесс, лист 5, операция 020): установка стакана
(поз.2 корпуса) и двух направляющих (поз.5 корпуса), прижим направляющих
к внутренней стенке стакана и прихватка.  Два оппозитных пневмоцилиндра
(Ø60) через штоки и рычаги (поз.4) разводят толкатели (поз.3), которые
прижимают направляющие к стенке стакана.  Верхняя часть приспособления
поворачивается на основании (поз.14); воздух подводится через
вращающееся соединение (ось поз.12 во втулке поз.13).

Система координат: Z вверх, начало - центр нижней плоскости основания,
X - ось пневмоцилиндров (вправо на главном виде), Y - от наблюдателя
главного вида (вверх на виде сверху).  Размеры - мм.

Запуск:  python3 build.py
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
NAME = "prisposoblenie_svarochnoe_1"

# ===========================================================================
# ИСХОДНЫЕ РАЗМЕРЫ (лист 6).  "изм." - измерено по векторной геометрии PDF
# (1 pt = 0.3528 мм, М1:1), "*" - справочный размер чертежа.
# ===========================================================================
# --- Вертикальная цепочка -------------------------------------------------
Z_AX = 128.0          # ось пневмоцилиндров: 128±0,5 (вид слева)
Z_TOP_JAW = 278.0     # верх губок: габарит 278 (вид слева)
# Главный разрез построен на 1,15..1,2 мм "ниже" размеров 128 и 278 -
# узлы выше основания подняты на эту величину (см. NOTES.md).

# --- Основание поз.14 -----------------------------------------------------
B_R_OUT = 106.0       # Ø212 (вид сверху; разрез: R105,8)
B_R_IN = 93.2         # Ø186 (разрез)
B_H = 72.0            # 72 (разрез)
B_EAR_T = 15.0        # 15 - толщина лап
B_FLOOR = (55.0, 64.0)  # дно: 9* (изм. 55,3..64,0)
B_REC_R = 89.2        # расточка под фланец корпуса Ø178,4 (изм.)
B_BORE_R = 25.3       # отверстие под втулку Ø50,6 (изм.)
B_FLR_R = 75.3        # внутр. кромка кольцевого дна (изм.)
B_HUB_R = 31.0        # ступица (принято)
B_RIB = 12.0          # толщина рёбер (принято)
EAR_X = 140.0         # конец лапы: 21 + паз (вид сверху, изм. 140,4)
EAR_W_TIP = 17.8      # полуширина лапы на конце (изм.)
EAR_TAN = (93.7, 49.2)  # точка касания кромки лапы с окружностью Ø212 (изм.)
SLOT_W = 12.0         # паз 12* (вид слева)
SLOT_XC = 125.0       # центр R6 паза (изм. 125,1)
WIN_Z = (7.0, 47.0)   # окно в стенке основания: 40 (вид слева, изм. 7,1..47,2)
WIN_HALF_X = 20.0     # полуширина окна - принято
FIT_Z = 38.0          # ось штуцера: 38 (вид слева)

# --- Кольцо поз.11 и винты поз.21 -----------------------------------------
R11 = (84.1, 106.0)   # изм.
Z11 = (72.0, 81.0)    # 9* (разрез)
PCD21 = 194.0         # Ø194 (вид сверху) - окружность винтов поз.21
N21 = 6               # 6 винтов через 60° (видны под 180°, 0°, -60°, -120°)

# --- Корпус поз.7 ---------------------------------------------------------
H_FL = (89.0, 64.0, 72.0)     # фланец Ø178 (зазор 0,2 к расточке основания)
H_SKIRT_R = 84.0              # юбка в кольце поз.11 (Ø168,2 изм.)
H_LOW = (85.0, Z_AX - 45.0, 123.0)  # нижний пояс Ø170 (вид слева ±84,8), R5
H_UP_R = 74.0                 # верхний пояс Ø148 (вид сверху R74, вид слева ±73,9)
H_TOP = Z_AX + 45.0 + 5.0     # 5* - выступ над цилиндрами (178)
CYL_R = 45.0                  # Ø90* - цилиндры/крышки
CYL_END = 154.1               # торец цилиндра (изм.)
BORE_R = 30.0                 # Ø60 H9/f9
BORE_X0 = 89.2                # дно расточки (изм.)
STOP = (93.2, 21.75, 16.75)   # упорный бурт (изм. Ø43,5 -> Ø33,5)
ROD_R = 12.0                  # Ø24 H7/h6
CAV1 = (52.2, Z_AX - 14.95, Z_AX + 33.95)   # полость Ø104,4 (изм.)
CAV2 = (49.0, Z_AX + 33.95, H_TOP)          # полость Ø98 (изм.)
OPEN_R = (75.3, 71.3)          # нижняя расточка корпуса (изм.)
G26 = (83.1, 88.0, 17.0)       # канавка кольца поз.26 (изм.)
CH_CAP_Z = 87.85               # канал к бесштоковой полости (изм.)
CH_ROD_Z = 100.35              # канал к штоковой полости (изм.)
CH_D = 5.0                     # Ø5*
CH_VX = 151.5                  # подъём канала в крышку (изм. 149..153,2)
PCD19 = 75.0                   # Ø75 (вид слева)
N19 = 5                        # 5 болтов через 72°

# --- Крышка поз.10, прокладка поз.9 ---------------------------------------
COV_X = (155.1, 164.1)         # фланец крышки (изм.)
GASK_X = (154.1, 155.1)        # прокладка 1 мм (изм. 0,9)
SPIG = (149.0, 29.95)          # Ø60 Js7/h7 - центрирующий поясок
RECESS_R = 20.0                # выточка Ø40 (изм. 39,96)
TAB = (Z_AX - 44.0, 5.0)       # прилив внизу крышки R5 (вид слева)

# --- Поршень поз.8, шток --------------------------------------------------
PIST = (97.0, 116.2)           # изм.; 55* - от бурта до крышки
PIST_R = 29.95                 # Ø60 f9
G27 = (104.1, 109.1, 25.0)     # канавка кольца поз.27
ROD_END = 9.4                  # торец штока (изм.)
ROD_HOLE = (22.0, 6.0)         # поперечное отверстие Ø12 под шаровую головку рычага
ROD_SPIG = (12.0, 8.0)         # резьбовой хвостовик М16, 12 мм - принято

# --- Ось поворотная поз.12, втулка поз.13, шайба поз.15, гайки поз.23 -----
S12_FL = (71.2, 83.0, Z_AX - 14.95)   # фланец Ø142,6 (изм.), верх = пол полости
SH_R = 15.0                    # Ø30 H6/m6
SH_Z0 = 25.9                   # торец втулки/заплечик оси (изм.)
THR = (6.0, 4.0)               # М12, конец резьбы z=4 (изм.)
G25 = [(25.9, 30.9), (51.0, 56.0), (76.0, 81.0)]  # канавки колец поз.25 (изм.)
G25_R = 10.15
AIR_G = [(35.7, 40.8, 7.7), (64.8, 69.8, 7.8)]     # кольцевые проточки (изм.); 12,5 и 29
VCH = [(-5.05, 31.2), (5.1, 57.1)]  # вертикальные каналы Ø5 (x, низ)
PLUG_Z = 6.2                   # заглушка Ø5 H8/u8 (изм. 105,7..111,9)
SL = (25.3, 15.0, 25.9, 81.0)  # втулка поз.13: R нар, R вн, z низ, z верх
BOSS = (10.0, 26.0, 51.0, 54.5)  # прилив под штуцер: ±x, z0, z1, торец Y (вид слева)
D15 = (25.3, 6.3, 20.9, 25.9)  # шайба поз.15
NUT23 = (18.0, 6.0)            # гайка М12 ГОСТ 5916-70: S=18; m=6 по чертежу (изм. 8,9..14,9..20,9)

# --- Верхний узел (главный разрез + 1,2 мм) -------------------------------
Z5 = (173.2, H_TOP, 193.0)     # поз.5: низ пояска, низ/верх фланца 15*
R5 = (49.0, 74.0, 56.0, 44.2)  # Ø98, Ø148, Ø112 Js6, Ø88 H8
Z_BR = (226.2, 241.9, 250.6, 258.0)  # мост: низ, дно Т-паза, уступ, верх (80 от плоскости корпуса, вид слева)
T_SLOT = (27.1, 19.1)          # Т-паз: 54*, 38* (вид слева) + зазор 0,1
PCD5 = 126.0                   # Ø126 - винты фланца поз.5 (вид сверху)
Z_PIN8 = Z5[1] + 30.0 - 0.3    # штифт Ø8 H7/m8: 30±0,5 от плоскости корпуса
Z_PIV = 188.1                  # ось рычага Ø8 (изм. 186,9 + 1,2)
X_PIV = 22.0                   # 44±1
L_BLK = (44.1, 178.0, 198.0, 8.1, 37.2, 6.0)  # опора рычагов Ø88 f9
J = (56.1, 63.3, 194.8, 63.3)  # опора: x_in, x_out, z низ (зазор 2), ±y
Z_ST = 267.2                   # ось стакана (изм. 266,0 + 1,2)
ST_R = (66.5, 61.5)            # стакан Ø133×5 (изм. Ø132,2×4,9)
ST_Y = (-70.0, 140.0)          # длина стакана 210 (вид слева изм.); 246 = 140 + R106 основания
ST_HOLE_R = 56.0               # отверстия под патрубки (стенка обрывается на x=±56,1)
GD = (61.0, 53.0, 260.0, 274.0, -62.0, 131.1)  # направляющая 8×14×193,1 (изм.; 8 от торца стакана)
JAW = (66.6, 76.0, 212.7, 225.3, -70.0, 140.0)  # губки: R вн, R нар, низ, низ в середине
PUSH = (32.9, 41.0)            # толкатель: внутр. торец, полудлина (вид сверху)
LEV_T = 5.0                    # полутолщина рычага (принято)

PARTS = []   # (key, pos, name_ru, qty_in_node, material, standard, note, solid, color)
SPEC = {}


def C(r, g, b, a=1.0):
    return cq.Color(r, g, b, a)


STEEL = C(0.62, 0.64, 0.68)
STEEL_D = C(0.45, 0.47, 0.52)
BODY = C(0.30, 0.45, 0.62)
BASEC = C(0.35, 0.38, 0.42)
RUBBER = C(0.08, 0.08, 0.08)
BRASS = C(0.80, 0.65, 0.25)
FAST = C(0.25, 0.25, 0.28)
RED = C(0.75, 0.25, 0.20)
GREEN = C(0.30, 0.55, 0.35)
WORK = C(0.72, 0.72, 0.72, 0.45)
WORK2 = C(0.85, 0.55, 0.20, 0.8)


# ===========================================================================
# ПРИМИТИВЫ
# ===========================================================================
def V(x, y, z):
    return cq.Vector(x, y, z)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p, d, h):
    return cq.Solid.makeCylinder(r, h, V(*p), V(*d))


def cylX(r, x0, x1, y=0.0, z=Z_AX):
    return cyl(r, (min(x0, x1), y, z), (1, 0, 0), abs(x1 - x0))


def cylY(r, y0, y1, x=0.0, z=Z_AX):
    return cyl(r, (x, min(y0, y1), z), (0, 1, 0), abs(y1 - y0))


def cylZ(r, z0, z1, x=0.0, y=0.0):
    return cyl(r, (x, y, min(z0, z1)), (0, 0, 1), abs(z1 - z0))


def cone(r0, r1, p, d, h):
    return cq.Solid.makeCone(r0, r1, h, V(*p), V(*d))


def rev_z(pts):
    """Тело вращения вокруг оси Z; pts = [(r, z), ...] (замкнутый контур)."""
    w = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return w.val()


def rev_x(pts, z=Z_AX, y=0.0):
    """Тело вращения вокруг оси, параллельной X; pts = [(x, r), ...]."""
    w = cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (1, 0, 0))
    return w.val().translate(V(0, y, z))


def prism_xz(pts, y0, y1):
    """Призма: контур в плоскости XZ, выдавливание по Y от y0 до y1."""
    w = cq.Workplane("XZ", origin=(0, y1, 0)).polyline(pts).close().extrude(y1 - y0)
    return w.val()


def prism_yz(pts, x0, x1):
    """Призма: контур в плоскости YZ (y, z), выдавливание по X."""
    w = cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(x1 - x0)
    return w.val()


def hexprism(s, p, d, h):
    """Шестигранник под ключ s, ось d (единичный вектор по оси)."""
    e = s / math.cos(math.radians(30))
    w = cq.Workplane("XY").polygon(6, e).extrude(h).val()
    return orient(w, p, d)


def orient(shape, p, d):
    """Повернуть тело, построенное вдоль +Z от начала, на ось d и перенести в p."""
    d = tuple(d)
    if d == (0, 0, 1):
        s = shape
    elif d == (0, 0, -1):
        s = shape.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    elif d == (1, 0, 0):
        s = shape.rotate(V(0, 0, 0), V(0, 1, 0), 90)
    elif d == (-1, 0, 0):
        s = shape.rotate(V(0, 0, 0), V(0, 1, 0), -90)
    elif d == (0, 1, 0):
        s = shape.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    elif d == (0, -1, 0):
        s = shape.rotate(V(0, 0, 0), V(1, 0, 0), 90)
    else:
        raise ValueError(d)
    return s.translate(V(*p))


def U(*sh):
    s = sh[0]
    for o in sh[1:]:
        s = s.fuse(o)
    return s.clean()


def cut(s, *tools):
    for t in tools:
        s = s.cut(t)
    return s.clean()


def mir(s):
    return s.mirror("YZ")


def single(s):
    """Вернуть единственное тело (Solid) из результата булевой операции."""
    sols = s.Solids()
    if len(sols) == 1:
        return sols[0]
    return cq.Compound.makeCompound(sols)


def add(key, pos, name, solid, color, material="Сталь 45 ГОСТ 1050-2013",
        standard="", note="", group=None):
    solid = single(solid)
    assert solid.isValid(), key
    PARTS.append((key, solid, color))
    g = group or key
    if g not in SPEC:
        SPEC[g] = {"key": g, "pos": pos, "name_ru": name, "qty": 0,
                   "material": material, "standard": standard, "note": note}
    SPEC[g]["qty"] += 1


# ===========================================================================
# КРЕПЁЖ ПО ГОСТ
# ===========================================================================
def bolt_hex(d, L, s, k, p, dvec):
    """Болт с шестигранной головкой ГОСТ 7798-70; p - опорная плоскость головки,
    dvec - направление стержня."""
    head = hexprism(s, (0, 0, -k), (0, 0, 1), k)
    head = head.intersect(cone(s * 0.5, s * 0.5 + 1.73 * k, (0, 0, -k), (0, 0, 1), k))  # фаска 30°
    shank = cylZ(d / 2, 0, L - 0.8).fuse(cone(d / 2, d / 2 - 0.8, (0, 0, L - 0.8), (0, 0, 1), 0.8))
    return orient(U(head, shank), p, dvec)


def screw_cheese(d, L, D, k, n, t, p, dvec):
    """Винт с цилиндрической головкой ГОСТ 1491-80 (шлиц n×t)."""
    head = cylZ(D / 2, -k, 0)
    head = cut(head, box(-n / 2, n / 2, -D, D, -k, -k + t))
    shank = cylZ(d / 2, 0, L - 0.5).fuse(cone(d / 2, d / 2 - 0.5, (0, 0, L - 0.5), (0, 0, 1), 0.5))
    return orient(U(head, shank), p, dvec)


def screw_round(d, L, D, k, n, t, p, dvec):
    """Винт с полукруглой головкой ГОСТ 17473-80."""
    R = (D * D / 4 + k * k) / (2 * k)
    sph = cq.Solid.makeSphere(R, V(0, 0, R - k), angleDegrees1=-90, angleDegrees2=90)
    head = sph.intersect(cylZ(D / 2, -k - 0.01, 0))
    head = cut(head, box(-n / 2, n / 2, -D, D, -k - 1, -k + t))
    shank = cylZ(d / 2, 0, L)
    return orient(U(head, shank), p, dvec)


def nut_hex(s, m, d, p, dvec):
    """Гайка шестигранная (фаски 30° с двух сторон)."""
    h = hexprism(s, (0, 0, 0), (0, 0, 1), m)
    ch = cone(s * 0.5 - 0.1, s * 0.5 + 0.9 * m, (0, 0, 0), (0, 0, 1), m).intersect(
        cone(s * 0.5 + 0.9 * m, s * 0.5 - 0.1, (0, 0, 0), (0, 0, 1), m))
    h = h.intersect(ch.fuse(cylZ(s * 0.5 - 0.1, 0, m)))
    h = cut(h, cylZ(d / 2, -1, m + 1))
    return orient(h, p, dvec)


def oring_x(d1, d2, x, ax_z=Z_AX, y=0.0):
    """Кольцо ГОСТ 9833-73 в свободном состоянии, ось || X."""
    return cq.Solid.makeTorus(d1 / 2 + d2 / 2, d2 / 2, V(x, y, ax_z), V(1, 0, 0))


def oring_z(d1, d2, z, x=0.0, y=0.0):
    return cq.Solid.makeTorus(d1 / 2 + d2 / 2, d2 / 2, V(x, y, z), V(0, 0, 1))


def polar_yz(r, ang_deg, x):
    """Точка на окружности r в плоскости YZ (угол от +Z, по часовой при виде слева)."""
    a = math.radians(ang_deg)
    return (x, r * math.sin(a), Z_AX + r * math.cos(a))


BOLT_ANG = [0, 72, 144, 216, 288]    # болты поз.19: верхний на вертикали (вид слева)


# ===========================================================================
# ДЕТАЛИ
# ===========================================================================
def make_base():
    """Основание поз.14 (литое): стакан Ø212/Ø186, дно с отверстием под втулку,
    расточка Ø178 под фланец корпуса, две лапы с пазами 12, окна под штуцера."""
    prof = [(B_FLR_R, B_FLOOR[0]), (B_R_IN, B_FLOOR[0]), (B_R_IN, 0.0), (B_R_OUT, 0.0),
            (B_R_OUT, B_H), (B_REC_R, B_H), (B_REC_R, B_FLOOR[1]), (B_FLR_R, B_FLOOR[1])]
    s = rev_z(prof)
    # ступица под втулку поз.13 и 4 ребра (на разрезе вдоль ребра не штрихуются - ГОСТ 2.305)
    s = s.fuse(cylZ(B_HUB_R, B_FLOOR[0], B_FLOOR[1]))
    for a in (0, 90):
        s = s.fuse(box(-B_FLR_R - 1, B_FLR_R + 1, -B_RIB / 2, B_RIB / 2, B_FLOOR[0], B_FLOOR[1])
                   .rotate(V(0, 0, 0), V(0, 0, 1), a))
    s = s.cut(cylZ(B_BORE_R, B_FLOOR[0] - 1, B_FLOOR[1] + 1))
    for sgn in (1, -1):
        ear = cq.Workplane("XY").polyline([
            (sgn * EAR_X, -EAR_W_TIP), (sgn * EAR_X, EAR_W_TIP), (sgn * EAR_TAN[0], EAR_TAN[1]),
            (sgn * 60.0, EAR_TAN[1]), (sgn * 60.0, -EAR_TAN[1]), (sgn * EAR_TAN[0], -EAR_TAN[1])
        ]).close().extrude(B_EAR_T).val()
        ear = cut(ear, cylZ(B_R_IN, -1, B_EAR_T + 1))
        s = s.fuse(ear)
        slot = U(box(min(sgn * SLOT_XC, sgn * (EAR_X + 1)), max(sgn * SLOT_XC, sgn * (EAR_X + 1)),
                     -SLOT_W / 2, SLOT_W / 2, -1, B_EAR_T + 1),
                 cylZ(SLOT_W / 2, -1, B_EAR_T + 1, x=sgn * SLOT_XC))
        s = s.cut(slot)
        # окно в стенке (вид слева, размер 40)
        s = s.cut(box(-WIN_HALF_X, WIN_HALF_X, sgn * 80.0, sgn * 110.0, WIN_Z[0], WIN_Z[1]) if sgn > 0
                  else box(-WIN_HALF_X, WIN_HALF_X, -110.0, -80.0, WIN_Z[0], WIN_Z[1]))
    # резьбовые отверстия М6 под винты поз.21 (по наружному Ø резьбы)
    for i in range(N21):
        a = math.radians(i * 360 / N21)
        x, y = PCD21 / 2 * math.cos(a), PCD21 / 2 * math.sin(a)
        s = s.cut(cylZ(3.0, B_H - 12.0, B_H + 1, x, y))
    return s.clean()


def make_ring11():
    s = rev_z([(R11[0], Z11[0]), (R11[1], Z11[0]), (R11[1], Z11[1]), (R11[0], Z11[1])])
    for i in range(N21):
        a = math.radians(i * 360 / N21)
        x, y = PCD21 / 2 * math.cos(a), PCD21 / 2 * math.sin(a)
        s = s.cut(cylZ(3.3, Z11[0] - 1, Z11[1] + 1, x, y))
        s = s.cut(cylZ(5.5, Z11[1] - 4.1, Z11[1] + 1, x, y))
    return s.clean()


def make_housing():
    """Корпус поз.7: литое тело вращения + два цилиндра Ø90 вдоль X."""
    # (CAV2 -> CAV1 ступень на z=CAV2[1]; от CAV1 до низа полости)
    prof = [(OPEN_R[0], H_FL[1]), (H_FL[0], H_FL[1]), (H_FL[0], H_FL[2]),
            (H_SKIRT_R, H_FL[2]), (H_SKIRT_R, H_LOW[1]), (H_LOW[0], H_LOW[1])] + \
        [(H_LOW[0], H_LOW[2] - 5.0)] + \
        [(H_LOW[0] - 5 + 5 * math.cos(math.radians(90 * i / 8)),
          H_LOW[2] - 5 + 5 * math.sin(math.radians(90 * i / 8))) for i in range(1, 9)] + \
        [(H_UP_R, H_LOW[2]), (H_UP_R, H_TOP), (CAV2[0], H_TOP), (CAV2[0], CAV2[1]),
         (CAV1[0], CAV2[1]), (CAV1[0], CAV1[1]), (OPEN_R[1], CAV1[1]),
         (OPEN_R[1], 80.75), (OPEN_R[0], 76.75)]
    body = rev_z(prof)
    wings = cylX(CYL_R, -CYL_END, CYL_END)
    wings = cut(wings, cylZ(CAV1[0], CAV1[1] - 30, CAV1[1]))    # не заполнять низ под осью 12
    s = body.fuse(wings)
    # полость (повтор - цилиндры заполнили её)
    s = s.cut(cylZ(CAV1[0], CAV1[1], CAV1[2]))
    s = s.cut(cylZ(CAV2[0], CAV2[1] - 0.01, H_TOP + 1))
    s = s.cut(cylZ(OPEN_R[1], 70, CAV1[1] + 0.001))
    for sg in (1, -1):
        s = s.cut(cylX(BORE_R, sg * BORE_X0, sg * (CYL_END + 1)))
        # упорный бурт (усечённый конус) оставляем - он часть корпуса: вырезаем
        # кольцевое пространство между буртом и стенкой расточки
        ring = cylX(BORE_R, sg * STOP[0], sg * BORE_X0)
        bur = cone(STOP[1], STOP[2], (sg * BORE_X0, 0, Z_AX), (sg, 0, 0), STOP[0] - BORE_X0)
        s = s.cut(ring.cut(bur))
        s = s.cut(cylX(ROD_R, sg * 44.0, sg * (STOP[0] + 0.5)))
        s = s.cut(cylX(G26[2], sg * G26[0], sg * G26[1]))
        # каналы подвода воздуха
        s = s.cut(cylX(CH_D / 2, sg * (OPEN_R[1] - 1), sg * CH_VX, z=CH_CAP_Z))
        s = s.cut(cylZ(2.0, CH_CAP_Z, Z_AX - BORE_R + 0.5, x=sg * CH_VX))
        s = s.cut(cylX(CH_D / 2, sg * (OPEN_R[1] - 1), sg * (BORE_X0 + 0.5), z=CH_ROD_Z))
        # резьбовые отверстия М6 под болты поз.19
        for a in BOLT_ANG:
            p = polar_yz(PCD19 / 2, a, sg * CYL_END)
            s = s.cut(cylX(3.0, sg * (CYL_END - 12.0), sg * (CYL_END + 1), y=p[1], z=p[2]))
    # резьбовые отверстия М6 под винты фланца поз.5 (Ø126)
    for i in range(6):
        a = math.radians(i * 60)
        s = s.cut(cylZ(3.0, H_TOP - 14.0, H_TOP + 1, PCD5 / 2 * math.cos(a), PCD5 / 2 * math.sin(a)))
    return s.clean()


def make_cover(sg):
    """Крышка цилиндра поз.10 (sg=-1 левая, +1 правая)."""
    x0, x1 = COV_X
    s = cylX(CYL_R, sg * x0, sg * x1)
    s = s.fuse(cylX(TAB[1], sg * x0, sg * x1, z=TAB[0]))
    s = s.fuse(cylX(SPIG[1], sg * SPIG[0], sg * x0))
    s = s.cut(cylX(RECESS_R, sg * SPIG[0] - sg * 1, sg * (x0 - 0.1)))
    for a in BOLT_ANG:
        p = polar_yz(PCD19 / 2, a, 0)
        s = s.cut(cylX(3.3, sg * (x0 - 1), sg * (x1 + 1), y=p[1], z=p[2]))
    # канал из корпуса в выточку крышки
    s = s.cut(cylZ(2.0, Z_AX - SPIG[1] - 1, Z_AX - RECESS_R + 1, x=sg * CH_VX))
    return s.clean()


def make_gasket(sg):
    s = cylX(CYL_R, sg * GASK_X[0], sg * GASK_X[1]).cut(cylX(BORE_R, sg * 150, sg * 160))
    for a in BOLT_ANG:
        p = polar_yz(PCD19 / 2, a, 0)
        s = s.cut(cylX(3.3, sg * 150, sg * 160, y=p[1], z=p[2]))
    return s.clean()


def make_piston(sg):
    s = cylX(PIST_R, sg * PIST[0], sg * PIST[1])
    s = s.cut(cylX(PIST_R + 1, sg * G27[0], sg * G27[1]).cut(cylX(G27[2], sg * 100, sg * 112)))
    s = s.cut(cylX(ROD_SPIG[1], sg * PIST[0] - sg * 0.5, sg * (PIST[0] + ROD_SPIG[0])))
    return s.clean()


def make_rod(sg):
    """Шток: Ø24, поперечное отверстие Ø12 под шаровую головку рычага,
    резьбовой хвостовик М16 в поршне."""
    s = rev_x([(ROD_END, 0), (ROD_END, ROD_R - 2), (ROD_END + 2, ROD_R), (PIST[0], ROD_R),
               (PIST[0], ROD_SPIG[1]), (PIST[0] + ROD_SPIG[0] - 1, ROD_SPIG[1]),
               (PIST[0] + ROD_SPIG[0], ROD_SPIG[1] - 1), (PIST[0] + ROD_SPIG[0], 0)])
    if sg < 0:
        s = mir(s)
    xh = sg * ROD_HOLE[0]
    s = s.cut(cylZ(ROD_HOLE[1], Z_AX - 20, Z_AX + 20, x=xh))
    s = s.cut(cone(ROD_HOLE[1], ROD_HOLE[1] + 1.6, (xh, 0, Z_AX + ROD_R - 1.5), (0, 0, 1), 1.6))
    s = s.cut(cone(ROD_HOLE[1], ROD_HOLE[1] + 1.6, (xh, 0, Z_AX - ROD_R + 1.5), (0, 0, -1), 1.6))
    return s.clean()


def make_lever(sg):
    """Рычаг поз.4: нижняя шаровая головка Ø12 (в штоке), бобышка Ø16 с
    отверстием Ø8 под ось поз.6, верхняя шаровая головка Ø10 (в толкателе)."""
    zb = Z_AX
    pv = (-X_PIV, Z_PIV)
    up = (-46.0, 246.9)
    t = LEV_T
    low = prism_xz([(-24.38, zb + 5.4), (-29.89, 187.24), (-13.97, 187.24), (-19.30, zb + 5.3)], -t, t)
    boss = cylY(8.0, -t, t, x=pv[0], z=pv[1])
    upper = prism_xz([(-29.80, 186.6), (-45.55, 241.9), (-41.74, 244.3), (-14.82, 191.7)], -t, t)
    b1 = cq.Solid.makeSphere(6.0, V(-22.0, 0, zb), angleDegrees1=-90, angleDegrees2=90)
    b2 = cq.Solid.makeSphere(5.0, V(up[0], 0, up[1]), angleDegrees1=-90, angleDegrees2=90)
    s = U(low, boss, upper, b1, b2)
    s = s.cut(cylY(4.0, -t - 1, t + 1, x=pv[0], z=pv[1]))
    s = s.clean()
    return s if sg < 0 else mir(s)


def make_pivot_pin(sg):
    """Ось рычага поз.6: Ø8, длина 96 (через опору рычагов в стенку поз.5)."""
    s = rev_x([(0, 0), (0, 3.5), (0.5, 4.0), (95.5, 4.0), (96.0, 3.5), (96.0, 0)], z=0)
    s = s.rotate(V(0, 0, 0), V(0, 0, 1), 90).translate(V(sg * X_PIV, -48.0, Z_PIV))
    return s


def make_lever_support():
    """Опора рычагов (без номера позиции): диск Ø88 f9 с двумя пазами под рычаги."""
    r, z0, z1, xi, xo, hy = L_BLK
    s = cylZ(r, z0, z1)
    for sg in (1, -1):
        s = s.cut(box(min(sg * xi, sg * xo), max(sg * xi, sg * xo), -hy, hy, z0 - 1, z1 + 1))
        s = s.cut(cylY(4.0, -50, 50, x=sg * X_PIV, z=Z_PIV))
    return s.clean()


def make_part5():
    """Корпус толкателей поз.5: центрирующий поясок Ø98, фланец Ø148×15,
    труба Ø112 Js6 / Ø88 H8, мост с Т-пазом (54*/38*) для толкателей и окнами
    под рычаги."""
    s = rev_z([(R5[3], Z5[0]), (R5[0], Z5[0]), (R5[0], Z5[1]), (R5[1], Z5[1]), (R5[1], Z5[2]),
               (R5[2], Z5[2]), (R5[2], Z_BR[0]), (R5[3], Z_BR[0])])
    bridge = box(-R5[2], R5[2], -R5[2], R5[2], Z_BR[0] - 0.5, Z_BR[3])
    keep = cylZ(R5[2], Z_BR[0] - 1, Z_BR[3] + 1).fuse(cylY(60.8, -70, 70, z=Z_ST))
    bridge = bridge.intersect(keep)
    s = s.fuse(bridge)
    # Т-паз вдоль X
    s = s.cut(box(-80, 80, -T_SLOT[0], T_SLOT[0], Z_BR[1], Z_BR[2]))
    s = s.cut(box(-80, 80, -T_SLOT[1], T_SLOT[1], Z_BR[2] - 0.1, Z_BR[3] + 1))
    # окна под рычаги (контур главного разреза) и расточка Ø88 насквозь
    for sg in (1, -1):
        w = prism_xz([(sg * 8.97, Z_BR[0] - 2), (sg * 8.97, Z_BR[0]), (sg * 12.95, Z_BR[1] + 0.1),
                      (sg * 53.17, Z_BR[1] + 0.1), (sg * 44.2, Z_BR[0]), (sg * 44.2, Z_BR[0] - 2)], -7, 7)
        s = s.cut(w)
    s = s.cut(cylZ(R5[3], Z5[0] - 1, Z_BR[0] - 0.01))
    # фаска верхних кромок моста по Y (вид слева)
    for sy in (1, -1):
        s = s.cut(prism_yz([(sy * 52.2, Z_BR[3] + 0.01), (sy * 57, Z_BR[3] + 0.01), (sy * 57, Z_BR[3] - 4.0)],
                           -80, 80))
    # отверстия: штифты Ø8 (к опорам), оси рычагов Ø8, винты фланца
    for sg in (1, -1):
        s = s.cut(cylX(4.0, sg * 45.3, sg * 60, z=Z_PIN8))
        s = s.cut(cylY(4.0, -48.0, 48.0, x=sg * X_PIV, z=Z_PIV))
    for i in range(6):
        a = math.radians(i * 60)
        x, y = PCD5 / 2 * math.cos(a), PCD5 / 2 * math.sin(a)
        s = s.cut(cylZ(3.3, Z5[1] - 1, Z5[2] + 1, x, y))
        s = s.cut(cylZ(6.0, Z5[2] - 4.1, Z5[2] + 1, x, y))
    return s.clean()


def make_support_J(sg):
    """Опора стакана (без номера позиции): планка 7,2 мм с ложементом R66,5,
    штифтуется к поз.5 штифтом Ø8 H7/m8."""
    xi, xo, z0, hy = J
    s = box(xi, xo, -hy, hy, z0, Z_ST)
    s = s.cut(cylY(ST_R[0] + 0.05, -hy - 1, hy + 1, z=Z_ST))
    s = s.cut(cylX(4.0, xi - 1, xo + 1, z=Z_PIN8))
    s = s.clean()
    return s if sg > 0 else mir(s)


def make_jaw(sg):
    """Губка (ложемент) поз.1: сектор R66,6..R76 вокруг оси стакана,
    длина 212, в средней части (|y|<63,3) - вырез под механизм."""
    ri, ro, zb, zbm, y0, y1 = JAW
    s = cylY(ro, y0, y1, z=Z_ST).cut(cylY(ri, y0 - 1, y1 + 1, z=Z_ST))
    s = s.intersect(box(-ro - 1, 0, y0, y1, zb, Z_TOP_JAW))
    s = s.cut(box(-J[1], 1, -J[3], J[3], zb - 1, Z_TOP_JAW + 1))
    s = s.cut(box(-ro - 1, 1, -J[3], J[3], zb - 1, zbm))
    s = s.clean()
    return s if sg < 0 else mir(s)


def make_pusher(sg):
    """Толкатель поз.3: Т-образный хвостовик в пазу поз.5, гнездо под верхнюю
    головку рычага, паз под направляющую изделия."""
    prof = [(-PUSH[0], 242.0), (-PUSH[0], GD[3]), (-GD[1], GD[3]), (-GD[1], GD[2]),
            (-59.1, GD[2]), (-59.1, 259.85), (-55.9, 242.0)]
    s = prism_xz(prof, -PUSH[1], PUSH[1])
    tee = U(box(-80, 0, -27.0, 27.0, 241.0, Z_BR[2] - 0.1),
            box(-80, 0, -19.0, 19.0, Z_BR[2] - 0.2, Z_BR[3] + 0.1),
            box(-80, 0, -PUSH[1], PUSH[1], Z_BR[3] + 0.1, 290))
    s = s.intersect(tee)
    pocket = prism_xz([(-53.17, 240), (-53.17, 256.8), (-40.47, 256.8), (-40.47, 245.7),
                       (-38.35, 242.0), (-38.35, 240)], -6.0, 6.0)
    s = s.cut(pocket)
    # резьбовые отверстия М3: винты поз.22 (сверху) и поз.16 (торец)
    for y in (-11.7, 11.7):
        s = s.cut(cylZ(1.5, GD[3] - 8.0, GD[3] + 1, x=-45.3, y=y))
    for x in (-48.9, -39.0):
        s = s.cut(cylY(1.5, -PUSH[1] - 1, -PUSH[1] + 8.0, x=x, z=266.0))
    s = s.clean()
    return s if sg < 0 else mir(s)


def make_plate2(sg):
    """Планка поз.2: прижимает направляющую сверху; отогнутый край у стенки стакана."""
    t0, t1 = GD[3], GD[3] + 1.6
    s = box(-60.8, -39.7, -20, 20, t0, t1)
    s = s.fuse(box(-60.3, -58.8, -20, 20, t1 - 0.01, 277.4))
    for y in (-11.7, 11.7):
        s = s.cut(cylZ(1.7, t0 - 1, t1 + 1, x=-45.3, y=y))
    s = s.clean()
    return s if sg < 0 else mir(s)


def make_endplate(sg):
    s = box(-52.5, -PUSH[0], -PUSH[1] - 2.2, -PUSH[1], Z_BR[3] + 0.1, GD[3])
    for x in (-48.9, -39.0):
        s = s.cut(cylY(1.7, -50, -30, x=x, z=266.0))
    s = s.clean()
    return s if sg < 0 else mir(s)


def make_spindle():
    """Ось поворотная поз.12: планшайба Ø142,6 (низ корпуса), вал Ø30 с
    канавками под кольца поз.25 и воздушными проточками, резьба М12."""
    fr, fz0, fz1 = S12_FL
    prof = [(0, THR[1]), (THR[0] - 1, THR[1]), (THR[0], THR[1] + 1), (THR[0], SH_Z0),
            (SH_R, SH_Z0), (SH_R, fz0), (fr, fz0), (fr, fz1), (0, fz1)]
    s = rev_z(prof)
    for z0, z1 in G25:
        s = s.cut(cylZ(SH_R + 1, z0, z1).cut(cylZ(G25_R, z0 - 1, z1 + 1)))
    for z0, z1, r in AIR_G:
        s = s.cut(cylZ(SH_R + 1, z0, z1).cut(cylZ(r, z0 - 1, z1 + 1)))
    # вертикальные каналы Ø5 (сверху заглушены поз."заглушка")
    (xl, zl), (xr, zr) = VCH
    s = s.cut(cylZ(CH_D / 2, zl, fz1 + 1, x=xl))
    s = s.cut(cylZ(CH_D / 2, zr, fz1 + 1, x=xr))
    # радиальные связи канал -> проточка
    s = s.cut(cylX(CH_D / 2, xl, -SH_R, z=(AIR_G[0][0] + AIR_G[0][1]) / 2))
    s = s.cut(cylX(CH_D / 2, xr, SH_R, z=(AIR_G[1][0] + AIR_G[1][1]) / 2))
    # горизонтальные каналы в планшайбе
    s = s.cut(cylX(CH_D / 2, xl, -fr - 1, z=CH_CAP_Z))
    s = s.cut(cylX(CH_D / 2, xr, fr + 1, z=CH_ROD_Z))
    s = s.cut(cylX(CH_D / 2, 66.0, fr + 1, z=CH_CAP_Z))     # (видны на разрезе справа)
    s = s.cut(cylX(CH_D / 2, -66.2, -fr - 1, z=CH_ROD_Z))   # (видны на разрезе слева)
    return s.clean()


def make_plug(x):
    s = cylZ(CH_D / 2, S12_FL[2] - PLUG_Z, S12_FL[2] - 0.5, x=x)
    s = s.fuse(cone(CH_D / 2, CH_D / 2 - 0.5, (x, 0, S12_FL[2] - 0.5), (0, 0, 1), 0.5))
    return s


def make_sleeve():
    """Втулка поз.13 (неподвижна в основании): Ø50,6/Ø30 H6, приливы под штуцера."""
    ro, ri, z0, z1 = SL
    s = cylZ(ro, z0, z1)
    for sy in (1, -1):
        s = s.fuse(box(-BOSS[0], BOSS[0], min(sy * 15, sy * BOSS[3]), max(sy * 15, sy * BOSS[3]),
                       BOSS[1], BOSS[2]))
    s = s.cut(cylZ(ri, z0 - 1, z1 + 1))
    # +Y: канал к нижней проточке
    s = s.cut(cylY(CH_D / 2, 14.0, BOSS[3] + 1, z=FIT_Z))
    s = s.cut(cylY(5.0, BOSS[3] - 10.0, BOSS[3] + 1, z=FIT_Z))       # М10 под поз.18
    # -Y: канал к верхней проточке (через сверление в стенке)
    zup = (AIR_G[1][0] + AIR_G[1][1]) / 2
    s = s.cut(cylY(CH_D / 2, -BOSS[3] - 1, -18.5, z=FIT_Z))
    s = s.cut(cylY(5.0, -BOSS[3] - 1, -BOSS[3] + 10.0, z=FIT_Z))
    s = s.cut(cylZ(2.0, FIT_Z - 2.0, zup + 2.0, y=-20.5))
    s = s.cut(cylY(2.0, -22.5, -14.0, z=zup))
    return s.clean()


def make_disc15():
    r, ri, z0, z1 = D15
    return cylZ(r, z0, z1).cut(cylZ(ri, z0 - 1, z1 + 1))


def make_fitting18(sy):
    """Штуцер ввертной поз.18: шестигранник S14×7, резьба М10×10, внутр. М8."""
    ax = (0, sy, 0)
    body = hexprism(14.0, (0, 0, 0), (0, 0, 1), 7.0).fuse(cylZ(5.0, -10.0, 0))
    body = cut(body, cylZ(2.5, -11, 8), cylZ(4.0, 1.0, 8.0))
    return orient(body, (0, sy * BOSS[3], FIT_Z), ax)


def make_fitting17(sy):
    """Штуцер (ниппель) поз.17 под шланг Ø8: резьба М8×6, бурт Ø12, ёлочка Ø9."""
    s = U(cylZ(4.0, 1.0, 7.0), cylZ(6.0, 7.0, 9.0), cylZ(4.35, 9.0, 18.5),
          cone(4.6, 3.0, (0, 0, 18.5), (0, 0, 1), 2.5))
    s = cut(s, cylZ(2.0, 0, 22))
    return orient(s, (0, sy * BOSS[3], FIT_Z), (0, sy, 0))


def make_stakan():
    s = cylY(ST_R[0], ST_Y[0], ST_Y[1], z=Z_ST).cut(cylY(ST_R[1], ST_Y[0] - 1, ST_Y[1] + 1, z=Z_ST))
    s = s.cut(cylZ(ST_HOLE_R, Z_ST - 80, Z_ST + 80))
    return s.clean()


def make_guide(sg):
    xo, xi, z0, z1, y0, y1 = GD
    s = box(-xo, -xi, y0, y1, z0, z1)
    return s if sg < 0 else mir(s)


# ===========================================================================
# СБОРКА
# ===========================================================================
def build():
    SIDES = (("L", -1), ("R", 1))
    # ---- изделие (стакан + 2 направляющие) -----------------------------
    add("izdelie_stakan", "", "Изделие: стакан (поз.2 корпуса задвижки), труба 133×5",
        make_stakan(), WORK, "Сталь 20 ГОСТ 1050-2013", "Труба 133×5 ГОСТ 8732-78",
        "Изделие (не входит в приспособление); отверстия Ø112 под патрубки", group="izdelie_stakan")
    for sd, sg in SIDES:
        add("izdelie_napravl_" + sd, "", "Изделие: направляющая (поз.5 корпуса), 8×14×193",
            make_guide(sg), WORK2, "Сталь 20 ГОСТ 1050-2013", "",
            "Изделие; прижимается толкателем поз.3 к стенке стакана", group="izdelie_napravl")
    # ---- основание, поворотная часть -----------------------------------
    add("p14_osnovanie", "14", "Основание", make_base(), BASEC, "СЧ 20 ГОСТ 1412-85")
    add("p11_koltso", "11", "Кольцо прижимное", make_ring11(), STEEL_D)
    for i in range(N21):
        a = math.radians(i * 360 / N21)
        p = (PCD21 / 2 * math.cos(a), PCD21 / 2 * math.sin(a), Z11[1] - 4.1)
        add("p21_vint_%d" % (i + 1), "21", "Винт М6-6g×16.58 ГОСТ 1491-80",
            screw_cheese(6.0, 16.0, 10.0, 3.9, 1.6, 1.8, p, (0, 0, -1)), FAST,
            "Сталь 35", "ГОСТ 1491-80", group="p21_vint")
    add("p07_korpus", "7", "Корпус", make_housing(), BODY, "СЧ 20 ГОСТ 1412-85")
    add("p12_os_povorotnaya", "12", "Ось поворотная (распределитель воздуха)", make_spindle(),
        STEEL)
    for i, (x, _) in enumerate(VCH):
        add("x_zaglushka_%d" % (i + 1), "", "Заглушка Ø5 u8 (штифт) - позиция на чертеже не указана",
            make_plug(x), STEEL_D, standard="", note="Посадка Ø5 H8/u8", group="x_zaglushka")
    add("p13_vtulka", "13", "Втулка распределителя", make_sleeve(), BRASS, "БрАЖ9-4 ГОСТ 18175-78")
    add("p15_shayba", "15", "Шайба упорная", make_disc15(), STEEL)
    add("p23_gayka_1", "23", "Гайка М12 ГОСТ 5916-70", nut_hex(NUT23[0], NUT23[1], 12.0,
        (0, 0, D15[2] - NUT23[1]), (0, 0, 1)), FAST, "Сталь 35", "ГОСТ 5916-70", group="p23_gayka")
    add("p23_gayka_2", "23", "Гайка М12 ГОСТ 5916-70", nut_hex(NUT23[0], NUT23[1], 12.0,
        (0, 0, D15[2] - 2 * NUT23[1]), (0, 0, 1)), FAST, "Сталь 35", "ГОСТ 5916-70", group="p23_gayka")
    for i, (z0, z1) in enumerate(G25):
        add("p25_koltso_%d" % (i + 1), "25", "Кольцо 020-030-58-2-2 ГОСТ 9833-73",
            oring_z(19.5, 5.8, (z0 + z1) / 2), RUBBER, "Резина 7-В-14", "ГОСТ 9833-73",
            "Показано в свободном состоянии", group="p25_koltso")
    for i, sy in enumerate((1, -1)):
        add("p18_shtutser_vvertnoy_%d" % (i + 1), "18", "Штуцер ввертной М10 (S14)",
            make_fitting18(sy), BRASS, "Латунь ЛС59-1", "", group="p18_shtutser")
        add("p17_shtutser_%d" % (i + 1), "17", "Штуцер (ниппель) под шланг Ø8",
            make_fitting17(sy), BRASS, "Латунь ЛС59-1", "", group="p17_shtutser")
    # ---- пневмоцилиндры -------------------------------------------------
    for sd, sg in SIDES:
        add("p10_kryshka_" + sd, "10", "Крышка цилиндра", make_cover(sg), BODY,
            "СЧ 20 ГОСТ 1412-85", group="p10_kryshka")
        add("p09_prokladka_" + sd, "9", "Прокладка", make_gasket(sg), GREEN,
            "Паронит ПОН ГОСТ 481-80", group="p09_prokladka")
        add("p08_porshen_" + sd, "8", "Поршень", make_piston(sg), STEEL, group="p08_porshen")
        add("x_shtok_" + sd, "", "Шток Ø24 h6 - позиция на чертеже не указана", make_rod(sg), STEEL,
            "Сталь 45 ГОСТ 1050-2013", "", "Хвостовик М16 ввёрнут в поршень", group="x_shtok")
        add("p27_koltso_" + sd, "27", "Кольцо 050-060-58-2-2 ГОСТ 9833-73",
            oring_x(49.5, 5.8, sg * (G27[0] + G27[1]) / 2), RUBBER, "Резина 7-В-14", "ГОСТ 9833-73",
            "Показано в свободном состоянии", group="p27_koltso")
        add("p26_koltso_" + sd, "26", "Кольцо 024-034-58-2-2 ГОСТ 9833-73",
            oring_x(23.5, 5.8, sg * (G26[0] + G26[1]) / 2), RUBBER, "Резина 7-В-14", "ГОСТ 9833-73",
            "Показано в свободном состоянии", group="p26_koltso")
        for i, a in enumerate(BOLT_ANG):
            p = polar_yz(PCD19 / 2, a, sg * COV_X[1])
            add("p19_bolt_%s%d" % (sd, i + 1), "19", "Болт М6-6g×18.58 ГОСТ 7798-70",
                bolt_hex(6.0, 18.0, 10.0, 4.0, p, (-sg, 0, 0)), FAST, "Сталь 35", "ГОСТ 7798-70",
                group="p19_bolt")
    # ---- рычажный механизм ---------------------------------------------
    add("p05_korpus_tolkateley", "5", "Корпус толкателей", make_part5(), STEEL_D)
    for i in range(6):
        a = math.radians(i * 60)
        p = (PCD5 / 2 * math.cos(a), PCD5 / 2 * math.sin(a), Z5[2] - 4.1)
        add("x_vint_flantsa_%d" % (i + 1), "", "Винт М6-6g×20.58 ГОСТ 1491-80 - позиция не указана",
            screw_cheese(6.0, 20.0, 10.0, 3.9, 1.6, 1.8, p, (0, 0, -1)), FAST, "Сталь 35",
            "ГОСТ 1491-80", "Крепление поз.5 к корпусу (Ø126)", group="x_vint_flantsa")
    add("x_opora_rychagov", "", "Опора рычагов Ø88 f9 - позиция на чертеже не указана",
        make_lever_support(), STEEL)
    for sd, sg in SIDES:
        add("p04_rychag_" + sd, "4", "Рычаг", make_lever(sg), RED, "Сталь 40Х ГОСТ 4543-2016",
            group="p04_rychag")
        add("p06_os_" + sd, "6", "Ось рычага Ø8", make_pivot_pin(sg), STEEL_D, group="p06_os")
        add("x_opora_stakana_" + sd, "", "Опора стакана (ложемент) - позиция на чертеже не указана",
            make_support_J(sg), STEEL, group="x_opora_stakana")
        add("x_shtift_" + sd, "", "Штифт 8m6×18 ГОСТ 3128-70 - позиция не указана",
            cylX(4.0, sg * 45.3, sg * 63.3, z=Z_PIN8), FAST, "Сталь 45", "ГОСТ 3128-70",
            "Посадка Ø8 H7/m8", group="x_shtift")
        add("p01_gubka_" + sd, "1", "Губка (ложемент)", make_jaw(sg), STEEL, group="p01_gubka")
        add("p03_tolkatel_" + sd, "3", "Толкатель", make_pusher(sg), GREEN, group="p03_tolkatel")
        add("p02_planka_" + sd, "2", "Планка", make_plate2(sg), STEEL_D, "Сталь 65Г ГОСТ 14959-2016",
            group="p02_planka")
        for i, y in enumerate((-11.7, 11.7)):
            add("p22_vint_%s%d" % (sd, i + 1), "22", "Винт М3-6g×8.58 ГОСТ 17473-80",
                screw_round(3.0, 8.0, 5.5, 2.1, 0.8, 1.0, (sg * 45.3, y, GD[3] + 1.6), (0, 0, -1)),
                FAST, "Сталь 35", "ГОСТ 17473-80", group="p22_vint")
        add("x_planka_tortsevaya_" + sd, "", "Планка торцевая - позиция на чертеже не указана",
            make_endplate(sg), STEEL_D, group="x_planka_tortsevaya")
        for i, x in enumerate((-48.9, -39.0)):
            add("p16_vint_%s%d" % (sd, i + 1), "16", "Винт М3-6g×8.58 ГОСТ 17473-80",
                screw_round(3.0, 8.0, 5.5, 2.1, 0.8, 1.0, (x if sg < 0 else -x, -PUSH[1] - 2.2, 266.0),
                            (0, 1, 0)), FAST, "Сталь 35", "ГОСТ 17473-80", group="p16_vint")


ALLOWED = [("koltso", None)]   # кольца ГОСТ 9833: деформация (натяг) допускается


def allowed(k1, k2):
    return "koltso" in k1 or "koltso" in k2


def check():
    print("Проверка тел ...")
    bbs = {}
    for key, s, _ in PARTS:
        assert s.isValid(), key
        bbs[key] = s.BoundingBox()
    allbb = None
    for b in bbs.values():
        allbb = b if allbb is None else allbb.add(b)
    print("Габарит: X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f" % (
        allbb.xmin, allbb.xmax, allbb.ymin, allbb.ymax, allbb.zmin, allbb.zmax))
    bad, okd = [], []
    n = len(PARTS)
    for i in range(n):
        ki, si, _ = PARTS[i]
        a = bbs[ki]
        for j in range(i + 1, n):
            kj, sj, _ = PARTS[j]
            b = bbs[kj]
            if (a.xmin > b.xmax + 0.01 or b.xmin > a.xmax + 0.01 or a.ymin > b.ymax + 0.01 or
                    b.ymin > a.ymax + 0.01 or a.zmin > b.zmax + 0.01 or b.zmin > a.zmax + 0.01):
                continue
            v = si.intersect(sj).Volume()
            if v > 0.05:
                (okd if allowed(ki, kj) else bad).append((ki, kj, v))
    for k1, k2, v in okd:
        print("  допустимо (натяг кольца): %s / %s: %.2f мм3" % (k1, k2, v))
    for k1, k2, v in bad:
        print("  ПЕРЕСЕЧЕНИЕ %s / %s: %.2f мм3" % (k1, k2, v))
    print("Пересечений: %d (допустимых %d)" % (len(bad), len(okd)))
    return bad, okd, allbb


def export(bad, okd, allbb):
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name=NAME)
    for key, s, col in PARTS:
        assy.add(cq.Workplane().add(s), name=key, color=col)
    # GLB - первым (грубая триангуляция, пока тела не триангулированы для STL)
    tol = float(os.environ.get("GLB_TOL", "0.12"))
    assy.save(os.path.join(OUT, NAME + ".glb"), tolerance=tol, angularTolerance=0.4)
    assy.save(os.path.join(OUT, NAME + ".step"))
    for key, s, col in PARTS:
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, "parts_stl", key + ".stl"),
                            tolerance=0.05, angularTolerance=0.15)
    print("GLB: %.2f МБ" % (os.path.getsize(os.path.join(OUT, NAME + ".glb")) / 1e6))
    spec = list(SPEC.values())
    for it in spec:
        it["nodes"] = [k for k, _, _ in PARTS if k == it["key"] or k.startswith(it["key"] + "_")]
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    rep = {"bbox": [allbb.xmin, allbb.xmax, allbb.ymin, allbb.ymax, allbb.zmin, allbb.zmax],
           "interferences": bad, "allowed_overlaps": okd,
           "volumes": {k: s.Volume() for k, s, _ in PARTS}}
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    build()
    bad, okd, bb = check()
    if "--nocheck" not in sys.argv:
        pass
    export(bad, okd, bb)
    print("Готово: %d тел" % len(PARTS))
