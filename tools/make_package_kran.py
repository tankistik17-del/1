# -*- coding: utf-8 -*-
"""
Файлы «для флешки» с моделью шарового крана DN 50 PN 40 (рисунок 1.1 ВКР).
Каждый файл самостоятельный, открывается на Windows без установки программ и без интернета.

  python3 tools/make_package_kran.py <папка назначения>

  Кран DN50 - 3D просмотр.html — модель, библиотеки и шрифты внутри одного файла
  Кран DN50 - сборка.step      — для КОМПАС-3D, SolidWorks, Inventor, FreeCAD
  Кран DN50 - сборка.glb       — для «Средства 3D-просмотра» Windows
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRAN = os.path.join(REPO, "crane_dn50_pn40")
sys.path.insert(0, os.path.join(REPO, "tools"))
from offline_html import inline_page  # noqa: E402


def main():
    dst = sys.argv[1]
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    page = open(os.path.join(KRAN, "viewer", "index.html"), encoding="utf-8").read()
    with open(os.path.join(dst, "Кран DN50 - 3D просмотр.html"), "w", encoding="utf-8") as f:
        f.write(inline_page(page))
    out = os.path.join(KRAN, "out")
    shutil.copy(os.path.join(out, "kran_DN50_PN40_sborka.step"), os.path.join(dst, "Кран DN50 - сборка.step"))
    shutil.copy(os.path.join(out, "kran_DN50_PN40_sborka.glb"), os.path.join(dst, "Кран DN50 - сборка.glb"))
    for fn in sorted(os.listdir(dst)):
        print("%8.1f МБ  %s" % (os.path.getsize(os.path.join(dst, fn)) / 1e6, fn))


if __name__ == "__main__":
    main()
