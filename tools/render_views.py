#!/usr/bin/env python3
"""
Render orthographic engineering views of a GLB (exported by CadQuery, Z-up CAD frame)
to PNG images using headless Chromium + three.js (software GL).

Usage:
  python3 render_views.py model.glb out_prefix [--views front,top,left,iso]
                          [--section y] [--section-offset 0] [--size 1100]
                          [--hide name1,name2] [--only name1,name2] [--clean]

Нужны playwright и Chromium; three.js берётся из zadvizhka_proekt/viewer/offline/lib.

Views (CAD frame, Z up):
  front : camera on -Y looking +Y   (shows XZ plane; X to the right, Z up)
  back  : camera on +Y looking -Y
  top   : camera on +Z looking down (X right, Y up)
  bottom: camera on -Z
  left  : camera on -X looking +X   (shows YZ; -Y to the right... see label)
  right : camera on +X looking -X
  iso   : isometric-ish from (-1,-1.3,0.9)

--section AX : cut the model with plane AX = offset, removing the half nearer to the
  camera of the 'front'-like view (for y: removes y<offset so you look at the cut face
  from -Y). Cut solids show a dark-grey filled cut face (back-face trick), like hatching.
  Allowed: x, y, z.

Each output image has a caption with the view name and the overall model bounding box in mm,
plus a 10/50/100 mm scale bar, so dimensions can be compared with the drawing.
Writes <out_prefix>_<view>.png for each view and prints the bounding box.
"""
import argparse
import base64
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "..", "zadvizhka_proekt", "viewer", "offline", "lib")

