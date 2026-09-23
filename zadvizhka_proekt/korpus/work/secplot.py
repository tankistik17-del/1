"""Section of the model at plane y=0 (or z=c) overlaid on drawing vectors (sheet 2).
usage: secplot.py out.png xmin xmax zmin zmax [plane]"""
import sys, json, math
sys.path.insert(0, '/home/user/1/zadvizhka_proekt/korpus')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cadquery as cq
from build import make_korpus_parts
out = sys.argv[1]; x0, x1, z0, z1 = map(float, sys.argv[2:6])
segs = json.load(open('/home/user/1/zadvizhka_proekt/korpus/work/segs2.json'))
PX = 0.36; K = 8.05; OX, OY = 1710.0, 1447.3
fig, ax = plt.subplots(figsize=(12, 12 * (z1 - z0) / (x1 - x0)))
for s in segs:
    if s[0] != 'l': continue
    _, a, b, c, d, w = s
    X = [(a / PX - OX) / K, (c / PX - OX) / K]; Z = [-(b / PX - OY) / K, -(d / PX - OY) / K]
    if max(X) < x0 or min(X) > x1 or max(Z) < z0 or min(Z) > z1: continue
    ax.plot(X, Z, color='red', lw=0.4 if w < 1 else 1.0, alpha=0.8)
plane = cq.Face.makePlane(1000, 1000, cq.Vector(0, 0, 0), cq.Vector(0, 1, 0))
for key, name, wp, col in make_korpus_parts():
    sec = wp.val().intersect(cq.Solid.makeBox(2000, 0.001, 2000, cq.Vector(-1000, -0.0005, -1000)))
    for e in sec.Edges():
        pts = [e.positionAt(t) for t in [i / 20 for i in range(21)]]
        if max(abs(p.y) for p in pts) > 0.01: continue
        ax.plot([p.x for p in pts], [p.z for p in pts], color='blue', lw=0.8)
ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.set_aspect('equal'); ax.grid(alpha=0.3)
fig.savefig(out, dpi=110, bbox_inches='tight')
