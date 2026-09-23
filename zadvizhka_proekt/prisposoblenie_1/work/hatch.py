import pickle, math
from collections import defaultdict
items=pickle.load(open('vec6.pkl','rb'))
PX=200/25.4
ox,oy=1930,2545.3
H=[]
for k,p,w in items:
    if abs(w-0.48)>0.01: continue
    (x0,y0),(x1,y1)=[((a-ox)/PX,-(b-oy)/PX) for a,b in p]
    L=math.hypot(x1-x0,y1-y0)
    if L<0.8: continue
    s=(y1-y0)/(x1-x0) if abs(x1-x0)>1e-6 else 99
    if abs(abs(s)-1)<0.03 or abs(abs(s)-1)>0.03:
        H.append((x0,y0,x1,y1,s,L))
def lines_in(xa,xb,ya,yb):
    out=[]
    for x0,y0,x1,y1,s,L in H:
        mx,my=(x0+x1)/2,(y0+y1)/2
        if xa<=mx<=xb and ya<=my<=yb: out.append((x0,y0,x1,y1,s,L))
    return out
