import pymupdf, math, sys
doc=pymupdf.open('/root/.claude/uploads/86fac385-3f3e-5e76-a6d4-4fcfb153bd6d/959ac31e-___________.pdf')
p=doc[6]
MM=25.4/72
segs=[]
seen=set()
for it in p.get_drawings():
    w=round(it.get('width') or 0,2)
    for i in it['items']:
        a,b=i[1],i[2]
        k=tuple(sorted([(round(a.x,2),round(a.y,2)),(round(b.x,2),round(b.y,2))]))+(w,)
        if k in seen: continue
        seen.add(k)
        segs.append((a.x,a.y,b.x,b.y,w))
def region(x0,y0,x1,y1,minw=0):
    """pt region"""
    return [s for s in segs if min(s[0],s[2])>=x0 and max(s[0],s[2])<=x1 and min(s[1],s[3])>=y0 and max(s[1],s[3])<=y1 and s[4]>=minw]
CX=704.88; ZB=1069.92
def tomm(x,y,cx=CX,zb=ZB): return ((x-cx)*MM,(zb-y)*MM)
def plot(fname, X0,X1,Z0,Z1, cx=CX, zb=ZB, grid=5, dpi_scale=12, minw=0.4, label_every=10):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    W=(X1-X0); H=(Z1-Z0)
    fig=plt.figure(figsize=(W*dpi_scale/100, H*dpi_scale/100), dpi=100)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(X0,X1); ax.set_ylim(Z0,Z1); ax.set_aspect('equal')
    import numpy as np
    for g in np.arange(np.ceil(X0/grid)*grid, X1, grid):
        ax.axvline(g, color=('#f88' if g%label_every==0 else '#fdd'), lw=0.6 if g%label_every==0 else 0.4, zorder=0)
        if g%label_every==0: ax.text(g, Z0+0.3, '%g'%g, color='r', fontsize=7)
    for g in np.arange(np.ceil(Z0/grid)*grid, Z1, grid):
        ax.axhline(g, color=('#88f' if g%label_every==0 else '#ddf'), lw=0.6 if g%label_every==0 else 0.4, zorder=0)
        if g%label_every==0: ax.text(X0+0.3, g, '%g'%g, color='b', fontsize=7)
    for s in segs:
        x0,z0=tomm(s[0],s[1],cx,zb); x1,z1=tomm(s[2],s[3],cx,zb)
        if max(x0,x1)<X0 or min(x0,x1)>X1 or max(z0,z1)<Z0 or min(z0,z1)>Z1: continue
        if s[4]<minw: col='#aaa'; lw=0.4
        elif s[4]<1: col='#393'; lw=0.6
        else: col='k'; lw=1.3
        ax.plot([x0,x1],[z0,z1],color=col,lw=lw)
    fig.savefig(fname); plt.close(fig)
