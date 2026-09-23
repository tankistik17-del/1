"""Overlay model planar sections (red) on drawing vector lines (black) of the main view.
Left half: plane Y=0 (X<=0); right half: plane at 22.5 deg (X>=0)."""
import sys, os, glob, math
sys.path.insert(0, os.path.dirname(__file__))
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_UniformDeflection
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
import vec
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parts = {}
for f in sorted(glob.glob(os.path.join(HERE, 'out/parts_step/*.step'))):
    parts[os.path.basename(f)[:-5]] = cq.importers.importStep(f).val()

def section_polys(shape, rot):
    s = shape.rotate(cq.Vector(0,0,0), cq.Vector(0,0,1), -rot) if rot else shape
    sec = BRepAlgoAPI_Section(s.wrapped, gp_Pln(gp_Pnt(0,0,0), gp_Dir(0,1,0)))
    sec.Build()
    out = []
    ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        c = BRepAdaptor_Curve(e)
        d = GCPnts_UniformDeflection(c, 0.02)
        pts = [c.Value(d.Parameter(i)) for i in range(1, d.NbPoints()+1)] if d.IsDone() else []
        out.append([(p.X(), p.Z()) for p in pts])
        ex.Next()
    return out

def clip(pl, keep):
    out=[]; cur=[]
    for p in pl:
        if keep(p[0]): cur.append(p)
        else:
            if len(cur)>1: out.append(cur)
            cur=[]
    if len(cur)>1: out.append(cur)
    return out

def densify(pl, step=0.5):
    o=[]
    for a,b in zip(pl[:-1],pl[1:]):
        n=max(1,int(math.hypot(b[0]-a[0],b[1]-a[1])/step))
        for i in range(n): o.append((a[0]+(b[0]-a[0])*i/n, a[1]+(b[1]-a[1])*i/n))
    o.append(pl[-1]); return o

polys = []
for k, s in parts.items():
    for pl in section_polys(s, 0):
        for c in clip(densify(pl), lambda x: x <= 0.05): polys.append((k, c))
    for pl in section_polys(s, 22.5):
        for c in clip(densify(pl), lambda x: x >= -0.05): polys.append((k, c))

def plot(fname, X0, X1, Z0, Z1, scale=10, grid=5):
    W = X1-X0; H = Z1-Z0
    fig = plt.figure(figsize=(W*scale/100, H*scale/100), dpi=100)
    ax = fig.add_axes([0,0,1,1]); ax.set_xlim(X0,X1); ax.set_ylim(Z0,Z1); ax.set_aspect('equal')
    for g in np.arange(np.ceil(X0/grid)*grid, X1, grid):
        ax.axvline(g, color='#eee', lw=0.4, zorder=0)
        if g % 10 == 0: ax.text(g, Z0+0.3, '%g'%g, color='b', fontsize=6)
    for g in np.arange(np.ceil(Z0/grid)*grid, Z1, grid):
        ax.axhline(g, color='#eee', lw=0.4, zorder=0)
        if g % 10 == 0: ax.text(X0+0.3, g, '%g'%g, color='b', fontsize=6)
    for s in vec.segs:
        if s[4] < 1: continue
        x0,z0 = vec.tomm(s[0],s[1]); x1,z1 = vec.tomm(s[2],s[3])
        if max(x0,x1)<X0 or min(x0,x1)>X1 or max(z0,z1)<Z0 or min(z0,z1)>Z1: continue
        ax.plot([x0,x1],[z0,z1], color='k', lw=1.6, alpha=0.55)
    for k, pl in polys:
        xs=[p[0] for p in pl]; zs=[p[1] for p in pl]
        ax.plot(xs, zs, color='r', lw=0.8)
    fig.savefig(fname); plt.close(fig)

R = os.path.join(HERE, 'renders')
plot(os.path.join(R,'ovl_full.png'), -120, 110, -5, 325, scale=5)
plot(os.path.join(R,'ovl_low.png'), -120, 110, -2, 112, scale=8)
plot(os.path.join(R,'ovl_mid.png'), -70, 70, 95, 215, scale=11)
plot(os.path.join(R,'ovl_head.png'), -70, 70, 240, 325, scale=11)
print('ok', len(polys))
