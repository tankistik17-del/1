# -*- coding: utf-8 -*-
"""
3D-модель: «Приспособление сварочное №2» (лист 7 дипломного проекта
«Технология сборки-сварки корпуса задвижки трубопровода», М 1:1).

Пневматическое приспособление: плита-основание, корпус (ось-распределитель) с
вращающимся соединением (втулка 16, кольца 29, штуцеры 3/4), пневмоцилиндр
(гильза 18, поршень 14, шток 2, крышка 11, трубка подвода воздуха 13) и
захватная головка (траверса 10, оси 9, рычаги 5 с подпружиненными фиксаторами 6/7).
Установленная заготовка (фланец стакана поз.17 + стакан) показана отдельно.

Система координат: Z — ось приспособления (вверх), начало — центр нижней
плоскости плиты-основания. X — вправо на главном виде (разрез А-А), Y — от
наблюдателя главного вида. Левая половина главного вида — разрез плоскостью
Y=0 (X<0, штуцеры), правая — плоскостью под углом 22°30' к оси X (палец 24,
трубка 13, каналы крышки). Все размеры — мм.

Запуск:  python3 build.py   (CadQuery 2.8)
Результат: out/ — сборка STEP/GLB, детали STEP/STL, spec.json, check.json.
"""
import json
import math
import os
import sys

import cadquery as cq
from cadquery import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
GLB_TOL, GLB_ANG = 0.12, 0.45   # точность триангуляции GLB (ограничение ≤ 4 МБ)

# ---------------------------------------------------------------------------
# Общие размеры (лист 7)
# ---------------------------------------------------------------------------
H_TOTAL = 320.0      # габаритная высота 320 (вид слева)
Z_PIN = 258.0        # ось осей 9 головки: 258 (вид слева)
A_SEC = 22.5         # угол секущей плоскости А-А / пальца 24: 22°30'±1° (вид сверху)
R_AIR = 48.6         # радиус оси воздушного канала/трубки 13 (замер по векторам 48.55..48.7)

# Плита-основание (поз. не указана) — главный вид / вид слева
BASE_D = 200.0       # Ø200
BASE_H = 15.0        # 15
BASE_FLAT_Y = 70.0   # уступы |Y|>=70 (вид слева, замер 69.7..70.2)
BASE_FLAT_H = 8.0    # толщина плиты в зоне уступов (вид слева, замер 8.07)
SLOT_Y = 84.0        # оси пазов под крепёж: 168/2 (вид слева)
SLOT_W = 12.0        # ширина паза (22* от кромки до дна паза: 100-22=78=84-6)
RING_ID_R = 60.0     # выступ-кольцо под втулку 16, внутр. R (замер 60.03)
RING_OD_R = 69.7     # наружн. R (замер 69.68)
RING_TOP = 17.0      # 17* — опора втулки 16
HUB_BOT = 13.0       # низ корпуса 15 (9 от низа до оси первого кольца 29, 22-9=13)
SCREW_R = 45.0       # винты М10: 55 от кромки Ø200 → R45

# Корпус 15 (ось-распределитель)
HUB_R = 59.95        # Ø120 (посадка во втулку 16 Ø120), зазор 0.05
GROOVE_R = 54.86     # дно канавок (замер 54.86)
ORING_Z = (22.0, 44.5, 67.0)   # оси колец 29: 22 = 13+9; шаг 10+12.5 / 12.5+10 (вид слева)
ORING_GW = 5.1       # ширина канавки под кольцо (замер 5.08..5.17)
PORT_Z = (32.0, 57.0)          # оси штуцеров: 32 и 32+25 (главный вид)
AIRG_W = 10.0        # ширина кольцевой воздушной канавки 10* (главный вид)
CAVITY_R = 28.1      # полость Ø56* (замер 56.2)
CAVITY_BOT = 49.7    # дно полости (замер)
PLATE_Z0, PLATE_Z1 = 67.0, 83.0   # плита корпуса: 16* и 83* (вид слева / главный)
PLATE_R = 105.0      # R105 (вид сверху)
PLATE_FLAT_X = -85.0 # лыска: 190 = 105 + 85 (вид сверху)
PLATE_RIM_R = 100.0  # дуга R100 у пазов (вид сверху, габарит 200 на виде слева)
PLATE_RIM_HALF = 19.4  # полуугол дуги R100 (хорда ±33.3 на виде сверху)
PSLOT_R = 85.0       # центр паза 12 / выборки 34 (вид сверху)
PSLOT_W = 12.0       # 12 (вид сверху)
PCB_W = 34.0         # 34 (вид сверху)
PCB_DEPTH = 5.0      # глубина выборки 34 — не указана, принято 5
LIP_RECESS_R = 70.1  # выточка под бурт втулки 16 (R69.68 + зазор)
LIP_TOP = 72.9       # верх бурта втулки (замер 72.90)
NECK_R = 58.25       # шейка корпуса (замер 58.25), центрирует фланец 17
NECK_TOP = 99.0      # торец под прокладку 1 (замер 98.98)
SPIG_R = 38.45       # центрирующий поясок Ø77 h8 в гильзе Ø77 H9 (зазор 0.05)
SPIG_TOP = 108.3     # верх пояска: 60* = 168.3 - 108.3
BOLT_PCD_R = 52.0    # R52 (вид сверху) — болты крепления гильзы и крышки
BOLT_N = 10          # 10 шт: проекции на виде слева Y=0, ±30.6, ±49.5 (R52·sin36°/72°)

# Втулка 16 (неподвижная часть вращающегося соединения)
SL_IR = 60.0
SL_OR = 69.7         # Ø140 (замер 69.68, вид слева ±70)
SL_BOSS_X = -81.1    # прилив под штуцеры (замер 81.11)
SL_BOSS_W = 20.4     # ширина прилива (вид слева, замер 20.35)
SL_BOSS_Z = (22.0, 66.95)

# Штуцер 3 / шайба 4 (М10×1, шестигранник S13)
FIT_TIP_X = -110.0   # конец штуцера: 215 - 105 = 110 (вид сверху)

# Пневмоцилиндр
BORE_R = 38.5        # Ø77 H9
TUBE_OR = 44.0       # 88* (вид слева)
FL_R = 57.6          # фланцы гильзы и крышка (замер 56.2..58, вид слева ±58..59)
G_BOT0, G_BOT1 = 100.0, 111.6    # нижний фланец гильзы (замер 99.99..111.59)
G_TOP0, G_TOP1 = 173.4, 187.4    # верхний фланец гильзы 14* (вид слева)
COVER_Z0, COVER_Z1 = 189.0, 203.0  # плита крышки 14* (вид слева)
COVER_SPIG_BOT = 168.3           # 30* ход: 168.3 - 138.3; 60*: 168.3-108.3
NECK_TOP_COVER = 246.9           # верх горловины крышки (замер 246.89)
NECK_COVER_R = 23.2              # горловина (замер 23.20)
NECK_FLAT = 20.0                 # 40* (вид слева) — лыски горловины
ROD_R = 9.95                     # Ø20 h6 (зазор 0.05 в Ø20 H7)
CH_Z = COVER_Z1 - 7.0            # 7 — ось горизонтального канала Ø5 H8/u8

