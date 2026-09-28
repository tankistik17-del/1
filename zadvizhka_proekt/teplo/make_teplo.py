# -*- coding: utf-8 -*-
"""
Страница «Тепловой процесс сварки и ЗТВ».

  python3 make_teplo.py [папка]

Пишет teplo/index.html (веб: шрифты с Google Fonts) и, если указана папка,
самодостаточный «Тепловой процесс сварки.html» (шрифты встроены, интернет не нужен).
Расчёты выполняются в браузере; эталон на numpy — thermal.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
from offline_html import FONTS_LINK, PRECONNECT, fonts_css  # noqa: E402


def main():
    page = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    if len(sys.argv) > 1:
        assert FONTS_LINK in page
        off = page.replace(PRECONNECT, "").replace(FONTS_LINK, "<style>\n" + fonts_css() + "</style>")
        assert "googleapis" not in off
        os.makedirs(sys.argv[1], exist_ok=True)
        dst = os.path.join(sys.argv[1], "Тепловой процесс сварки.html")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(off)
        print(dst, "%.2f МБ" % (os.path.getsize(dst) / 1e6))


if __name__ == "__main__":
    main()
