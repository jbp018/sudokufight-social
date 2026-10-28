"""
Diagramas de técnicas de sudoku para las tarjetas educativas.

Cada ejemplo se construye con una función que COMPRUEBA la lógica antes de
dibujar (que el par desnudo sea de verdad un par, que lo que se tacha sea lo
que de verdad se puede eliminar...): un diagrama que enseñe algo falso es peor
que ninguno. Si un ejemplo se edita mal, falla al importar, no al publicar.

Tipos:
  rows  una fila de 9 celdas con candidatos, ANTES y DESPUÉS (pares, tríos,
        único oculto)
  grid  tablero 9×9 con las posiciones posibles de UN número (apuntadores,
        caja-línea, X-Wing)
  board tablero con números colocados, celda objetivo y su fila/columna/caja
        (único desnudo)
"""
from PIL import ImageDraw

import theme as T
from theme import GOLD, STEEL, WHITE, font, text_centered_y

RED = "#E24B4A"      # el rojo de errores de la app
CELL = "#13263F"     # fondo de celda
LINE = "#2B4668"     # líneas del tablero
BOX_LINE = "#6B8CAE"  # separación de cajas 3×3
HL = "#185FA5"       # celda destacada (el azul de la app)
SHADE = "#1B3354"    # zona que se está mirando (fila, caja...)


def S(*digits) -> frozenset:
    return frozenset(digits)


# ───────────────────────── ejemplos de filas ─────────────────────────────────

def _eliminate(row, idx_keep, digits, hidden=False):
    """Devuelve (elim, after): qué candidatos se tachan y cómo queda la fila."""
    elim = {}
    for i, cell in enumerate(row):
        if isinstance(cell, int):
            continue
        if hidden:
            if i in idx_keep:
                gone = cell - set(digits)
                if gone:
                    elim[i] = gone
        elif i not in idx_keep:
            gone = cell & set(digits)
            if gone:
                elim[i] = gone
    after = [c if isinstance(c, int) else frozenset(c - elim.get(i, set())) for i, c in enumerate(row)]
    return elim, after


def _check_row_is_consistent(row):
    placed = {c for c in row if isinstance(c, int)}
    for i, c in enumerate(row):
        if not isinstance(c, int):
            assert not (c & placed), f"el candidato {c & placed} ya está colocado en la fila"


def _naked_set(row, idx, digits):
    _check_row_is_consistent(row)
    assert len(idx) == len(digits), "un conjunto desnudo tiene tantas celdas como números"
    union = set().union(*(row[i] for i in idx))
    assert union == set(digits), f"las celdas deben contener solo {digits}, tienen {union}"
    elim, after = _eliminate(row, idx, digits)
    assert elim, "el ejemplo no elimina nada"
    return {"kind": "rows", "before": row, "after": after, "hl": set(idx),
            "gold": {i: set(digits) for i in idx}, "elim": elim, "solved": None}


def _hidden_set(row, idx, digits):
    _check_row_is_consistent(row)
    assert len(idx) == len(digits)
    for d in digits:
        where = {i for i, c in enumerate(row) if not isinstance(c, int) and d in c}
        assert where and where <= set(idx), f"el {d} aparece fuera de las celdas {idx}: {where}"
    elim, after = _eliminate(row, idx, digits, hidden=True)
    assert elim, "el ejemplo no elimina nada"
    return {"kind": "rows", "before": row, "after": after, "hl": set(idx),
            "gold": {i: set(digits) for i in idx}, "elim": elim, "solved": None}


def _hidden_single(row, digit):
    _check_row_is_consistent(row)
    where = [i for i, c in enumerate(row) if not isinstance(c, int) and digit in c]
    assert len(where) == 1, f"el {digit} debe caber en una sola celda, cabe en {where}"
    i = where[0]
    assert len(row[i]) > 1, "para que sea 'oculto' la celda debe tener más candidatos"
    after = list(row)
    after[i] = digit
    return {"kind": "rows", "before": row, "after": after, "hl": {i}, "gold": {i: {digit}},
            "elim": {}, "solved": i}


# ───────────────────────── ejemplos de tablero con un número ─────────────────

def _grid(digit, cands, pattern, shade, elim_expected, rect=None):
    return {"kind": "grid", "digit": digit, "cands": set(cands), "pattern": set(pattern),
            "shade": set(shade), "elim": set(elim_expected), "rect": rect}


