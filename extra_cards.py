"""
Contenido con más gancho que una lista: duelo por un puesto, logro del juego
y tarjetas educativas (cómo se juega, trucos, para mejorar). Válidas para
formato story y post (theme.set_format).

    python extra_cards.py     # vistas previas en output/
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

import theme as T
from theme import (
    EMOJI_FONT, GOLD, STEEL, WHITE, draw_cta, fit_font, font, format_stat, glow,
    text_centered_y, wrap_text,
)

DIR = Path(__file__).resolve().parent
ACHIEVEMENTS = json.loads((DIR / "achievements.json").read_text(encoding="utf-8"))
EDU = json.loads((DIR / "content" / "edu.json").read_text(encoding="utf-8"))

EDU_LABEL = {
    "howto": ("📘", "CÓMO SE JUEGA"),
    "truco": ("💡", "TRUCO DE SUDOKU"),
    "mejora": ("🚀", "PARA MEJORAR"),
    "curiosidad": ("🧠", "CURIOSIDAD"),
}


def _centered(draw, text, fnt, y, fill):
    draw.text(((T.W - draw.textlength(text, font=fnt)) / 2, y), text, font=fnt, fill=fill)


def _gap(kind: str, a: dict, b: dict) -> int:
    if kind == "day":
        return abs(a["elapsed"] - b["elapsed"])
    return abs(a.get("points", 0) - b.get("points", 0))


def find_closest_battle(kind: str, top: list) -> tuple:
    """La pareja de puestos consecutivos con menos diferencia: la pelea más
    emocionante de la clasificación, no siempre la del 1º-2º."""
    pairs = [(i, i + 1) for i in range(len(top) - 1)]
    return min(pairs, key=lambda p: _gap(kind, top[p[0]], top[p[1]]))


def render_duel_card(kind: str, data: dict, out_path: Path, pair: tuple | None = None) -> None:
    """Cara a cara entre dos puestos. Por defecto, la pelea más reñida."""
    top = data[kind]["top"]
    if len(top) < 2:
        return
    pair = pair or find_closest_battle(kind, top)
    first, second = top[pair[0]], top[pair[1]]

    y0 = int(T.center_block(760))
    img = T.new_canvas()
    halo = glow(T.W // 2, y0 + 380, 620, (24, 95, 165))
    img.paste(halo, (0, 0), halo)
    draw = ImageDraw.Draw(img)
    T.draw_header(img, draw, centered=True)

    if pair == (0, 1):
        eyebrow = {"day": "¿QUIÉN GANA HOY?", "month": "¿QUIÉN MANDA ESTE MES?", "year": "¿QUIÉN MANDA ESTE AÑO?"}[kind]
    else:
        eyebrow = f"¡PELEA POR EL TOP {pair[1] + 1}!"
    _centered(draw, eyebrow, font("seguisb.ttf", 36), y0, GOLD)

    sf = font("seguisb.ttf", 38)
    name_y = y0 + 90
    f1 = fit_font(draw, first["username"], "segoeuib.ttf", 80, T.W - 140)
    _centered(draw, first["username"], f1, name_y, WHITE)
    _centered(draw, format_stat(kind, first), sf, name_y + 120, GOLD)

    # Espada sin el selector de variación FE0F: con él, el glyph de color de
    # Segoe UI Emoji reserva el doble de ancho del que pinta y queda a un lado.
    vs_y = name_y + 260
    vf = font(EMOJI_FONT, 110)
    sword = "⚔"
    draw.text(((T.W - draw.textlength(sword, font=vf)) / 2, vs_y), sword, font=vf, embedded_color=True)

    name2_y = vs_y + 140
    f2 = fit_font(draw, second["username"], "segoeuib.ttf", 80, T.W - 140)
    _centered(draw, second["username"], f2, name2_y, WHITE)
    _centered(draw, format_stat(kind, second), sf, name2_y + 120, STEEL)

    gap_txt = "¡Separados por segundos!" if kind == "day" else f"Solo {_gap(kind, first, second)} puntos los separan"
    _centered(draw, gap_txt, fit_font(draw, gap_txt, "seguisb.ttf", 40, T.W - 140), name2_y + 220, WHITE)

    draw_cta(draw, "¿Te unes a la pelea? Descárgala gratis")
    T.OUTPUT.mkdir(exist_ok=True)
    img.save(out_path)


def render_achievement_card(out_path: Path, achievement: dict) -> None:
    """Uno de los logros reales del juego (solo visibles dentro de la app, en
    Premium): enseña la profundidad del juego a quien aún no lo tiene."""
    img = T.new_canvas()
    draw = ImageDraw.Draw(img)
    df = font("segoeui.ttf", 34)
    lines = wrap_text(draw, achievement["desc"], df, T.W - 200)
    block_h = 520 + len(lines) * 46 + 80
    y0 = int(T.center_block(block_h))

    halo = glow(T.W // 2, y0 + 220, 560, (232, 160, 32))
    img.paste(halo, (0, 0), halo)
    draw = ImageDraw.Draw(img)
    T.draw_header(img, draw, centered=True)

    _centered(draw, "LOGRO DESBLOQUEABLE", font("seguisb.ttf", 36), y0, GOLD)

    badge_r = 130
    cx, cy = T.W // 2, y0 + 90 + badge_r
    draw.ellipse([cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r], outline=GOLD, width=6)
    bf = font(EMOJI_FONT, 120)
    bw = draw.textlength(achievement["emoji"], font=bf)
    draw.text((cx - bw / 2, text_centered_y(draw, achievement["emoji"], bf, cy)),
              achievement["emoji"], font=bf, embedded_color=True)

    title_y = cy + badge_r + 60
    _centered(draw, achievement["title"], fit_font(draw, achievement["title"], "segoeuib.ttf", 64, T.W - 120), title_y, WHITE)

    desc_y = title_y + 110
    for line in lines:
        _centered(draw, line, df, desc_y, STEEL)
        desc_y += 46
    _centered(draw, f"Uno de los {len(ACHIEVEMENTS)} logros de Sudoku Fight", font("segoeui.ttf", 28), desc_y + 50, STEEL)

    draw_cta(draw, "Desbloquéalos todos · descárgala gratis")
    T.OUTPUT.mkdir(exist_ok=True)
    img.save(out_path)


def render_edu_card(out_path: Path, item: dict) -> None:
    """Explicación de cómo se juega, truco o consejo para mejorar."""
    img = T.new_canvas()
    draw = ImageDraw.Draw(img)
    T.draw_header(img, draw, centered=True)

    bf = font("segoeui.ttf", 38)
    lines = wrap_text(draw, item["body"], bf, T.W - 180)
    block_h = 240 + len(lines) * 54
    y0 = int(T.center_block(block_h))

    emoji, label = EDU_LABEL[item["kind"]]
    ef, lf = font(EMOJI_FONT, 36), font("seguisb.ttf", 36)
    emoji_w = draw.textlength(emoji + " ", font=ef)
    start = (T.W - emoji_w - draw.textlength(label, font=lf)) / 2
    draw.text((start, y0), emoji + " ", font=ef, embedded_color=True)
    draw.text((start + emoji_w, y0), label, font=lf, fill=GOLD)

    title_y = y0 + 110
    _centered(draw, item["title"], fit_font(draw, item["title"], "segoeuib.ttf", 68, T.W - 140), title_y, WHITE)

    body_y = title_y + 130
    for line in lines:
        _centered(draw, line, bf, body_y, STEEL)
        body_y += 54

    draw_cta(draw, "Pon a prueba tu técnica · descárgala gratis")
    T.OUTPUT.mkdir(exist_ok=True)
    img.save(out_path)


def main():
    from ranking_cards import SAMPLE

    T.OUTPUT.mkdir(exist_ok=True)
    for fmt in ("story", "post"):
        T.set_format(fmt)
        render_duel_card("month", SAMPLE, T.OUTPUT / f"prev_{fmt}_duel_month.png")
        render_achievement_card(T.OUTPUT / f"prev_{fmt}_achievement.png", ACHIEVEMENTS[4])
        render_edu_card(T.OUTPUT / f"prev_{fmt}_edu_truco.png", next(i for i in EDU if i["id"] == "pares_desnudos"))
        render_edu_card(T.OUTPUT / f"prev_{fmt}_edu_howto.png", next(i for i in EDU if i["id"] == "modos"))
    T.set_format("story")
    print("Vistas previas en", T.OUTPUT)


if __name__ == "__main__":
    main()
