# -*- coding: utf-8 -*-
"""
GLB (выгрузка CadQuery) -> USDZ для просмотра на iPhone/iPad (Quick Look, AR).

  pip install usd-core trimesh
  python3 tools/glb_to_usdz.py model.glb [model.usdz]

Каждая деталь сборки становится отдельным мешем со своим цветом (UsdPreviewSurface).
Единицы — миллиметры (metersPerUnit = 0.001), поэтому в AR модель встаёт в натуральную величину.
Ось Y вверх, как в glTF и как ожидает AR Quick Look.
"""
import os
import re
import sys

import numpy as np
import trimesh
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, Vt


def ident(name, used):
    s = re.sub(r"[^A-Za-z0-9_]", "_", name or "part")
    if not s or s[0].isdigit():
        s = "p_" + s
    base, i = s, 1
    while s in used:
        i += 1
        s = "%s_%d" % (base, i)
    used.add(s)
    return s


def material_of(geom):
    """(r, g, b, a) в линейном 0..1 из PBR-материала glTF."""
    try:
        m = geom.visual.material
        c = getattr(m, "baseColorFactor", None)
        if c is not None:
            c = np.asarray(c, dtype=float)
            if c.max() > 1.0:
                c = c / 255.0
            return tuple(float(v) for v in c[:4]) if len(c) >= 4 else (*map(float, c[:3]), 1.0)
    except Exception:
        pass
    try:
        c = geom.visual.face_colors[0] / 255.0
        return tuple(float(v) for v in c)
    except Exception:
        return (0.7, 0.7, 0.7, 1.0)


def convert(glb, usdz):
    scene = trimesh.load(glb, force="scene")
    usda = os.path.splitext(usdz)[0] + ".tmp.usdc"
    stage = Usd.Stage.CreateNew(usda)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root = UsdGeom.Xform.Define(stage, "/Model")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Scope.Define(stage, "/Model/Materials")
    mats = {}
    used = set()
    n_tri = 0
    # CadQuery пишет каждую грань отдельным примитивом: собираем их обратно в детали
    # (узел непосредственно под корнем сборки) с разбивкой по цвету.
    parents = scene.graph.transforms.parents
    def part_of(node):
        while parents.get(node) not in (None, "world") and parents.get(parents[node]) not in (None, "world"):
            node = parents[node]
        return node
    groups = {}
    for node in scene.graph.nodes_geometry:
        tf, gname = scene.graph[node]
        geom = scene.geometry[gname]
        if not isinstance(geom, trimesh.Trimesh) or len(geom.faces) == 0:
            continue
        g = geom.copy()
        g.apply_transform(tf)
        rgba = tuple(round(v, 3) for v in material_of(geom))
        groups.setdefault((part_of(node), rgba), []).append(g)
    for (part, rgba), meshes in groups.items():
        g = trimesh.util.concatenate(meshes)
        name = ident(part, used)
        mesh = UsdGeom.Mesh.Define(stage, "/Model/" + name)
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(g.vertices, dtype=np.float32)))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(g.faces), 3, dtype=np.int32)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(g.faces, dtype=np.int32).ravel()))
        mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(g.vertex_normals, dtype=np.float32)))
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDoubleSidedAttr(True)
        lo, hi = g.bounds
        mesh.CreateExtentAttr([Gf.Vec3f(*map(float, lo)), Gf.Vec3f(*map(float, hi))])
        n_tri += len(g.faces)
        if rgba not in mats:
            mpath = "/Model/Materials/m%d" % len(mats)
            mat = UsdShade.Material.Define(stage, mpath)
            sh = UsdShade.Shader.Define(stage, mpath + "/pbr")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgba[:3]))
            sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.2)
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
            if rgba[3] < 0.999:
                sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(rgba[3]))
            mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
            mats[rgba] = mat
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mats[rgba])
    stage.GetRootLayer().Save()
    ok = UsdUtils.CreateNewARKitUsdzPackage(usda, usdz)
    os.remove(usda)
    if not ok:
        raise RuntimeError("не удалось упаковать " + usdz)
    return len(used), n_tri


def check(usdz):
    """Все штатные валидаторы USD (UsdValidation, включая UsdzPackageValidator)."""
    from pxr import UsdValidation
    reg = UsdValidation.ValidationRegistry()
    ctx = UsdValidation.ValidationContext(reg.GetOrLoadAllValidators())
    stage = Usd.Stage.Open(usdz)
    errs = [e for e in ctx.Validate(stage)
            if e.GetType() in (UsdValidation.ValidationErrorType.Error,
                               UsdValidation.ValidationErrorType.Warn)]
    msgs = ["%s: %s" % (e.GetName(), e.GetMessage()) for e in errs]
    info = "defaultPrim=%s, upAxis=%s, metersPerUnit=%s" % (
        stage.GetDefaultPrim().GetName(), UsdGeom.GetStageUpAxis(stage), UsdGeom.GetStageMetersPerUnit(stage))
    return msgs, info


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".usdz"
    n, t = convert(src, dst)
    msgs, info = check(dst)
    print("%s: %d деталей, %d треугольников, %.2f МБ; %s; замечаний валидатора: %d" % (
        dst, n, t, os.path.getsize(dst) / 1e6, info, len(msgs)))
    for m in msgs[:20]:
        print("  ", m)
