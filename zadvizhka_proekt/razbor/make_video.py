# -*- coding: utf-8 -*-
"""
Видео (MP4) и PDF-версия разбора сварочных приспособлений — для устройств, где страница не открывается.

  pip install imageio-ffmpeg pillow playwright
  python3 make_video.py <папка назначения>

Страница razbor рендерится в headless Chromium покадрово (window.__rz.render), к каждому кадру
добавляется подпись шага. Результат:
  «Приспособление 1 - как работает.mp4», «Приспособление 2 - как работает.mp4» (H.264, 1280×720)
  «Приспособления - разбор.pdf» — тот же текст, что на странице, с кадрами каждого шага.
"""
import base64
import html
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FPS = 24
W, H, BAR = 1280, 720, 116
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TITLES = ["Приспособление сварочное №1 (лист 6, операция 020)",
          "Приспособление сварочное №2 (лист 7, операция 025)"]
SUBS = ["Стакан + 2 направляющие: базирование, пневмозажим через рычаги, прихватка с поворотом",
        "Стакан + фланец: палец 22°30′, пневмозажим головкой, кольцевой шов с вращением стола"]
FILES = ["Приспособление 1 - как работает.mp4", "Приспособление 2 - как работает.mp4"]


def plain(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def first_sentence(h):
    m = re.search(r"<p>(.*?)</p>", h, re.S)
    t = plain(m.group(1) if m else h).strip()
    s = re.split(r"(?<=[.!?])\s", t)[0]
    return s


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if draw.textlength(nxt, font=font) <= width:
            cur = nxt
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def caption_frame(img, n, total, title, sub):
    f_t = ImageFont.truetype(FONT_B, 25)
    f_s = ImageFont.truetype(FONT, 19)
    f_n = ImageFont.truetype(FONT_B, 17)
    canvas = Image.new("RGB", (W, H), (238, 241, 244))
    img = img.convert("RGB")
    k = min(W / img.width, (H - BAR) / img.height)
    im = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    canvas.paste(im, ((W - im.width) // 2, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, H - BAR, W, H], fill=(27, 42, 58))
    d.text((28, H - BAR + 14), "ШАГ %d / %d" % (n, total), font=f_n, fill=(224, 149, 74))
    d.text((150, H - BAR + 10), title, font=f_t, fill=(255, 255, 255))
    for j, line in enumerate(wrap(d, sub, f_s, W - 178)[:2]):
        d.text((150, H - BAR + 48 + j * 26), line, font=f_s, fill=(200, 212, 226))
    return canvas


def title_card(title, sub):
    c = Image.new("RGB", (W, H), (27, 42, 58))
    d = ImageDraw.Draw(c)
    d.text((80, 250), "КАК РАБОТАЕТ", font=ImageFont.truetype(FONT_B, 24), fill=(224, 149, 74))
    for j, line in enumerate(wrap(d, title, ImageFont.truetype(FONT_B, 44), W - 160)):
        d.text((80, 290 + j * 56), line, font=ImageFont.truetype(FONT_B, 44), fill=(255, 255, 255))
    for j, line in enumerate(wrap(d, sub, ImageFont.truetype(FONT, 24), W - 160)):
        d.text((80, 420 + j * 34), line, font=ImageFont.truetype(FONT, 24), fill=(200, 212, 226))
    return c


def main():
    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, "make_razbor.py"), tmp], check=True, capture_output=True)
    page_file = os.path.join(tmp, "Приспособления - разбор.html")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    keyframes = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                              args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = b.new_context(viewport={"width": 1320, "height": 1000}, offline=True, device_scale_factor=1)
        pg = ctx.new_page()
        pg.goto("file://" + urllib.parse.quote(page_file))
        pg.add_style_tag(content=".fx{grid-template-columns:1fr!important}.stage{width:%dpx;height:%dpx!important}"
                                 ".stage .hud,.stage .legend{display:none}" % (W, H - BAR))
        pg.wait_for_function("window.__rz && window.__rz.ready()", timeout=120000)
        pg.evaluate("window.__rz.freeze()")
        pg.wait_for_timeout(500)
        for fi in range(2):
            steps = pg.evaluate("fi => window.__rz.steps(fi)", fi)
            canvas = pg.locator(".stage canvas").nth(fi)
            canvas.scroll_into_view_if_needed()
            fdir = os.path.join(tmp, "f%d" % fi)
            os.makedirs(fdir)
            n = 0

            def put(im, count=1):
                nonlocal n
                for _ in range(count):
                    im.save(os.path.join(fdir, "%05d.png" % n))
                    n += 1
            put(title_card(TITLES[fi], SUBS[fi]), int(2.5 * FPS))
            keyframes[fi] = []
            for i, s in enumerate(steps):
                frames = max(2, int(round(s["dur"] * FPS)))
                sub = first_sentence(s["html"])
                for k in range(frames + 1):
                    pg.evaluate("([fi,i,t]) => window.__rz.render(fi,i,t)", [fi, i, k / frames])
                    shot = Image.open(io.BytesIO(canvas.screenshot()))
                    fr = caption_frame(shot, i + 1, len(steps), s["title"], sub)
                    put(fr, int(1.4 * FPS) if k == frames else 1)
                keyframes[fi].append((shot, s))
                print("лист %d, шаг %d/%d" % (6 + fi, i + 1, len(steps)), flush=True)
            out = os.path.join(dst, FILES[fi])
            subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(fdir, "%05d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "medium",
                            "-movflags", "+faststart", out], check=True)
            print(out, "%.1f МБ, %.0f с" % (os.path.getsize(out) / 1e6, n / FPS))

        # PDF: те же разделы страницы, вместо 3D-сцен — кадры каждого шага с полным текстом
        for fi in range(2):
            items = []
            for i, (im, s) in enumerate(keyframes[fi]):
                buf = io.BytesIO()
                im.convert("RGB").save(buf, "JPEG", quality=84)
                items.append({"img": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                              "n": i + 1, "title": s["title"], "html": s["html"]})
            pg.evaluate("""([fi, items]) => {
              const fx = document.querySelectorAll('.fx')[fi];
              const div = document.createElement('div'); div.className = 'pdfsteps';
              div.innerHTML = items.map(it => `<div class="ps"><img src="${it.img}"><div><div class="pn">Шаг ${it.n}</div><h4>${it.title}</h4>${it.html}</div></div>`).join('');
              fx.replaceWith(div);
            }""", [fi, items])
        pg.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
        pg.add_style_tag(content="""
          @page{size:A4;margin:12mm}
          body{padding:0;font-size:12pt;background:#fff}
          nav.toc{display:none}
          .pdfsteps{display:grid;gap:5mm;margin-top:4mm}
          .ps{display:grid;grid-template-columns:95mm 1fr;gap:5mm;break-inside:avoid;border-top:1px solid #c9d2dc;padding-top:3mm}
          .ps img{width:95mm;height:auto;border:1px solid #c9d2dc}
          .ps h4{font-family:'PT Sans Narrow',Arial,sans-serif;font-size:14pt;margin:0 0 2mm}
          .ps p{font-size:10.5pt;margin:0 0 2mm}
          .pn{font-family:'PT Mono',monospace;font-size:9pt;color:#c9731f}
          .card,details,.route{break-inside:avoid}
          section.block{break-before:page}
          section.block#route{break-before:auto}
          .route svg{min-width:0}
        """)
        pg.emulate_media(media="print", color_scheme="light")
        pg.wait_for_timeout(800)
        pdf = os.path.join(dst, "Приспособления - разбор.pdf")
        pg.pdf(path=pdf, format="A4", print_background=True,
               margin=dict(top="12mm", bottom="12mm", left="12mm", right="12mm"))
        print(pdf, "%.1f МБ" % (os.path.getsize(pdf) / 1e6))
        b.close()
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
