# -*- coding: utf-8 -*-
"""
Собирает общий просмотрщик 3D-моделей проекта «Задвижка трубопровода».

  python3 make_viewer.py            -> viewer/index.html + viewer/models/*.js + viewer/sheets/*.jpg
  (открывать через локальный сервер:  python3 -m http.server  в папке zadvizhka_proekt, затем /viewer/)

Модели берутся из <модель>/out/*.glb и <модель>/out/spec.json. GLB кладётся в models/<key>.js
в base64 и подключается тегом <script>: так модель грузится и там, где запрещён fetch.
"""
import base64
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PDF = os.environ.get("ZADV_PDF", "")

MODELS = [
    # key, dir, sheet, title, subtitle, default section axis
    ("zadvizhka", "zadvizhka", 1, "Задвижка трубопровода", "Сборочный чертёж, М 1:1", "y"),
    ("korpus", "korpus", 2, "Корпус", "Сварная сборочная единица, М 1:1", "y"),
    ("prisposoblenie_1", "prisposoblenie_1", 6, "Приспособление сварочное №1", "Пневматическое, М 1:1", "y"),
    ("prisposoblenie_2", "prisposoblenie_2", 7, "Приспособление сварочное №2", "Пневматическое, М 1:1", "y"),
    ("oborudovanie", "oborudovanie", 8, "Сварочное оборудование", "Общий вид, М 1:5", "none"),
    ("planirovka", "planirovka", 9, "Планировка участка", "Участок сборки-сварки, М 1:50", "none"),
]


def main():
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "sheets"), exist_ok=True)
    cfg = []
    for key, d, sheet, title, sub, sec in MODELS:
        glbs = sorted(glob.glob(os.path.join(ROOT, d, "out", "*.glb")))
        if not glbs:
            print("нет GLB для", key, file=sys.stderr)
            continue
        glb = max(glbs, key=os.path.getsize)
        b64 = base64.b64encode(open(glb, "rb").read()).decode()
        with open(os.path.join(HERE, "models", key + ".js"), "w") as f:
            f.write("(window.ZADV_MODELS=window.ZADV_MODELS||{})[%s]=\"%s\";\n" % (json.dumps(key), b64))
        spec = []
        sp = os.path.join(ROOT, d, "out", "spec.json")
        if os.path.exists(sp):
            spec = json.load(open(sp, encoding="utf-8"))
        sheet_img = "sheets/sheet%d.jpg" % sheet
        if PDF and not os.path.exists(os.path.join(HERE, sheet_img)):
            import pymupdf
            doc = pymupdf.open(PDF)
            pix = doc[sheet - 1].get_pixmap(dpi=110)
            pix.save(os.path.join(HERE, sheet_img), jpg_quality=82)
        cfg.append(dict(key=key, sheet=sheet, title=title, sub=sub, section=sec,
                        model="models/%s.js" % key, sheetImg=sheet_img, spec=spec))
        print("ok", key, os.path.getsize(os.path.join(HERE, "models", key + ".js")) // 1024, "KB")
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = tpl.replace("/*__CONFIG__*/[]", json.dumps(cfg, ensure_ascii=False))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
