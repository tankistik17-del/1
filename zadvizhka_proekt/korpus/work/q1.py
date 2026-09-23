import json, sys, math
segs=json.load(open('/home/user/1/zadvizhka_proekt/korpus/work/segs1.json'))
PX=0.36  # pt per 200dpi px
MM=25.4/72
def box(x0,y0,x1,y1,wmin=0,kind=None):
    # box in 200dpi px
    out=[]
    for s in segs:
        if s[0]!='l': continue
        _,a,b,c,d,w=s
        if w<wmin: continue
        ax,ay,cx,cy=a/PX,b/PX,c/PX,d/PX
        if min(ax,cx)>=x0 and max(ax,cx)<=x1 and min(ay,cy)>=y0 and max(ay,cy)<=y1:
            out.append((ax,ay,cx,cy,w))
    return out
if __name__=='__main__':
    x0,y0,x1,y1=map(float,sys.argv[1:5]); wmin=float(sys.argv[5]) if len(sys.argv)>5 else 1.0
    L=box(x0,y0,x1,y1,wmin)
    # merge: print long ones
    L=[l for l in L if math.hypot(l[2]-l[0],l[3]-l[1])>float(sys.argv[6] if len(sys.argv)>6 else 15)]
    L.sort(key=lambda l:(round(l[0]),round(l[1])))
    for l in L:
        print('%8.1f %8.1f -> %8.1f %8.1f  len=%6.1fpx w=%.2f'%(l[0],l[1],l[2],l[3],math.hypot(l[2]-l[0],l[3]-l[1]),l[4]))
