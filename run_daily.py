"""
Publica lo que toca ahora según el plan de hoy (ver content_plan.py).

El servidor lo lanza varias veces al día (ver .github/workflows/daily.yml). En
cada ejecución publica las piezas cuya hora ya ha llegado y que aún no salieron,
por orden de hora. Como GitHub no garantiza la puntualidad al minuto, una pieza
sale en la primera ejecución posterior a su hora.

    python run_daily.py                          # publica lo que toque ahora
    python run_daily.py --dry-run                # genera las imágenes, no publica
    python run_daily.py --sample --dry-run --at 23:59   # todo el día, datos de muestra

ADMIN_KEY (entorno o --key) para leer los rankings; IG_ACCESS_TOKEN para publicar.
"""
import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import extra_cards
import ranking_cards
import theme as T
from content_plan import get_plan, mark_done
from theme import MESES, fecha_es, fetch_rankings, hoy

KEEP_DAYS = 7
HASHTAGS = "#sudoku #sudokufight #pasatiempos #juegosdelogica #entrenamientomental"
DOWNLOAD = "Sudoku Fight es gratis: enlace en la bio."


def mes_label(month_key: str) -> str:
    y, m = month_key.split("-")
    return f"{MESES[int(m) - 1].capitalize()} {y}"


def fetch_for(piece: dict, base_url: str, key: str, sample: bool) -> dict:
    if sample:
        return ranking_cards.SAMPLE
    a = piece["args"]
    return fetch_rankings(base_url, key, day=a.get("day"), month=a.get("month"), year=a.get("year"))


def render_piece(piece: dict, data: dict | None, out: Path, today: date) -> bool:
    """Dibuja la pieza en su formato. False si no hay nada que mostrar
    (p. ej. ayer nadie jugó el reto)."""
    T.set_format("story" if piece["slot"] == "story" else "post")
    ctype, a = piece["type"], piece["args"]
    out.unlink(missing_ok=True)

    if ctype == "champion_day":
        ranking_cards.render_champion_card(
            "day", data, out, fecha_es(date.fromisoformat(a["day"])), podium=False)
    elif ctype == "champion_month":
        month = a.get("month")
        ranking_cards.render_champion_card("month", data, out, mes_label(month) if month else MESES[today.month - 1].capitalize())
    elif ctype == "champion_year":
        ranking_cards.render_champion_card("year", data, out, a.get("year", str(today.year)))
    elif ctype == "ranking_month":
        if a.get("final"):
            ranking_cards.render_card("month", data, out, f"{mes_label(a['month'])} · final")
        else:
            ranking_cards.render_card("month", data, out, MESES[today.month - 1].capitalize())
    elif ctype == "ranking_year":
        sub = f"{a['year']} · final" if a.get("final") else f"a {fecha_es(today)}"
        ranking_cards.render_card("year", data, out, sub)
    elif ctype == "duel_month":
        extra_cards.render_duel_card("month", data, out)
    elif ctype == "achievement":
        ach = next(x for x in extra_cards.ACHIEVEMENTS if x["title"] == a["title"])
        extra_cards.render_achievement_card(out, ach)
    elif ctype == "edu":
        item = next(x for x in extra_cards.EDU if x["id"] == a["item"])
        extra_cards.render_edu_card(out, item)
    else:
        print(f"  tipo desconocido: {ctype}")
        return False
    return out.exists()