PIST_Z0, PIST_Z1 = 111.2, 138.3  # поршень (толщина 27.1 — замер), низ. положение
PIST_R = 38.45                   # Ø77 f9

# Головка: масштаб по Z выше оси 258 так, чтобы верх = 320 (замер 257.5 → 320.89)
KZ = (H_TOTAL - Z_PIN) / (320.89 - 257.5)


def kz(z):
    """Перевод замеренной по чертежу отметки головки в модельную (258/320)."""
    return Z_PIN + (z - 257.5) * KZ


PIN_X = 29.0         # 58/2
LATCH_X = 46.0       # 92/2
LEV_T = 10.2         # полутолщина рычага (вид слева 20.4)
EAR_T = 5.0          # полутолщина проушины рычага / хвостовика штока (выносной элемент Б)
TRAV_T = 10.0        # полутолщина траверсы 10 (Б: 20.5), под ось 8×20
SLOT_T = 5.1         # полуширина пазов траверсы

# Заготовка: фланец стакана (поз.17) Ø210, 8 отв. Ø18 на Ø180, 22°30'
FL17_R = 105.0
FL17_HOLE_D = 18.0
FL17_PCD_R = 90.0

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
Z_AX = Vector(0, 0, 1)


def pol(r, ang_deg):
    a = math.radians(ang_deg)
    return (r * math.cos(a), r * math.sin(a))


def W(solid):
    return cq.Workplane("XY").add(solid)


def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, z1 - z0, Vector(x, y, z0), Z_AX)


def cyl_ax(r, p, d, length):
    return cq.Solid.makeCylinder(r, length, Vector(*p), Vector(*d))


def cone_ax(r1, r2, p, d, length):
    return cq.Solid.makeCone(r1, r2, length, Vector(*p), Vector(*d))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, Vector(x0, y0, z0))


def ring(r_in, r_out, z0, z1):
    return cyl(r_out, z0, z1).cut(cyl(r_in, z0 - 1, z1 + 1))


def revolve(pts):
    """Тело вращения вокруг Z; pts = [(R, Z), ...] в плоскости XZ."""
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def torus(R, r, z, x=0.0, y=0.0, d=(0, 0, 1)):
    return cq.Solid.makeTorus(R, r, Vector(x, y, z), Vector(*d))


def hex_prism(e, z0, z1, x=0.0, y=0.0, rot=0.0):
    s = cq.Workplane("XY").polygon(6, e).extrude(z1 - z0).val()
    if rot:
        s = s.rotate(Vector(0, 0, 0), Z_AX, rot)
    return s.translate(Vector(x, y, z0))


def hex_head(S, z0, z1, x=0.0, y=0.0, chamfer_top=True):
    """Шестигранная головка под ключ S с фаской 30° (ГОСТ 7798-70 / 5915-70)."""
    e = S / math.cos(math.radians(30))
    h = hex_prism(e, z0, z1, 0, 0, 30)
    dw = 0.95 * S / 2
    c = (e / 2 - dw) * math.tan(math.radians(30))
    if chamfer_top:
        prof = [(0, z0), (e / 2 + 1, z0), (e / 2 + 1, z1 - c - 0.3), (dw, z1), (0, z1)]
    else:
        prof = [(0, z0), (dw, z0), (e / 2 + 1, z0 + c + 0.3), (e / 2 + 1, z1), (0, z1)]
    return h.intersect(revolve(prof)).translate(Vector(x, y, 0))


def rot_z(s, ang):
    return s.rotate(Vector(0, 0, 0), Z_AX, ang)


def drill(r, p, d, depth, tip=True):
    """Сверление Ø2r из точки p по направлению d на глубину depth с конусом 118°."""
    d = Vector(*d).normalized()
    s = cyl_ax(r, p, d.toTuple(), depth)
    if tip:
        h = r / math.tan(math.radians(59))
        e = Vector(*p) + d * depth
        s = s.fuse(cone_ax(r, 0.0, e.toTuple(), d.toTuple(), h))
    return s


def fuse_all(solids):
    s = solids[0]
    for t in solids[1:]:
        s = s.fuse(t)
    return s.clean()


def bolt_hex(d, L, k, S, z_head_top=None, z_under_head=None, down=True, x=0.0, y=0.0):
    """Болт с шестигранной головкой ГОСТ 7798-70 вдоль Z (S — размер под ключ).
    down=True: головка сверху (опорная плоскость z_under_head), стержень вниз."""
    if down:
        zu = z_under_head
        head = hex_head(e, zu, zu + k, x, y, True)
        shank = cyl(d / 2, zu - L, zu + 0.01, x, y)
        ch = 0.6
        shank = shank.cut(ring(d / 2 - ch, d / 2 + 1, zu - L - 1, zu - L + ch)).fuse(
            cone_ax(d / 2 - ch, d / 2, (x, y, zu - L), (0, 0, 1), ch))
        return head.fuse(shank).clean()
    else:  # головка снизу, стержень вверх
        zu = z_under_head
        head = hex_head(e, zu - k, zu, x, y, False)
        shank = cyl(d / 2, zu - 0.01, zu + L, x, y)
        return head.fuse(shank).clean()


def arr(fn, n):
    return [fn(i) for i in range(n)]


BOLT_ANG = [i * 360.0 / BOLT_N for i in range(BOLT_N)]   # 0°, 36°, ... (вид слева)

# ---------------------------------------------------------------------------
# Детали
# ---------------------------------------------------------------------------


def make_base():
    """Плита-основание Ø200×15 (поз. на листе не указана)."""
    s = cyl(BASE_D / 2, 0, BASE_H)
    for sg in (1, -1):
        # уступы толщиной 8 при |Y|>=70 (вид слева)
        y0, y1 = (BASE_FLAT_Y, 101) if sg > 0 else (-101, -BASE_FLAT_Y)
        s = s.cut(box(-101, 101, y0, y1, BASE_FLAT_H, BASE_H + 1))
        # U-образный паз 12 под крепёж к планшайбе, ось Y=±84, 22* от кромки
        yc = sg * SLOT_Y
        s = s.cut(cyl(SLOT_W / 2, -1, BASE_H + 1, 0, yc))
        yy0, yy1 = (yc, 101) if sg > 0 else (-101, yc)
        s = s.cut(box(-SLOT_W / 2, SLOT_W / 2, yy0, yy1, -1, BASE_H + 1))
    # выступ-кольцо под втулку 16 (17*)
    s = s.fuse(ring(RING_ID_R, RING_OD_R, BASE_H - 0.5, RING_TOP))
    # гнездо под корпус 15 (глубина 2: низ корпуса на 13)
    s = s.cut(cyl(RING_ID_R, HUB_BOT, RING_TOP + 1))
    # 4 отверстия под винты М10 ГОСТ 17475-80 с потайной головкой (зенковка 90°)
    for a in (0, 90, 180, 270):
        x, y = pol(SCREW_R, a)
        s = s.cut(cyl(5.5, -1, HUB_BOT + 1, x, y))
        s = s.cut(cone_ax(11.0, 5.5, (x, y, 0.0), (0, 0, 1), 5.5))
        s = s.cut(cyl(11.0, -1, 0.0, x, y))
    return W(s.clean())


