"""
Tarjetas de clasificación y de campeón — Sudoku Fight. Funcionan en formato
story (9:16) y post (4:5): ver theme.set_format.

    python ranking_cards.py --sample     # vista previa con datos de muestra

La clasificación DIARIA completa no se publica nunca (es una de las
funciones que más se consultan en la app): solo el campeón del día.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

import theme as T
from theme import (
    BLUE, DIVIDER, EMOJI_FONT, GOLD, ICON, MEDALS, STEEL, TAB_INACTIVE, WHITE, X0, X1,
    draw_cta, fit_font, font, format_stat, glow, rounded_rect, text_centered_y,
)

# Mes y año: datos REALES de las capturas del 1 oct 2026. Día: usuarios reales
# vistos en el ranking. Solo para vistas previas, sin llamar a la API.
SAMPLE = {
    "day": {
        "date": "2026-10-08",
        "top": [
            {"rank": 1, "username": "micruosa", "elapsed": 115},
            {"rank": 2, "username": "Jaimesmbc", "elapsed": 127},
            {"rank": 3, "username": "gonzalodelacruz", "elapsed": 141},
        ],
    },
    "month": {
        "top": [
            {"rank": 1, "username": "Jaimesmbc", "points": 3593, "days": 8},
            {"rank": 2, "username": "micruosa", "points": 3462, "days": 8},
            {"rank": 3, "username": "Laia", "points": 2958, "days": 8},
            {"rank": 4, "username": "Bruno", "points": 2701, "days": 8},
            {"rank": 5, "username": "jbp018", "points": 2540, "days": 8},
            {"rank": 6, "username": "sergiogomezvi", "points": 2488, "days": 8},
            {"rank": 7, "username": "alejoetc", "points": 2210, "days": 7},
            {"rank": 8, "username": "prove23", "points": 2105, "days": 7},
        ],
    },
    "year": {
        "top": [
            {"rank": 1, "username": "micruosa", "points": 11912, "days": 26},
            {"rank": 2, "username": "Jaimesmbc", "points": 10914, "days": 25},
            {"rank": 3, "username": "jbp018", "points": 9013, "days": 29},
            {"rank": 4, "username": "prove23", "points": 6807, "days": 205},
            {"rank": 5, "username": "Bruno", "points": 4997, "days": 198},
            {"rank": 6, "username": "sergiogomezvi", "points": 4687, "days": 180},
            {"rank": 7, "username": "gonzalodelacruz", "points": 4447, "days": 165},
            {"rank": 8, "username": "patriciaprovedo", "points": 3803, "days": 150},
        ],
    },
}

TABS = [("day", "HOY"), ("month", "MES"), ("year", "AÑO")]
LIST_LABEL = {"month": "CLASIFICACIÓN DEL MES", "year": "CLASIFICACIÓN DEL AÑO"}
CHAMPION_LABEL = {"day": "CAMPEÓN DEL DÍA", "month": "CAMPEÓN DEL MES", "year": "CAMPEÓN DEL AÑO"}


def render_card(kind: str, data: dict, out_path: Path, subtitle: str, label: str | None = None) -> None:
    """Lista del top (mes o año) con el estilo de la pantalla de ranking."""
    img = T.new_canvas()
    draw = ImageDraw.Draw(img)

    icon = Image.open(ICON).convert("RGBA").resize((110, 110))
    icon_y = T.TOP_SAFE
    img.paste(icon, (X0, icon_y), icon)
    wf = font("segoeuib.ttf", 50)
    draw.text((X0 + 130, icon_y + 10), "SUDOKU", font=wf, fill=WHITE)
    draw.text((X0 + 130 + draw.textlength("SUDOKU ", font=wf), icon_y + 10), "FIGHT", font=wf, fill=GOLD)
    draw.text((X0 + 130, icon_y + 72), "sudokufight.es", font=font("segoeui.ttf", 28), fill=STEEL)

    # Pestañas Hoy / Mes / Año, como el selector real del ranking.
    tabs_y, tab_h, gap = icon_y + 150, 76, 14
    tab_w = (X1 - X0 - 2 * gap) / 3
    tf_sel, tf_un = font("seguisb.ttf", 30), font("segoeui.ttf", 30)
    for i, (tkind, tlabel) in enumerate(TABS):
        tx0 = X0 + i * (tab_w + gap)
        active = tkind == kind
        rounded_rect(draw, [tx0, tabs_y, tx0 + tab_w, tabs_y + tab_h], 18, BLUE if active else TAB_INACTIVE)
        tf = tf_sel if active else tf_un
        tw = draw.textlength(tlabel, font=tf)
        draw.text((tx0 + (tab_w - tw) / 2, text_centered_y(draw, tlabel, tf, tabs_y + tab_h / 2)),
                  tlabel, font=tf, fill=WHITE if active else STEEL)

    subtitle_y = tabs_y + tab_h + 36
    draw.text((X0, subtitle_y), f"{label or LIST_LABEL[kind]} · {subtitle}", font=font("segoeui.ttf", 30), fill=STEEL)

    # Lista plana con línea divisoria, igual que en la app.
    rows = data[kind]["top"][:9]
    list_y = subtitle_y + 70
    row_h = min(128, (T.cta_top() - 24 - list_y) / max(len(rows), 1))
    ef = font(EMOJI_FONT, int(min(54, row_h * 0.42)))
    for idx, row in enumerate(rows):
        rank = row["rank"]
        y = list_y + idx * row_h
        cy = y + row_h / 2
        if idx > 0:
            draw.line([(X0, y), (X1, y)], fill=DIVIDER, width=2)
        if rank in MEDALS:
            draw.text((X0, cy - ef.size * 0.62), MEDALS[rank], font=ef, embedded_color=True)
        else:
            rf = font("segoeui.ttf", 38)
            draw.text((X0 + 4, text_centered_y(draw, str(rank), rf, cy)), str(rank), font=rf, fill=STEEL)
        uf = font("seguisb.ttf", 38)
        draw.text((X0 + 150, text_centered_y(draw, row["username"], uf, cy)), row["username"], font=uf, fill=WHITE)
        stat = format_stat(kind, row)
        sf = font("seguisb.ttf", 38)
        draw.text((X1 - draw.textlength(stat, font=sf), text_centered_y(draw, stat, sf, cy)), stat, font=sf, fill=GOLD)

    draw_cta(draw, "Descárgala gratis · link en bio")
    T.OUTPUT.mkdir(exist_ok=True)
    img.save(out_path)


def render_champion_card(kind: str, data: dict, out_path: Path, subtitle: str, podium: bool = True) -> None:
    """Ficha individual del campeón: una sola persona, en grande. Con
    podium=False no se nombra a nadie más (el campeón del día no revela el
    resto de la clasificación diaria)."""
    top = data[kind]["top"]
    if not top:
        return
    champion = top[0]
    show_podium = podium and len(top) >= 3

    block_h = 620 if show_podium else 540
    y0 = int(T.center_block(block_h))

    img = T.new_canvas()
    halo = glow(T.W // 2, y0 + 280, 560, (232, 160, 32))
    img.paste(halo, (0, 0), halo)
    draw = ImageDraw.Draw(img)
    T.draw_header(img, draw, centered=True)

    crown_f = font(EMOJI_FONT, 150)
    crown_w = draw.textlength("👑", font=crown_f)
    draw.text(((T.W - crown_w) / 2, y0), "👑", font=crown_f, embedded_color=True)

    label = CHAMPION_LABEL[kind]
    label_y = y0 + 180
    lf = font("seguisb.ttf", 34)
    draw.text(((T.W - draw.textlength(label, font=lf)) / 2, label_y), label, font=lf, fill=GOLD)
    sf = font("segoeui.ttf", 28)
    draw.text(((T.W - draw.textlength(subtitle, font=sf)) / 2, label_y + 46), subtitle, font=sf, fill=STEEL)

    name_y = label_y + 120
    uf = fit_font(draw, champion["username"], "segoeuib.ttf", 96, T.W - 120)
    draw.text(((T.W - draw.textlength(champion["username"], font=uf)) / 2, name_y), champion["username"], font=uf, fill=WHITE)

    stat_y = name_y + 150
    stat_txt = f"{format_stat(kind, champion)} · {'tiempo' if kind == 'day' else 'puntos'}"
    stf = font("seguisb.ttf", 44)
    draw.text(((T.W - draw.textlength(stat_txt, font=stf)) / 2, stat_y), stat_txt, font=stf, fill=GOLD)

    if show_podium:
        # Emoji y texto por separado: un emoji de color no se renderiza
        # mezclado con otra fuente en la misma llamada a draw.text.
        pf, pef = font("seguisb.ttf", 32), font(EMOJI_FONT, 32)
        parts = [("🥈", True), (f" {top[1]['username']}      ", False), ("🥉", True), (f" {top[2]['username']}", False)]
        total = sum(draw.textlength(t, font=pef if e else pf) for t, e in parts)
        px, py = (T.W - total) / 2, stat_y + 110
        for text, is_emoji in parts:
            f = pef if is_emoji else pf
            draw.text((px, text_centered_y(draw, text, f, py + 20)), text, font=f, fill=WHITE, embedded_color=is_emoji)
            px += draw.textlength(text, font=f)

    draw_cta(draw, "¿Le superas? Descárgala gratis · link en bio")
    T.OUTPUT.mkdir(exist_ok=True)
    img.save(out_path)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    T.OUTPUT.mkdir(exist_ok=True)
    for fmt in ("story", "post"):
        T.set_format(fmt)
        render_card("month", SAMPLE, T.OUTPUT / f"prev_{fmt}_ranking_month.png", "Octubre")
        render_card("year", SAMPLE, T.OUTPUT / f"prev_{fmt}_ranking_year.png", "2026")
        render_champion_card("day", SAMPLE, T.OUTPUT / f"prev_{fmt}_champion_day.png", "8 de octubre", podium=False)
        render_champion_card("month", SAMPLE, T.OUTPUT / f"prev_{fmt}_champion_month.png", "Septiembre 2026")
    T.set_format("story")
    print("Vistas previas en", T.OUTPUT)


if __name__ == "__main__":
    main()
