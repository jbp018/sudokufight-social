"""
Copia las novedades de la app al repo del bot (content/novedades.json).

El bot corre en la nube y no puede leer sudoku-app (repo privado), así que las
novedades viajan en este archivo. Lanzar esto, y hacer commit + push, cada vez
que se añada una novedad nueva a frontend/novedades.js. Los textos salen de
locales/es.json, los mismos que lee el usuario dentro de la app.

    python sync_novedades.py

El bot no anuncia una novedad hasta que su versión (`desde`) esté publicada en
la App Store, así que se puede sincronizar antes de que salga el build.
"""
import json
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent
APP = DIR.parent / "sudoku-app" / "frontend"
OUT = DIR / "content" / "novedades.json"


def main():
    js = (APP / "novedades.js").read_text(encoding="utf-8")
    entries = re.findall(r"\{\s*id:\s*'(\w+)'\s*,\s*emoji:\s*'([^']+)'\s*,\s*desde:\s*'([\d.]+)'", js)
    texts = json.loads((APP / "locales" / "es.json").read_text(encoding="utf-8"))["novedades"]

    items = []
    for id_, emoji, desde in reversed(entries):  # en el js la más nueva va arriba; aquí, de más antigua a más nueva
        t = texts[id_]
        items.append({"id": id_, "emoji": emoji, "desde": desde, "title": t["title"], "body": t["body"]})
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} novedades -> {OUT}")
    for n in items:
        print(f"  {n['desde']:6s} {n['id']}: {n['title']}")


if __name__ == "__main__":
    main()