def make_hub():
    """Корпус 15: ось-распределитель с плитой R105, шейкой и пояском Ø77."""
    prof = [(0, HUB_BOT), (HUB_R, HUB_BOT), (HUB_R, PLATE_Z1), (NECK_R, PLATE_Z1),
            (NECK_R, NECK_TOP), (SPIG_R, NECK_TOP), (SPIG_R, SPIG_TOP - 1.35),
            (SPIG_R - 1.35, SPIG_TOP), (0, SPIG_TOP)]
    body = revolve(prof)
    # плита R105 с лыской X=-85, дугами R100 у пазов, пазами 12 и выборками 34
    plate = cyl(PLATE_R, PLATE_Z0, PLATE_Z1)
    plate = plate.cut(box(-120, PLATE_FLAT_X, -120, 120, PLATE_Z0 - 1, PLATE_Z1 + 1))
    for sg in (1, -1):
        a0 = 90 - PLATE_RIM_HALF if sg > 0 else 270 - PLATE_RIM_HALF
        wedge = (cq.Workplane("XY").workplane(offset=PLATE_Z0 - 1)
                 .polyline([(0, 0), pol(130, a0), pol(130, a0 + PLATE_RIM_HALF),
                            pol(130, a0 + 2 * PLATE_RIM_HALF)]).close()
                 .extrude(PLATE_Z1 - PLATE_Z0 + 2).val())
        rim = ring(PLATE_RIM_R, 130, PLATE_Z0 - 1, PLATE_Z1 + 1).intersect(wedge)
        plate = plate.cut(rim)
        yc = sg * PSLOT_R
        yy0, yy1 = (yc, 130) if sg > 0 else (-130, yc)
        plate = plate.cut(cyl(PSLOT_W / 2, PLATE_Z0 - 1, PLATE_Z1 + 1, 0, yc))
        plate = plate.cut(box(-PSLOT_W / 2, PSLOT_W / 2, yy0, yy1, PLATE_Z0 - 1, PLATE_Z1 + 1))
        plate = plate.cut(cyl(PCB_W / 2, PLATE_Z1 - PCB_DEPTH, PLATE_Z1 + 1, 0, yc))
        plate = plate.cut(box(-PCB_W / 2, PCB_W / 2, yy0, yy1, PLATE_Z1 - PCB_DEPTH, PLATE_Z1 + 1))
    # выточка снизу под бурт втулки 16
    plate = plate.cut(cyl(LIP_RECESS_R, PLATE_Z0 - 1, LIP_TOP))
    s = body.fuse(plate).clean()
    # полость Ø56* (подвод воздуха под поршень)
    s = s.cut(cyl(CAVITY_R, CAVITY_BOT, SPIG_TOP + 1))
    # канавки под кольца 29 и воздушные канавки 10*
    for z in ORING_Z:
        s = s.cut(ring(GROOVE_R, 70, z - ORING_GW / 2, z + ORING_GW / 2))
    for z in PORT_Z:
        s = s.cut(ring(GROOVE_R, 70, z - AIRG_W / 2, z + AIRG_W / 2))
    # верхний радиальный канал Ø5* (Z=57): канавка -> полость, плоскость Y=0 (X<0)
    s = s.cut(cyl_ax(2.7, (-(HUB_R + 1), 0, PORT_Z[1]), (1, 0, 0), HUB_R + 1 - CAVITY_R + 1))
    # нижний радиальный канал Ø5.5 (Z=32): от канавки (180°) до оси и по 22°30' до канала
    s = s.cut(cyl_ax(2.75, (-(HUB_R + 1), 0, PORT_Z[0]), (1, 0, 0), HUB_R + 1))
    d22 = (math.cos(math.radians(A_SEC)), math.sin(math.radians(A_SEC)), 0)
    s = s.cut(drill(2.75, (0, 0, PORT_Z[0]), d22, R_AIR + 2.5))
    # вертикальный канал Ø5 на R48.6 (22°30') к трубке 13
    xa, ya = pol(R_AIR, A_SEC)
    s = s.cut(drill(2.5, (xa, ya, NECK_TOP + 1), (0, 0, -1), NECK_TOP + 1 - 26.1))
    # резьбовые отверстия М10 (винты крепления к плите), глубина 11
    for a in (0, 90, 180, 270):
        x, y = pol(SCREW_R, a)
        s = s.cut(drill(5.0, (x, y, HUB_BOT - 1), (0, 0, 1), 12.0))
    # резьбовые отверстия М6 под болты нижнего фланца гильзы (R52, 10 шт.)
    for a in BOLT_ANG:
        x, y = pol(BOLT_PCD_R, a)
        s = s.cut(drill(3.0, (x, y, NECK_TOP + 1), (0, 0, -1), 16.0))
    # отверстие Ø16 H8 под палец 24 (R90, 22°30')
    xp, yp = pol(FL17_PCD_R, A_SEC)
    s = s.cut(cyl(8.0, PLATE_Z0 - 1, PLATE_Z1 + 1, xp, yp))
    return W(s.clean())


def make_sleeve():
    """Втулка 16 — неподвижная обойма вращающегося соединения с приливом под штуцеры."""
    s = ring(SL_IR, SL_OR, RING_TOP + 0.05, LIP_TOP - 0.05)
    boss = box(SL_BOSS_X, -65.0, -SL_BOSS_W / 2, SL_BOSS_W / 2, SL_BOSS_Z[0], SL_BOSS_Z[1])
    s = s.fuse(boss).clean()
    for z in PORT_Z:
        s = s.cut(cyl_ax(5.0, (SL_BOSS_X - 1, 0, z), (1, 0, 0), 81.11 - 67.06 + 1))  # М10×1
        s = s.cut(cyl_ax(2.7, (-67.5, 0, z), (1, 0, 0), 8.0))                      # Ø5.4
    return W(s.clean())


def make_oring(R, cs, z, x=0.0, y=0.0, d=(0, 0, 1)):
    return W(torus(R, cs / 2, z, x, y, d))


def make_fitting(z):
    """Штуцер 3 под рукав: резьба М10×1, шестигранник S13, ниппель Ø10.3/Ø11.7."""
    parts = [
        cyl(5.0, 0, 82.1 - 71.3),                  # резьба М10×1 (L=10.8)
        cyl(7.35, 82.1 - 71.3, 84.24 - 71.3),       # бурт Ø14.7
        hex_prism(15.0, 84.24 - 71.3, 91.27 - 71.3),  # S13 (e=15.0)
        cyl(5.15, 91.27 - 71.3 - 0.01, 105.35 - 71.3),  # ниппель Ø10.3
        cyl(5.85, 105.35 - 71.3, 105.85 - 71.3),    # ёрш Ø11.7
        cone_ax(5.85, 4.25, (0, 0, 105.85 - 71.3), (0, 0, 1), 110.0 - 105.85),
    ]
    s = fuse_all(parts).cut(cyl(2.5, -1, 50))
    # ось Z -> направление -X, начало в точке X=-71.3
    s = s.rotate(Vector(0, 0, 0), Vector(0, 1, 0), -90).translate(Vector(-71.3, 0, z))
    return W(s)