def _box(b):
    r0, c0 = (b // 3) * 3, (b % 3) * 3
    return {(r, c) for r in range(r0, r0 + 3) for c in range(c0, c0 + 3)}


def _pointing(digit, box, line_is_row, line, cands):
    cands = set(cands)
    in_box = cands & _box(box)
    axis = 0 if line_is_row else 1
    assert len(in_box) >= 2 and {p[axis] for p in in_box} == {line}, "en la caja, el número debe estar en una sola línea"
    elim = {p for p in cands if p[axis] == line and p not in _box(box)}
    assert elim, "no elimina nada"
    shade = _box(box)
    return _grid(digit, cands, in_box, shade, elim)


def _box_line(digit, row, cands):
    cands = set(cands)
    in_row = {p for p in cands if p[0] == row}
    boxes = {(p[0] // 3) * 3 + p[1] // 3 for p in in_row}
    assert len(in_row) >= 2 and len(boxes) == 1, "en la fila, el número debe caber solo dentro de una caja"
    box = boxes.pop()
    elim = {p for p in cands & _box(box) if p[0] != row}
    assert elim, "no elimina nada"
    shade = {(row, c) for c in range(9)}
    return _grid(digit, cands, in_row, shade, elim)


def _xwing(digit, rows, cols, cands):
    cands = set(cands)
    corners = {(r, c) for r in rows for c in cols}
    for r in rows:
        assert {p[1] for p in cands if p[0] == r} == set(cols), f"la fila {r} debe tener el número solo en las columnas {cols}"
    elim = {p for p in cands if p[1] in cols and p[0] not in rows}
    assert elim, "no elimina nada"
    shade = {(r, c) for c in cols for r in range(9)}
    return _grid(digit, cands, corners, shade, elim, rect=(min(rows), min(cols), max(rows), max(cols)))


# ───────────────────────── único desnudo en un tablero real ──────────────────

CLASSIC = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"


def _naked_single(puzzle=CLASSIC):
    g = [[int(puzzle[r * 9 + c]) for c in range(9)] for r in range(9)]

    def peers(r, c):
        cells = {(r, i) for i in range(9)} | {(i, c) for i in range(9)} | \
                {(r // 3 * 3 + i, c // 3 * 3 + j) for i in range(3) for j in range(3)}
        cells.discard((r, c))
        return cells

    best = None
    for r in range(9):
        for c in range(9):
            if g[r][c]:
                continue
            seen = {g[p[0]][p[1]] for p in peers(r, c)} - {0}
            if len(seen) == 8:
                missing = ({1, 2, 3, 4, 5, 6, 7, 8, 9} - seen).pop()
                best = best or (r, c, missing, peers(r, c))
    assert best, "el tablero no tiene ninguna celda que vea ocho números distintos"
    r, c, answer, shade = best
    return {"kind": "board", "givens": g, "target": (r, c), "answer": answer, "shade": shade}


# ───────────────────────── catálogo ──────────────────────────────────────────

def _catalog() -> dict:
    return {
        "pares_desnudos": {
            **_naked_set([S(3, 7), S(1, 3, 5, 7), S(3, 7), 6, S(2, 3, 4, 9), S(1, 4, 7, 9),
                          S(1, 2, 3, 5), S(2, 5, 7, 9), 8], idx=(0, 2), digits=(3, 7)),
            "caption": "Dos celdas de la fila solo admiten el 3 y el 7: son suyos, así que se borran del resto de la fila.",
            "legend": [(GOLD, "El par"), (RED, "Se elimina")],
        },
        "pares_ocultos": {
            **_hidden_set([S(1, 2, 5, 8), S(1, 4, 5, 9), S(1, 5, 6, 9), 3, S(4, 5, 6, 9), S(2, 4, 8, 9),
                           S(1, 4, 6, 9), S(1, 5, 6, 9), 7], idx=(0, 5), digits=(2, 8)),
            "caption": "El 2 y el 8 solo caben en dos celdas de la fila: esas celdas son suyas, y se borra cualquier otro candidato.",
            "legend": [(GOLD, "El par oculto"), (RED, "Se elimina")],
        },
        "trios": {
            **_naked_set([S(2, 5), S(2, 3, 5, 6), S(5, 9), 1, S(3, 4, 6, 9), S(2, 9),
                          S(4, 5, 8, 9), 7, S(3, 6, 8)], idx=(0, 2, 5), digits=(2, 5, 9)),
            "caption": "Tres celdas cuyos candidatos son solo 2, 5 y 9 se los reparten: se borran del resto de la fila.",
            "legend": [(GOLD, "El trío"), (RED, "Se elimina")],
        },
        "single_oculto": {
            **_hidden_single([S(1, 5, 6), 3, S(1, 5, 7, 8), S(1, 5, 6, 7), 9, S(4, 5, 6, 7),
                              S(1, 6, 8), 2, S(1, 5, 7, 8)], digit=4),
            "caption": "El 4 solo cabe en una celda de la fila: es su número, aunque esa celda tenga más candidatos.",
            "legend": [(GOLD, "El único sitio")],
        },
        "apuntadores": {
            **_pointing(5, box=0, line_is_row=True, line=1,
                        cands={(1, 0), (1, 2), (1, 4), (1, 7), (0, 6), (3, 4), (5, 8), (6, 1), (8, 5), (7, 2)}),
            "caption": "En la caja, el 5 solo cabe en la fila 2: no puede ir en el resto de esa fila, fuera de la caja.",
            "legend": [(GOLD, "El par apuntador"), (RED, "Se elimina")],
        },
        "caja_linea": {
            **_box_line(3, row=3, cands={(3, 1), (3, 2), (4, 1), (5, 2), (0, 3), (1, 7), (2, 4),
                                          (6, 2), (7, 5), (8, 8)}),
            "caption": "En la fila 4, el 3 solo cabe dentro de una caja: se borra del resto de esa caja.",
            "legend": [(GOLD, "El 3 de la fila"), (RED, "Se elimina")],
        },
        "xwing": {
            **_xwing(7, rows=(1, 5), cols=(2, 7),
                     cands={(1, 2), (1, 7), (5, 2), (5, 7), (3, 2), (7, 2), (4, 7), (8, 7),
                            (0, 4), (2, 5), (6, 0), (6, 5), (7, 4), (8, 1)}),
            "caption": "El 7 solo cabe en dos columnas de dos filas: ocupará una diagonal u otra, y se borra del resto de esas columnas.",
            "legend": [(GOLD, "Las cuatro esquinas"), (RED, "Se elimina")],
        },
        "single_desnudo": {
            **_naked_single(),
            "caption": None,  # se rellena abajo: depende del número que salga
            "legend": [(GOLD, "La celda"), (SHADE, "Lo que ve")],
        },
    }


def _fill_naked_single_caption(cat):
    n = cat["single_desnudo"]["answer"]
    cat["single_desnudo"]["caption"] = (
        f"Esta celda ve ocho números distintos en su fila, su columna y su caja: solo puede ser el {n}.")
    return cat


CATALOG = _fill_naked_single_caption(_catalog())


def get(item_id: str) -> dict | None:
    return CATALOG.get(item_id)


# ───────────────────────── dibujo ────────────────────────────────────────────

def _cx(draw, text, fnt, cx, cy, fill):
    w = draw.textlength(text, font=fnt)
    draw.text((cx - w / 2, text_centered_y(draw, text, fnt, cy)), text, font=fnt, fill=fill)


def _strike(draw, cx, cy, size):
    h = size * 0.42
    draw.line([(cx - h, cy + h), (cx + h, cy - h)], fill=RED, width=max(3, size // 9))


def _row_height(cell: int) -> int:
    return 2 * cell + 2 * 40 + 36


def draw_rows(draw: ImageDraw.ImageDraw, spec: dict, y: int, cell: int) -> int:
    total_w = 9 * cell
    x0 = (T.W - total_w) // 2
    lf = font("seguisb.ttf", 26)
    ff = font("seguisb.ttf", int(cell * 0.28))
    big = font("segoeuib.ttf", int(cell * 0.58))
    step = cell * 0.28

    def block(top, row, mode):
        for i, c in enumerate(row):
            bx, by = x0 + i * cell, top
            hl = i in spec["hl"]
            draw.rounded_rectangle([bx + 3, by + 3, bx + cell - 3, by + cell - 3], radius=12,
                                   fill=HL if hl else CELL, outline=LINE, width=2)
            cx, cy = bx + cell / 2, by + cell / 2
            if isinstance(c, int):
                _cx(draw, str(c), big, cx, cy, WHITE if not (mode == "after" and i == spec["solved"]) else GOLD)
                continue
            for d in sorted(c):
                px = cx + ((d - 1) % 3 - 1) * step
                py = cy + ((d - 1) // 3 - 1) * step
                gold = d in spec["gold"].get(i, ())
                elim = mode == "before" and d in spec["elim"].get(i, ())
                color = RED if elim else (GOLD if gold else (WHITE if hl else STEEL))
                _cx(draw, str(d), ff, px, py, color)
                if elim:
                    _strike(draw, px, py, int(cell * 0.28))

    draw.text((x0, y), "ANTES", font=lf, fill=STEEL)
    block(y + 40, spec["before"], "before")
    y2 = y + 40 + cell + 36
    arrow = "↓"
    draw.text((T.W // 2 - draw.textlength(arrow, font=lf) / 2, y + 40 + cell + 2), arrow, font=lf, fill=STEEL)
    draw.text((x0, y2), "DESPUÉS", font=lf, fill=STEEL)
    block(y2 + 40, spec["after"], "after")
    return _row_height(cell)


def draw_grid(draw: ImageDraw.ImageDraw, spec: dict, y: int, cell: int) -> int:
    size = 9 * cell
    x0 = (T.W - size) // 2
    ff = font("segoeuib.ttf", int(cell * 0.5))
    for r in range(9):
        for c in range(9):
            p = (r, c)
            bx, by = x0 + c * cell, y + r * cell
            fill = HL if p in spec["pattern"] else (SHADE if p in spec["shade"] else CELL)
            draw.rectangle([bx, by, bx + cell, by + cell], fill=fill, outline=LINE)
            if p in spec["cands"]:
                color = GOLD if p in spec["pattern"] else (RED if p in spec["elim"] else STEEL)
                _cx(draw, str(spec["digit"]), ff, bx + cell / 2, by + cell / 2, color)
                if p in spec["elim"]:
                    _strike(draw, bx + cell / 2, by + cell / 2, int(cell * 0.5))
    for k in range(0, 10, 3):
        draw.line([(x0, y + k * cell), (x0 + size, y + k * cell)], fill=BOX_LINE, width=4)
        draw.line([(x0 + k * cell, y), (x0 + k * cell, y + size)], fill=BOX_LINE, width=4)
    if spec.get("rect"):
        # Conectores entre las cuatro esquinas, sin pisar los números de las celdas.
        r1, c1, r2, c2 = spec["rect"]
        mid = cell // 2
        for r in (r1, r2):
            yy = y + r * cell + mid
            draw.line([(x0 + (c1 + 1) * cell, yy), (x0 + c2 * cell, yy)], fill=GOLD, width=4)
        for c in (c1, c2):
            xx = x0 + c * cell + mid
            draw.line([(xx, y + (r1 + 1) * cell), (xx, y + r2 * cell)], fill=GOLD, width=4)
    return size


def draw_board(draw: ImageDraw.ImageDraw, spec: dict, y: int, cell: int) -> int:
    size = 9 * cell
    x0 = (T.W - size) // 2
    ff = font("segoeuib.ttf", int(cell * 0.55))
    tr, tc = spec["target"]
    for r in range(9):
        for c in range(9):
            bx, by = x0 + c * cell, y + r * cell
            fill = HL if (r, c) == (tr, tc) else (SHADE if (r, c) in spec["shade"] else CELL)
            draw.rectangle([bx, by, bx + cell, by + cell], fill=fill, outline=LINE)
            v = spec["givens"][r][c]
            if v:
                _cx(draw, str(v), ff, bx + cell / 2, by + cell / 2, WHITE)
            elif (r, c) == (tr, tc):
                _cx(draw, str(spec["answer"]), ff, bx + cell / 2, by + cell / 2, GOLD)
    for k in range(0, 10, 3):
        draw.line([(x0, y + k * cell), (x0 + size, y + k * cell)], fill=BOX_LINE, width=4)
        draw.line([(x0 + k * cell, y), (x0 + k * cell, y + size)], fill=BOX_LINE, width=4)
    draw.rectangle([x0 + tc * cell, y + tr * cell, x0 + (tc + 1) * cell, y + (tr + 1) * cell], outline=GOLD, width=5)
    return size


def height(spec: dict, cell: int) -> int:
    return _row_height(cell) if spec["kind"] == "rows" else 9 * cell


def draw(draw_: ImageDraw.ImageDraw, spec: dict, y: int, cell: int) -> int:
    return {"rows": draw_rows, "grid": draw_grid, "board": draw_board}[spec["kind"]](draw_, spec, y, cell)


def draw_legend(draw_: ImageDraw.ImageDraw, legend: list, y: int) -> None:
    f = font("segoeui.ttf", 28)
    gap, dot = 44, 22
    widths = [dot + 12 + draw_.textlength(t, font=f) for _, t in legend]
    x = (T.W - (sum(widths) + gap * (len(legend) - 1))) / 2
    for (color, text), w in zip(legend, widths):
        draw_.ellipse([x, y + 4, x + dot, y + 4 + dot], fill=color, outline=LINE if color == SHADE else None, width=2)
        draw_.text((x + dot + 12, y), text, font=f, fill=STEEL)
        x += w + gap
