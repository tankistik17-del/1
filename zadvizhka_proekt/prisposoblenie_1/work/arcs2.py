import pickle, math, numpy as np, sys
from dump import dump
def fitc(pts):
    A=np.array([[x,y,1] for x,y in pts]); b=np.array([-(x*x+y*y) for x,y in pts])
    s=np.linalg.lstsq(A,b,rcond=None)[0]
    cx,cy=-s[0]/2,-s[1]/2; r=math.sqrt(max(cx*cx+cy*cy-s[2],0))
    res=max(abs(math.hypot(x-cx,y-cy)-r) for x,y in pts)
    return cx,cy,r,res
def polylines(segs,tol=0.05,maxseg=6,maxturn=25):
    # unique
    S=[]; seen=set()
    for q,w in segs:
        a,b=q
        if math.dist(a,b)>maxseg or math.dist(a,b)<1e-3: continue
        k=tuple(sorted([(round(a[0],2),round(a[1],2)),(round(b[0],2),round(b[1],2))]))
        if k in seen: continue
        seen.add(k); S.append((a,b))
    from collections import defaultdict
    key=lambda p:(round(p[0]/tol),round(p[1]/tol))
    ends=defaultdict(list)
    for i,(a,b) in enumerate(S): ends[key(a)].append(i); ends[key(b)].append(i)
    used=[False]*len(S); out=[]
    def ang(p,q): return math.atan2(q[1]-p[1],q[0]-p[0])
    for i in range(len(S)):
        if used[i]: continue
        used[i]=True; poly=[S[i][0],S[i][1]]
        for d in (1,0):
            while True:
                end=poly[-1] if d else poly[0]; prev=poly[-2] if d else poly[1]
                nx=None
                for j in ends[key(end)]:
                    if used[j]: continue
                    a,b=S[j]; new=b if key(a)==key(end) else a
                    t=math.degrees(abs((ang(prev,end)-ang(end,new)+math.pi)%(2*math.pi)-math.pi))
                    if t<maxturn: nx=(j,new);break
                if nx is None: break
                used[nx[0]]=True
                if d: poly.append(nx[1])
                else: poly.insert(0,nx[1])
        out.append(poly)
    return out
def report(xa,xb,ya,yb,minpts=4,minw=1.0,ox=1930,oy=2545.3,maxseg=6):
    segs=dump(xa,xb,ya,yb,ox=ox,oy=oy,minw=minw)
    for poly in polylines(segs,maxseg=maxseg):
        if len(poly)<minpts: continue
        cx,cy,r,res=fitc(poly)
        print(f'n={len(poly):3d} c=({cx:8.2f},{cy:8.2f}) R={r:7.2f} res={res:.2f}  ({poly[0][0]:.1f},{poly[0][1]:.1f})->({poly[-1][0]:.1f},{poly[-1][1]:.1f})')
if __name__=='__main__':
    a=[float(v) for v in sys.argv[1:5]]
    kw={}
    if len(sys.argv)>5: kw['minw']=float(sys.argv[5])
    if len(sys.argv)>7: kw['ox']=float(sys.argv[6]); kw['oy']=float(sys.argv[7])
    report(*a,**kw)