def make_washer4(z):
    s = cyl_ax(7.35, (-82.1, 0, z), (1, 0, 0), 1.0).cut(cyl_ax(5.1, (-83, 0, z), (1, 0, 0), 3))
    return W(s)


def make_csk_screw(a):
    """Винт М10×20 ГОСТ 17475-80 (потайная головка D18, k5), головкой вниз."""
    x, y = pol(SCREW_R, a)
    head = cyl(9.0, 1.0, 2.0, x, y).fuse(cone_ax(9.0, 5.0, (x, y, 2.0), (0, 0, 1), 4.0))
    shank = cyl(5.0, 5.99, 21.0, x, y)
    s = head.fuse(shank).clean()
    s = s.cut(box(x - 1.25, x + 1.25, y - 10, y + 10, 0, 3.5))      # шлиц 2.5
    return W(s)


def make_pin24():
    """Палец установочный 24: хвостовик Ø16 u8 (запрессовка в плиту корпуса),
    бурт Ø25, установочная часть — шестигранник e17.9 в отверстие Ø18 фланца."""
    z0 = 62.91 + 0.37
    prof = [(0, z0), (7.25, z0), (8.0, z0 + 0.75), (8.0, 80.30), (7.7, 80.30),
            (7.7, PLATE_Z1 - 0.2), (8.0, PLATE_Z1), (12.5, PLATE_Z1), (12.5, 87.24),
            (0, 87.24)]
    low = revolve(prof)
    top = hex_prism(17.9, 87.24, 103.41, rot=0).intersect(
        revolve([(0, 87.0), (8.95, 87.0), (8.95, 99.09), (7.5, 103.41), (0, 103.41)]))
    s = low.fuse(top).clean()
    s = s.cut(hex_prism(8.08, 99.4, 103.5))            # шестигранное углубление S7
    xp, yp = pol(FL17_PCD_R, A_SEC)
    s = rot_z(s, A_SEC).translate(Vector(xp, yp, 0))
    return W(s)


def make_gasket(z0, z1, r_out):
    """Прокладка 1 (паронит ГОСТ 481-80)."""
    s = ring(BORE_R + 0.05, r_out, z0, z1)
    for a in BOLT_ANG:
        x, y = pol(BOLT_PCD_R, a)
        s = s.cut(cyl(3.3, z0 - 1, z1 + 1, x, y))
    xa, ya = pol(R_AIR, A_SEC)
    s = s.cut(cyl(2.5, z0 - 1, z1 + 1, xa, ya))
    return W(s)


def make_gilza():
    """Гильза 18: труба Ø88*/Ø77 H9 с приварными фланцами, лыска под трубку 13."""
    s = ring(BORE_R, TUBE_OR, G_BOT1 - 0.5, G_TOP0 + 0.5)
    s = s.fuse(ring(BORE_R, FL_R, G_BOT0, G_BOT1)).fuse(ring(BORE_R, FL_R, G_TOP0, G_TOP1)).clean()
    # лыска на 22°30' (плоскость на расстоянии 42.55 от оси) для трубки 13
    flat = box(42.55, 60, -30, 30, G_BOT1, G_TOP0)
    s = s.cut(rot_z(flat, A_SEC))
    xa, ya = pol(R_AIR, A_SEC)
    s = s.cut(cyl(6.05, G_BOT0 - 1, G_TOP1 + 1, xa, ya))   # отв. под трубку Ø12
    for a in BOLT_ANG:
        x, y = pol(BOLT_PCD_R, a)
        s = s.cut(cyl(3.3, G_BOT0 - 1, G_BOT1 + 1, x, y))  # Ø6.6 под болты М6
        s = s.cut(cyl(3.0, G_TOP0 - 1, G_TOP1 + 1, x, y))  # резьба М6 (по наруж. Ø)
    return W(s.clean())


def make_tube13():
    """Трубка 13 подвода воздуха в надпоршневую полость: Ø12/Ø5, 2 канавки под кольца 25."""
    z0, z1 = G_BOT0 + 0.05, 186.7
    s = ring(2.5, 6.0, z0, z1)
    for zc in (105.8, 181.7):
        s = s.cut(ring(3.55, 7.0, zc - 1.7, zc + 1.7))
    xa, ya = pol(R_AIR, A_SEC)
    return W(s.translate(Vector(xa, ya, 0)))


def make_oring25(zc):
    xa, ya = pol(R_AIR, A_SEC)
    return make_oring(4.8, 3.0, zc, xa, ya)


def make_piston():
    """Поршень 14: Ø77 f9, 2 канавки под кольца 28, выточка Ø40.5 под гайки 23."""
    c = 1.0
    prof = [(0, PIST_Z0), (PIST_R - c, PIST_Z0), (PIST_R, PIST_Z0 + c), (PIST_R, PIST_Z1 - c),
            (PIST_R - c, PIST_Z1), (0, PIST_Z1)]
    s = revolve(prof)
    for zc in (119.17, 130.34):
        s = s.cut(ring(33.27, 40, zc - 2.54, zc + 2.54))
    s = s.cut(cyl(20.28, PIST_Z0 - 1, 122.3))     # выточка
    s = s.cut(cyl(6.0, 122.2, PIST_Z1 + 1))       # Ø12 H8
    return W(s.clean())


def make_rod():
    """Шток 2: Ø20 h6, цапфа Ø12 k7 с канавкой под кольцо 26, резьба М12,
    хвостовик с лысками 10 и отверстием под ось 9 (Б)."""
    zb = 105.4
    prof = [(0, zb), (5.3, zb), (6.0, zb + 0.7), (6.0, 122.3), (4.0, 122.3), (4.0, 124.4),
            (5.95, 124.4), (5.95, 131.0), (2.88, 131.0), (2.88, 134.4), (5.95, 134.4),
            (5.95, PIST_Z1), (ROD_R, PIST_Z1), (ROD_R, 263.3), (7.8, 266.0), (0, 266.0)]
    s = revolve(prof)
    # лыски хвостовика (Y=±5) от 248.57
    z_fl = 248.07 + 0.5
    for sg in (1, -1):
        y0, y1 = (EAR_T, 20) if sg > 0 else (-20, -EAR_T)
        s = s.cut(box(-20, 20, y0, y1, z_fl, 270))
    s = s.cut(cyl_ax(4.05, (0, -20, Z_PIN), (0, 1, 0), 40))
    return W(s.clean())


