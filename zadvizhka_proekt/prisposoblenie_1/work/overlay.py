import pickle, math, sys
from PIL import Image, ImageDraw
items=pickle.load(open('/home/user/1/zadvizhka_proekt/prisposoblenie_1/work/vec6.pkl','rb'))
PX=200/25.4
def overlay(render, out, ox, oy, cx, cz, ppm, dz, sgn_x=1, crop=None, region=None, w=(1.6,)):
    im=Image.open(render).convert('RGB'); W,H=im.size
    d=ImageDraw.Draw(im)
    for k,p,wd in items:
        if wd<1.0: continue
        (x0,y0),(x1,y1)=p
        X0=(x0-ox)/PX*sgn_x; Z0=-(y0-oy)/PX+dz; X1=(x1-ox)/PX*sgn_x; Z1=-(y1-oy)/PX+dz
        if region and not (region[0]<=X0<=region[1] and region[2]<=Z0<=region[3]): continue
        d.line([(W/2+(X0-cx)*ppm, H/2-(Z0-cz)*ppm),(W/2+(X1-cx)*ppm, H/2-(Z1-cz)*ppm)],fill=(255,0,0),width=1)
    if crop: im=im.crop(crop)
    im.save(out)
if __name__=='__main__':
    pass