def caption_for(piece: dict, data: dict | None, today: date) -> str:
    """Pie de foto de los posts (las stories no llevan)."""
    ctype, a = piece["type"], piece["args"]
    if ctype == "edu":
        item = next(x for x in extra_cards.EDU if x["id"] == a["item"])
        return f"{item['title']}\n\n{item['body']}\n\nGuárdalo para tu próxima partida 📌\n\n{DOWNLOAD}\n\n{HASHTAGS}"

    if ctype in ("champion_month", "champion_year"):
        kind = "month" if ctype == "champion_month" else "year"
        top = data[kind]["top"][0]
        period = mes_label(a["month"]) if kind == "month" else a.get("year", str(today.year))
        nxt = "del próximo mes" if kind == "month" else "del próximo año"
        return (f"👑 {period} ya tiene campeón: {top['username']}, con {top['points']} puntos.\n\n"
                f"¿Quién será el campeón {nxt}? Entra en la clasificación y compite.\n\n{DOWNLOAD}\n\n{HASHTAGS}")

    if ctype in ("ranking_month", "ranking_year"):
        kind = "month" if ctype == "ranking_month" else "year"
        final = a.get("final")
        period = mes_label(a["month"]) if kind == "month" and final else (a.get("year") if kind == "year" and final else None)
        head = f"🏆 Clasificación final · {period}" if final else f"📊 Así va la clasificación del año a {fecha_es(today)}"
        medals = ["🥇", "🥈", "🥉"]
        rows = "\n".join(f"{medals[i]} {r['username']} · {r['points']} pts" for i, r in enumerate(data[kind]["top"][:3]))
        return f"{head}\n\n{rows}\n\n¿Te metes en el podio? {DOWNLOAD}\n\n{HASHTAGS}"
    return f"{DOWNLOAD}\n\n{HASHTAGS}"


def cleanup_old_images(today: date) -> None:
    """Las imágenes de public/ solo hacen falta unas horas (Instagram las
    descarga al publicar); se borran las de más de KEEP_DAYS días."""
    public = Path(__file__).resolve().parent / "public"
    if public.exists():
        limit = (today - timedelta(days=KEEP_DAYS)).isoformat()
        for f in public.glob("*.jpg"):
            if f.name[:10] < limit:
                f.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sample", action="store_true", help="datos de muestra, sin llamar a la API")
    p.add_argument("--key", default=os.environ.get("ADMIN_KEY", ""))
    p.add_argument("--base-url", default="https://api.sudokufight.es")
    p.add_argument("--dry-run", action="store_true", help="dibuja, pero no publica ni guarda nada")
    p.add_argument("--at", help="HH:MM: simular otra hora (por defecto, la actual)")
    p.add_argument("--date", help="YYYY-MM-DD: simular otro día (solo con --dry-run)")
    args = p.parse_args()

    if args.date and not args.dry_run:
        sys.exit("--date solo se puede usar con --dry-run")
    today = date.fromisoformat(args.date) if args.date else hoy()
    now_hhmm = args.at or T.ahora().strftime("%H:%M")
    if not args.sample and not args.key:
        sys.exit("Falta ADMIN_KEY (o usa --sample)")

    plan = get_plan(today, dry_run=args.dry_run)
    due = [h for h in plan if not h["done"] and h["time"] <= now_hhmm]
    print(f"{today} {now_hhmm}: {len(plan)} piezas en el plan, {len(due)} pendientes de publicar ahora")

    T.OUTPUT.mkdir(exist_ok=True)
    cleanup_old_images(today)
    failures = 0
    for piece in due:
        label = f"{piece['time']} {piece['slot']} {piece['type']} {piece.get('ref') or ''}".strip()
        try:
            data = fetch_for(piece, args.base_url, args.key, args.sample) if piece["type"] not in ("edu", "achievement") else None
            out = T.OUTPUT / f"{today}_{piece['n']}_{piece['type']}.png"
            if not render_piece(piece, data, out, today):
                print(f"- {label}: sin datos que mostrar, se omite")
                if not args.dry_run:
                    mark_done(today, piece["n"], skipped=True)
                continue
            if args.dry_run:
                print(f"- {label}: dibujada en {out.name} (dry-run)")
                continue
            from publish import publish_image

            caption = caption_for(piece, data, today) if piece["slot"] == "post" else ""
            media_id = publish_image(out, story=piece["slot"] == "story", caption=caption,
                                     name=f"{today}_{piece['n']}_{piece['type']}")
            mark_done(today, piece["n"])
            print(f"- {label}: publicada ({media_id})")
            time.sleep(20)  # que las stories salgan en orden
        except Exception as e:  # una pieza que falla no bloquea las demás
            failures += 1
            print(f"- {label}: ERROR {type(e).__name__}: {e}")
    T.set_format("story")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