def make_nut23(z0):
    """Гайка М12 низкая (S18, m6) ГОСТ 5916-70."""
    s = hex_prism(20.78, z0, z0 + 6.0, rot=30).cut(cyl(6.0, z0 - 1, z0 + 7))
    s = s.intersect(revolve([(0, z0), (9.0, z0), (10.5, z0 + 1.5), (10.5, z0 + 4.5),
                             (9.0, z0 + 6.0), (0, z0 + 6.0)]))
    return W(s)


def make_cover():
    """Крышка 11 с горловиной (направляющей штока), каналами Ø5 и отв. под болты 21."""
    c = 1.0
    prof = [(ROD_R + 0.05, COVER_SPIG_BOT), (SPIG_R - c, COVER_SPIG_BOT), (SPIG_R, COVER_SPIG_BOT + c),
            (SPIG_R, COVER_Z0), (FL_R, COVER_Z0), (FL_R, COVER_Z1), (NECK_COVER_R, COVER_Z1),
            (NECK_COVER_R, NECK_TOP_COVER), (ROD_R + 0.05, NECK_TOP_COVER)]
    s = revolve(prof)
    for sg in (1, -1):   # лыски горловины 40*
        y0, y1 = (NECK_FLAT, 40) if sg > 0 else (-40, -NECK_FLAT)
        s = s.cut(box(-40, 40, y0, y1, COVER_Z1 + 0.5, NECK_TOP_COVER + 1))
    s = s.cut(cyl(30.31, COVER_SPIG_BOT - 1, 174.06))           # карман Ø60.6
    s = s.cut(ring(ROD_R, 15.16, 178.1, 183.3))                 # канавка кольца 27
    d22 = (math.cos(math.radians(A_SEC)), math.sin(math.radians(A_SEC)), 0)
    # горизонтальный канал Ø5 H8 (ось на 7 ниже торца), от кромки к оси
    p0 = pol(FL_R + 1, A_SEC)
    s = s.cut(drill(2.5, (p0[0], p0[1], CH_Z), tuple(-v for v in d22), FL_R + 1 - 15.16))
    # вертикальный канал Ø5.67 в карман надпоршневой полости (R23.0)
    x1, y1 = pol(22.98, A_SEC)
    s = s.cut(cyl(2.83, 173.5, CH_Z + 0.5, x1, y1))
    # вертикальный канал Ø5 от трубки 13
    xa, ya = pol(R_AIR, A_SEC)
    s = s.cut(cyl(2.5, COVER_Z0 - 1, CH_Z + 0.5, xa, ya))
    for a in BOLT_ANG:
        x, y = pol(BOLT_PCD_R, a)
        s = s.cut(cyl(3.3, COVER_Z0 - 1, COVER_Z1 + 1, x, y))
    return W(s.clean())


def make_plug12():
    """Заглушка 12: Ø5 u8 × 5.6, запрессована в канал Ø5 H8 (торец заподлицо)."""
    s = revolve([(0, 0), (2.0, 0), (2.5, 0.5), (2.5, 5.1), (2.0, 5.6), (0, 5.6)])
    s = s.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)  # ось Z -> +X
    s = s.translate(Vector(FL_R - 5.6, 0, CH_Z))
    return W(rot_z(s, A_SEC))


def make_bolt_top(a):
    x, y = pol(BOLT_PCD_R, a)
    return W(bolt_hex(6.0, 25.0, 4.0, 10.0, z_under_head=COVER_Z1, x=x, y=y))


def make_bolt_bot(a):
    x, y = pol(BOLT_PCD_R, a)
    return W(bolt_hex(6.0, 25.0, 4.0, 10.0, z_under_head=G_BOT1, x=x, y=y))


# ---- Головка ---------------------------------------------------------------

def stadium_xz(x0, x1, zc, r, y0, y1):
    """Пластина с полукруглыми концами (R=r) в плоскости XZ, толщина по Y."""
    s = box(x0, x1, y0, y1, zc - r, zc + r)
    s = s.fuse(cyl_ax(r, (x0, y0, zc), (0, 1, 0), y1 - y0)).fuse(cyl_ax(r, (x1, y0, zc), (0, 1, 0), y1 - y0))
    return s.clean()


def make_traversa():
    """Траверса 10: соединяет шток 2 и рычаги 5 осями 9 (пазы 10.2 под проушины)."""
    s = stadium_xz(-PIN_X, PIN_X, Z_PIN, 8.0, -TRAV_T, TRAV_T)
    s = s.cut(box(-13.38, 13.38, -SLOT_T, SLOT_T, Z_PIN - 9, Z_PIN + 9))
    s = s.cut(box(20.32, 40, -SLOT_T, SLOT_T, Z_PIN - 9, Z_PIN + 9))
    s = s.cut(box(-40, -20.32, -SLOT_T, SLOT_T, Z_PIN - 9, Z_PIN + 9))
    for x in (-PIN_X, 0.0, PIN_X):
        s = s.cut(cyl_ax(4.0, (x, -20, Z_PIN), (0, 1, 0), 40))    # Ø8 H7 (посадка m6)
    return W(s.clean())


def make_os9(x):
    """Ось 9 Ø8×20 (выносной элемент Б: H7/m6 в траверсе, H11/h11 в проушине)."""
    s = revolve([(0, -10), (3.5, -10), (4.0, -9.5), (4.0, 9.5), (3.5, 10), (0, 10)])
    s = s.rotate(Vector(0, 0, 0), Vector(1, 0, 0), -90)   # ось Z -> +Y
    return W(s.translate(Vector(x, 0, Z_PIN)))


def lever_profile():
    pts = [(-37.0, 267.63), (-28.19, 267.63), (-28.19, 291.59), (-23.28, 301.67),
           (-23.28, 318.01), (-25.91, 320.89), (-57.57, 320.89), (-65.19, 315.64),
           (-65.19, 308.44), (-64.18, 308.44), (-64.18, 293.62), (-57.91, 293.62),
           (-57.91, 310.64), (-37.0, 310.64)]
    return [(x, kz(z)) for x, z in pts]


def make_lever(side):
    """Рычаг-прихват 5 (левый side=-1 / правый side=+1)."""
    pts = lever_profile()
    body = (cq.Workplane("XZ", origin=(0, LEV_T, 0)).polyline(pts).close()
            .extrude(2 * LEV_T).val())   # XZ: нормаль -Y, от Y=+LEV_T до -LEV_T
    # упорный выступ (опора на траверсу) X -28.19..-23.2
    lug = box(-28.19, -23.2, -LEV_T, LEV_T, Z_PIN + 8.0 + 0.1, kz(279.32))
    # проушина толщиной 10 (выносной элемент Б) R8 вокруг оси
    ear = cyl_ax(8.0, (-PIN_X, -EAR_T, Z_PIN), (0, 1, 0), 2 * EAR_T)
    ear = ear.fuse(box(-37.0, -28.19, -EAR_T, EAR_T, Z_PIN, kz(267.63) + 0.5))
    s = body.fuse(lug).fuse(ear).clean()
    s = s.cut(cyl_ax(4.05, (-PIN_X, -20, Z_PIN), (0, 1, 0), 40))     # Ø8 H11
    if side > 0:
        s = s.mirror("YZ")
    return W(s)


