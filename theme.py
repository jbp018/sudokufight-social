"""
Piezas compartidas por todos los generadores de imágenes de Instagram
(ranking_cards.py, extra_cards.py): paleta de la app, fuentes, formato
(story 9:16 o post 4:5) y utilidades de dibujo. Nada de esto publica ni
decide contenido, solo dibuja.

Uso: llamar a set_format("story" | "post") antes de dibujar; las tarjetas leen
theme.W / theme.H / theme.TOP_SAFE... en el momento de dibujar.
"""
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

DIR = Path(__file__).resolve().parent
OUTPUT = DIR / "output"
ICON = DIR / "assets" / "icon.png"
FONTS = Path(r"C:\Windows\Fonts")

# nombre: (ancho, alto, margen superior, margen inferior).
# Story: Instagram tapa ~230px arriba (perfil/cerrar) y ~250px abajo (barra
# de respuesta). Post: Instagram exige proporción entre 4:5 y 1.91:1 y no
# tapa nada, 1080x1350 es el máximo vertical permitido.
FORMATS = {"story": (1080, 1920, 230, 250), "post": (1080, 1350, 70, 70)}

W = H = TOP_SAFE = BOTTOM_SAFE = 0
X0, X1 = 60, 1020
CTA_H = 104


def set_format(name: str) -> None:
    global W, H, TOP_SAFE, BOTTOM_SAFE
    W, H, TOP_SAFE, BOTTOM_SAFE = FORMATS[name]


set_format("story")

# Paleta de la app (sudoku-app/frontend/screens), sampleada pixel a pixel de
# capturas reales el 1 oct 2026 — no inventada.
NAVY_DARK = "#0E1A2B"
NAVY = "#1E3A5F"
NAVY_LIGHT = "#243B54"
BLUE = "#185FA5"
STEEL = "#6B8CAE"
GOLD = "#E8A020"
WHITE = "#FFFFFF"
DIVIDER = "#223154"       # línea entre filas
TAB_INACTIVE = "#182E45"  # pestaña sin seleccionar

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
EMOJI_FONT = "seguiemj.ttf"

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def ahora() -> datetime:
    """Ahora en España: el servidor de GitHub va en UTC."""
    return datetime.now(ZoneInfo("Europe/Madrid"))


def hoy() -> date:
    return ahora().date()


def fecha_es(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]}"


def fetch_rankings(base_url: str, key: str, day: str | None = None,
                   month: str | None = None, year: str | None = None) -> dict:
    params = {"key": key}
    if day:
        params["day"] = day
    if month:
        params["month"] = month
    if year:
        params["year"] = year
    r = requests.get(f"{base_url}/admin/social/rankings", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def format_stat(kind: str, row: dict) -> str:
    if kind == "day":
        m, s = divmod(int(row["elapsed"]), 60)
        return f"{m}:{s:02d}"
    return f"{row['points']} pts"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def new_canvas() -> Image.Image:
    return Image.new("RGB", (W, H), NAVY_DARK)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def text_centered_y(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, cy: float) -> float:
    """Y donde dibujar `text` para que quede verticalmente centrado en cy."""
    _, top, _, bottom = draw.textbbox((0, 0), text, font=fnt)
    return cy - (top + bottom) / 2


def fit_font(draw: ImageDraw.ImageDraw, text: str, name: str, max_size: int, max_width: float) -> ImageFont.FreeTypeFont:
    """La letra más grande de `name` que no se salga de max_width."""
    size = max_size
    while size > 24:
        f = font(name, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 4
    return font(name, 24)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: float) -> list:
    """Reparte `text` en líneas que no se salgan de max_width (por palabras)."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def glow(cx: int, cy: int, radius: int, color: tuple, max_alpha: int = 90) -> Image.Image:
    """Resplandor radial suave centrado en (cx, cy). radial_gradient('L') sale
    oscuro en el centro y claro en el borde: lo invertimos para que brille el
    centro, y limitamos la opacidad para que quede como un halo."""
    g = ImageOps.invert(Image.radial_gradient("L")).resize((radius * 2, radius * 2))
    g = g.point(lambda v: v * max_alpha // 255)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tint = Image.new("RGBA", (radius * 2, radius * 2), color)
    tint.putalpha(g)
    layer.paste(tint, (cx - radius, cy - radius), tint)
    return layer


def header_bottom() -> int:
    return TOP_SAFE + 90


def cta_top() -> int:
    return H - BOTTOM_SAFE - CTA_H


def center_block(block_h: float) -> float:
    """Y superior para que un bloque de contenido de `block_h` px quede
    centrado entre la cabecera y el botón, sea story o post."""
    top, bottom = header_bottom(), cta_top()
    return top + max(20, (bottom - top - block_h) / 2)


def draw_header(img: Image.Image, draw: ImageDraw.ImageDraw, centered: bool = False) -> int:
    """Icono + wordmark 'SUDOKU FIGHT' (blanco/dorado)."""
    icon = Image.open(ICON).convert("RGBA").resize((90, 90))
    wf = font("segoeuib.ttf", 42)
    sudoku_w = draw.textlength("SUDOKU ", font=wf)
    fight_w = draw.textlength("FIGHT", font=wf)
    start_x = (W - (90 + 16 + sudoku_w + fight_w)) / 2 if centered else X0
    img.paste(icon, (int(start_x), TOP_SAFE), icon)
    draw.text((start_x + 90 + 16, TOP_SAFE + 6), "SUDOKU ", font=wf, fill=WHITE)
    draw.text((start_x + 90 + 16 + sudoku_w, TOP_SAFE + 6), "FIGHT", font=wf, fill=GOLD)
    return header_bottom()


def draw_cta(draw: ImageDraw.ImageDraw, text: str) -> None:
    """Botón dorado de llamada a la acción, siempre en el mismo sitio."""
    y = cta_top()
    rounded_rect(draw, [X0, y, X1, y + CTA_H], 26, GOLD)
    cf = fit_font(draw, text, "seguisb.ttf", 36, X1 - X0 - 40)
    ctw = draw.textlength(text, font=cf)
    draw.text(((W - ctw) / 2, text_centered_y(draw, text, cf, y + CTA_H / 2)), text, font=cf, fill=NAVY_DARK)
