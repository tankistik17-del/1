# -*- coding: utf-8 -*-
"""
Видео (MP4) и PDF-версия разбора сварочных приспособлений — для устройств, где страница не открывается.

  pip install imageio-ffmpeg pillow playwright
  python3 make_video.py <папка назначения>        (ONLY_PDF=1 — только PDF, без видео)

Страница razbor рендерится в headless Chromium покадрово (window.__rz.render), к каждому кадру
добавляется подпись шага. Страница снимается с devicePixelRatio = S при прежней CSS-вёрстке
(сцена 1280×604 CSS-px → 1920×906 px), поэтому кадр чёткий без масштабирования. Результат:
  «Приспособление 1 - как работает.mp4», «Приспособление 2 - как работает.mp4» (H.264, 1920×1080, 30 к/с)
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
FPS = 30
S = 1.5                                  # плотность пикселей при съёмке страницы (devicePixelRatio)
W0, H0, BAR0 = 1280, 720, 116            # кадр в CSS-пикселях страницы
W, H, BAR = round(W0 * S), round(H0 * S), round(BAR0 * S)   # 1920×1080, полоса подписи 174


def px(v):
    return round(v * S)


class Frames:
    """Кадры PNG для ffmpeg; повторы (удержание кадра) — жёсткие ссылки на уже записанный файл."""

    def __init__(self, d):
        self.d, self.n = d, 0
        os.makedirs(d, exist_ok=True)

    def put(self, im, count=1):
        first = None
        for _ in range(count):
            f = os.path.join(self.d, "%05d.png" % self.n)
            if first is None:
                im.save(f, compress_level=1)
                first = f
            else:
                os.link(first, f)
            self.n += 1


def encode(frames_dir, out):
    """H.264 High 4.1, yuv420p — открывается стандартным плеером Windows; высокое качество (crf 17)."""
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(frames_dir, "%05d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                    "-tune", "animation", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-movflags", "+faststart", out], check=True)
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
    m = re.search(r"<p(?:\s[^>]*)?>(.*?)</p>", h, re.S)
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
    f_t = ImageFont.truetype(FONT_B, px(25))
    f_s = ImageFont.truetype(FONT, px(19))
    f_n = ImageFont.truetype(FONT_B, px(17))
    canvas = Image.new("RGB", (W, H), (238, 241, 244))
    img = img.convert("RGB")
    k = min(W / img.width, (H - BAR) / img.height)
    if abs(k - 1) < 0.01:
        # снимок уже в размер кадра (±несколько px от рамки) — без пересэмплирования, лишнее обрезать
        dx, dy = max(0, img.width - W), max(0, img.height - (H - BAR))
        im = img.crop((dx // 2, dy // 2, img.width - (dx - dx // 2), img.height - (dy - dy // 2)))
    else:
        im = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    canvas.paste(im, ((W - im.width) // 2, (H - BAR - im.height) // 2))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, H - BAR, W, H], fill=(27, 42, 58))
    d.text((px(28), H - BAR + px(14)), "ШАГ %d / %d" % (n, total), font=f_n, fill=(224, 149, 74))
    d.text((px(150), H - BAR + px(10)), title, font=f_t, fill=(255, 255, 255))
    for j, line in enumerate(wrap(d, sub, f_s, W - px(178))[:2]):
        d.text((px(150), H - BAR + px(48) + j * px(26)), line, font=f_s, fill=(200, 212, 226))
    return canvas


def title_card(title, sub):
    c = Image.new("RGB", (W, H), (27, 42, 58))
    d = ImageDraw.Draw(c)
    f_k, f_t, f_s = ImageFont.truetype(FONT_B, px(24)), ImageFont.truetype(FONT_B, px(44)), ImageFont.truetype(FONT, px(24))
    d.text((px(80), px(250)), "КАК РАБОТАЕТ", font=f_k, fill=(224, 149, 74))
    for j, line in enumerate(wrap(d, title, f_t, W - px(160))):
        d.text((px(80), px(290) + j * px(56)), line, font=f_t, fill=(255, 255, 255))
    for j, line in enumerate(wrap(d, sub, f_s, W - px(160))):
        d.text((px(80), px(420) + j * px(34)), line, font=f_s, fill=(200, 212, 226))
    return c


def main():
    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, "make_razbor.py"), tmp], check=True, capture_output=True)
    page_file = os.path.join(tmp, "Приспособления - разбор.html")
    keyframes = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                              args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = b.new_context(viewport={"width": 1320, "height": 1000}, offline=True, device_scale_factor=S)
        pg = ctx.new_page()
        pg.goto("file://" + urllib.parse.quote(page_file))
        pg.add_style_tag(content=".fx{grid-template-columns:1fr!important}.stage{width:%dpx;height:%dpx!important}"
                                 ".stage .hud,.stage .legend{display:none}" % (W0, H0 - BAR0))
        pg.wait_for_function("window.__rz && window.__rz.ready()", timeout=120000)
        pg.evaluate("window.__rz.freeze()")
        pg.wait_for_timeout(500)
        for fi in range(2):
            steps = pg.evaluate("fi => window.__rz.steps(fi)", fi)
            canvas = pg.locator(".stage canvas").nth(fi)
            canvas.scroll_into_view_if_needed()
            fdir = os.path.join(tmp, "f%d" % fi)
            fw = Frames(fdir)
            put = fw.put
            put(title_card(TITLES[fi], SUBS[fi]), int(2.5 * FPS))
            keyframes[fi] = []
            for i, s in enumerate(steps):
                frames = max(2, int(round(s["dur"] * FPS)))
                sub = first_sentence(s["html"])
                only_pdf = os.environ.get("ONLY_PDF")
                for k in (range(frames, frames + 1) if only_pdf else range(frames + 1)):
                    pg.evaluate("([fi,i,t]) => window.__rz.render(fi,i,t)", [fi, i, k / frames])
                    shot = Image.open(io.BytesIO(canvas.screenshot()))
                    fr = caption_frame(shot, i + 1, len(steps), s["title"], sub)
                    put(fr, int(1.4 * FPS) if k == frames else 1)
                keyframes[fi].append((shot, s))
                print("лист %d, шаг %d/%d" % (6 + fi, i + 1, len(steps)), flush=True)
            if os.environ.get("ONLY_PDF"):
                continue
            out = os.path.join(dst, FILES[fi])
            encode(fdir, out)
            print(out, "%.1f МБ, %.0f с" % (os.path.getsize(out) / 1e6, fw.n / FPS))

        # PDF: те же разделы страницы, вместо 3D-сцен — кадры каждого шага с полным текстом
        for fi in range(2):
            items = []
            for i, (im, s) in enumerate(keyframes[fi]):
                buf = io.BytesIO()
                im = im.convert("RGB")
                im = im.crop((4, 4, im.width - 4, im.height - 4))   # без рамки по краю кадра
                from PIL import ImageChops
                bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
                box = ImageChops.difference(im, bg).point(lambda v: 255 if v > 25 else 0).getbbox()
                if box:
                    m = 16
                    im = im.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height)))
                im.save(buf, "JPEG", quality=86)
                items.append({"img": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                              "n": i + 1, "title": s["title"], "html": s["html"]})
            pg.evaluate("""([fi, items]) => {
              const fx = document.querySelector(`.fx[data-fx="${fi+1}"]`);
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
          .ps{display:grid;grid-template-columns:80mm 1fr;gap:5mm;break-inside:avoid;border-top:1px solid #c9d2dc;padding-top:3mm}
          .ps img{width:80mm;max-height:95mm;object-fit:contain;border:1px solid #c9d2dc}
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
