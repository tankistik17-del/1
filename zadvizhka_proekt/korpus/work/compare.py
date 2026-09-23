"""Overlay drawing (red) on an orthographic render at the same scale.
usage: compare.py render.png sheet.png out.png view  [zoom] [size]
view: front (XZ; drawing origin = sheet2 main view axis) or top (XY; plan view)"""
import sys, math
from PIL import Image, ImageOps
import numpy as np
rpng, spng, out, view = sys.argv[1:5]
zoom = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
size = int(sys.argv[6]) if len(sys.argv) > 6 else 1100
aspect = 0.75
bb = dict(x=(-112, 112), y=(-105, 105), z=(-105, 155))
sz = [bb[a][1] - bb[a][0] for a in 'xyz']
R = math.sqrt(sum(s * s for s in sz)) * 0.55 * zoom
ppm = size / (2 * R / aspect)
K = 8.05
if view == 'front':
    O = (1710.0, 1447.3); cu, cv = 0.0, sum(bb['z']) / 2   # model center (x, z)
else:
    O = (1710.0, 3640.7); cu, cv = 0.0, sum(bb['y']) / 2
ren = Image.open(rpng).convert('RGB')
W, H = ren.size
sh = Image.open(spng).convert('L')
# drawing px of model point (u,v): (O[0]+u*K, O[1]-v*K); render px: (W/2+(u-cu)*ppm, H/2-(v-cv)*ppm)
s = ppm / K
# crop drawing region corresponding to full render
u0 = cu - (W / 2) / ppm; v1 = cv + (H / 2) / ppm
x0 = O[0] + u0 * K; y0 = O[1] - v1 * K
crop = sh.crop((int(x0), int(y0), int(x0 + W / s), int(y0 + H / s))).resize((W, H), Image.LANCZOS)
a = np.array(ren).astype(float)
d = np.array(crop).astype(float) / 255.0
mask = d < 0.6
a[mask] = [230, 0, 0]
Image.fromarray(a.astype(np.uint8)).save(out)
print('ppm', ppm)
