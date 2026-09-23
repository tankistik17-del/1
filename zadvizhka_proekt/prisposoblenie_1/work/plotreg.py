import pickle, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
items=pickle.load(open('vec6.pkl','rb'))
PX=200/25.4  # px per mm at 1:1
def plot(name,x0,y0,x1,y1,ox,oy,grid=5,minw=0.0,dpi=100,figw=18):
    """region in px; origin (ox,oy) px -> mm coords, y up"""
    fig,ax=plt.subplots(figsize=(figw,figw*(y1-y0)/(x1-x0)))
    for k,pts,w in items:
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        if max(xs)<x0 or min(xs)>x1 or max(ys)<y0 or min(ys)>y1: continue
        if w<minw: continue
        c={1.68:'k',0.48:'b',0.26:'0.6'}.get(round(w,2),'r')
        lw={1.68:1.2,0.48:0.6,0.26:0.3}.get(round(w,2),0.5)
        ax.plot([(x-ox)/PX for x in xs],[-(y-oy)/PX for y in ys],c,lw=lw)
    ax.set_xlim((x0-ox)/PX,(x1-ox)/PX); ax.set_ylim(-(y1-oy)/PX,-(y0-oy)/PX)
    ax.set_aspect('equal')
    import numpy as np
    ax.set_xticks(np.arange(np.floor((x0-ox)/PX/grid)*grid,(x1-ox)/PX,grid))
    ax.set_yticks(np.arange(np.floor(-(y1-oy)/PX/grid)*grid,-(y0-oy)/PX,grid))
    ax.grid(True,lw=0.3,color='g',alpha=0.5)
    ax.tick_params(labelsize=6)
    plt.xticks(rotation=90)
    plt.tight_layout(); plt.savefig(name,dpi=dpi); plt.close()
if __name__=='__main__':
    a=sys.argv
    plot(a[1],*[float(v) for v in a[2:8]],grid=float(a[8]) if len(a)>8 else 5, minw=float(a[9]) if len(a)>9 else 0)
