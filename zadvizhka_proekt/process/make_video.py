# -*- coding: utf-8 -*-
"""
Видео (MP4) техпроцесса сборки-сварки корпуса и PDF страницы с экономикой — для устройств без поддержки страницы.

  python3 make_video.py <папка>        (ONLY_PDF=1 — только PDF)
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "razbor"))
from make_video import FPS, W0, H0, BAR0, Frames, caption_frame, pdf_image, video_context, first_sentence, title_card  # noqa: E402

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def crop(im):
    im = im.convert("RGB").crop((4, 4, im.width - 4, im.height - 4))
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).point(lambda v: 255 if v > 25 else 0).getbbox()
    if box:
        m = 16
        im = im.crop((max(box[0]-m, 0), max(box[1]-m, 0), min(box[2]+m, im.width), min(box[3]+m, im.height)))
    return im


def main():
    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, "make_process.py"), tmp], check=True, capture_output=True)
    page = os.path.join(tmp, "Сборка-сварка и экономика.html")
    only_pdf = bool(os.environ.get("ONLY_PDF"))
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                              args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = video_context(b)
        pg = ctx.new_page()
        pg.goto("file://" + urllib.parse.quote(page))
        pg.add_style_tag(content=".fx{grid-template-columns:1fr!important}.stage{width:%dpx;height:%dpx!important}"
                                 ".stage .hud .st,.stage .legend{display:none}" % (W0, H0 - BAR0))
        pg.wait_for_function("window.__rz && window.__rz.ready()", timeout=120000)
        pg.evaluate("window.__rz.freeze()")
        steps = pg.evaluate("() => window.__rz.steps(0)")
        canvas = pg.locator(".stage").first
        canvas.scroll_into_view_if_needed()
        fw = Frames(None if only_pdf else os.path.join(dst, "Сборка-сварка корпуса.mp4"))
        put = fw.put
        if not only_pdf:
            put(title_card("Сборка-сварка корпуса задвижки: операции 020–050",
                           "Детали, швы, нормы времени и гидроиспытание — по маршрутному техпроцессу (листы 2, 4, 5)"), int(2.5 * FPS))
        keys = []
        for i, s in enumerate(steps):
            fr = max(2, int(round(s["dur"] * FPS)))
            rng = range(fr, fr + 1) if only_pdf else range(fr + 1)
            for k in rng:
                pg.evaluate("([i,t]) => window.__rz.render(0,i,t)", [i, k / fr])
                shot = Image.open(io.BytesIO(canvas.screenshot()))
                if not only_pdf:
                    put(caption_frame(shot, i + 1, len(steps), s["title"], first_sentence(s["html"])), int(1.3 * FPS) if k == fr else 1)
            keys.append((shot, s))
            print("шаг", i + 1, flush=True)
        out = fw.close()
        if out:
            print(out, "%.1f МБ, %.0f с" % (os.path.getsize(out) / 1e6, fw.n / FPS))
        items = []
        for i, (im, s) in enumerate(keys):
            items.append({"img": pdf_image(crop(im)), "n": i + 1, "title": s["title"], "html": s["html"]})
        pg.evaluate("""(items) => {
          const fx = document.querySelector('.fx');
          const d = document.createElement('div'); d.className = 'pdfsteps';
          d.innerHTML = items.map(it => `<div class="ps"><img src="${it.img}"><div><div class="pn">Шаг ${it.n}</div><h4>${it.title}</h4>${it.html}</div></div>`).join('');
          fx.replaceWith(d);
        }""", items)
        pg.add_style_tag(content="""
          @page{size:A4;margin:12mm}
          body{padding:0;font-size:11pt;background:#fff}
          nav.toc{display:none}
          .pdfsteps{display:grid;gap:4mm}
          .ps{display:grid;grid-template-columns:70mm 1fr;gap:5mm;break-inside:avoid;border-top:1px solid #c9d2dc;padding-top:3mm}
          .ps img{width:70mm;max-height:70mm;object-fit:contain;border:1px solid #c9d2dc}
          .ps h4{font-family:'PT Sans Narrow',Arial,sans-serif;font-size:13pt;margin:0 0 2mm}
          .ps p{font-size:10pt;margin:0 0 2mm}
          .pn{font-family:'PT Mono',monospace;font-size:9pt;color:#c9731f}
          .card,.kpi,.chart,tr{break-inside:avoid}
          #norm,#eco,#calc,#inputs{break-before:page}
          .grid2{grid-template-columns:1fr!important}
          table.t input{border:0;background:transparent}
        """)
        pg.emulate_media(media="print", color_scheme="light")
        pg.evaluate("() => { renderEcon(); }")
        pg.wait_for_timeout(600)
        pdf = os.path.join(dst, "Сборка-сварка и экономика.pdf")
        pg.pdf(path=pdf, format="A4", print_background=True, margin=dict(top="12mm", bottom="12mm", left="12mm", right="12mm"))
        print(pdf, "%.1f МБ" % (os.path.getsize(pdf) / 1e6))
        b.close()
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
