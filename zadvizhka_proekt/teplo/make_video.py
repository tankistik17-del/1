# -*- coding: utf-8 -*-
"""
Видео (MP4) и PDF-версия страницы «Тепловой процесс сварки» — для устройств, где страница не открывается.

  python3 make_video.py <папка назначения>        (ONLY_PDF=1 — только PDF)

Результат: «Тепловой процесс сварки.mp4» (H.264, 1920×1080, 30 к/с) и «Тепловой процесс сварки.pdf».
Страница снимается с devicePixelRatio = S: холсты рисуются в том же разрешении, кадр не растягивается.
"""
import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "razbor"))
from make_video import FPS, S, Frames, caption_frame, encode, title_card  # noqa: E402

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
CASES = [("shov1", "Шов №1 (направляющая — стакан)"),
         ("shov2", "Шов №2 (стакан — фланец)")]


def shot(loc):
    return Image.open(io.BytesIO(loc.screenshot()))


def main():
    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, "make_teplo.py"), tmp], check=True, capture_output=True)
    page_file = os.path.join(tmp, "Тепловой процесс сварки.html")
    only_pdf = bool(os.environ.get("ONLY_PDF"))
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
        ctx = b.new_context(viewport={"width": 1300, "height": 1000}, offline=True, device_scale_factor=S)
        pg = ctx.new_page()
        pg.goto("file://" + urllib.parse.quote(page_file))
        pg.wait_for_function("window.__teplo && window.__teplo.ready()", timeout=300000)
        pg.evaluate("window.__frozen = true")
        pg.add_style_tag(content=".scene{grid-template-columns:1.1fr 1fr!important}")
        fdir = os.path.join(tmp, "frames")
        fw = Frames(fdir)
        put = fw.put
        snaps = {}

        total = 1 + 2 * len(CASES)
        step = 0
        if not only_pdf:
            put(title_card("Тепловой процесс сварки корпуса задвижки",
                           "Расчёт по Рыкалину и численная модель сечения швов: I = 134 А, U = 23 В, v = 46 м/ч, "
                           "q/v ≈ 193 Дж/мм, сталь 20"), int(3 * FPS))
        # 1. Вид сверху: движение дуги
        step += 1
        top = pg.locator("#vizTop .cv")
        top.scroll_into_view_if_needed()
        for k in range(1 if only_pdf else int(7 * FPS)):
            pg.evaluate("s => { window.__teplo.TOP.shift = s; window.__teplo.drawTop(); }", k / FPS * 12.8)
            im = shot(top)
            if not only_pdf:
                put(caption_frame(im, step, total, "Тепловое поле при движении дуги (вид сверху, стенка 6 мм)",
                                  "Изотермы сжаты перед дугой и вытянуты позади: металл нагревается резко, "
                                  "а остывает медленнее. Изотерма 735 °C (Ac₁) тянется за дугой на ≈ 9 мм."))
        snaps["top"] = im
        # 2. Сечения швов
        sc = pg.locator("#vizSec .scene")
        for key, title in CASES:
            pg.click('.case[data-case="%s"]' % key)
            pg.click('.view[data-view="temp"]')
            pg.click('.zoom[data-zoom="near"]')
            sc.scroll_into_view_if_needed()
            step += 1
            ts = [0.45 + 3.55 * (k / (12 * FPS)) ** 1.6 for k in range(int(12 * FPS) + 1)]
            if only_pdf:
                ts = [0.9]
            for t in ts:
                pg.evaluate("t => window.__teplo.setT(t)", t)
                im = shot(sc)
                if not only_pdf:
                    put(caption_frame(im, step, total, title + " — нагрев и остывание",
                                      "Слева поле температур в сечении, справа термические циклы точек ЗТВ. "
                                      "Полоса 800–500 °C — интервал t₈/₅."))
            if not only_pdf:
                put(im, int(1.0 * FPS))
            pg.evaluate("t => window.__teplo.setT(t)", 0.9)
            snaps[key + "_t"] = shot(sc)
            pg.click('.view[data-view="zones"]')
            step += 1
            im = shot(sc)
            snaps[key + "_z"] = im
            if not only_pdf:
                put(caption_frame(im, step, total, title + " — строение ЗТВ",
                                  "Цвет — максимальная температура точки: металл шва, перегрев, нормализация, "
                                  "неполная перекристаллизация, рекристаллизация."), int(4 * FPS))
            print("готово:", key, flush=True)
        if not only_pdf:
            out = os.path.join(dst, "Тепловой процесс сварки.mp4")
            encode(fdir, out)
            print(out, "%.1f МБ, %.0f с" % (os.path.getsize(out) / 1e6, fw.n / FPS))

        # PDF: интерактивные сцены заменяются снимками
        def uri(im):
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=88)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        figs = [("Шов №1: поле температур при t = 0,9 с и термические циклы", snaps["shov1_t"]),
                ("Шов №1: строение ЗТВ (максимальные температуры)", snaps["shov1_z"]),
                ("Шов №2: поле температур при t = 0,9 с и термические циклы", snaps["shov2_t"]),
                ("Шов №2: строение ЗТВ (максимальные температуры)", snaps["shov2_z"])]
        pg.evaluate("""(figs) => {
          const v = document.getElementById('vizSec');
          const d = document.createElement('div'); d.className = 'pfigs';
          d.innerHTML = figs.map(f => `<figure><img src="${f[1]}"><figcaption>${f[0]}</figcaption></figure>`).join('') +
            document.getElementById('legSec').outerHTML;
          v.replaceWith(d);
        }""", [[f[0], uri(f[1])] for f in figs])
        pg.evaluate("src => { const cv = document.querySelector('#vizTop .cv'); cv.innerHTML = '<img style=\"width:100%\" src=\"' + src + '\">'; }",
                    uri(snaps["top"]))
        pg.add_style_tag(content="""
          @page{size:A4;margin:12mm}
          body{padding:0;font-size:11.5pt;background:#fff}
          nav.toc,#vizTop .bar button,#rerun{display:none}
          section.block{break-inside:auto}
          .pfigs figure{margin:0 0 5mm;break-inside:avoid}
          .pfigs img{width:100%;border:1px solid #c9d2dc}
          .pfigs figcaption{font-family:'PT Sans Narrow',Arial,sans-serif;font-size:11pt;color:#566779}
          .card,.res .k,details,.calc{break-inside:avoid}
          #sec,#steel,#model{break-before:page}
        """)
        pg.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
        pg.emulate_media(media="print", color_scheme="light")
        pg.wait_for_timeout(600)
        pdf = os.path.join(dst, "Тепловой процесс сварки.pdf")
        pg.pdf(path=pdf, format="A4", print_background=True, margin=dict(top="12mm", bottom="12mm", left="12mm", right="12mm"))
        print(pdf, "%.1f МБ" % (os.path.getsize(pdf) / 1e6))
        b.close()
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
