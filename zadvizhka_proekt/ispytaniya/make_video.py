# -*- coding: utf-8 -*-
"""
Видео (MP4) контроля и испытаний корпуса и PDF страницы — для устройств без поддержки страницы.

  python3 make_video.py <папка>        (ONLY_PDF=1 — только PDF)
"""
import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

import imageio_ffmpeg
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "razbor"))
from make_video import FPS, H, W, BAR, caption_frame, first_sentence, title_card  # noqa: E402

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
    subprocess.run([sys.executable, os.path.join(HERE, "make_ispytaniya.py"), tmp], check=True, capture_output=True)
    page = os.path.join(tmp, "Контроль и испытания корпуса.html")
    only_pdf = bool(os.environ.get("ONLY_PDF"))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                              args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = b.new_context(viewport={"width": 1320, "height": 1000}, offline=True)
        pg = ctx.new_page()
        pg.goto("file://" + urllib.parse.quote(page))
        pg.add_style_tag(content=".fx{grid-template-columns:1fr!important}.stage{width:%dpx;height:%dpx!important}"
                                 ".stage .hud .st,.stage .legend{display:none}" % (W, H - BAR))
        pg.wait_for_function("window.__rz && window.__rz.ready()", timeout=120000)
        pg.evaluate("window.__rz.freeze()")
        fdir = os.path.join(tmp, "f")
        os.makedirs(fdir)
        n = 0

        def put(im, c=1):
            nonlocal n
            for _ in range(c):
                im.save(os.path.join(fdir, "%05d.png" % n))
                n += 1

        # (сцена, список шагов, брак?) — годный корпус, затем тот же корпус со свищом с шага выдержки
        parts = [(0, None, False, "ВИК"), (1, None, False, "Гидроиспытание"), (1, [3, 4, 6], True, "Гидроиспытание: корпус со свищом")]
        keys = {0: [], 1: []}
        if not only_pdf:
            put(title_card("Контроль и испытания корпуса задвижки",
                           "Визуально-измерительный контроль швов и гидравлическое испытание пробным давлением (пояснительная записка, п. 1.13)"), int(2.5 * FPS))
        for fi, only, leak, name in parts:
            if only_pdf and leak:
                continue
            pg.evaluate("v => window.__rz.setLeak(v)", leak)
            pg.evaluate("fi => { window.__rz.fixtures[fi]._rec = false; }", fi)
            steps = pg.evaluate("fi => window.__rz.steps(fi)", fi)
            canvas = pg.locator(".stage").nth(fi)
            canvas.scroll_into_view_if_needed()
            idx = only if only is not None else range(len(steps))
            if not only_pdf:
                put(title_card(name, ""), int(1.2 * FPS))
            for i in idx:
                s = steps[i]
                fr = max(2, int(round(s["dur"] * FPS)))
                rng = range(fr, fr + 1) if only_pdf else range(fr + 1)
                for k in rng:
                    pg.evaluate("([f,i,t]) => window.__rz.render(f,i,t)", [fi, i, k / fr])
                    shot = Image.open(io.BytesIO(canvas.screenshot()))
                    if not only_pdf:
                        put(caption_frame(shot, i + 1, len(steps), s["title"], first_sentence(s["html"])), int(1.3 * FPS) if k == fr else 1)
                if not leak:
                    keys[fi].append((shot, s))
                print(name, "шаг", i + 1, flush=True)
        pg.evaluate("v => window.__rz.setLeak(v)", False)
        if not only_pdf:
            out = os.path.join(dst, "Контроль и испытания корпуса.mp4")
            subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(fdir, "%05d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", out], check=True)
            print(out, "%.1f МБ, %.0f с" % (os.path.getsize(out) / 1e6, n / FPS))
        for fi in (0, 1):
            items = []
            for i, (im, s) in enumerate(keys[fi]):
                buf = io.BytesIO()
                crop(im).save(buf, "JPEG", quality=86)
                items.append({"img": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), "n": i + 1, "title": s["title"], "html": s["html"]})
            pg.evaluate("""([fi, items]) => {
              const fx = document.querySelectorAll('.fx')[fi];
              const d = document.createElement('div'); d.className = 'pdfsteps';
              d.innerHTML = items.map(it => `<div class="ps"><img src="${it.img}"><div><div class="pn">Шаг ${it.n}</div><h4>${it.title}</h4>${it.html}</div></div>`).join('');
              fx.replaceWith(d);
            }""", [0, items])
        pg.add_style_tag(content="""
          @page{size:A4;margin:12mm}
          body{padding:0;font-size:11pt;background:#fff}
          nav.toc,.defpick,.chart .tip{display:none!important}
          .defall{display:grid;gap:4mm}
          .defall .defcard{grid-template-columns:62mm 1fr;break-inside:avoid;padding:3mm}
          .pdfsteps{display:grid;gap:4mm}
          .ps{display:grid;grid-template-columns:70mm 1fr;gap:5mm;break-inside:avoid;border-top:1px solid #c9d2dc;padding-top:3mm}
          .ps img{width:70mm;max-height:70mm;object-fit:contain;border:1px solid #c9d2dc}
          .ps h4{font-family:'PT Sans Narrow',Arial,sans-serif;font-size:13pt;margin:0 0 2mm}
          .ps p{font-size:10pt;margin:0 0 2mm}
          .pn{font-family:'PT Mono',monospace;font-size:9pt;color:#c9731f}
          .card,.chart,tr{break-inside:avoid}
          #defects,#hydro,#press,#inputs{break-before:page}
          .grid2{grid-template-columns:1fr!important}
          table.t input{border:0;background:transparent}
        """)
        pg.emulate_media(media="print", color_scheme="light")
        pg.evaluate("() => { drawChart(); chartCursor(-1, 0); }")
        pg.wait_for_timeout(600)
        pdf = os.path.join(dst, "Контроль и испытания корпуса.pdf")
        pg.pdf(path=pdf, format="A4", print_background=True, margin=dict(top="12mm", bottom="12mm", left="12mm", right="12mm"))
        print(pdf, "%.1f МБ" % (os.path.getsize(pdf) / 1e6))
        b.close()
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