def latch_z():
    return kz(297.65)


def make_latch_body(side):
    """Корпус фиксатора (поз. не указана): блок с каналом Ø11.93 под фиксатор 6."""
    z0, z1 = kz(279.65) + 0.05, kz(308.78)
    s = box(-53.34, -37.05, -LEV_T, LEV_T, z0, z1)
    s = s.cut(cyl_ax(11.93 / 2, (-60, 0, latch_z()), (1, 0, 0), 30))
    s = s.cut(drill(3.0, (-LATCH_X, 0, z0 - 1), (0, 0, 1), kz(290.66) - z0 + 1))   # М6
    s = s.cut(cyl(3.0, latch_z(), z1 + 1, -LATCH_X, 0))                             # Ø6 сверху
    if side > 0:
        s = s.mirror("YZ")
    return W(s.clean())


def make_skoba8(side):
    """Скоба 8 (Г-образная крышка фиксатора): стенка-упор пружины + полка под болт 20."""
    zb, zt = kz(277.71), kz(308.78)
    wall = box(-55.12, -53.39, -LEV_T, LEV_T, zb, zt)
    shelf = box(-55.12, -38.10, -LEV_T, LEV_T, zb, kz(279.65))
    s = wall.fuse(shelf).clean().cut(cyl(3.3, zb - 1, zt, -LATCH_X, 0))
    if side > 0:
        s = s.mirror("YZ")
    return W(s)


def make_fiksator6(side):
    """Фиксатор (плунжер) 6: Ø11.85, сферический торец R8.96, гнездо Ø8.4 под пружину."""
    zc = latch_z()
    # профиль вращения вокруг оси X в локальных координатах (x — вдоль оси, r)
    x0, x1, xa = -51.14, -39.29, -37.05
    rs = 8.96
    xc = xa - rs
    rr = 11.85 / 2
    xs = xc + math.sqrt(rs * rs - rr * rr)     # сечение сферы радиусом rr
    prof = (cq.Workplane("XY").moveTo(x0, 0).lineTo(x0, rr).lineTo(xs, rr)
            .threePointArc((xc + math.sqrt(rs * rs - (rr / 2) ** 2), rr / 2), (xa, 0)).close())
    s = prof.revolve(360, (0, 0, 0), (1, 0, 0)).val()
    s = s.cut(cyl_ax(8.39 / 2, (x0 - 1, 0, 0), (1, 0, 0), (-41.06) - x0 + 1))
    s = s.translate(Vector(0, 0, zc))
    if side > 0:
        s = s.mirror("YZ")
    return W(s)


def make_spring7(side):
    """Пружина сжатия 7: проволока d1.0, D нар. 7.4, ~5.5 витка (ГОСТ 13766-86)."""
    x0, x1 = -53.34 + 0.05, -41.06 - 0.05
    d = 1.0
    Dm = 6.4
    L = x1 - x0 - d
    n = 5.5
    pitch = L / n
    helix = cq.Wire.makeHelix(pitch, L, Dm / 2)
    prof = cq.Workplane("XZ").center(Dm / 2, 0).circle(d / 2)
    s = prof.sweep(cq.Workplane().add(helix), isFrenet=True).val()
    s = s.translate(Vector(0, 0, d / 2))
    s = s.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90).translate(Vector(x0, 0, latch_z()))
    if side > 0:
        s = s.mirror("YZ")
    return W(s)


def make_bolt20(side):
    """Болт М6×12 ГОСТ 7798-70 (крепление скобы 8 к корпусу фиксатора)."""
    zu = kz(277.71)
    s = hex_head(10.0, zu - 4.0, zu, -LATCH_X, 0, False).fuse(cyl(3.0, zu - 0.01, zu + 12.0, -LATCH_X, 0))
    s = s.clean()
    if side > 0:
        s = s.mirror("YZ")
    return W(s)


def make_kolodka():
    """Колодка (поз. не указана) — зажимаемая губками рычагов 5 (46.56×23.3, 40*)."""
    z0, z1 = kz(285.33), kz(308.61)
    s = cq.Workplane("XY").add(box(-23.2, 23.2, -NECK_FLAT, NECK_FLAT, z0, z1))
    s = s.edges("|Y and >Z").fillet(4.0)
    return s


# ---- Заготовка ------------------------------------------------------------

def make_flange17():
    """Фланец стакана 17 (устанавливаемая деталь поз.4 корпуса, лист 2):
    Ø210, 8 отв. Ø18 на Ø180, 22°30'; бурт с фаской 45° снизу, расточка под стакан."""
    dz = 0.37
    prof = [(NECK_R + 0.05, 82.63 + dz), (65.36, 82.63 + dz), (70.02, 87.63 + dz),
            (FL17_R, 87.63 + dz), (FL17_R, 107.95 + dz), (64.05, 107.95 + dz),
            (64.05, 99.74 + dz), (NECK_R + 0.05, 99.74 + dz)]
    s = revolve(prof)
    for k in range(8):
        x, y = pol(FL17_PCD_R, A_SEC + 45 * k)
        s = s.cut(cyl(FL17_HOLE_D / 2, 80, 120, x, y))
    return W(s.clean())


def make_stakan():
    """Стакан (деталь поз.2 корпуса) — устанавливаемая заготовка, торец в расточке фланца."""
    dz = 0.37
    return W(ring(57.95, 64.0, 99.74 + dz + 0.05, 182.63 + dz))


# ---------------------------------------------------------------------------
# Состав сборки
# ---------------------------------------------------------------------------
C_BASE = cq.Color(0.45, 0.47, 0.50)
C_HUB = cq.Color(0.62, 0.64, 0.68)
C_SLEEVE = cq.Color(0.80, 0.62, 0.30)
C_CYL = cq.Color(0.70, 0.74, 0.80)
C_PIST = cq.Color(0.55, 0.60, 0.70)
C_ROD = cq.Color(0.85, 0.86, 0.88)
C_HEAD = cq.Color(0.35, 0.50, 0.65)
C_LEVER = cq.Color(0.20, 0.42, 0.62)
C_STD = cq.Color(0.25, 0.25, 0.27)
C_RUB = cq.Color(0.08, 0.08, 0.08)
C_GASK = cq.Color(0.55, 0.35, 0.20)
C_FIT = cq.Color(0.83, 0.70, 0.35)
C_SPR = cq.Color(0.75, 0.75, 0.20)
C_WP = cq.Color(0.40, 0.75, 0.45, 0.55)

# key, pos, name_ru, material, standard, note, fn, color
PARTS = []


def add(key, pos, name, mat, std, note, fn, color):
    PARTS.append(dict(key=key, pos=pos, name=name, mat=mat, std=std, note=note, fn=fn, color=color))


add("plita", "", "Плита-основание Ø200", "Сталь 45 ГОСТ 1050-2013", "",
    "Поз. на листе не указана (вероятно 19 или 22). Ø200×15, уступы 8 мм при |Y|≥70, 2 паза 12 (168, 22*), выступ Ø139.4×2 под втулку 16",
    make_base, C_BASE)