PAGE = r"""
<html><head><meta charset="utf-8"><style>
body{margin:0;background:#fff;font-family:Arial,sans-serif}
#cap{position:absolute;left:8px;top:6px;font-size:15px;color:#111;background:rgba(255,255,255,.85);padding:2px 6px}
#bar{position:absolute;left:10px;bottom:10px;font-size:13px;color:#111}
#bar div{height:6px;background:#111;margin-bottom:3px}
</style></head><body><div id="cap"></div><div id="bar"></div>
<script src="three.min.js"></script><script src="GLTFLoader.js"></script>
<script>
window.renderAll = async function(b64, opts){
  const S = opts.size;
  const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
  renderer.setSize(S, Math.round(S*opts.aspect)); renderer.localClippingEnabled = true;
  document.body.appendChild(renderer.domElement);
  const buf = Uint8Array.from(atob(b64), c=>c.charCodeAt(0)).buffer;
  const gltf = await new Promise((res,rej)=>new THREE.GLTFLoader().parse(buf,'',res,rej));
  const root = gltf.scene;
  // undo glTF Y-up rotation: CAD frame (Z up) becomes world frame
  root.traverse(o=>{ if(o.parent===root || o===root){} });
  root.children.forEach(c=>{ c.quaternion.identity(); });
  root.quaternion.identity();
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0xffffff);
  scene.add(root); root.updateMatrixWorld(true);
  const hide = new Set(opts.hide||[]), only = new Set(opts.only||[]);
  root.traverse(o=>{
    if(!o.name) return;
    if(hide.has(o.name)) o.visible=false;
  });
  if(only.size){ root.traverse(o=>{ if(o.parent===root.children[0] || (o.parent===root && root.children.length>1)){ o.visible = only.has(o.name); } }); }
  let clip = null;
  if(opts.section){
    const n = {x:[1,0,0], y:[0,1,0], z:[0,0,-1]}[opts.section];
    const sign = opts.section==='z' ? -1 : 1;
    clip = new THREE.Plane(new THREE.Vector3(...n), -sign*opts.offset);
  }
  const meshes=[]; root.traverse(o=>{ if(o.isMesh) meshes.push(o); });
  meshes.forEach(m=>{
    const base = m.material.color ? m.material.color.clone() : new THREE.Color(0x999999);
    m.material = new THREE.MeshLambertMaterial({color: base, side: THREE.FrontSide,
      clippingPlanes: clip?[clip]:[], polygonOffset:true, polygonOffsetFactor:1, polygonOffsetUnits:1});
    if(clip){
      const cut = opts.partCut ? base.clone().lerp(new THREE.Color(0xffffff), 0.35) : new THREE.Color(0xd08a4a);
      const back = new THREE.Mesh(m.geometry, new THREE.MeshBasicMaterial({color: cut, side: THREE.BackSide, clippingPlanes:[clip]}));
      m.add(back);
    }
    const eg = new THREE.EdgesGeometry(m.geometry, 28);
    const ln = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0x111111, clippingPlanes: clip?[clip]:[]}));
    m.add(ln);
  });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x9a9a9a, 0.95));
  const dl = new THREE.DirectionalLight(0xffffff, 0.55); dl.position.set(-1,-2,3); scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xffffff, 0.25); dl2.position.set(2,1,-1); scene.add(dl2);
  const box = new THREE.Box3();
  root.traverse(o=>{ if(o.isMesh && o.visible){ let v=true,p=o; while(p){ if(!p.visible) v=false; p=p.parent;} if(v) box.expandByObject(o);} });
  const c = box.getCenter(new THREE.Vector3()), sz = box.getSize(new THREE.Vector3());
  const dirs = {front:[0,-1,0], back:[0,1,0], top:[0,0,1], bottom:[0,0,-1], left:[-1,0,0], right:[1,0,0], iso:[-1,-1.3,0.9], iso2:[1,-1.3,0.9]};
  const out = {};
  for(const v of opts.views){
    const d = new THREE.Vector3(...dirs[v]).normalize();
    const R = sz.length()*0.55 * opts.zoom;
    const aspect = 1/opts.aspect;
    const cam = new THREE.OrthographicCamera(-R*aspect, R*aspect, R, -R, 0.1, 1e6);
    cam.up.set(0,0,1); if(v==='top'||v==='bottom') cam.up.set(0,1,0);
    cam.position.copy(c).addScaledVector(d, sz.length()*3); cam.lookAt(c); cam.updateProjectionMatrix();
    renderer.render(scene, cam);
    // scale bar: pixels per mm
    const pxPerMm = (S)/(2*R*aspect);
    let L = 10; for(const cand of [10,20,50,100,200,500,1000,2000,5000,10000]){ if(cand*pxPerMm < S*0.25) L=cand; }
    out[v] = {png: renderer.domElement.toDataURL('image/png'), pxPerMm, bar:L};
  }
  return {bbox:{xmin:box.min.x,xmax:box.max.x,ymin:box.min.y,ymax:box.max.y,zmin:box.min.z,zmax:box.max.z}, views: out};
};
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("out_prefix")
    ap.add_argument("--views", default="front,top,left,iso")
    ap.add_argument("--section", choices=["x", "y", "z"])
    ap.add_argument("--section-offset", type=float, default=0.0)
    ap.add_argument("--size", type=int, default=1100)
    ap.add_argument("--aspect", type=float, default=0.75, help="height/width")
    ap.add_argument("--zoom", type=float, default=1.0, help="<1 zooms in")
    ap.add_argument("--hide", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--clean", action="store_true", help="без подписи и масштабной линейки, поля обрезаны")
    a = ap.parse_args()
    b64 = base64.b64encode(open(a.glb, "rb").read()).decode()
    opts = dict(size=a.size, aspect=a.aspect, zoom=a.zoom, views=a.views.split(","),
                section=a.section, offset=a.section_offset,
                hide=[h for h in a.hide.split(",") if h], only=[h for h in a.only.split(",") if h],
                partCut=a.clean)
    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None,
                              args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": a.size, "height": int(a.size * a.aspect)})

        def rt(route):
            u = route.request.url
            for f in ("three.min.js", "GLTFLoader.js"):
                if u.endswith(f):
                    return route.fulfill(path=os.path.join(VENDOR, f), content_type="application/javascript")
            if u.startswith("http://render.local/"):
                return route.fulfill(body=PAGE, content_type="text/html")
            return route.abort()
        pg.route("**/*", rt)
        pg.goto("http://render.local/index.html")
        res = pg.evaluate("([b,o]) => window.renderAll(b,o)", [b64, opts])
        bb = res["bbox"]
        dims = "X %.1f..%.1f (%.1f)  Y %.1f..%.1f (%.1f)  Z %.1f..%.1f (%.1f) mm" % (
            bb["xmin"], bb["xmax"], bb["xmax"] - bb["xmin"], bb["ymin"], bb["ymax"], bb["ymax"] - bb["ymin"],
            bb["zmin"], bb["zmax"], bb["zmax"] - bb["zmin"])
        print("bbox:", dims)
        for v, d in res["views"].items():
            if a.clean:
                import io
                from PIL import Image, ImageChops
                im = Image.open(io.BytesIO(base64.b64decode(d["png"].split(",", 1)[1]))).convert("RGB")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                box = ImageChops.difference(im, bg).getbbox()
                if box:
                    m = 12
                    im = im.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height)))
                fn = "%s_%s.png" % (a.out_prefix, v)
                im.save(fn)
                print("wrote", fn)
                continue
            cap = "%s%s | %s" % (v, (" | section %s=%g" % (a.section, a.section_offset)) if a.section else "", dims)
            pg.evaluate("""([png,cap,bar,ppm]) => {
                document.querySelector('canvas').remove();
                let img=document.getElementById('im'); if(!img){img=document.createElement('img');img.id='im';document.body.prepend(img);}
                img.src=png; document.getElementById('cap').textContent=cap;
                document.getElementById('bar').innerHTML='<div style="width:'+(bar*ppm)+'px"></div>'+bar+' mm';
            }""", [d["png"], cap, d["bar"], d["pxPerMm"]])
            pg.wait_for_timeout(100)
            fn = "%s_%s.png" % (a.out_prefix, v)
            pg.screenshot(path=fn)
            print("wrote", fn)
            pg.evaluate("() => { const c=document.createElement('canvas'); document.body.appendChild(c); }")
        b.close()


if __name__ == "__main__":
    main()
