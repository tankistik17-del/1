import pickle, math, numpy as np
items=pickle.load(open('vec6.pkl','rb'))
PX=200/25.4
def chains(x0,y0,x1,y1,minw=0.3,tol=0.6):
    segs=[(p,w) for k,p,w in items if w>=minw and all(x0<=q[0]<=x1 and y0<=q[1]<=y1 for q in p)]
    # build polylines by endpoint matching
    from collections import defaultdict
    used=[False]*len(segs)
    key=lambda q:(round(q[0]/tol),round(q[1]/tol))
    ends=defaultdict(list)
    for i,(p,w) in enumerate(segs):
        ends[key(p[0])].append(i); ends[key(p[1])].append(i)
    out=[]
    for i in range(len(segs)):
        if used[i]: continue
        used[i]=True
        poly=[segs[i][0][0],segs[i][0][1]]; w=segs[i][1]
        for direction in (1,0):
            while True:
                end=poly[-1] if direction else poly[0]
                nxt=None
                for j in ends[key(end)]:
                    if not used[j] and segs[j][1]==w:
                        nxt=j;break
                if nxt is None: break
                used[nxt]=True
                a,b=segs[nxt][0]
                if key(a)==key(end): new=b
                else: new=a
                if direction: poly.append(new)
                else: poly.insert(0,new)
        out.append((poly,w))
    return out
def fitc(pts):
    A=np.array([[x,y,1] for x,y in pts]); b=np.array([-(x*x+y*y) for x,y in pts])
    s=np.linalg.lstsq(A,b,rcond=None)[0]
    cx,cy=-s[0]/2,-s[1]/2; r=math.sqrt(cx*cx+cy*cy-s[2])
    res=max(abs(math.hypot(x-cx,y-cy)-r) for x,y in pts)
    return cx,cy,r,res
def report(x0,y0,x1,y1,ox,oy,minpts=5,minw=0.3):
    for poly,w in chains(x0,y0,x1,y1,minw):
        if len(poly)<minpts: continue
        # detect curved: fit circle
        cx,cy,r,res=fitc(poly)
        L=sum(math.dist(poly[i],poly[i+1]) for i in range(len(poly)-1))
        ang=[math.degrees(math.atan2(-(y-cy),x-cx)) for x,y in (poly[0],poly[-1])]
        print(f'w={w:.2f} n={len(poly)} L={L/PX:.1f}mm  c=({(cx-ox)/PX:.2f},{-(cy-oy)/PX:.2f}) R={r/PX:.2f} res={res/PX:.2f} a={ang[0]:.0f}..{ang[1]:.0f} start=({(poly[0][0]-ox)/PX:.1f},{-(poly[0][1]-oy)/PX:.1f}) end=({(poly[-1][0]-ox)/PX:.1f},{-(poly[-1][1]-oy)/PX:.1f})')

def arcs(x0,y0,x1,y1,ox,oy,minw=0.3,maxseg=6.0,minpts=4,tol=0.6,minR=1.0):
    global items
    allit=items
    items=[(k,p,w) for k,p,w in allit if math.dist(p[0],p[1])/PX<maxseg]
    try:
        ch=chains(x0,y0,x1,y1,minw,tol)
    finally:
        items=allit
    res_list=[]
    for poly,w in ch:
        if len(poly)<minpts: continue
        cx,cy,r,res=fitc(poly)
        if r/PX<minR: continue
        L=sum(math.dist(poly[i],poly[i+1]) for i in range(len(poly)-1))
        a0=math.degrees(math.atan2(-(poly[0][1]-cy),poly[0][0]-cx)); a1=math.degrees(math.atan2(-(poly[-1][1]-cy),poly[-1][0]-cx))
        res_list.append(((cx-ox)/PX,-(cy-oy)/PX,r/PX,res/PX,L/PX,w,a0,a1,len(poly)))
    res_list.sort(key=lambda t:(round(t[0]),round(t[1]),t[2]))
    for cx,cy,r,res,L,w,a0,a1,n in res_list:
        print(f'c=({cx:7.2f},{cy:7.2f}) R={r:6.2f} D={2*r:6.2f} res={res:.2f} L={L:6.1f} w={w:.2f} ang {a0:.0f}->{a1:.0f} n={n}')
