import pickle, math, sys
items=pickle.load(open('/home/user/1/zadvizhka_proekt/prisposoblenie_1/work/vec6.pkl','rb'))
PX=200/25.4
def dump(xa,xb,ya,yb,ox=1930,oy=2545.3,minw=1.0,maxw=9,any_inside=False):
    out=[]
    for k,p,w in items:
        if w<minw or w>maxw: continue
        q=[((x-ox)/PX,-(y-oy)/PX) for x,y in p]
        ins=[xa<=a<=xb and ya<=b<=yb for a,b in q]
        if (any(ins) if any_inside else all(ins)):
            out.append((q,w))
    return out
if __name__=='__main__':
    a=[float(v) for v in sys.argv[1:5]]
    kw={}
    if len(sys.argv)>5: kw['minw']=float(sys.argv[5])
    for q,w in dump(*a,**kw):
        L=math.dist(q[0],q[1])
        print(f'({q[0][0]:8.2f},{q[0][1]:8.2f}) -> ({q[1][0]:8.2f},{q[1][1]:8.2f})  L={L:6.2f} w={w:.2f}')
