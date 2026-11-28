"""
Token de Instagram: lectura y renovación automática.

El token dura 60 días y cada renovación (GET refresh_access_token) devuelve un
token NUEVO, así que hay que guardarlo cada vez. Un workflow no puede reescribir
los secretos del repo con su GITHUB_TOKEN, así que el token vigente vive cifrado
en el propio repo (`token.enc`, Fernet/AES) y la clave (secreto TOKEN_KEY) es lo
único que no se guarda en él. Un repo público con el token cifrado no filtra nada
mientras la clave no se filtre.

  load()           -> {"token": ..., "refreshed": "YYYY-MM-DD"}
  current_token()  -> el token a usar al publicar
  maybe_refresh()  -> lo renueva si han pasado REFRESH_EVERY_DAYS (se llama
                      desde run_daily.py en cada ejecución; casi todas no hacen nada)

Sin TOKEN_KEY o sin token.enc se usa el token del entorno / .env (el de arranque)
y no se renueva nada. Si falla la renovación, se sigue publicando con el token
actual (sigue siendo válido), pero la ejecución falla a la vista cuando ya van
WARN_AFTER_DAYS días, para que salte el aviso mucho antes de que caduque.

    python token_store.py            # estado: cuántos días lleva el token
    python token_store.py --force    # renovar ya (Instagram exige >24 h desde la última)
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests
from cryptography.fernet import Fernet, InvalidToken

from theme import hoy

DIR = Path(__file__).resolve().parent
STORE = DIR / "token.enc"
API = "https://graph.instagram.com"
REFRESH_EVERY_DAYS = 7
WARN_AFTER_DAYS = 45  # el token dura 60


def _fernet() -> Fernet | None:
    key = os.environ.get("TOKEN_KEY", "").strip()
    return Fernet(key.encode()) if key else None


def _bootstrap_token() -> str:
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    env_file = DIR / ".env"
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("IG_ACCESS_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token:
        sys.exit("Falta el token de Instagram (token.enc + TOKEN_KEY, IG_ACCESS_TOKEN o .env)")
    return token


def load() -> dict:
    f = _fernet()
    if f and STORE.exists():
        try:
            return json.loads(f.decrypt(STORE.read_bytes()))
        except (InvalidToken, ValueError):
            print("aviso: token.enc no se pudo descifrar con TOKEN_KEY; uso el token del entorno")
    return {"token": _bootstrap_token(), "refreshed": None}


def save(state: dict) -> None:
    f = _fernet()
    if not f:
        raise RuntimeError("sin TOKEN_KEY no se puede guardar el token")
    STORE.write_bytes(f.encrypt(json.dumps(state).encode()))


def current_token() -> str:
    return load()["token"]


def age_days(state: dict, today: date | None = None) -> int | None:
    return (( today or hoy()) - date.fromisoformat(state["refreshed"])).days if state.get("refreshed") else None


def maybe_refresh(today: date | None = None, force: bool = False) -> bool:
    """True si renovó. Lanza RuntimeError solo si falla y el token ya está en la
    zona de riesgo (o su edad es desconocida)."""
    if not _fernet():
        return False
    today = today or hoy()
    state = load()
    age = age_days(state, today)
    if not force and age is not None and age < REFRESH_EVERY_DAYS:
        return False
    try:
        r = requests.get(f"{API}/refresh_access_token",
                         params={"grant_type": "ig_refresh_token", "access_token": state["token"]}, timeout=20)
        r.raise_for_status()
        new = r.json()["access_token"]
    except Exception as e:
        detail = getattr(getattr(e, "response", None), "text", "")[:200]
        if age is None or age >= WARN_AFTER_DAYS:
            raise RuntimeError(f"no se pudo renovar el token de Instagram (lleva {age} días): {e} {detail}") from e
        print(f"aviso: no se pudo renovar el token (lleva {age} días, aún vale): {e}")
        return False
    save({"token": new, "refreshed": today.isoformat()})
    print(f"token de Instagram renovado ({today})")
    return True


def main():
    if "--force" in sys.argv:
        print("renovado" if maybe_refresh(force=True) else "no se pudo renovar (sin TOKEN_KEY)")
    state = load()
    age = age_days(state)
    print("token.enc:", "presente" if STORE.exists() else "no existe", "| última renovación:",
          state.get("refreshed"), f"({age} días)" if age is not None else "")


if __name__ == "__main__":
    main()
