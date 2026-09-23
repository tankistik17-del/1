# -*- coding: utf-8 -*-
"""
Собирает общий просмотрщик 3D-моделей проекта «Задвижка трубопровода».

  python3 make_viewer.py            -> viewer/index.html + viewer/models/*.json + viewer/sheets/*.jpg
  (открывать через локальный сервер:  python3 -m http.server  в папке zadvizhka_proekt, затем /viewer/)

Модели берутся из <модель>/out/*.glb и <модель>/out/spec.json. GLB переводится в glTF-JSON
со встроенным буфером (формат .json раздаётся любым веб-сервером и хостингом артефактов).
"""
import base64
import glob
import json
import os
import struct
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


def glb_to_gltf_json(path):
    b = open(path, "rb").read()
    magic, ver, length = struct.unpack("<4sII", b[:12])
    assert magic == b"glTF", path
    off = 12
    js, binchunk = None, b""
    while off < len(b):
        clen, ctype = struct.unpack("<I4s", b[off:off + 8])
        data = b[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            js = json.loads(data)
        elif ctype == b"BIN\x00":
            binchunk = data
        off += 8 + clen
    js["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binchunk).decode()
    return json.dumps(js, separators=(",", ":"))


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
        with open(os.path.join(HERE, "models", key + ".json"), "w") as f:
            f.write(glb_to_gltf_json(glb))
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
                        model="models/%s.json" % key, sheetImg=sheet_img, spec=spec))
        print("ok", key, os.path.getsize(os.path.join(HERE, "models", key + ".json")) // 1024, "KB")
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = tpl.replace("/*__CONFIG__*/[]", json.dumps(cfg, ensure_ascii=False))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
