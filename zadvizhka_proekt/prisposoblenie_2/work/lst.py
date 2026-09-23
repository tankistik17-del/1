from vec import *
import sys
def lst(X0,X1,Z0,Z1,cx=CX,zb=ZB,minw=1.0,maxw=9):
    out=[]
    for s in segs:
        if s[4]<minw or s[4]>maxw: continue
        x0,z0=tomm(s[0],s[1],cx,zb); x1,z1=tomm(s[2],s[3],cx,zb)
        if min(x0,x1)>=X0 and max(x0,x1)<=X1 and min(z0,z1)>=Z0 and max(z0,z1)<=Z1:
            if (x0,z0)>(x1,z1): x0,z0,x1,z1=x1,z1,x0,z0
            out.append((round(x0,2),round(z0,2),round(x1,2),round(z1,2)))
    out=sorted(set(out))
    # classify
    H=[o for o in out if abs(o[1]-o[3])<0.05]; V=[o for o in out if abs(o[0]-o[2])<0.05]; O=[o for o in out if o not in H and o not in V]
    print('H:'); [print('  z=%.2f x %.2f..%.2f'%(o[1],o[0],o[2])) for o in sorted(H,key=lambda o:(o[1],o[0]))]
    print('V:'); [print('  x=%.2f z %.2f..%.2f'%(o[0],min(o[1],o[3]),max(o[1],o[3]))) for o in sorted(V)]
    print('O:'); [print('  ',o) for o in O]
if __name__=='__main__':
    a=[float(v) for v in sys.argv[1:5]]
    kw={}
    if len(sys.argv)>5: kw['cx']=float(sys.argv[5])
    if len(sys.argv)>6: kw['zb']=float(sys.argv[6])
    lst(*a,**kw)
