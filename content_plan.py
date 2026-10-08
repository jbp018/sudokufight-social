"""
Calendario de contenido — Sudoku Fight. Decide QUÉ se publica cada día, a qué
hora, y recuerda qué ya salió. No dibuja ni publica (eso es run_daily.py).

Reglas (todas las horas son de España):

  Stories
    07:00  campeón del día anterior (todos los días)
    07:10  clasificación del MES: los lunes, y el día 1 con el mes ya cerrado
    09:00  campeón del mes (el día 1)  ·  09:10 campeón del año (1 de enero)
    14:00 / 19:30  contenido: 1 o 2 stories (2 la mayoría de días). Sobre todo
           educativo (cómo se juega, trucos, mejorar); de vez en cuando un
           duelo por un puesto y, rara vez, un logro (solo se ven en Premium)

  Posts de feed
    mar y vie 13:00        educativo
    día 1, 12:30 y 18:00   campeón del mes + clasificación del mes cerrado
    día 15, 12:30          clasificación del año
    1 enero 12:30 y 18:00  campeón del año + clasificación del año cerrado
                           (los del mes se pasan al día 2)

  La clasificación DIARIA no se publica nunca: es de lo que más se consulta
  en la app. Solo el campeón del día.

El plan de un día se crea la primera vez que se pide y queda fijo; el
servidor corre varias veces al día y solo va marcando piezas como hechas.
history.json guarda todo, también para no repetir contenido.

    python content_plan.py [--date 2026-10-30] [--dry-run]
"""
import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

import extra_cards
from theme import hoy

DIR = Path(__file__).resolve().parent
HISTORY = DIR / "history.json"

STORY_SLOTS = ["14:00", "19:30"]
EDU_WEIGHT, DUEL_WEIGHT, ACHIEVEMENT_WEIGHT = 7, 2, 1
DUEL_COOLDOWN_DAYS = 4
ACHIEVEMENT_COOLDOWN_DAYS = 7


def load_history() -> list:
    return json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []


def save_history(history: list) -> None:
    HISTORY.write_text(json.dumps(history[-600:], indent=2, ensure_ascii=False), encoding="utf-8")


def _days_since(history: list, today: date, ctype: str, ref: str | None = None) -> int:
    """Días desde la última vez que salió (9999 si nunca)."""
    dates = [date.fromisoformat(h["date"]) for h in history
             if h["type"] == ctype and (ref is None or h.get("ref") == ref)]
    return (today - max(dates)).days if dates else 9999


def _pick_least_recent(history: list, today: date, ctype: str, refs: list, taken: set) -> str:
    """El elemento (id) más antiguo sin usar; los no usados nunca, primero y al azar."""
    pool = [r for r in refs if r not in taken] or refs
    scored = [(_days_since(history, today, ctype, r), random.random(), r) for r in pool]
    return max(scored)[2]


def _month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def build_day(today: date, history: list) -> list:
    iso = today.isoformat()
    yesterday = today - timedelta(days=1)
    prev_month_last = today.replace(day=1) - timedelta(days=1)
    pieces = []

    def add(slot, ctype, time, args=None, ref=None):
        pieces.append({"date": iso, "slot": slot, "type": ctype, "time": time,
                       "args": args or {}, "ref": ref, "done": False})

    add("story", "champion_day", "07:00", {"day": yesterday.isoformat()})

    if today.day == 1:
        add("story", "ranking_month", "07:10", {"month": _month_key(prev_month_last), "final": True})
        add("story", "champion_month", "09:00", {"month": _month_key(prev_month_last)})
        if today.month == 1:
            year = str(today.year - 1)
            add("story", "champion_year", "09:10", {"year": year})
            add("post", "champion_year", "12:30", {"year": year})
            add("post", "ranking_year", "18:00", {"year": year, "final": True})
        else:
            add("post", "champion_month", "12:30", {"month": _month_key(prev_month_last)})
            add("post", "ranking_month", "18:00", {"month": _month_key(prev_month_last), "final": True})
    elif today.weekday() == 0:
        add("story", "ranking_month", "07:10")

    if today.month == 1 and today.day == 2:  # los del mes de diciembre, un día después de los del año
        dec = _month_key(date(today.year - 1, 12, 1))
        add("post", "champion_month", "12:30", {"month": dec})
        add("post", "ranking_month", "18:00", {"month": dec, "final": True})

    if today.day == 15:
        add("post", "ranking_year", "12:30")

    taken_edu = set()
    edu_ids = [i["id"] for i in extra_cards.EDU]
    if today.weekday() in (1, 4):  # martes y viernes
        ref = _pick_least_recent(history, today, "edu", edu_ids, taken_edu)
        taken_edu.add(ref)
        add("post", "edu", "13:00", {"item": ref}, ref)

    n_stories = random.choices([1, 2], weights=[35, 65])[0]
    slots = STORY_SLOTS if n_stories == 2 else [random.choice(STORY_SLOTS)]
    used_today = set()
    for time in slots:
        options = [("edu", EDU_WEIGHT)]
        # El duelo y el logro no se repiten el mismo día (saldría la misma imagen).
        if "duel_month" not in used_today and _days_since(history, today, "duel_month") >= DUEL_COOLDOWN_DAYS:
            options.append(("duel_month", DUEL_WEIGHT))
        if "achievement" not in used_today and _days_since(history, today, "achievement") >= ACHIEVEMENT_COOLDOWN_DAYS:
            options.append(("achievement", ACHIEVEMENT_WEIGHT))
        types, weights = zip(*options)
        ctype = random.choices(types, weights=weights, k=1)[0]
        used_today.add(ctype)
        if ctype == "edu":
            ref = _pick_least_recent(history, today, "edu", edu_ids, taken_edu)
            taken_edu.add(ref)
            add("story", "edu", time, {"item": ref}, ref)
        elif ctype == "achievement":
            titles = [a["title"] for a in extra_cards.ACHIEVEMENTS]
            ref = _pick_least_recent(history, today, "achievement", titles, set())
            add("story", "achievement", time, {"title": ref}, ref)
        else:
            add("story", "duel_month", time)

    pieces.sort(key=lambda p: p["time"])
    for n, p in enumerate(pieces):
        p["n"] = n
    return pieces


def get_plan(today: date | None = None, dry_run: bool = False) -> list:
    """Piezas de hoy. Si hoy no tiene plan, lo crea y lo guarda; si ya lo
    tiene, lo devuelve tal cual (para que varias ejecuciones sean coherentes)."""
    today = today or hoy()
    history = load_history()
    existing = [h for h in history if h["date"] == today.isoformat()]
    if existing:
        return existing
    new = build_day(today, history)
    if not dry_run:
        save_history(history + new)
    return new


def mark_done(today: date, n: int, skipped: bool = False) -> None:
    history = load_history()
    for h in history:
        if h["date"] == today.isoformat() and h["n"] == n:
            h["done"] = True
            if skipped:
                h["skipped"] = True
    save_history(history)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    today = date.fromisoformat(args.date) if args.date else hoy()
    for piece in get_plan(today, dry_run=args.dry_run):
        print(piece["time"], piece["slot"].ljust(5), piece["type"], piece.get("ref") or "", piece["args"] or "")


if __name__ == "__main__":
    main()
