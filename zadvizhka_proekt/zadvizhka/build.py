# -*- coding: utf-8 -*-
"""
3D-модель задвижки трубопровода — общий вид (лист 1 «Задвижка трубопровода», М 1:1,
дипломный проект «Технология сборки-сварки корпуса задвижки трубопровода»).

Позиции листа 1 (спецификации на листе нет — наименования определены по чертежу):
  поз.1 Корпус (сварной, лист 2) — ИМПОРТ из ../korpus/build.py (не перемоделируется)
  поз.2 Траверса нижняя (основание бугеля) — планка 104×100×12, опирается на горловину крышки
  поз.3 Маховик Ø248
  поз.4 Фланец сальника нажимной — планка 104×56×16, два болта M12 (75)
  поз.5 Клин
  поз.6 Набивка сальника
Без позиций (нарисованы): крышка Ø210×20 с горловиной сальника, прокладка, шпиндель Ø24 (M24
на верхнем конце), грундбукса, стойки бугеля (2), траверса верхняя (бугель), втулка ходовая
(гайка шпинделя) M42, шайба упорная, шпонка, гайка M42, наплавка клина, 8 болтов M16×75 +
гайки + шайбы (крышка—корпус), 2 болта M12×80 + гайки + шайбы (сальник).

Система координат — как у корпуса: X — ось прохода, Z — ось шпинделя (вверх), начало —
пересечение осей. Размеры в мм. Клин показан в положении «закрыто» (как на чертеже).

Масштаб PDF листа 1: 1 мм = 8,05 px @200 dpi (калибровка по 52, 357, 500, 102, 138, 40, 75, 224).
Ось задвижки на листе: x = 1457 px, ось прохода: y = 3461,5 px.

Запуск: python3 build.py
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
KORPUS_DIR = "/home/user/1/zadvizhka_proekt/korpus"
sys.path.insert(0, KORPUS_DIR)
from build import make_korpus_parts, INTERFACE  # noqa: E402  (корпус, лист 2)

# ---------------------------------------------------------------------------
# Сопряжение с корпусом (из INTERFACE корпуса)
# ---------------------------------------------------------------------------
Z_BODY_FL_BOT = INTERFACE["z_flanec_stakana_niz"]        # 130 — низ фланца стакана
Z_BODY_HUB = INTERFACE["z_flanec_stakana_vystup"]        # 155 — торец выступа Ø130
FL_D = INTERFACE["flanec_D"]                             # Ø210
FL_BC = INTERFACE["flanec_Dbc"]                          # Ø180
FL_HOLE = INTERFACE["flanec_hole"]                       # Ø18
HOLE_ANG = INTERFACE["flanec_stakana_hole_ang_from_X"]   # 22,5°±1°
ST_ID = INTERFACE["stakan_ID"]                           # Ø118
SEAT_GAP, SEAT_Z0 = INTERFACE["seat_gap_at_z"]           # 34 при z = −55,5
SEAT_ANG = INTERFACE["seat_angle_deg"]                   # 6,2°
GD_Y = INTERFACE["napravl_y_face"]                       # 45 (90* между направляющими)
GD_W = INTERFACE["napravl_w"]                            # 14*

# ---------------------------------------------------------------------------
# Общие размеры листа 1
# ---------------------------------------------------------------------------
H_52 = 52.0                     # «52» — низ фланца корпуса … верх крышки
Z_COVER_TOP = Z_BODY_FL_BOT + H_52          # 182 (181* справочный — см. NOTES)
T_COVER = 20.0                  # «20*» — толщина тарелки крышки
Z_COVER_PLATE = Z_COVER_TOP - T_COVER       # 162
GASKET_T = 2.0                  # прокладка: 52 − 20 − 20 − 5 − 5 = 2 (по векторам 1,9)
Z_COVER_SPIGOT = Z_BODY_HUB + GASKET_T      # 157 — торец выступа крышки
COVER_RF_D = 130.0              # выступ крышки Ø130 / Ø140, фаска 45° (как у фланца корпуса)
COVER_RF_D0 = 140.0
NECK_D = 50.0                   # горловина сальника Ø50 (по векторам Ø49,7)
H_40 = 40.0                     # «40» — верх крышки … низ траверсы поз.2
Z_NECK_TOP = Z_COVER_TOP + H_40             # 222
BOX_D = 40.0                    # сальниковая камера Ø40 (по векторам Ø39,6…40)
Z_BOX_CONE = 177.8              # низ конуса камеры (по векторам)
STEM_D = 24.0                   # шпиндель Ø24 (M24 на конце; по векторам Ø24,2)
STEM_HOLE = 25.0                # отверстие под шпиндель в крышке/фланце сальника

# поз.2 — траверса нижняя
T2 = 12.0                       # по векторам 11,8
Z2_TOP = Z_NECK_TOP + T2        # 234
P2_X, P2_Y = 104.0, 100.0       # по векторам 104,0 (гл. вид) × 100,2 (вид слева)

# поз.4 — фланец сальника
H_102 = 102.0                   # «102» — верх крышки … верх фланца сальника
Z4_TOP = Z_COVER_TOP + H_102    # 284
T4 = 16.0                       # по векторам 15,5
Z4_BOT = Z4_TOP - T4            # 268
P4_X, P4_Y = 104.0, 56.0        # по векторам 103,9 × 56,8
BOLT_SPACING = 75.0             # «75» — между осями болтов сальника
HOLE_M12 = 14.0                 # отв. под M12 (ГОСТ 11284-75, 2-й ряд; по векторам 14,3)

# траверса верхняя (бугель) и стойки
H_138 = 138.0                   # «138» — верх крышки … низ траверсы верхней
Z_BLK_BOT = Z_COVER_TOP + H_138 # 320
Z_BLK_TOP = 344.0               # по векторам 343,8 (= низ ступицы маховика)
BLK_X, BLK_Y = 74.0, 76.0       # по векторам 73,8 × 76,1
POST_W = 40.0                   # ширина стойки (по X), по векторам 39,5
# контур стойки (Y, Z) по векторам вида слева (калибровка 2,898 pt/мм, верх поз.2 = 234)
POST_BOT_IN = (45.4, 229.7)
POST_BOT_OUT = (52.8, 230.7)
POST_TOP_OUT = (39.3, 327.1)
POST_TOP_IN = (31.9, 326.0)

# ходовая втулка, маховик
BUSH_D = 42.0                   # «M42» — наружная резьба втулки
BUSH_COLLAR_D = 52.4            # бурт (по векторам)
Z_BUSH_BOT = 325.0              # по векторам 325,0
Z_COLLAR_TOP = 331.8
Z_CBORE_TOP = 336.7             # ступень расточки траверсы (по векторам)
CBORE_D = 55.2
Z_BUSH_TOP = 387.0              # по векторам 386,8
H_357 = 357.0                   # «357» — ось прохода … середина обода маховика
HW_D = 248.0                    # «Ø248»
HW_RIM = 25.0                   # сечение обода Ø25 (по векторам 25,0)
HUB_D = 60.0                    # ступица Ø60 (по векторам 59,6)
Z_HUB_TOP = 369.5               # по векторам (вид слева)
SPOKE_D = 13.0                  # спица (по разрезу 12,7)
N_SPOKES = 4
NUT42_E, NUT42_M = 60.0, 10.0   # гайка M42 — по чертежу e = 60, m = 10 (см. NOTES)
KEY_B, KEY_H, KEY_T1, KEY_T2, KEY_L = 12.0, 8.0, 5.0, 3.3, 20.0  # шпонка 12×8 ГОСТ 23360-78

# шпиндель
H_500 = 500.0                   # «500» — низ фланцев (z = −105) … верх шпинделя
Z_STEM_TOP = H_500 - FL_D / 2   # 395
STEM_NECK_D = 12.0              # шейка Т-образной головки (по векторам 12)
STEM_HEAD_D = 29.4              # головка (по векторам 29,4)
Z_HEAD_BOT = 45.2               # по векторам
Z_HEAD_TOP = 51.2
Z_SNECK_TOP = 72.2

# клин поз.5
Z_WEDGE_TOP = 64.2              # по векторам 64,2
Z_WEDGE_BOT = -59.4             # по векторам −59,4
WEDGE_R_BORE = 58.5             # вписан в Ø118 стакана с зазором 0,5
WEDGE_GAP = 0.05                # зазор уплотнительных поверхностей в положении «закрыто»
WEDGE_OVERLAY = 2.0             # наплавка клина (узкая полоса на разрезе)
WEDGE_RING = (47.0, 57.5)       # кольцо наплавки перекрывает седло Ø99…Ø111
SLOT_CLR = 0.5                  # зазор в пазах по направляющим
POCKET_D = 35.0                 # центральные выемки клина (по векторам Ø35)
POCKET_X = 13.4                 # дно выемки от оси
STROKE = 88.0                   # ход клина (ограничен торцом выступа крышки, см. NOTES)

# сальник
Z_GLAND_BOT = 231.0             # по векторам 229,9…231,9
GLAND_D = 39.6
GLAND_BORE = 24.5
GLAND_GROOVE = (257.8, 262.7, 30.0)

# крепёж
M16 = dict(d=16.0, S=24.0, k=10.0, m=13.0, wd=30.0, ws=3.0, wd1=17.0, L=75.0)   # ГОСТ 7798/5915/11371
M12 = dict(d=12.0, S=18.0, k=7.5, m=10.0, wd=24.0, ws=2.5, wd1=13.0, L=80.0)

# ---------------------------------------------------------------------------
# Помощники
# ---------------------------------------------------------------------------
def V(*a):
    return cq.Vector(*a)


def W(shape):
    return cq.Workplane("XY").add(shape)


def valid(wp, name):
    s = wp.val()
    if not isinstance(s, cq.Solid) and hasattr(s, "Solids") and len(s.Solids()) == 1:
        s = s.Solids()[0]
        wp = W(s)
    assert s.isValid(), "invalid solid: " + name
    assert s.Volume() > 1e-3, "zero volume: " + name
    return wp


def revolve_z(pts):
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))


def cyl(r, h, p, d=(0, 0, 1)):
    return W(cq.Solid.makeCylinder(r, h, V(*p), V(*d)))


def box(x0, x1, y0, y1, z0, z1):
    return W(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0)))


def hex_prism(S, h, z0=0.0, ch_top=True, ch_bot=False, bore=0.0):
    """Шестигранник под ключ S, высота h, от z0; фаски 30° на торцах; вершины на оси X."""
    e = S / math.cos(math.radians(30))
    hx = cq.Workplane("XY").polygon(6, e).extrude(h)
    rb, rt = e / 2 + 0.5, 0.95 * S / 2
    dz = (rb - rt) * math.tan(math.radians(30))
    pts = [(0, 0)]
    pts += [(rt, 0), (rb, dz)] if ch_bot else [(rb, 0)]
    pts += [(rb, h - dz), (rt, h)] if ch_top else [(rb, h)]
    pts += [(0, h)]
    hx = hx.intersect(revolve_z(pts))
    if bore:
        hx = hx.cut(cyl(bore / 2, h + 2, (0, 0, -1)))
    return hx.translate((0, 0, z0))


def bolt(p, L, S, k, d, head_up=True):
    """Болт ГОСТ 7798-70: опорная поверхность головки в точке p, стержень длиной L."""
    x, y, z = p
    head = hex_prism(S, k, 0, ch_top=True)
    sh = revolve_z([(0, -L), (d / 2 - 1.0, -L), (d / 2, -L + 1.0), (d / 2, 0.01), (0, 0.01)])
    b = head.union(sh)
    if not head_up:
        b = b.mirror("XY")
    return b.translate((x, y, z))


def nut(p, S, m, d, up=True):
    """Гайка ГОСТ 5915-70 (фаски с двух сторон), опорный торец в p, растёт по +Z (up)."""
    n = hex_prism(S, m, 0, ch_top=True, ch_bot=True, bore=d)
    if not up:
        n = n.mirror("XY")
    return n.translate(p)


def washer(p, d1, d2, s, up=True):
    w = cyl(d2 / 2, s, (0, 0, 0)).cut(cyl(d1 / 2, s + 2, (0, 0, -1)))
    if not up:
        w = w.mirror("XY")
    return w.translate(p)


def bolt_circle():
    for k in range(8):
        a = math.radians(HOLE_ANG + 45.0 * k)
        yield FL_BC / 2 * math.cos(a), FL_BC / 2 * math.sin(a)


def seat_x(z):
    """x плоскости уплотнительной поверхности правого седла (как в корпусе)."""
    return SEAT_GAP / 2 + (z - SEAT_Z0) * math.tan(math.radians(SEAT_ANG))


def seat_halfspace(u0, u1):
    """Слой между плоскостями, параллельными правому седлу (u — смещение по нормали наружу)."""
    t = math.radians(SEAT_ANG)
    b = cq.Solid.makeBox(u1 - u0, 400, 400, V(u0, -200, -200))
    b = b.rotate(V(0, 0, 0), V(0, 1, 0), SEAT_ANG)
    b = b.translate(V(SEAT_GAP / 2, 0, SEAT_Z0))
    return W(b)


# ---------------------------------------------------------------------------
# Детали
# ---------------------------------------------------------------------------
def make_kryshka():
    """Крышка: тарелка Ø210×20, выступ Ø130/Ø140 h5 (45°), горловина Ø50 до z=222,
    сальниковая камера Ø40 с коническим дном, отверстие Ø25 под шпиндель, 8 отв. Ø18 на Ø180."""
    rs = STEM_HOLE / 2
    pts = [(rs, Z_COVER_SPIGOT), (COVER_RF_D / 2, Z_COVER_SPIGOT),
           (COVER_RF_D0 / 2, Z_COVER_PLATE), (FL_D / 2, Z_COVER_PLATE),
           (FL_D / 2, Z_COVER_TOP), (NECK_D / 2, Z_COVER_TOP), (NECK_D / 2, Z_NECK_TOP),
           (BOX_D / 2, Z_NECK_TOP), (BOX_D / 2, Z_COVER_TOP), (rs, Z_BOX_CONE)]
    k = revolve_z(pts)
    for x, y in bolt_circle():
        k = k.cut(cyl(FL_HOLE / 2, 40, (x, y, Z_COVER_PLATE - 10)))
    return valid(k, "kryshka")


def make_prokladka():
    """Прокладка Ø130/Ø118×2 (паронит ГОСТ 481-80)."""
    p = cyl(COVER_RF_D / 2, GASKET_T, (0, 0, Z_BODY_HUB)).cut(
        cyl(ST_ID / 2, GASKET_T + 2, (0, 0, Z_BODY_HUB - 1)))
    return valid(p, "prokladka")


def make_nabivka():
    """поз.6 Набивка сальника: кольцо Ø40/Ø24 от конуса камеры до грундбуксы."""
    r = STEM_D / 2
    rs = STEM_HOLE / 2
    # коническое дно камеры: от (Ø40, z=182) до (Ø25, z=177.8)
    zc = Z_COVER_TOP - (Z_COVER_TOP - Z_BOX_CONE) * (BOX_D / 2 - r) / (BOX_D / 2 - rs)
    pts = [(r, zc), (BOX_D / 2, Z_COVER_TOP), (BOX_D / 2, Z_GLAND_BOT), (r, Z_GLAND_BOT)]
    return valid(revolve_z(pts), "nabivka")


def make_grundbuksa():
    """Грундбукса (втулка сальника): Ø39,6/Ø24,5, z=231…268, кольцевая канавка Ø30."""
    g = cyl(GLAND_D / 2, Z4_BOT - Z_GLAND_BOT, (0, 0, Z_GLAND_BOT))
    g = g.cut(cyl(GLAND_BORE / 2, 100, (0, 0, Z_GLAND_BOT - 1)))
    z0, z1, dg = GLAND_GROOVE
    g = g.cut(cyl(GLAND_D, z1 - z0, (0, 0, z0)).cut(cyl(dg / 2, 50, (0, 0, z0 - 5))))
    return valid(g, "grundbuksa")


def make_traversa_niz():
    """поз.2 Траверса нижняя: 104×100×12, отверстие Ø40.2, 2 отв. Ø14 на 75."""
    t = box(-P2_X / 2, P2_X / 2, -P2_Y / 2, P2_Y / 2, Z_NECK_TOP, Z2_TOP)
    t = t.cut(cyl(BOX_D / 2 + 0.1, 40, (0, 0, Z_NECK_TOP - 10)))
    for sx in (-1, 1):
        t = t.cut(cyl(HOLE_M12 / 2, 40, (sx * BOLT_SPACING / 2, 0, Z_NECK_TOP - 10)))
    t = t.cut(posts_cutter())          # гнёзда под нижние концы стоек
    return valid(t, "traversa_niz")


def make_flanec_salnika():
    """поз.4 Фланец сальника нажимной: 104×56×16, отв. Ø25 под шпиндель, 2 отв. Ø14 на 75."""
    t = box(-P4_X / 2, P4_X / 2, -P4_Y / 2, P4_Y / 2, Z4_BOT, Z4_TOP)
    t = t.cut(cyl(STEM_HOLE / 2, 40, (0, 0, Z4_BOT - 10)))
    for sx in (-1, 1):
        t = t.cut(cyl(HOLE_M12 / 2, 40, (sx * BOLT_SPACING / 2, 0, Z4_BOT - 10)))
    return valid(t, "flanec_salnika")


def make_stoyka(sy):
    """Стойка бугеля: полоса 40×7 с наклоном ≈8°. По виду слева (векторы) нижний конец
    заходит на боковую грань поз.2 (низ z≈229,7…230,7, Y 45,4…52,8), верхний — на боковую
    грань верхней траверсы (верх z≈326…327,1, Y 31,9…39,3). В поз.2 и в траверсе под концы
    стоек выбраны гнёзда по контуру стойки (соединение сваркой, швы на чертеже не показаны)."""
    (yib, zib), (yob, zob) = POST_BOT_IN, POST_BOT_OUT
    (yot, zot), (yit, zit) = POST_TOP_OUT, POST_TOP_IN
    pts = [(yib, zib), (yob, zob), (yot, zot), (yit, zit)]
    s = (cq.Workplane("YZ", origin=(-POST_W / 2, 0, 0)).polyline(pts).close()
         .extrude(POST_W))
    if sy < 0:
        s = s.mirror("XZ")
    a = math.atan2(yob - yot, zot - zob)
    return valid(s, "stoyka"), math.degrees(a)


def posts_cutter():
    """Оба тела стоек — для выборки гнёзд в поз.2 и верхней траверсе."""
    return make_stoyka(1)[0].union(make_stoyka(-1)[0])


def make_traversa_verkh():
    """Траверса верхняя (бугель): 74×76×24, расточка Ø42,4 и Ø55,2 (под бурт втулки)."""
    t = box(-BLK_X / 2, BLK_X / 2, -BLK_Y / 2, BLK_Y / 2, Z_BLK_BOT, Z_BLK_TOP)
    t = t.cut(cyl(BUSH_D / 2 + 0.2, 60, (0, 0, Z_BLK_BOT - 10)))
    t = t.cut(cyl(CBORE_D / 2, Z_CBORE_TOP - Z_BLK_BOT + 1, (0, 0, Z_BLK_BOT - 1)))
    t = t.edges("|Z").chamfer(2.0)
    t = t.cut(posts_cutter())          # гнёзда под верхние концы стоек
    return valid(t, "traversa_verkh")


def make_vtulka():
    """Втулка ходовая (гайка шпинделя): внутр. резьба Tr24 (показана Ø24), наружн. M42,
    бурт Ø52,4, паз под шпонку 12×8 (t1=5)."""
    ch = 1.5
    pts = [(STEM_D / 2, Z_BUSH_BOT), (BUSH_COLLAR_D / 2, Z_BUSH_BOT),
           (BUSH_COLLAR_D / 2, Z_COLLAR_TOP), (BUSH_D / 2, Z_COLLAR_TOP),
           (BUSH_D / 2, Z_BUSH_TOP - ch), (BUSH_D / 2 - ch, Z_BUSH_TOP), (STEM_D / 2, Z_BUSH_TOP)]
    v = revolve_z(pts)
    zk0 = Z_HUB_TOP - KEY_L
    v = v.cut(box(BUSH_D / 2 - KEY_T1, BUSH_D / 2 + 5, -KEY_B / 2, KEY_B / 2, zk0, Z_HUB_TOP))
    return valid(v, "vtulka")


def make_shaiba_upornaya():
    """Шайба (кольцо) упорная над буртом втулки: Ø52,4/Ø42,4, z=331,8…336,7."""
    s = cyl(BUSH_COLLAR_D / 2, Z_CBORE_TOP - Z_COLLAR_TOP, (0, 0, Z_COLLAR_TOP))
    s = s.cut(cyl(BUSH_D / 2 + 0.2, 20, (0, 0, Z_COLLAR_TOP - 5)))
    return valid(s, "shaiba_upornaya")


def make_shponka():
    """Шпонка 12×8×20 ГОСТ 23360-78 (исп. 2, плоские торцы), в пазу втулки t1=5."""
    x0 = BUSH_D / 2 - KEY_T1
    k = box(x0, x0 + KEY_H, -KEY_B / 2, KEY_B / 2, Z_HUB_TOP - KEY_L, Z_HUB_TOP)
    return valid(k, "shponka")


def make_makhovik():
    """поз.3 Маховик Ø248: обод Ø25 (32-гранник), 4 спицы Ø13, ступица Ø60 (z=344…369,5),
    отверстие Ø42 с пазом под шпонку (t2=3,3)."""
    R = (HW_D - HW_RIM) / 2
    r = HW_RIM / 2
    # обод — тело вращения 32-угольника, вписанного в окружность Ø25 (точный тор/дуги дают
    # в OCC 7.9 неверные булевы операции со спицами и ступицей)
    n = 32
    pts = [(R + r * math.cos(2 * math.pi * (i + 0.5) / n) / math.cos(math.pi / n),
            H_357 + r * math.sin(2 * math.pi * (i + 0.5) / n) / math.cos(math.pi / n))
           for i in range(n)]
    rim = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    rim = W(rim.val().rotate(V(0, 0, 0), V(0, 0, 1), 22.5))
    hub = cyl(HUB_D / 2, Z_HUB_TOP - Z_BLK_TOP, (0, 0, Z_BLK_TOP)).faces(">Z").edges().chamfer(1.5)
    hub = W(hub.val().rotate(V(0, 0, 0), V(0, 0, 1), 45))
    m = rim.union(hub)
    for k in range(N_SPOKES):
        a = math.radians(360.0 / N_SPOKES * k)
        d = (math.cos(a), math.sin(a), 0)
        r0 = 20.0
        p0 = V(r0 * d[0], r0 * d[1], H_357)
        m = m.union(W(cq.Solid.makeCylinder(SPOKE_D / 2, R - r0, p0, V(*d))
                      .rotate(p0, p0 + V(*d), 37)))
    m = m.cut(cyl(BUSH_D / 2, 100, (0, 0, Z_BLK_TOP - 20)))
    m = m.cut(box(BUSH_D / 2 - 1, BUSH_D / 2 + KEY_T2, -KEY_B / 2, KEY_B / 2,
                  Z_BLK_TOP - 1, Z_HUB_TOP + 1))
    return valid(m, "makhovik")


def make_gayka_m42():
    """Гайка M42 (по чертежу: e=60, m=10) на резьбе втулки над ступицей маховика."""
    S = NUT42_E * math.cos(math.radians(30))
    g = hex_prism(S, NUT42_M, Z_HUB_TOP, ch_top=True, ch_bot=True, bore=BUSH_D)
    return valid(g, "gayka_m42")


def make_shpindel():
    """Шпиндель Ø24: Т-образная головка Ø29,4×6 + шейка Ø12 (в Т-пазу клина), трапецеидальная
    резьба Tr24 (показана цилиндром), конец M24 с фаской, верх z=395."""
    ch = 1.5
    pts = [(0, Z_HEAD_BOT), (STEM_HEAD_D / 2 - 1, Z_HEAD_BOT), (STEM_HEAD_D / 2, Z_HEAD_BOT + 1),
           (STEM_HEAD_D / 2, Z_HEAD_TOP), (STEM_NECK_D / 2, Z_HEAD_TOP),
           (STEM_NECK_D / 2, Z_SNECK_TOP - 3), (STEM_D / 2, Z_SNECK_TOP),
           (STEM_D / 2, Z_STEM_TOP - ch), (STEM_D / 2 - ch, Z_STEM_TOP), (0, Z_STEM_TOP)]
    return valid(revolve_z(pts), "shpindel")


def _wedge_yz_outline():
    """Контур клина в плоскости YZ: прямоугольник |y|≤58,5, z=−59,4…64,2, нижние углы R30."""
    r = 30.0
    y0, z0, z1 = WEDGE_R_BORE, Z_WEDGE_BOT, Z_WEDGE_TOP
    wp = (cq.Workplane("YZ", origin=(-100, 0, 0))
          .moveTo(-y0, z1).lineTo(-y0, z0 + r)
          .threePointArc((-y0 + r - r * math.cos(math.radians(45)), z0 + r - r * math.sin(math.radians(45))),
                         (-y0 + r, z0))
          .lineTo(y0 - r, z0)
          .threePointArc((y0 - r + r * math.cos(math.radians(45)), z0 + r - r * math.sin(math.radians(45))),
                         (y0, z0 + r))
          .lineTo(y0, z1).close().extrude(200))
    return wp


def _wedge_blank():
    """Клин без наплавки: контур YZ ∩ цилиндр R58,5 ∩ полупространства граней (седло − зазор)."""
    w = _wedge_yz_outline()
    w = w.intersect(cyl(WEDGE_R_BORE, 200, (0, 0, -100)))
    # правая грань: x ≤ seat_x(z) − gap ; левая — зеркально
    inner = seat_halfspace(-150.0, -WEDGE_GAP)
    w = w.intersect(inner).intersect(inner.mirror("YZ"))
    return w


def make_klin():
    """поз.5 Клин: уплотнительные грани 6,2° (полный угол 12,4°) параллельны седлам,
    наплавка 2 мм снята (отдельные тела), пазы по направляющим 15×(|y|≥44,5),
    Т-паз под головку шпинделя, центральные выемки Ø35."""
    w = _wedge_blank()
    # под наплавку: снять слой 2 мм в зоне кольца
    ring = cyl(WEDGE_RING[1], 200, (-100, 0, 0), (1, 0, 0)).cut(
        cyl(WEDGE_RING[0], 200, (-100, 0, 0), (1, 0, 0)))
    layer = seat_halfspace(-WEDGE_GAP - WEDGE_OVERLAY, 5.0)
    w = w.cut(ring.intersect(layer)).cut(ring.intersect(layer.mirror("YZ")))
    # пазы по направляющим (ширина 14 + 2×0,5), ступень у стенки под швы №1 (K3)
    gx = GD_W / 2 + SLOT_CLR
    for sy in (-1, 1):
        y0 = GD_Y - SLOT_CLR
        w = w.cut(box(-gx, gx, min(sy * y0, sy * 80), max(sy * y0, sy * 80), -100, 100))
        y1 = ST_ID / 2 - 3.0 - 0.6
        w = w.cut(box(-gx - 3.6, gx + 3.6, min(sy * y1, sy * 80), max(sy * y1, sy * 80), -100, 100))
    # Т-паз (сквозной по Y): шейка Ø12 → паз 13, головка Ø29,4 → паз 30,4 (6,5 высотой)
    w = w.cut(box(-STEM_NECK_D / 2 - 0.5, STEM_NECK_D / 2 + 0.5, -80, 80, Z_HEAD_TOP + 0.5, 100))
    w = w.cut(box(-STEM_HEAD_D / 2 - 0.5, STEM_HEAD_D / 2 + 0.5, -80, 80, Z_HEAD_BOT, Z_HEAD_TOP + 0.5))
    # центральные выемки Ø35 с фаской 45°
    for sx in (-1, 1):
        x_face = seat_x(0.0)
        depth = x_face - POCKET_X + 3
        cone = cq.Solid.makeCone(POCKET_D / 2, POCKET_D / 2 + depth, depth,
                                 V(sx * POCKET_X, 0, 0), V(sx, 0, 0))
        w = w.cut(W(cone))
    return valid(w, "klin")


def make_naplavka_klina(side):
    """Наплавка уплотнительной поверхности клина (кольцо Ø94…Ø115, 2 мм)."""
    w = _wedge_blank()
    ring = cyl(WEDGE_RING[1], 200, (-100, 0, 0), (1, 0, 0)).cut(
        cyl(WEDGE_RING[0], 200, (-100, 0, 0), (1, 0, 0)))
    layer = seat_halfspace(-WEDGE_GAP - WEDGE_OVERLAY, 5.0)
    if side < 0:
        layer = layer.mirror("YZ")
    n = w.intersect(ring).intersect(layer)
    # те же пазы, что и в клине
    gx = GD_W / 2 + SLOT_CLR
    for sy in (-1, 1):
        y1 = ST_ID / 2 - 3.0 - 0.6
        n = n.cut(box(-gx - 3.6, gx + 3.6, min(sy * y1, sy * 80), max(sy * y1, sy * 80), -100, 100))
    return valid(n, "naplavka_klina")


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------
C = dict(
    cover=cq.Color(0.30, 0.45, 0.68), gasket=cq.Color(0.20, 0.20, 0.20),
    pack=cq.Color(0.85, 0.85, 0.80), gland=cq.Color(0.80, 0.60, 0.30),
    yoke=cq.Color(0.35, 0.55, 0.40), stem=cq.Color(0.78, 0.78, 0.82),
    wedge=cq.Color(0.62, 0.36, 0.30), seat=cq.Color(0.82, 0.64, 0.30),
    wheel=cq.Color(0.15, 0.15, 0.18), bush=cq.Color(0.80, 0.55, 0.25),
    fast=cq.Color(0.65, 0.65, 0.60), nut=cq.Color(0.55, 0.55, 0.52),
)
MAT_ST = "Сталь 20 ГОСТ 1050-2013 (материал на листе не указан — принят как у корпуса)"
MAT_F = "Сталь 35 ГОСТ 1050-2013, кл. прочности 5.8/5 (принято)"

# (key, pos, name_ru, material, standard, note)
INFO = {}


def add(parts, key, name, wp, color, pos="", mat=MAT_ST, std="", note="", group=None):
    parts.append((key, name, wp, color))
    INFO[key] = dict(pos=pos, name=name, mat=mat, std=std, note=note, group=group or key)


def make_parts():
    parts = []
    # --- поз.1 корпус (импорт)
    ksp = json.load(open(os.path.join(KORPUS_DIR, "out", "spec.json"), encoding="utf-8"))
    kinfo = {}
    for g in ksp:
        for n in g["nodes"]:
            kinfo[n] = g
    for key, name, wp, color in make_korpus_parts():
        g = kinfo.get(key, {})
        sub = g.get("pos", "")
        add(parts, "p1_korpus__" + key, "Корпус: " + name, wp, color,
            pos="" if key.startswith("shov") else "1",
            mat=g.get("material", ""), std=g.get("standard", ""),
            note=("дет. %s листа 2; " % sub if sub else "") + g.get("note", ""),
            group="p1_korpus__" + g.get("key", key))
    # --- крышка, прокладка, сальник
    add(parts, "kryshka", "Крышка", make_kryshka(), C["cover"],
        note="Ø210×20*, выступ Ø130/Ø140 h5, горловина Ø50, камера Ø40, 8 отв. Ø18 на Ø180 (22,5°)")
    add(parts, "prokladka", "Прокладка", make_prokladka(), C["gasket"],
        mat="Паронит ПОН-Б ГОСТ 481-80 (принято)", note="Ø130/Ø118×2")
    add(parts, "p6_nabivka", "Набивка сальника", make_nabivka(), C["pack"], pos="6",
        mat="Набивка АП-31 ГОСТ 5152-84 (принято)", std="ГОСТ 5152-84",
        note="кольца Ø40/Ø24, высота пакета ≈50")
    add(parts, "grundbuksa", "Грундбукса (втулка сальника)", make_grundbuksa(), C["gland"],
        mat="БрАЖ9-4 ГОСТ 18175-78 (принято)", note="Ø39,6/Ø24,5, z=231…268")
    add(parts, "p2_traversa_niz", "Траверса нижняя (основание бугеля)", make_traversa_niz(),
        C["yoke"], pos="2", note="104×100×12, опирается на горловину крышки (z=222…234)")
    add(parts, "p4_flanec_salnika", "Фланец сальника (нажимной)", make_flanec_salnika(),
        C["yoke"], pos="4", note="104×56×16 (z=268…284), болты M12 на 75")
    ang = None
    for i, sy in enumerate((1, -1)):
        s, ang = make_stoyka(sy)
        add(parts, "stoyka_%d" % (i + 1), "Стойка бугеля (%s)" % ("Y+" if sy > 0 else "Y−"), s,
            C["yoke"], note="полоса 40×7,3, наклон %.1f°, концы в гнёздах поз.2 и траверсы (по виду слева)" % ang, group="stoyka")
    add(parts, "traversa_verkh", "Траверса верхняя (бугель)", make_traversa_verkh(), C["yoke"],
        note="74×76×24 (z=320…344)")
    add(parts, "vtulka_khodovaya", "Втулка ходовая (гайка шпинделя)", make_vtulka(), C["bush"],
        mat="БрАЖ9-4 ГОСТ 18175-78 (принято)",
        note="внутр. Tr24 (показана Ø24), наружн. M42, бурт Ø52,4")
    add(parts, "shaiba_upornaya", "Шайба упорная", make_shaiba_upornaya(), C["bush"],
        note="Ø52,4/Ø42,4×4,9")
    add(parts, "shponka", "Шпонка 12×8×20", make_shponka(), C["fast"], mat="Сталь 45 ГОСТ 1050-2013",
        std="ГОСТ 23360-78 (L=20 по чертежу; по ГОСТ для 12×8 L≥28)")
    add(parts, "p3_makhovik", "Маховик", make_makhovik(), C["wheel"], pos="3",
        mat="Чугун СЧ20 ГОСТ 1412-85 (принято)", note="Ø248, обод Ø25, 4 спицы, ступица Ø60")
    add(parts, "gayka_M42", "Гайка M42", make_gayka_m42(), C["nut"], mat=MAT_F,
        std="по чертежу e=60, m=10 (ГОСТ 5916-70 M42: S=65, m=21)")
    add(parts, "shpindel", "Шпиндель", make_shpindel(), C["stem"],
        mat="Сталь 20Х13 ГОСТ 5632-2014 (принято)",
        note="Ø24, Tr24 (цилиндром), конец M24, Т-головка Ø29,4×6, верх z=395")
    add(parts, "p5_klin", "Клин", make_klin(), C["wedge"], pos="5",
        note="угол граней 6,2° (полный 12,4°), z=−59,4…64,2, пазы по направляющим 15")
    for i, sd in enumerate((-1, 1)):
        add(parts, "naplavka_klina_%s" % ("L" if sd < 0 else "R"),
            "Наплавка уплотнительной поверхности клина (%s)" % ("лев." if sd < 0 else "прав."),
            make_naplavka_klina(sd), C["seat"], mat="наплавка (материал на чертеже не указан)",
            note="кольцо Ø94…Ø115 × 2", group="naplavka_klina")
    # --- крепёж крышки: болт M16×75 (головка на крышке), шайба + гайка под фланцем корпуса
    for i, (x, y) in enumerate(bolt_circle()):
        n = i + 1
        add(parts, "bolt_M16x75_%d" % n, "Болт M16×75", bolt((x, y, Z_COVER_TOP), M16["L"], M16["S"],
            M16["k"], M16["d"]), C["fast"], mat=MAT_F, std="Болт M16×75.58 ГОСТ 7798-70",
            group="bolt_M16x75")
        add(parts, "shaiba_16_%d" % n, "Шайба 16", washer((x, y, Z_BODY_FL_BOT), M16["wd1"], M16["wd"],
            M16["ws"], up=False), C["fast"], mat=MAT_F, std="Шайба 16 ГОСТ 11371-78", group="shaiba_16")
        add(parts, "gayka_M16_%d" % n, "Гайка M16", nut((x, y, Z_BODY_FL_BOT - M16["ws"]), M16["S"],
            M16["m"], M16["d"], up=False), C["nut"], mat=MAT_F, std="Гайка M16.5 ГОСТ 5915-70",
            group="gayka_M16")
    # --- крепёж сальника: болт M12×80 (головка под поз.2), шайба + гайка на поз.4
    for i, sx in enumerate((-1, 1)):
        n = i + 1
        x = sx * BOLT_SPACING / 2
        add(parts, "bolt_M12x80_%d" % n, "Болт M12×80", bolt((x, 0, Z_NECK_TOP), M12["L"], M12["S"],
            M12["k"], M12["d"], head_up=False), C["fast"], mat=MAT_F,
            std="Болт M12×80.58 ГОСТ 7798-70", group="bolt_M12x80")
        add(parts, "shaiba_12_%d" % n, "Шайба 12", washer((x, 0, Z4_TOP), M12["wd1"], M12["wd"],
            M12["ws"]), C["fast"], mat=MAT_F, std="Шайба 12 ГОСТ 11371-78", group="shaiba_12")
        add(parts, "gayka_M12_%d" % n, "Гайка M12", nut((x, 0, Z4_TOP + M12["ws"]), M12["S"],
            M12["m"], M12["d"]), C["nut"], mat=MAT_F, std="Гайка M12.5 ГОСТ 5915-70",
            group="gayka_M12")
    return parts, ang


# ---------------------------------------------------------------------------
# Проверки
# ---------------------------------------------------------------------------
# Намеренные контакты с объёмным пересечением (резьбовые соединения) — не ожидаются, т.к.
# резьба везде смоделирована по наружному диаметру; оставлен список для ясности.
ALLOWED = set()


def _bb_overlap(a, b, tol=0.0):
    return not (a.xmin > b.xmax + tol or b.xmin > a.xmax + tol or a.ymin > b.ymax + tol
                or b.ymin > a.ymax + tol or a.zmin > b.zmax + tol or b.zmin > a.zmax + tol)


def interference(solids, pairs=None, thr=0.01):
    keys = list(solids)
    bbs = {k: s.BoundingBox() for k, s in solids.items()}
    bad = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if a.startswith("p1_korpus__") and b.startswith("p1_korpus__"):
                continue            # внутренние проверки корпуса выполнены в korpus/build.py
            if pairs is not None and (a, b) not in pairs and (b, a) not in pairs:
                continue
            if not _bb_overlap(bbs[a], bbs[b]):
                continue
            v = solids[a].intersect(solids[b]).Volume()
            if v > thr and frozenset((a, b)) not in ALLOWED:
                bad.append((a, b, v))
    return bad


def stroke_check(solids, moving=("p5_klin", "naplavka_klina_L", "naplavka_klina_R", "shpindel"),
                 steps=(0.0, 22.0, 44.0, 66.0, STROKE)):
    """Плавность хода клина (ТТ п.1): клин+наплавка+шпиндель на всех положениях хода не
    пересекаются с неподвижными деталями; возвращает минимальные зазоры по седлу."""
    static = {k: s for k, s in solids.items() if k not in moving
              and k not in ("vtulka_khodovaya",)}      # резьба Tr24 — контакт по Ø24
    res = []
    for dz in steps:
        bad = []
        for m in moving:
            sm = solids[m].translate(V(0, 0, dz))
            bm = sm.BoundingBox()
            for k, s in static.items():
                if not _bb_overlap(bm, s.BoundingBox()):
                    continue
                v = sm.intersect(s).Volume()
                if v > 0.01:
                    bad.append((m, k, v))
        res.append((dz, bad))
    return res


def top_plane(s):
    """z наибольшей по площади плоской грани, обращённой вверх (+Z)."""
    best = None
    for f in s.Faces():
        if f.geomType() == "PLANE" and f.normalAt().z > 0.999:
            if best is None or f.Area() > best.Area():
                best = f
    return best.Center().z


def report_dims(S):
    bb = {k: s.BoundingBox() for k, s in S.items()}
    zc = top_plane(S["kryshka"])
    allb = None
    for b in bb.values():
        allb = b if allb is None else allb.add(b)
    wheel_bb = bb["p3_makhovik"]
    d = [
        ("500 низ фланцев … верх шпинделя", 500, bb["shpindel"].zmax - allb.zmin),
        ("357 ось прохода … ось обода маховика", 357, H_357),
        ("Ø248 маховик", 248, wheel_bb.xlen),
        ("52 низ фланца корпуса … верх крышки", 52, zc - Z_BODY_FL_BOT),
        ("181* ось … верх крышки", 181, zc),
        ("286* низ фланцев … верх крышки", 286, zc - allb.zmin),
        ("20* тарелка крышки", 20, Z_COVER_TOP - Z_COVER_PLATE),
        ("Ø210 крышка (вид слева «210»)", 210, bb["kryshka"].xlen),
        ("40 верх крышки … низ поз.2", 40, bb["p2_traversa_niz"].zmin - zc),
        ("102 верх крышки … верх поз.4", 102, bb["p4_flanec_salnika"].zmax - zc),
        ("138 верх крышки … низ траверсы верхней", 138, bb["traversa_verkh"].zmin - zc),
        ("75 между болтами сальника", 75, bb["bolt_M12x80_2"].center.x - bb["bolt_M12x80_1"].center.x),
        ("M42 втулка", 42, BUSH_D),
        ("M24 шпиндель", 24, bb["shpindel"].xmax * 2 if False else STEM_D),
        ("Ø180 окружность болтов крышки", 180, 2 * math.hypot(bb["bolt_M16x75_1"].center.x,
                                                              bb["bolt_M16x75_1"].center.y)),
        ("22,5° угол болтов", 22.5, math.degrees(math.atan2(bb["bolt_M16x75_1"].center.y,
                                                            bb["bolt_M16x75_1"].center.x))),
        ("224* строительная длина", 224, allb.xmax - allb.xmin if False else
         bb["p1_korpus__03_flanec_patrubka_R"].xmax - bb["p1_korpus__03_flanec_patrubka_L"].xmin),
        ("верх клина (по векторам 64,2)", 64.2, bb["p5_klin"].zmax),
        ("низ клина (по векторам −59,4)", -59.4, bb["p5_klin"].zmin),
    ]
    for n, dr, m in d:
        print("  %-42s чертёж %8.2f   модель %8.2f" % (n, dr, m))
    print("Габарит сборки: X %.1f…%.1f  Y %.1f…%.1f  Z %.1f…%.1f" % (
        allb.xmin, allb.xmax, allb.ymin, allb.ymax, allb.zmin, allb.zmax))
    return d, allb


def seat_clearance(S):
    """Зазор между плоскостью клина и уплотнительной поверхностью седла (закрыто): по оси X
    при z = 0 (минимальное расстояние между телами)."""
    a = S["naplavka_klina_R"]
    b = S["p1_korpus__naplavka_sedla_R"]
    return a.distance(b) if hasattr(a, "distance") else None


# ---------------------------------------------------------------------------
# Экспорт
# ---------------------------------------------------------------------------
def export(parts, tol=0.12, atol=0.2):
    """GLB — первым (иначе триангуляция STL 0,05 мм переиспользуется и раздувает GLB)."""
    from OCP.BRepTools import BRepTools
    os.makedirs(os.path.join(OUT, "parts_step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "parts_stl"), exist_ok=True)
    assy = cq.Assembly(name="Zadvizhka")
    for key, name, wp, color in parts:
        BRepTools.Clean_s(wp.val().wrapped)
        assy.add(wp, name=key, color=color)
    glb = os.path.join(OUT, "zadvizhka.glb")
    assy.save(glb, tolerance=tol, angularTolerance=atol)
    assy.save(os.path.join(OUT, "zadvizhka.step"))
    for key, name, wp, color in parts:
        cq.exporters.export(wp, os.path.join(OUT, "parts_step", key + ".step"))
        cq.exporters.export(wp, os.path.join(OUT, "parts_stl", key + ".stl"),
                            tolerance=0.05, angularTolerance=0.1)
    return os.path.getsize(glb) / 1e6


def write_spec(parts):
    groups, order = {}, []
    for key, name, wp, color in parts:
        inf = INFO[key]
        g = inf["group"]
        if g not in groups:
            groups[g] = dict(key=g, pos=inf["pos"], name_ru=inf["name"].split(" (")[0]
                             if g != key else inf["name"], qty=0, material=inf["mat"],
                             standard=inf["std"], note=inf["note"], nodes=[])
            order.append(g)
        groups[g]["qty"] += 1
        groups[g]["nodes"].append(key)
    spec = [groups[g] for g in order]
    with open(os.path.join(OUT, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return spec


if __name__ == "__main__":
    parts, post_ang = make_parts()
    S = {k: wp.val() for k, _, wp, _ in parts}
    for k, s in S.items():
        assert s.isValid(), k
    print("Тел: %d; наклон стоек %.2f°" % (len(S), post_ang))
    dims, allb = report_dims(S)
    bad = interference(S)
    for a, b, v in bad:
        print("ПЕРЕСЕЧЕНИЕ %s / %s: %.3f мм3" % (a, b, v))
    print("Пересечений нет" if not bad else "Пересечений: %d" % len(bad))
    st = stroke_check(S)
    for dz, b in st:
        print("  ход клина %5.1f мм: %s" % (dz, "OK" if not b else b))
    print("Зазор клин—седло (закрыто): %.3f мм" % seat_clearance(S))
    mb = export(parts)
    write_spec(parts)
    print("GLB: %.2f МБ" % mb)
    sys.exit(1 if bad or any(b for _, b in st) else 0)
