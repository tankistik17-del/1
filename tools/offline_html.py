# -*- coding: utf-8 -*-
"""
Превращает страницу просмотрщика в один самодостаточный HTML-файл: three.js, шрифты PT,
модели и картинки встраиваются внутрь. Файл открывается двойным щелчком без интернета
и без соседних папок.
"""
import base64
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFLINE = os.path.join(REPO, "zadvizhka_proekt", "viewer", "offline")

FONTS_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700'
              '&family=PT+Sans:wght@400;700&family=PT+Mono&display=swap">')
PRECONNECT = '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
LIBS = {
    "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js": "three.min.js",
    "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js": "GLTFLoader.js",
    "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js": "OrbitControls.js",
}


def data_uri(path, mime):
    return "data:%s;base64,%s" % (mime, base64.b64encode(open(path, "rb").read()).decode())


def fonts_css():
    fdir = os.path.join(OFFLINE, "fonts")
    css = open(os.path.join(fdir, "fonts.css"), encoding="utf-8").read()
    return re.sub(r"url\(([^)]+\.woff2)\)",
                  lambda m: "url(%s)" % data_uri(os.path.join(fdir, m.group(1)), "font/woff2"), css)


def script_block(js):
    assert "</script" not in js.lower(), "в встраиваемом скрипте есть </script>"
    return "<script>" + js + "</script>"


def inline_page(page, extra_scripts=()):
    """page — HTML просмотрщика с CDN-ссылками. extra_scripts — JS, который вставляется
    перед основным скриптом страницы (например, модели в base64)."""
    page = page.replace(PRECONNECT, "")
    assert FONTS_LINK in page
    page = page.replace(FONTS_LINK, "<style>\n" + fonts_css() + "</style>")
    for url, fn in LIBS.items():
        tag = '<script src="%s"></script>' % url
        assert tag in page, url
        js = open(os.path.join(OFFLINE, "lib", fn), encoding="utf-8").read()
        page = page.replace(tag, script_block(js))
    if extra_scripts:
        # после библиотек, перед основным скриптом страницы
        i = page.rindex("<script>\n")
        page = page[:i] + "".join(script_block(s) for s in extra_scripts) + "\n" + page[i:]
    assert "https://cdn" not in page and "fonts.googleapis" not in page
    return page
