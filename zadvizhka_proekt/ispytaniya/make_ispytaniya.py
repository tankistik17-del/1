# -*- coding: utf-8 -*-
"""
Страница «Контроль и испытания корпуса»: ВИК и гидроиспытание в 3D, дефекты швов, проверочный расчёт.

  python3 make_ispytaniya.py [папка]  # ispytaniya/index.html (+ самодостаточный файл в папке)

Траектории и длины швов — из ../process/out/economics.json (расчёт process/calc.py).

3D-плеер и вспомогательные функции берутся из ../razbor/template.html (общий код, без копий).
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REPO = os.path.dirname(PROJ)
sys.path.insert(0, os.path.join(REPO, "tools"))
from offline_html import inline_page  # noqa: E402


def between(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def main():
    rz = open(os.path.join(PROJ, "razbor", "template.html"), encoding="utf-8").read()
    helpers = between(rz, "const DATA = /*__DATA__*/{};", "// ---- spec tables ----")
    core = between(rz, "// ---- generic fixture scene ----", "// ================= Fixture 1 =================")
    econ = json.load(open(os.path.join(PROJ, "process", "out", "economics.json"), encoding="utf-8"))
    glb = os.path.join(PROJ, "korpus", "out", "korpus.glb")
    js = "(window.ZADV_MODELS=window.ZADV_MODELS||{})[\"korpus\"]=\"%s\";\n" % base64.b64encode(open(glb, "rb").read()).decode()
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    with open(os.path.join(HERE, "models", "korpus.js"), "w") as f:
        f.write(js)
    data = {"models": {"korpus": "models/korpus.js"}, "welds": econ["welds"]}
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    page = tpl.replace("/*__HELPERS__*/", helpers).replace("/*__FIXTURE_CORE__*/", core)
    page = page.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("index.html", len(page) // 1024, "KB")
    if len(sys.argv) > 1:
        os.makedirs(sys.argv[1], exist_ok=True)
        dst = os.path.join(sys.argv[1], "Контроль и испытания корпуса.html")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(inline_page(page, [js]))
        print(dst, "%.1f МБ" % (os.path.getsize(dst) / 1e6))


if __name__ == "__main__":
    main()