add("korpus_15", "15", "Корпус (ось-распределитель воздуха) с плитой R105", "Сталь 45 ГОСТ 1050-2013", "",
    "Ø120, канавки под кольца 29, кольцевые канавки 10*, каналы Ø5*, полость Ø56*, поясок Ø77 h8", make_hub, C_HUB)
add("vtulka_16", "16", "Втулка вращающегося соединения (неподвижная)", "Бронза БрАЖ9-4 ГОСТ 18175-78 (принято)", "",
    "Ø120/Ø139.4, прилив 20.4 под штуцеры 3", make_sleeve, C_SLEEVE)
for i, z in enumerate(ORING_Z):
    add("kolco_29_%d" % (i + 1), "29", "Кольцо уплотнительное 110-120-58", "Резина МБС", "ГОСТ 9833-73",
        "d=110 (дно канавки Ø109.7), D=120, сечение 5.8", (lambda z=z: make_oring(57.4, 5.8, z)), C_RUB)
for i, z in enumerate(PORT_Z):
    add("shtucer_3_%d" % (i + 1), "3", "Штуцер под рукав М10×1", "Сталь 20 ГОСТ 1050-2013",
        "резьба М10×1 ГОСТ 24705-2004", "S13, ниппель под рукав d8 (рукав ГОСТ 18698-79 не моделируется)",
        (lambda z=z: make_fitting(z)), C_FIT)
    add("shaiba_4_%d" % (i + 1), "4", "Шайба уплотнительная 10×14.7×1", "Медь М1 ГОСТ 859-2014", "",
        "под бурт штуцера 3", (lambda z=z: make_washer4(z)), C_FIT)
for i, a in enumerate((0, 90, 180, 270)):
    add("vint_M10_%d" % (i + 1), "", "Винт М10×20 с потайной головкой", "Сталь 35", "ГОСТ 17475-80",
        "крепление корпуса 15 к плите; поз. на листе не указана", (lambda a=a: make_csk_screw(a)), C_STD)
add("palec_24", "24", "Палец установочный (фиксация фланца под 22°30')", "Сталь 40Х ГОСТ 4543-2016", "",
    "хвостовик Ø16 H8/u8 в плите корпуса, бурт Ø25, установочная часть в отв. Ø18 фланца 17", make_pin24, C_HEAD)
add("prokladka_1_niz", "1", "Прокладка нижняя (гильза — корпус)", "Паронит ПОН-Б ГОСТ 481-80", "",
    "толщина 1.0 (замер)", lambda: make_gasket(NECK_TOP, G_BOT0, FL_R), C_GASK)
add("gilza_18", "18", "Гильза пневмоцилиндра с фланцами", "Труба 88×5.5 ГОСТ 8734-75 / Сталь 20; фланцы Ст3", "",
    "Ø77 H9, наружн. Ø88*, фланцы 14* и 11.6, лыска на 22°30' под трубку 13", make_gilza, C_CYL)
add("trubka_13", "13", "Трубка подвода воздуха в надпоршневую полость", "Сталь 20 ГОСТ 1050-2013", "",
    "Ø12/Ø5, R48.6 на 22°30'", make_tube13, C_CYL)
for i, zc in enumerate((105.8, 181.7)):
    add("kolco_25_%d" % (i + 1), "25", "Кольцо уплотнительное 007-012-30", "Резина МБС", "ГОСТ 9833-73",
        "уплотнение трубки 13 во фланцах гильзы", (lambda zc=zc: make_oring25(zc)), C_RUB)
add("porshen_14", "14", "Поршень", "Сталь 45 ГОСТ 1050-2013 (Д16Т — вариант)", "",
    "Ø77 f9, толщина 27.1, выточка под гайки 23", make_piston, C_PIST)
for i, zc in enumerate((119.17, 130.34)):
    add("kolco_28_%d" % (i + 1), "28", "Кольцо уплотнительное 067-077-58", "Резина МБС", "ГОСТ 9833-73",
        "уплотнение поршня 14", (lambda zc=zc: make_oring(35.9, 5.8, zc)), C_RUB)
add("shtok_2", "2", "Шток", "Сталь 40Х ГОСТ 4543-2016", "",
    "Ø20 h6, цапфа Ø12 k7, резьба М12, хвостовик 10 с отв. Ø8 H11", make_rod, C_ROD)
add("kolco_26", "26", "Кольцо уплотнительное 006-012-36", "Резина МБС", "ГОСТ 9833-73",
    "уплотнение цапфы штока в поршне", lambda: make_oring(4.44, 3.6, 132.7), C_RUB)
for i, z0 in enumerate((110.25, 116.25)):
    add("gaika_23_%d" % (i + 1), "23", "Гайка М12 низкая", "Сталь 35", "ГОСТ 5916-70",
        "S18, m6 (по чертежу); вторая — контргайка", (lambda z0=z0: make_nut23(z0)), C_STD)
add("prokladka_1_verh", "1", "Прокладка верхняя (гильза — крышка)", "Паронит ПОН-Б ГОСТ 481-80", "",
    "толщина 1.6 (замер)", lambda: make_gasket(G_TOP1, COVER_Z0, FL_R), C_GASK)
add("kryshka_11", "11", "Крышка пневмоцилиндра с направляющей горловиной", "Сталь 45 ГОСТ 1050-2013", "",
    "14*, поясок Ø77 h8, отв. Ø20 H7, горловина Ø46.4 с лысками 40*, каналы Ø5 H8", make_cover, C_CYL)
add("kolco_27", "27", "Кольцо уплотнительное 020-030-58", "Резина МБС", "ГОСТ 9833-73",
    "уплотнение штока в крышке", lambda: make_oring(12.55, 5.8, 180.7), C_RUB)
add("zaglushka_12", "12", "Заглушка канала Ø5 u8×5.6", "Сталь 20", "", "Ø5 H8/u8, 7 от торца крышки",
    make_plug12, C_STD)
for i, a in enumerate(BOLT_ANG):
    add("bolt_21_%02d" % (i + 1), "21", "Болт М6×25", "Сталь 35", "ГОСТ 7798-70",
        "крепление крышки 11 к гильзе 18", (lambda a=a: make_bolt_top(a)), C_STD)
for i, a in enumerate(BOLT_ANG):
    add("bolt_M6_niz_%02d" % (i + 1), "", "Болт М6×25", "Сталь 35", "ГОСТ 7798-70",
        "крепление гильзы 18 к корпусу 15; поз. на листе не указана", (lambda a=a: make_bolt_bot(a)), C_STD)
add("traversa_10", "10", "Траверса (серьга) головки", "Сталь 45 ГОСТ 1050-2013", "",
    "3 отв. Ø8 H7 (58), пазы 10.2 под проушины", make_traversa, C_HEAD)
