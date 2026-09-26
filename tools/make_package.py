# -*- coding: utf-8 -*-
"""
Собирает папку «для флешки»: всё открывается на Windows без установки программ и без интернета.

  python3 tools/make_package.py <исходный PDF чертежей> <папка назначения>

Состав:
  START_3D_prosmotr.html   — 3D-просмотр всех моделей (двойной щелчок, откроется в Edge/Chrome)
  Albom_3D_modeley.pdf     — виды, разрезы и спецификации всех моделей
  Chertezhi_ishodnye.pdf   — исходные чертежи
  STEP_dlya_KOMPAS_SolidWorks/*.step
  GLB_dlya_3D_prosmotra_Windows/*.glb
  PROCHITAJ.txt            — инструкция
  data/                    — служебные файлы просмотрщика (не удалять)

Нужны: cadquery-модели уже собраны (out/*.glb, *.step, spec.json), playwright + Chromium, pymupdf.
"""
import html
import json
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(REPO, "zadvizhka_proekt")
VIEWER = os.path.join(PROJ, "viewer")
OFFLINE = os.path.join(VIEWER, "offline")
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# ключ, папка, лист, название, подпись, есть ли разрез, файл glb/step (без расширения), имя для STEP
MODELS = [
    ("zadvizhka", "zadvizhka", 1, "Задвижка трубопровода", "Сборочный чертёж, М 1:1", True, "zadvizhka", "01_Zadvizhka_sborka"),
    ("korpus", "korpus", 2, "Корпус", "Сварная сборочная единица, М 1:1", True, "korpus", "02_Korpus"),
    ("prisposoblenie_1", "prisposoblenie_1", 6, "Приспособление сварочное №1", "Пневматическое, М 1:1", True,
     "prisposoblenie_svarochnoe_1", "06_Prisposoblenie_1"),
    ("prisposoblenie_2", "prisposoblenie_2", 7, "Приспособление сварочное №2", "Пневматическое, М 1:1", True,
     "prisposoblenie_svarochnoe_2", "07_Prisposoblenie_2"),
    ("oborudovanie", "oborudovanie", 8, "Общий вид сварочного оборудования", "Натуральная величина (лист М 1:5)", False,
     "oborudovanie", "08_Svarochnoe_oborudovanie"),
    ("planirovka", "planirovka", 9, "Планировка участка сборки-сварки", "Натуральная величина (лист М 1:50)", False,
     "planirovka_uchastka", "09_Planirovka_uchastka"),
]

