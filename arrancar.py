"""Arranque de un solo comando: `python arrancar.py`.

Levanta la API (api/servidor.py) que sirve, en el mismo proceso, los cuatro
endpoints y el front ya compilado (front/dist) si existe. Sin Node en la
demo: "arranca en frio" es criterio de evaluacion del caso (spec.md
seccion 5).

No valida ni imprime jamas GEMINI_API_KEY: solo avisa si no la encuentra.
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from api.servidor import crear_app

_A, _E, _I, _O, _U = (chr(0xe1), chr(0xe9), chr(0xed), chr(0xf3), chr(0xfa))


def _raiz_repo() -> Path:
    return Path(__file__).resolve().parent


def _hay_clave_gemini() -> bool:
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return True
    ruta_env = _raiz_repo() / ".env"
    if not ruta_env.exists():
        return False
    for linea in ruta_env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, _, valor = linea.partition("=")
        if nombre.strip() == "GEMINI_API_KEY" and valor.strip().strip('"').strip("'"):
            return True
    return False


def _avisar_si_falta_clave() -> None:
    if _hay_clave_gemini():
        return
    print(
        "AVISO: no se encontr" + _O + " GEMINI_API_KEY (ni en el entorno ni en .env). "
        "El segmentador real no podr" + _A + " llamar a Gemini -- solo funcionar" + _A +
        " para textos que ya est" + _E + "n en cach" + _E + " (.cache_llm/)."
    )


def _avisar_si_falta_front() -> tuple[bool, Path]:
    dist = _raiz_repo() / "front" / "dist"
    existe = dist.exists()
    if not existe:
        print(
            "AVISO: no existe front/dist. La ra" + _I + "z del servidor mostrar" + _A +
            " un mensaje en vez de la interfaz. Compila el front con, dentro de front/:\n"
            "  npm install\n"
            "  npm run build"
        )
    return existe, dist


def main() -> None:
    _avisar_si_falta_clave()
    existe_front, _ = _avisar_si_falta_front()

    host = os.environ.get("HOST", "127.0.0.1")
    puerto_http = int(os.environ.get("PORT", "8000"))

    print(f"Arrancando en http://{host}:{puerto_http}")
    if existe_front:
        print(f"http://{host}:{puerto_http} sirve el front compilado (front/dist).")
    else:
        print(f"http://{host}:{puerto_http} sirve solo la API hasta que compiles el front.")

    app = crear_app()
    uvicorn.run(app, host=host, port=puerto_http)


if __name__ == "__main__":
    main()
