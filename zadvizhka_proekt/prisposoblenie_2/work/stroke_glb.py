import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build as B
import cadquery as cq
dz = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
a = cq.Assembly(name="stroke")
for p in B.PARTS:
    if p["key"] in ("flanec_17", "stakan_zagotovka"):
        continue
    loc = cq.Location(cq.Vector(0, 0, dz if B.is_moving(p["key"]) else 0))
    a.add(p["fn"](), name=p["key"], color=p["color"], loc=loc)
a.save(os.path.join(B.HERE, "work", "stroke_%d.glb" % dz), tolerance=0.3, angularTolerance=0.6)
