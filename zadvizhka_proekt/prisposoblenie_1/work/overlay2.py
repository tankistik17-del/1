import pickle, math
from PIL import Image, ImageDraw
items=pickle.load(open('/home/user/1/zadvizhka_proekt/prisposoblenie_1/work/vec6.pkl','rb'))
PX=200/25.4
def ov(render,out,view,zoom,region_px,bb=((-168.1,168.1),(-106,140),(0,333.7)),dz=0.0,minw=1.0):
    im=Image.open(render).convert('RGB'); W,H=im.size
    sz=[b[1]-b[0] for b in bb]; c=[(b[0]+b[1])/2 for b in bb]
    L=math.sqrt(sum(v*v for v in sz)); R=L*0.55*zoom; ppm=W/(2*R*(W/H))
    d=ImageDraw.Draw(im)
    x0r,y0r,x1r,y1r=region_px
    for k,p,wd in items:
        if wd<minw: continue
        if not all(x0r<=q[0]<=x1r and y0r<=q[1]<=y1r for q in p): continue
        pts=[]
        for (px,py) in p:
            if view=='top':
                X=(px-1930)/PX; Y=-(py-3723.5)/PX
                pts.append((W/2+(X-c[0])*ppm, H/2-(Y-c[1])*ppm))
            else:  # left: s=-Y
                s=(px-5262)/PX; Z=(2744.7-py)/PX+dz
                pts.append((W/2+(s+c[1])*ppm, H/2-(Z-c[2])*ppm))
        d.line(pts,fill=(255,0,0),width=1)
    im.save(out)
