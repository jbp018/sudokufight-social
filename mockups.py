"""
Capturas de la app dentro de un móvil, para los posts de novedades.

Las capturas viven en screenshots/ y YA están anonimizadas (nombres inventados y
estadísticas cambiadas). Los originales con datos reales no se suben nunca.

Tipos de captura:
  screen  pantalla completa del móvil: se recorta la barra de estado (hora,
          batería...) y se enmarca como un teléfono
  card    imagen suelta (p. ej. la tarjeta de compartir): se pone tal cual,
          con sombra, sin marco de móvil
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import theme as T

SHOTS = T.DIR / "screenshots"
STATUS_BAR = 96          # px de la barra de estado en las capturas originales (738 de ancho)
BEZEL_COLOR = "#05080D"
BEZEL_EDGE = "#34455F"


def _rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _shadow(size: tuple, radius: int, blur: int = 28, alpha: int = 170) -> Image.Image:
    pad = blur * 3
    layer = Image.new("RGBA", (size[0] + pad * 2, size[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([pad, pad + 10, pad + size[0], pad + 10 + size[1]], radius=radius,
                                            fill=(0, 0, 0, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def phone(name: str, kind: str, height: int) -> tuple:
    """(imagen RGBA con sombra, margen de la sombra): una captura lista para
    pegar, de `height` px de alto sin contar la sombra."""
    img = Image.open(SHOTS / name).convert("RGBA")
    if kind == "screen":
        img = img.crop((0, STATUS_BAR, img.width, img.height))
        bezel = max(6, round(height * 0.011))
        inner_h = height - 2 * bezel
        inner_w = round(img.width * inner_h / img.height)
        screen = img.resize((inner_w, inner_h), Image.LANCZOS)
        radius = round(height * 0.055)
        screen = _rounded(screen, radius - bezel)
        body = Image.new("RGBA", (inner_w + 2 * bezel, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(body)
        d.rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=radius, fill=BEZEL_COLOR,
                            outline=BEZEL_EDGE, width=2)
        body.paste(screen, (bezel, bezel), screen)
    else:
        w = round(img.width * height / img.height)
        radius = round(height * 0.04)
        body = img.resize((w, height), Image.LANCZOS)
        d = ImageDraw.Draw(body)
        d.rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=radius, outline=BEZEL_EDGE, width=2)

    sh = _shadow(body.size, round(height * 0.05))
    pad = (sh.width - body.width) // 2
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out.alpha_composite(sh)
    out.alpha_composite(body, (pad, (sh.height - body.height) // 2 - 4))
    return out, pad


def compose(shots: list, max_w: int, max_h: int) -> Image.Image:
    """1-3 capturas juntas, ajustadas a max_w × max_h. Con 3, la central va
    delante y más grande; con 2, una al lado de la otra algo solapadas."""
    n = len(shots)
    scales = {1: [1.0], 2: [1.0, 1.0], 3: [0.86, 1.0, 0.86]}[n]
    order = {1: [0], 2: [0, 1], 3: [0, 2, 1]}[n]  # orden de pegado: la central, la última (delante)

    def build(h):
        built = [phone(name, kind, round(h * s)) for (name, kind), s in zip(shots, scales)]
        items = [b[0] for b in built]
        pads = [b[1] for b in built]
        bodies = [it.width - 2 * p for it, p in zip(items, pads)]  # ancho sin la sombra
        overlap = {1: 0, 2: 0.05, 3: 0.12}[n]
        ov = int(overlap * sum(bodies) / n)
        total = sum(bodies) - ov * (n - 1)
        return items, pads, bodies, total, ov

    h = max_h
    items, pads, bodies, total, ov = build(h)
    if total > max_w:  # no cabe a lo ancho: se reduce todo proporcionalmente
        h = int(h * max_w / total)
        items, pads, bodies, total, ov = build(h)
    canvas_h = max(it.height for it in items)
    margin = max(pads)
    canvas = Image.new("RGBA", (total + 2 * margin, canvas_h), (0, 0, 0, 0))
    xs, x = [], margin
    for b in bodies:
        xs.append(x)
        x += b - ov
    for i in order:
        canvas.alpha_composite(items[i], (xs[i] - pads[i], (canvas_h - items[i].height) // 2))
    return canvas
