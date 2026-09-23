import sys, math
from dump import dump
def uniq(xa,xb,ya,yb,ox=1930,oy=2545.3,minw=1.0,any_inside=False,merge=True):
    S=set()
    for q,w in dump(xa,xb,ya,yb,ox=ox,oy=oy,minw=minw,any_inside=any_inside):
        a,b=q
        a=(round(a[0],2),round(a[1],2)); b=(round(b[0],2),round(b[1],2))
        S.add(tuple(sorted([a,b])))
    S=sorted(S)
    if merge:
        # merge collinear H and V segments
        H={};V={};O=[]
        for a,b in S:
            if abs(a[1]-b[1])<0.05: H.setdefault(round(a[1],1),[]).append((min(a[0],b[0]),max(a[0],b[0])))
            elif abs(a[0]-b[0])<0.05: V.setdefault(round(a[0],1),[]).append((min(a[1],b[1]),max(a[1],b[1])))
            else: O.append((a,b))
        def mg(d):
            out=[]
            for k,iv in d.items():
                iv.sort(); cur=list(iv[0])
                for s,e in iv[1:]:
                    if s<=cur[1]+0.1: cur[1]=max(cur[1],e)
                    else: out.append((k,cur[0],cur[1])); cur=[s,e]
                out.append((k,cur[0],cur[1]))
            return sorted(out)
        return mg(H),mg(V),O
    return S
if __name__=='__main__':
    a=[float(v) for v in sys.argv[1:5]]
    kw={}
    if len(sys.argv)>6: kw['ox']=float(sys.argv[5]); kw['oy']=float(sys.argv[6])
    H,V,O=uniq(*a,any_inside=True,**kw)
    print('H (z: x0..x1):'); [print(f'  z={k:7.2f}  x {s:8.2f} .. {e:8.2f}  L={e-s:.2f}') for k,s,e in H if e-s>0.3]
    print('V (x: z0..z1):'); [print(f'  x={k:7.2f}  z {s:8.2f} .. {e:8.2f}  L={e-s:.2f}') for k,s,e in V if e-s>0.3]
    print('Other:'); [print(f'  ({a[0]:.2f},{a[1]:.2f})-({b[0]:.2f},{b[1]:.2f}) L={math.dist(a,b):.2f}') for a,b in O if math.dist(a,b)>1.5]
