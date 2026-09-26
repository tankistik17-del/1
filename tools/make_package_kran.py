# -*- coding: utf-8 -*-
"""
Папка «для флешки» с моделью шарового крана DN 50 PN 40 (рисунок 1.1 ВКР).
Открывается на Windows без установки программ и без интернета.

  python3 tools/make_package_kran.py <папка назначения>
"""
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRAN = os.path.join(REPO, "crane_dn50_pn40")
OFFLINE = os.path.join(REPO, "zadvizhka_proekt", "viewer", "offline")


def main():
    dst = sys.argv[1]
    if os.path.exists(dst):
        shutil.rmtree(dst)
    data = os.path.join(dst, "data")
    os.makedirs(os.path.join(dst, "Kartinki"))
    shutil.copytree(os.path.join(OFFLINE, "lib"), os.path.join(data, "lib"))
    shutil.copytree(os.path.join(OFFLINE, "fonts"), os.path.join(data, "fonts"))

    page = open(os.path.join(KRAN, "viewer", "index.html"), encoding="utf-8").read()
    page = page.replace('<link rel="preconnect" href="https://fonts.googleapis.com">\n', "")
    page = page.replace('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Sans:wght@400;700&family=PT+Mono&display=swap">',
                        '<link rel="stylesheet" href="data/fonts/fonts.css">')
    page = page.replace("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "data/lib/three.min.js")
    page = page.replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js", "data/lib/GLTFLoader.js")
    page = page.replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", "data/lib/OrbitControls.js")
    assert "https://cdn" not in page and "googleapis" not in page
    with open(os.path.join(dst, "START_3D_prosmotr.html"), "w", encoding="utf-8") as f:
        f.write(page)

    out = os.path.join(KRAN, "out")
    shutil.copy(os.path.join(out, "kran_DN50_PN40_sborka.step"), os.path.join(dst, "Kran_DN50_PN40_sborka.step"))
    shutil.copy(os.path.join(out, "kran_DN50_PN40_sborka.glb"), os.path.join(dst, "Kran_DN50_PN40_sborka.glb"))
    os.makedirs(os.path.join(dst, "STEP_detali"))
    for fn in sorted(os.listdir(os.path.join(out, "parts_step"))):
        shutil.copy(os.path.join(out, "parts_step", fn), os.path.join(dst, "STEP_detali", fn))

    glb = os.path.join(out, "kran_DN50_PN40_sborka.glb")

    def render(prefix, views, *extra):
        subprocess.run([sys.executable, os.path.join(REPO, "tools", "render_views.py"), glb,
                        os.path.join(dst, "Kartinki", prefix), "--views", views,
                        "--size", "2600", "--zoom", "0.95", "--clean", *extra], check=True, capture_output=True)
    render("kran", "iso,front,top,left")
    render("kran_razrez", "iso,front", "--section", "y")

    txt = """Кран шаровой DN 50 PN 40 — 3D-модель по рисунку 1.1 ВКР
=========================================================

Всё открывается на Windows без установки программ и без интернета.

1. START_3D_prosmotr.html — двойной щелчок: откроется браузер (Edge или Chrome) с 3D-моделью.
   Мышь: левая кнопка — вращать, колесо — масштаб, правая — сдвиг.
   Есть разрез по оси (как на рисунке 1.1), разнесённый вид, положения «открыт/закрыт»
   и спецификация 14 позиций с подсветкой деталей. Копируйте вместе с папкой data.

2. Kartinki — виды и разрезы модели в PNG (открываются стандартным просмотром фото).

3. Kran_DN50_PN40_sborka.step — сборка для КОМПАС-3D, SolidWorks, Inventor, FreeCAD;
   STEP_detali — каждая деталь отдельным файлом.

4. Kran_DN50_PN40_sborka.glb — открывается «Средством 3D-просмотра» Windows (3D Viewer).

Основные размеры: строительная длина 180 мм, высота до верха рукоятки 109 мм от оси,
вылет рукоятки 330 мм; фланцы DN 50 PN 40 по ГОСТ 33259-2015 (исп. B), патрубки 57×4.
"""
    with open(os.path.join(dst, "PROCHITAJ.txt"), "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(txt)

    zp = dst.rstrip("/") + ".zip"
    if os.path.exists(zp):
        os.remove(zp)
    base = os.path.basename(dst.rstrip("/"))
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(dst):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                z.write(full, os.path.join(base, os.path.relpath(full, dst)))
    print("zip:", zp, "%.1f МБ" % (os.path.getsize(zp) / 1e6))


if __name__ == "__main__":
    main()
