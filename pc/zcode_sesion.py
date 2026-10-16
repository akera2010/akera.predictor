#!/usr/bin/env python3
"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Lee tu suscripción ZCode System desde la terminal, una vez o en bucle, y guarda las páginas
en pc/zcode/ (HTML) y pc/zcode/ultimo.md (texto legible).

    python pc/zcode_sesion.py                 # una vez
    python pc/zcode_sesion.py --visible       # ver el navegador (útil si pide captcha)
    python pc/zcode_sesion.py --todo          # recorrer todo el área de miembros
    python pc/zcode_sesion.py --bucle 30      # repetir cada 30 minutos (mínimo 15)

Credenciales: ZCODE_USERNAME / ZCODE_PASSWORD en .env (las guarda pc/instalar_zcode_claude.py).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zcode_core import OUT, ZCodeClient, ZCodeError, as_markdown  # noqa: E402


def say(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def run_once(visible: bool, todo: bool, max_pages: int) -> None:
    async with ZCodeClient(visible=visible) as z:
        if not await z.login():
            raise ZCodeError("No se pudo iniciar sesión (usa --visible si la web pide captcha).")
        say("Sesión iniciada.")
        pages = await z.crawl(max_pages=max_pages) if todo else [await z.read()]
    OUT.mkdir(exist_ok=True)
    md = "\n\n---\n\n".join(as_markdown(p) for p in pages)
    (OUT / "ultimo.md").write_text(md, encoding="utf-8")
    say(f"{len(pages)} página(s) leídas → {OUT / 'ultimo.md'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lectura de ZCode System")
    ap.add_argument("--visible", action="store_true", help="muestra el navegador")
    ap.add_argument("--todo", action="store_true", help="recorre todo el área de miembros")
    ap.add_argument("--max", type=int, default=20, help="máximo de páginas con --todo")
    ap.add_argument("--bucle", type=int, default=0, metavar="MIN", help="repetir cada MIN minutos (mínimo 15)")
    args = ap.parse_args()
    interval = max(args.bucle, 15) * 60 if args.bucle else 0
    while True:
        try:
            asyncio.run(run_once(args.visible, args.todo, args.max))
        except ZCodeError as e:
            say(f"Error: {e}")
            if not interval:
                return 1
        except Exception as e:  # noqa: BLE001 - red caída, cambios en la web… seguir en bucle
            say(f"Error inesperado: {e}")
        if not interval:
            return 0
        say(f"Próxima lectura en {interval // 60} min (Ctrl+C para parar).")
        try:
            asyncio.run(asyncio.sleep(interval))
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
