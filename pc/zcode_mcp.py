#!/usr/bin/env python3
"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Servidor MCP para que la app de Claude (Claude Desktop o Claude Code) entre en tu
suscripción ZCode System y lea su contenido. Se ejecuta en TU PC; las credenciales salen
del archivo .env (ZCODE_USERNAME / ZCODE_PASSWORD) y nunca pasan por el chat.

Instalación automática en Claude Desktop:  python pc/instalar_zcode_claude.py
Claude Code:  claude mcp add zcode -- <ruta>/.venv/Scripts/python.exe <ruta>/pc/zcode_mcp.py

Herramientas:
  zcode_login           inicia sesión (o confirma que ya está iniciada)
  zcode_leer_pagina     lee una página concreta (por defecto, el resumen del VIP Club)
  zcode_leer_todo       recorre el área de miembros y devuelve todo su contenido
  zcode_buscar          busca un texto (jugador, equipo, deporte…) en lo leído
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402  (pip install "mcp>=1.10,<2")

from zcode_core import ZCodeClient, ZCodeError, as_markdown  # noqa: E402

mcp = FastMCP("zcode")
_client: ZCodeClient | None = None
_cache: dict[str, dict] = {}   # url -> última lectura (para zcode_buscar)


async def client() -> ZCodeClient:
    global _client
    if _client is None:
        _client = ZCodeClient()
        await _client.start()
    return _client


@mcp.tool()
async def zcode_login() -> str:
    """Inicia sesión en ZCode System con las credenciales del archivo .env del PC."""
    try:
        z = await client()
        ok = await z.login()
    except ZCodeError as e:
        return f"Error: {e}"
    return "Sesión iniciada en ZCode." if ok else (
        "No se pudo iniciar sesión. Revisa ZCODE_USERNAME/ZCODE_PASSWORD en .env; si la web pide captcha, "
        "ejecuta una vez `python pc/zcode_sesion.py --visible` y completa el login a mano.")


@mcp.tool()
async def zcode_leer_pagina(url: str = "") -> str:
    """Lee una página del área de miembros de ZCode y devuelve su texto, tablas y enlaces.

    url: dirección completa o relativa (p. ej. 'overview.php'). Vacío = página de resumen del VIP Club.
    """
    try:
        data = await (await client()).read(url or None)
    except ZCodeError as e:
        return f"Error: {e}"
    _cache[data["url"]] = data
    return as_markdown(data)


@mcp.tool()
async def zcode_leer_todo(max_paginas: int = 20) -> str:
    """Recorre el área de miembros del VIP Club siguiendo sus enlaces internos y devuelve todo
    lo leído. Espera unos segundos entre páginas. max_paginas: límite (1-60)."""
    max_paginas = max(1, min(int(max_paginas), 60))
    try:
        pages = await (await client()).crawl(max_pages=max_paginas)
    except ZCodeError as e:
        return f"Error: {e}"
    for p in pages:
        if "url" in p and not p.get("error"):
            _cache[p["url"]] = p
    budget = max(3_000, 120_000 // max(len(pages), 1))
    body = "\n\n---\n\n".join(as_markdown(p, max_chars=budget) for p in pages)
    return f"# ZCode VIP Club · {len(pages)} páginas leídas\n\n{body}"


@mcp.tool()
async def zcode_buscar(texto: str) -> str:
    """Busca un texto (jugador, equipo, torneo, deporte…) en las páginas de ZCode ya leídas
    con zcode_leer_pagina o zcode_leer_todo. Devuelve las líneas y filas de tabla que coinciden."""
    needle = texto.strip().lower()
    if not needle:
        return "Indica qué buscar."
    if not _cache:
        return "Aún no hay páginas leídas: usa primero zcode_leer_todo o zcode_leer_pagina."
    hits: list[str] = []
    for url, page in _cache.items():
        for line in page.get("text", "").splitlines():
            if needle in line.lower():
                hits.append(f"[{url}] {line.strip()}")
        for table in page.get("tables", []):
            header = table[0] if table else []
            for row in table[1:]:
                if any(needle in c.lower() for c in row):
                    hits.append(f"[{url}] " + " | ".join(f"{h}: {c}" if h else c for h, c in zip(header, row)))
    return "\n".join(hits[:200]) if hits else f"No aparece «{texto}» en las {len(_cache)} páginas leídas."


if __name__ == "__main__":
    mcp.run()