for nm, x in (("L", -PIN_X), ("C", 0.0), ("R", PIN_X)):
    add("os_9_%s" % nm, "9", "Ось Ø8×20", "Сталь 45", "по типу штифта ГОСТ 3128-70",
        "Б: Ø8 H7/m6 в траверсе, Ø8 H11/h11 в проушине", (lambda x=x: make_os9(x)), C_STD)
for nm, sd in (("L", -1), ("R", 1)):
    add("rychag_5_%s" % nm, "5", "Рычаг-прихват", "Сталь 45 ГОСТ 1050-2013", "", "толщина 20.4, проушина 10",
        (lambda sd=sd: make_lever(sd)), C_LEVER)
    add("korpus_fiks_%s" % nm, "", "Корпус фиксатора", "Сталь 45", "",
        "поз. на листе не указана; канал Ø11.93 под фиксатор 6", (lambda sd=sd: make_latch_body(sd)), C_HEAD)
    add("skoba_8_%s" % nm, "8", "Скоба (крышка фиксатора)", "Сталь 20", "", "упор пружины 7, крепится болтом 20",
        (lambda sd=sd: make_skoba8(sd)), C_HEAD)
    add("fiksator_6_%s" % nm, "6", "Фиксатор (плунжер)", "Сталь 45, HRC 40..45", "", "Ø11.85, сферический торец",
        (lambda sd=sd: make_fiksator6(sd)), C_ROD)
    add("pruzhina_7_%s" % nm, "7", "Пружина сжатия 1.0×7.4", "Проволока 65Г ГОСТ 9389-75", "ГОСТ 13766-86",
        "d=1.0, D=7.4, n≈5.5", (lambda sd=sd: make_spring7(sd)), C_SPR)
    add("bolt_20_%s" % nm, "20", "Болт М6×12", "Сталь 35", "ГОСТ 7798-70", "крепление скобы 8",
        (lambda sd=sd: make_bolt20(sd)), C_STD)
add("kolodka", "", "Колодка, зажимаемая губками рычагов 5", "Сталь 45", "",
    "поз. на листе не указана (заштрихована на главном виде), 46.4×23.3×40", make_kolodka, C_HUB)
add("flanec_17", "17", "Фланец стакана (свариваемая деталь поз.4 корпуса)", "Сталь 20 ГОСТ 1050-2013", "",
    "заготовка: Ø210, 8 отв. Ø18 на Ø180 под 22°30', толщина 20.3", make_flange17, C_WP)
add("stakan_zagotovka", "", "Стакан (свариваемая деталь поз.2 корпуса)", "Сталь 20", "",
    "заготовка, на листе 7 без номера позиции; Ø128/Ø116 по чертежу листа 7", make_stakan, C_WP)


# ---------------------------------------------------------------------------
# Построение, экспорт, проверки
# ---------------------------------------------------------------------------

def is_oring(k):
    return k.startswith("kolco_")


def build():
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="Prisposoblenie_svarochnoe_2")
    solids = {}
    for p in PARTS:
        wp = p["fn"]()
        v = wp.val()
        if not v.isValid():
            v = v.fix()
            wp = W(v)
        solids[p["key"]] = wp
        assy.add(wp, name=p["key"], color=p["color"])
        cq.exporters.export(wp, os.path.join(OUT, "parts_step", p["key"] + ".step"))
        cq.exporters.export(wp, os.path.join(OUT, "parts_stl", p["key"] + ".stl"),
                            tolerance=0.05, angularTolerance=0.25)
        print("built %-20s V=%10.1f valid=%s" % (p["key"], wp.val().Volume(), wp.val().isValid()))
        sys.stdout.flush()
    assy.save(os.path.join(OUT, "prisposoblenie_svarochnoe_2.step"))
    assy.save(os.path.join(OUT, "prisposoblenie_svarochnoe_2.glb"), tolerance=GLB_TOL,
              angularTolerance=GLB_ANG)
    if "--rot" in sys.argv:
        # вспомогательная сборка, повёрнутая на -22°30' (для рендера правой половины разреза А-А)
        rot = cq.Assembly(name="rot22")
        loc = cq.Location(Vector(0, 0, 0), Vector(0, 0, 1), -A_SEC)
        for p in PARTS:
            rot.add(solids[p["key"]], name=p["key"], color=p["color"], loc=loc)
        os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
        rot.save(os.path.join(HERE, "work", "model_rot22.glb"), tolerance=GLB_TOL, angularTolerance=GLB_ANG)
    return solids


def check(solids):
    res = {"invalid": [], "interferences": [], "oring_squeeze": []}
    all_bb = None
    for key, wp in solids.items():
        v = wp.val()
        bb = v.BoundingBox()
        all_bb = bb if all_bb is None else all_bb.add(bb)
        if not v.isValid() or v.Volume() <= 0:
            res["invalid"].append(key)
    res["bbox"] = [round(all_bb.xmin, 2), round(all_bb.xmax, 2), round(all_bb.ymin, 2),
                   round(all_bb.ymax, 2), round(all_bb.zmin, 2), round(all_bb.zmax, 2)]
    print("Габарит: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % tuple(res["bbox"]))
    keys = list(solids)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = solids[keys[i]].val(), solids[keys[j]].val()
            ba, bb_ = a.BoundingBox(), b.BoundingBox()
            if (ba.xmin > bb_.xmax or bb_.xmin > ba.xmax or ba.ymin > bb_.ymax
                    or bb_.ymin > ba.ymax or ba.zmin > bb_.zmax or bb_.zmin > ba.zmax):
                continue
            try:
                v = a.intersect(b).Volume()
            except Exception as ex:  # noqa
                v = -1
            if v > 0.01 or v < 0:
                rec = (keys[i], keys[j], round(v, 3))
                if is_oring(keys[i]) or is_oring(keys[j]):
                    res["oring_squeeze"].append(rec)
                else:
                    res["interferences"].append(rec)
    for r in res["interferences"]:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.3f мм3" % r)
    print("Обжатие колец (допустимо):", len(res["oring_squeeze"]))
    print("Невалидные тела:", res["invalid"])
    return res


def write_spec(solids):
    groups = {}
    order = []
    for p in PARTS:
        k = p["key"]
        base = k.rstrip("0123456789").rstrip("_")
        for suf in ("_L", "_R", "_C", "_niz", "_verh"):
            pass
        if base.endswith("_L") or base.endswith("_R") or base.endswith("_C"):
            base = base[:-2]
        gk = (base, p["pos"], p["name"])
        if gk not in groups:
            groups[gk] = dict(key=base + "*", pos=p["pos"], name_ru=p["name"], qty=0,
                              material=p["mat"], standard=p["std"], note=p["note"], nodes=[])
            order.append(gk)
        groups[gk]["qty"] += 1
        groups[gk]["nodes"].append(k)
    spec = [groups[g] for g in order]
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    return spec


if __name__ == "__main__":
    s = build()
    spec = write_spec(s)
    r = check(s)
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    print("GLB size: %.2f MB" % (os.path.getsize(os.path.join(OUT, "prisposoblenie_svarochnoe_2.glb")) / 1e6))
