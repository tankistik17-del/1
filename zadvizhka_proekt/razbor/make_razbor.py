# -*- coding: utf-8 -*-
"""
Страница «Как работают сварочные приспособления» (листы 6 и 7): пошаговые 3D-анимации и разбор.

  python3 make_razbor.py [папка для офлайн-файла]

Пишет:
  razbor/index.html + razbor/models/*.js         — веб-версия (three.js с CDN, модели рядом)
  <папка>/Приспособления - разбор.html           — один самодостаточный файл (без интернета)
Модели и спецификации берутся из ../prisposoblenie_1 и ../prisposoblenie_2 (out/*.glb, out/spec.json).
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

MODELS = {
    "prisposoblenie_1": ("prisposoblenie_1", "prisposoblenie_svarochnoe_1"),
    "prisposoblenie_2": ("prisposoblenie_2", "prisposoblenie_svarochnoe_2"),
}


def model_js(key, glb):
    b64 = base64.b64encode(open(glb, "rb").read()).decode()
    return "(window.ZADV_MODELS=window.ZADV_MODELS||{})[%s]=\"%s\";\n" % (json.dumps(key), b64)


def main():
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    data = {"models": {}, "spec1": [], "spec2": []}
    scripts = []
    for i, (key, (d, fname)) in enumerate(MODELS.items(), 1):
        out = os.path.join(PROJ, d, "out")
        js = model_js(key, os.path.join(out, fname + ".glb"))
        with open(os.path.join(HERE, "models", key + ".js"), "w") as f:
            f.write(js)
        scripts.append(js)
        data["models"][key] = "models/%s.js" % key
        data["spec%d" % i] = json.load(open(os.path.join(out, "spec.json"), encoding="utf-8"))
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    assert "/*__DATA__*/{}" in tpl
    page = tpl.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("index.html", len(page) // 1024, "KB")
    if len(sys.argv) > 1:
        os.makedirs(sys.argv[1], exist_ok=True)
        dst = os.path.join(sys.argv[1], "Приспособления - разбор.html")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(inline_page(page, scripts))
        print(dst, "%.1f МБ" % (os.path.getsize(dst) / 1e6))


if __name__ == "__main__":
    main()
