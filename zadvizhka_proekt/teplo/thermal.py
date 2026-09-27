# -*- coding: utf-8 -*-
"""
Тепловой расчёт сварки корпуса задвижки (эталонная реализация на numpy; страница повторяет её на JS).

Аналитика: Рыкалин Н.Н. — быстродвижущиеся источники (линейный в тонкой пластине, точечный на массивном теле).
Численно: теплопроводность в поперечном сечении шва (y, z) при быстродвижущемся источнике —
тепло вдоль шва не распространяется, мощность подаётся во времени по Гауссу (длительность прохода дуги).
"""
import math
import numpy as np

# Режим (лист 5): Iсв 134 А, Uд 23 В, Vсв 46 м/ч; КПД дуги MAG 0,8
I, U, V_MH, ETA = 134.0, 23.0, 46.0, 0.8
v = V_MH * 1000 / 3600            # мм/с
q = ETA * U * I                   # Вт
E = q / v                         # Дж/мм — погонная энергия
# Сталь 20, средние значения (Рыкалин): λ, cρ
LAM = 0.042                       # Вт/(мм·К)   (0,42 Вт/(см·К))
CRHO = 0.0052                     # Дж/(мм³·К)  (5,2 Дж/(см³·К))
A = LAM / CRHO                    # мм²/с
T0 = 20.0
TM = 1500.0                       # плавление (ликвидус стали 20 ≈ 1515, солидус ≈ 1470)


def t85_thin(delta, T0=T0):
    return E**2 / (4*math.pi*LAM*CRHO*delta**2) * (1/(500-T0)**2 - 1/(800-T0)**2)


def t85_thick(T0=T0):
    return E / (2*math.pi*LAM) * (1/(500-T0) - 1/(800-T0))


def delta_cr(T0=T0):
    return math.sqrt(E / (2*CRHO) * (1/(500-T0) + 1/(800-T0)))


def adams_thin_Y(Tp, delta, T0=T0):
    """Расстояние от границы сплавления до изотермы максимальной температуры Tp (Adams, тонкая пластина)."""
    return E / (math.sqrt(2*math.pi*math.e) * CRHO * delta) * (1/(Tp-T0) - 1/(TM-T0))


GEOMS = {
    # (y0,y1,z0,z1) прямоугольники материала, мм; корень шва; валик — треугольник катета K
    "plate6": dict(rects=[(-60, 60, -6, 0)], root=(0.0, 0.0), bead=None, box=(-60, 60, -6, 0)),
    "shov1": dict(rects=[(-40, 40, -6, 0), (-7, 7, 0, 8)], root=(7.0, 0.0), bead=(7.0, 0.0, +1, +1, 3.0), box=(-40, 40, -6, 8)),
    "shov2": dict(rects=[(-6, 50, -20, 0), (-6, 0, 0, 30)], root=(0.0, 0.0), bead=(0.0, 0.0, +1, +1, 3.0), box=(-6, 50, -20, 30)),
}


def build(geom, dx):
    y0, y1, z0, z1 = geom["box"]
    ny, nz = int(round((y1-y0)/dx)), int(round((z1-z0)/dx))
    yc = y0 + (np.arange(ny)+0.5)*dx
    zc = z0 + (np.arange(nz)+0.5)*dx
    Y, Z = np.meshgrid(yc, zc, indexing="ij")
    m = np.zeros((ny, nz), bool)
    for (a, b, c, d) in geom["rects"]:
        m |= (Y >= a) & (Y <= b) & (Z >= c) & (Z <= d)
    if geom["bead"]:
        by, bz, sy, sz, K = geom["bead"]
        u, w = (Y-by)*sy, (Z-bz)*sz
        m |= (u >= 0) & (w >= 0) & (u + w <= K)
    return Y, Z, m


def probe_cycles(name, pts, dx=0.25, t_end=12.0, rb=2.5, t_peak=0.8):
    """Термические циклы в точках pts [(y,z)]: возвращает t, T[:, i]."""
    g = GEOMS[name]
    Y, Z, m = build(g, dx)
    idx = [(min(Y.shape[0]-1, max(0, int((y-g['box'][0])/dx))), min(Y.shape[1]-1, max(0, int((z-g['box'][2])/dx)))) for y, z in pts]
    ry, rz = g["root"]
    w = np.exp(-((Y-ry)**2 + (Z-rz)**2) / rb**2) * m
    w /= w.sum() * dx * dx
    sig_t = rb / v / 2 ** 0.5
    dt = 0.2 * dx * dx / A
    T = np.full(m.shape, T0); mf = m.astype(float)
    dirs = [(0, 1), (0, -1), (1, 1), (1, -1)]
    nb = []
    for ax, s in dirs:
        a = np.roll(mf, s, ax)
        if ax == 0:
            a[0 if s == 1 else -1, :] = 0
        else:
            a[:, 0 if s == 1 else -1] = 0
        nb.append(a)
    ts, rec = [], []
    Tmax = T.copy()
    for k in range(int(t_end/dt)):
        t = k*dt
        P = E * math.exp(-0.5*((t-t_peak)/sig_t)**2) / (sig_t*math.sqrt(2*math.pi))
        lap = sum(nb[i]*(np.roll(T, s, ax)-T) for i, (ax, s) in enumerate(dirs))
        T = T + dt*(A*lap/(dx*dx) + P*w/CRHO)*mf
        np.maximum(Tmax, T, out=Tmax)
        if k % 20 == 0:
            ts.append(t); rec.append([T[i, j] for i, j in idx])
    return np.array(ts), np.array(rec), Tmax, (Y, Z, m)


def t85_of(ts, Ts):
    """Время охлаждения 800→500 °C по записанному циклу (после пика)."""
    ip = int(np.argmax(Ts))
    c = Ts[ip:]; tt = ts[ip:]
    if c.max() < 800:
        return None
    def cross(T):
        j = np.argmax(c <= T)
        return np.interp(T, [c[j], c[j-1]], [tt[j], tt[j-1]])
    return cross(500) - cross(800)


if __name__ == "__main__":
    print("v = %.2f мм/с, q = %.0f Вт, q/v = %.1f Дж/мм, a = %.2f мм²/с" % (v, q, E, A))
    print("δкр = %.2f мм" % delta_cr())
    for d in (5, 6, 8, 14, 20):
        print("  t8/5 тонкая пластина δ=%2d: %.2f с" % (d, t85_thin(d)))
    print("  t8/5 массивное тело: %.2f с" % t85_thick())
    print("  ширина ЗТВ до Ac1=735 (Adams, δ=6): %.2f мм; до 1100: %.2f мм" % (adams_thin_Y(735, 6), adams_thin_Y(1100, 6)))
    # проверка численной модели: пластина 6 мм, точка на поверхности вдали от корня (в ЗТВ)
    for name, pts in [("plate6", [(3.0, -3.0), (4.0, -3.0), (5.0, -3.0)])]:
        ts, rec, Tmax, _ = probe_cycles(name, pts)
        for i, p in enumerate(pts):
            print("  FD %s точка %s: Tmax %.0f °C, t8/5 = %s" % (name, p, rec[:, i].max(), t85_of(ts, rec[:, i])))
