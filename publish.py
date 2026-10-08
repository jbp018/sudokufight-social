"""
Publica una imagen como story o post en @sudokufight (Instagram API con
Instagram Login). Instagram solo descarga imágenes desde una URL pública, así
que cada imagen se convierte a JPEG, se sube a un repo público de GitHub y de
ahí la coge Instagram.

Dónde se aloja:
  - En la nube (GitHub Actions, variable GITHUB_REPOSITORY): en public/ de
    este mismo repo -> raw.githubusercontent.com.
  - En local: en sudoku-fight/social/ (repo de la web) -> sudokufight.es.

    python publish.py output/2026-10-09/story_1_tip.png --story
    python publish.py ruta.png --feed --caption "texto"
    python publish.py ruta.png --story --dry-run     # solo convierte a JPEG

Credenciales: IG_ACCESS_TOKEN en el entorno o en .env; nunca se imprimen.
Los posts de feed exigen proporción entre 4:5 y 1.91:1: las tarjetas 9:16 de
story NO valen tal cual para feed.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

DIR = Path(__file__).resolve().parent
API = "https://graph.instagram.com/v21.0"

REPO = os.environ.get("GITHUB_REPOSITORY")  # solo existe en GitHub Actions
if REPO:
    HOST_REPO, HOST_DIR = DIR, DIR / "public"
    PUBLIC_BASE = f"https://raw.githubusercontent.com/{REPO}/main/public"
else:
    HOST_REPO = DIR.parent / "sudoku-fight"
    HOST_DIR = HOST_REPO / "social"
    PUBLIC_BASE = "https://sudokufight.es/social"


def get_token() -> str:
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    env_file = DIR / ".env"
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("IG_ACCESS_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        sys.exit("Falta IG_ACCESS_TOKEN (variable de entorno o .env)")
    return token


def to_jpeg(png: Path, name: str | None = None) -> Path:
    HOST_DIR.mkdir(exist_ok=True)
    out = HOST_DIR / ((name or png.parent.name + "_" + png.stem) + ".jpg")
    Image.open(png).convert("RGB").save(out, "JPEG", quality=95)
    return out


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=HOST_REPO, check=True)


def host_publicly(jpg: Path) -> str:
    git("pull", "--rebase", "--autostash", "--quiet")
    git("add", str(jpg.relative_to(HOST_REPO)))
    git("commit", "-m", f"social: {jpg.name}", "--quiet")
    git("push", "--quiet")
    url = f"{PUBLIC_BASE}/{jpg.name}"
    for _ in range(40):  # GitHub Pages tarda hasta ~2 min en servirlo
        r = requests.head(url, timeout=10)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            return url
        time.sleep(5)
    sys.exit(f"La imagen no llegó a ser pública: {url}")


def create_container(token: str, image_url: str, story: bool, caption: str = "") -> str:
    """Pide a Instagram que descargue y valide la imagen. No publica nada."""
    data = {"image_url": image_url, "access_token": token}
    if story:
        data["media_type"] = "STORIES"
    elif caption:
        data["caption"] = caption
    r = requests.post(f"{API}/me/media", data=data, timeout=30)
    r.raise_for_status()
    container = r.json()["id"]

    for _ in range(30):
        s = requests.get(f"{API}/{container}", params={"fields": "status_code", "access_token": token}, timeout=15).json()
        if s.get("status_code") == "FINISHED":
            return container
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram rechazó la imagen: {s}")
        time.sleep(2)
    sys.exit("Instagram no terminó de procesar la imagen a tiempo")


def publish(token: str, image_url: str, story: bool, caption: str = "") -> str:
    container = create_container(token, image_url, story, caption)
    r = requests.post(f"{API}/me/media_publish", data={"creation_id": container, "access_token": token}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def publish_image(png: Path, story: bool, caption: str = "", name: str | None = None) -> str:
    """Todo el recorrido: JPEG -> URL pública -> Instagram. Devuelve el id."""
    url = host_publicly(to_jpeg(png, name))
    return publish(get_token(), url, story, caption)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image", type=Path, nargs="?")
    p.add_argument("--check", action="store_true",
                   help="sube una imagen de prueba y comprueba que Instagram la acepta; NO publica")
    kind = p.add_mutually_exclusive_group()
    kind.add_argument("--story", action="store_true")
    kind.add_argument("--feed", action="store_true")
    p.add_argument("--caption", default="")
    p.add_argument("--dry-run", action="store_true", help="solo convierte a JPEG; no sube ni publica")
    args = p.parse_args()

    if args.check:
        png = DIR / "output" / "check.png"
        png.parent.mkdir(exist_ok=True)
        Image.new("RGB", (1080, 1920), "#0E1A2B").save(png)
        url = host_publicly(to_jpeg(png, "check"))
        create_container(get_token(), url, story=True)
        print("OK: Instagram descargó y validó", url, "(no se publicó nada)")
        return
    if not args.image or not (args.story or args.feed):
        p.error("indica la imagen y --story o --feed (o usa --check)")
    if args.dry_run:
        print("JPEG listo:", to_jpeg(args.image))
        return
    print("Publicado, id:", publish_image(args.image, args.story, args.caption))


if __name__ == "__main__":
    main()