REMARKS = [
    "Лист 2: справочные размеры 160* и 268* противоречат друг другу и фланцам Ø210. В модели приняты 155 и 260 "
    "по размерной цепи листа 1 (181* + 105 = 286*).",
    "Трубы Ø111×6 и Ø130×6 и фланцы Ø210 с отверстиями на Ø180 не совпадают с рядами ГОСТ 8732-78 и "
    "ГОСТ 12820/12815 (для DN100 D = 215). В моделях взяты размеры чертежа.",
    "В технических требованиях указан «ГОСТ 2246-79», правильное обозначение — ГОСТ 2246-70.",
    "На листах 1, 6 и 7 нет спецификаций: наименования позиций определены по конструкции узлов. "
    "Детали без номера позиции на чертеже в спецификациях отмечены прочерком.",
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("%s\n%s" % (" ".join(cmd), r.stderr[-2000:]))
    return r.stdout


def render(glb, prefix, views, section=None):
    cmd = [sys.executable, os.path.join(REPO, "tools", "render_views.py"), glb, prefix,
           "--views", ",".join(views), "--size", "2600", "--zoom", "0.95", "--clean"]
    if section:
        cmd += ["--section", section]
    run(cmd)


def bbox_mm(glb):
    import trimesh
    s = trimesh.load(glb, force="scene")
    lo, hi = s.bounds  # glTF: Y вверх
    d = hi - lo
    return d[0], d[2], d[1]  # длина X, глубина, высота


def esc(s):
    return html.escape(str(s if s is not None else ""))


def album_html(pkg, items):
    css = open(os.path.join(OFFLINE, "fonts", "fonts.css"), encoding="utf-8").read().replace(
        "url(", "url(data/fonts/")
    parts = []
    toc = "".join("<tr><td>%d</td><td>%s</td><td>%s</td><td>%d</td></tr>" % (
        it["sheet"], esc(it["title"]), esc(it["sub"]), len(it["spec"])) for it in items)
    parts.append("""
<section class="page title">
  <div class="kicker">Дипломный проект · 3D-модели чертежей</div>
  <h1>Технология сборки-сварки корпуса задвижки трубопровода</h1>
  <p class="lead">Альбом трёхмерных моделей, построенных по листам графической части. Для каждого листа — общий вид,
  разрез (для механических узлов), ортогональные виды и спецификация модели.</p>
  <table class="toc"><thead><tr><th>Лист</th><th>Модель</th><th>Масштаб / вид</th><th>Строк спецификации</th></tr></thead>
  <tbody>%s</tbody></table>
  <div class="how">
    <h3>Как посмотреть модели на компьютере</h3>
    <p><b>START_3D_prosmotr.html</b> — двойной щелчок: откроется браузер (Edge или Chrome) с 3D-моделями. Интернет не нужен.
    Модель вращается мышью, есть разрез, разнесённый вид и спецификация с подсветкой деталей.</p>
    <p><b>STEP_dlya_KOMPAS_SolidWorks</b> — сборки в формате STEP для КОМПАС-3D, SolidWorks, Inventor, FreeCAD.
    <b>GLB_dlya_3D_prosmotra_Windows</b> — открываются встроенным «Средством 3D-просмотра» Windows.</p>
  </div>
</section>""" % toc)
    for it in items:
        L, W, H = it["dims"]
        dims = "габарит %s × %s × %s мм" % tuple(fmt(v) for v in (L, W, H))
        imgs = it["img"]
        main2 = ('<figure><img src="%s"><figcaption>Общий вид</figcaption></figure>' % imgs["iso"] +
                 ('<figure><img src="%s"><figcaption>Разрез фронтальной плоскостью</figcaption></figure>' % imgs["sec"]
                  if imgs.get("sec") else
                  '<figure><img src="%s"><figcaption>Общий вид с другой стороны</figcaption></figure>' % imgs["iso2"]))
        ortho = "".join('<figure><img src="%s"><figcaption>%s</figcaption></figure>' % (imgs[k], cap)
                        for k, cap in (("front", "Вид спереди"), ("top", "Вид сверху"), ("left", "Вид слева")) if imgs.get(k))
        rows = "".join("<tr><td class='c'>%s</td><td>%s%s</td><td class='c'>%s</td><td>%s</td></tr>" % (
            esc(s.get("pos") or "—"), esc(s.get("name_ru") or s.get("key")),
            ("<small>%s</small>" % esc(s["note"])) if s.get("note") else "",
            esc(s.get("qty", "")), esc("; ".join(x for x in (s.get("material"), s.get("standard")) if x)))
            for s in it["spec"])
        head = """<header class="run"><span class="sh">Лист %d</span><span class="nm">%s</span><span class="sb">%s · %s</span></header>""" % (
            it["sheet"], esc(it["title"]), esc(it["sub"]), dims)
        parts.append('<section class="page">%s<div class="two">%s</div></section>' % (head, main2))
        parts.append('<section class="page">%s<div class="three">%s</div></section>' % (head, ortho))
        parts.append("""<section class="page spec">%s<h2>Спецификация модели</h2>
<table class="sp"><colgroup><col style="width:9%%"><col style="width:45%%"><col style="width:7%%"><col></colgroup>
<thead><tr><th>Поз.</th><th>Наименование</th><th>Кол.</th><th>Материал, стандарт</th></tr></thead><tbody>%s</tbody></table></section>""" % (
            head, rows))
    parts.append("""<section class="page"><header class="run"><span class="sh">Итог</span><span class="nm">Замечания к чертежам</span>
<span class="sb">выявлены при построении моделей</span></header><ol class="rem">%s</ol>
<p class="fine">Размеры, проставленные на чертежах, перенесены в модели без изменений; непроставленная геометрия снята
с чертежей в масштабе. Стандартные изделия (крепёж, кольца, штифты, баллоны, рельсы) выполнены по ГОСТ.</p></section>""" %
                 "".join("<li>%s</li>" % esc(r) for r in REMARKS))
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Альбом 3D-моделей</title><style>
%s
@page{size:A4 landscape;margin:11mm 12mm}
:root{--ink:#1b2a3a;--muted:#5a6b7e;--line:#c9d2dc;--blue:#2f5d9a}
body{font-family:'PT Sans',Arial,sans-serif;color:var(--ink);font-size:10.5pt;margin:0}
h1,h2,h3,.run,.kicker{font-family:'PT Sans Narrow','Arial Narrow',Arial,sans-serif}
.page{break-after:page;position:relative}
.page:last-child{break-after:auto}
.title h1{font-size:30pt;line-height:1.05;margin:4mm 0 4mm;max-width:210mm}
.kicker{color:var(--blue);text-transform:uppercase;letter-spacing:.08em;font-size:11pt}
.lead{font-size:12pt;max-width:190mm;color:#2c3c4e}
.toc{border-collapse:collapse;margin:6mm 0;width:100%%}
.toc th,.toc td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left}
.toc th{font-family:'PT Sans Narrow',Arial,sans-serif;font-weight:400;color:var(--muted)}
.toc td:first-child,.toc td:last-child{font-family:'PT Mono',monospace}
.how{border-top:2px solid var(--ink);padding-top:3mm;max-width:230mm}
.how h3{margin:0 0 2mm;font-size:14pt}
.how p{margin:0 0 2mm}
.run{display:flex;gap:6mm;align-items:baseline;border-bottom:2px solid var(--ink);padding-bottom:2mm;margin-bottom:4mm}
.run .sh{font-family:'PT Mono',monospace;color:#fff;background:var(--blue);padding:1px 7px;font-size:10pt}
.run .nm{font-size:17pt;font-weight:700}
.run .sb{margin-left:auto;color:var(--muted);font-size:9.5pt}
figure{margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
figure img{max-width:100%%;object-fit:contain}
figcaption{font-family:'PT Sans Narrow',Arial,sans-serif;color:var(--muted);font-size:10.5pt;margin-top:2mm}
.two{display:grid;grid-template-columns:1fr 1fr;gap:6mm;height:160mm}
.two img{max-height:150mm}
.three{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5mm;height:160mm}
.three img{max-height:150mm}
.spec h2{font-size:13pt;margin:0 0 2mm}
.sp{border-collapse:collapse;width:100%%;font-size:9pt}
.sp th{font-family:'PT Sans Narrow',Arial,sans-serif;font-weight:400;color:var(--muted);text-align:left;border-bottom:1.5px solid var(--ink);padding:3px 5px}
.sp td{border-bottom:1px solid var(--line);padding:3px 5px;vertical-align:top}
.sp td.c{text-align:center;font-family:'PT Mono',monospace}
.sp small{display:block;color:var(--muted);font-size:8pt}
.sp tr{break-inside:avoid}
.rem{font-size:12pt;max-width:235mm;line-height:1.45}
.rem li{margin-bottom:3mm}
.fine{color:var(--muted);max-width:235mm}
</style></head><body>%s</body></html>""" % (css, "\n".join(parts))


def fmt(v):
    return ("%d" % round(v)) if v >= 100 else ("%.1f" % v).replace(".", ",")


def main():
    src_pdf, dst = sys.argv[1], sys.argv[2]
    if os.path.exists(dst):
        shutil.rmtree(dst)
    data = os.path.join(dst, "data")
    img_dir = os.path.join(data, "album")
    os.makedirs(img_dir)

    # 1. Офлайн-просмотрщик: модели (models/*.js), листы (sheets/*.jpg), библиотеки и шрифты рядом
    env = dict(os.environ, ZADV_PDF=src_pdf)
    subprocess.run([sys.executable, os.path.join(VIEWER, "make_viewer.py")], check=True, env=env, cwd=VIEWER)
    for sub in ("models", "sheets"):
        shutil.copytree(os.path.join(VIEWER, sub), os.path.join(data, sub))
    shutil.copytree(os.path.join(OFFLINE, "lib"), os.path.join(data, "lib"))
    shutil.copytree(os.path.join(OFFLINE, "fonts"), os.path.join(data, "fonts"))
    page = open(os.path.join(VIEWER, "index.html"), encoding="utf-8").read()
    page = page.replace('<link rel="preconnect" href="https://fonts.googleapis.com">\n', "")
    page = page.replace('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Sans:wght@400;700&family=PT+Mono&display=swap">',
                        '<link rel="stylesheet" href="data/fonts/fonts.css">')
    page = page.replace("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", "data/lib/three.min.js")
    page = page.replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js", "data/lib/GLTFLoader.js")
    page = page.replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", "data/lib/OrbitControls.js")
    page = page.replace('"models/', '"data/models/').replace('"sheets/', '"data/sheets/')
    with open(os.path.join(dst, "START_3D_prosmotr.html"), "w", encoding="utf-8") as f:
        f.write(page)

    # 2. STEP и GLB
    step_dir = os.path.join(dst, "STEP_dlya_KOMPAS_SolidWorks")
    glb_dir = os.path.join(dst, "GLB_dlya_3D_prosmotra_Windows")
    os.makedirs(step_dir)
    os.makedirs(glb_dir)
    items = []
    for key, d, sheet, title, sub, has_sec, fname, outname in MODELS:
        out = os.path.join(PROJ, d, "out")
        glb = os.path.join(out, fname + ".glb")
        shutil.copy(os.path.join(out, fname + ".step"), os.path.join(step_dir, outname + ".step"))
        shutil.copy(glb, os.path.join(glb_dir, outname + ".glb"))
        # 3. Картинки для альбома
        pre = os.path.join(img_dir, key)
        render(glb, pre, ["iso", "front", "top", "left"] if has_sec else ["iso", "iso2", "front", "top"])
        if has_sec:
            render(glb, pre + "_sec", ["iso"], section="y")
        img = {v: "data/album/%s_%s.png" % (key, v) for v in ("iso", "front", "top")}
        if has_sec:
            img["left"] = "data/album/%s_left.png" % key
            img["sec"] = "data/album/%s_sec_iso.png" % key
        else:
            img["iso2"] = "data/album/%s_iso2.png" % key
        spec = json.load(open(os.path.join(out, "spec.json"), encoding="utf-8"))
        items.append(dict(key=key, sheet=sheet, title=title, sub=sub, img=img, spec=spec, dims=bbox_mm(glb)))
        print("готово:", key)

    # 4. Альбом PDF (печать HTML в Chromium)
    ah = os.path.join(dst, "_album.html")
    with open(ah, "w", encoding="utf-8") as f:
        f.write(album_html(dst, items))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
        pg = b.new_page()
        pg.goto("file://" + ah)
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=os.path.join(dst, "Albom_3D_modeley.pdf"), format="A4", landscape=True,
               print_background=True, margin=dict(top="11mm", bottom="11mm", left="12mm", right="12mm"))
        b.close()
    os.remove(ah)

    # 5. Исходные чертежи и инструкция
    shutil.copy(src_pdf, os.path.join(dst, "Chertezhi_ishodnye.pdf"))
    txt = """Задвижка трубопровода — 3D-модели чертежей дипломного проекта
================================================================

Всё открывается на Windows без установки программ и без интернета.

1. START_3D_prosmotr.html
   Двойной щелчок — откроется браузер (Microsoft Edge или Chrome) с 3D-моделями всех листов.
   Вкладки сверху — листы проекта. Левая кнопка мыши — вращать, колесо — масштаб,
   правая кнопка — сдвиг. «Разрез» — сечение модели, «Разнести» — разнесённый вид.
   Щелчок по детали подсвечивает её строку в спецификации; внизу показан исходный лист.
   Файл работает только вместе с папкой data — копируйте папку целиком.

2. Albom_3D_modeley.pdf
   Альбом: общий вид, разрез, виды спереди/сверху/слева и спецификация по каждой модели,
   в конце — замечания к чертежам. Открывается в Edge как обычный PDF.

3. Chertezhi_ishodnye.pdf — исходные чертежи (9 листов).

4. STEP_dlya_KOMPAS_SolidWorks — сборки в формате STEP (КОМПАС-3D: Файл → Открыть,
   тип файла STEP; также SolidWorks, Inventor, FreeCAD). Детали сохраняют имена и цвета.

5. GLB_dlya_3D_prosmotra_Windows — открываются встроенным «Средством 3D-просмотра»
   Windows (3D Viewer). Если его нет, используйте START_3D_prosmotr.html.

Состав моделей:
  Лист 1 — задвижка в сборе;  Лист 2 — сварной корпус;
  Лист 6 — приспособление сварочное №1;  Лист 7 — приспособление сварочное №2;
  Лист 8 — сварочное оборудование (натуральная величина);
  Лист 9 — планировка участка (цех 36 × 18 м).
Листы 3–5 — плакаты и маршрутный техпроцесс, 3D-модели для них не требуются.
"""
    with open(os.path.join(dst, "PROCHITAJ.txt"), "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(txt)

    # 6. Zip
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
