#!/usr/bin/env python3
"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Sesión automática en tu cuenta de ZCode System (VIP Club), en tu PC.

Lee ZCODE_USERNAME y ZCODE_PASSWORD del archivo .env (nunca del código), inicia sesión
con un navegador Chromium, guarda la sesión para no repetir el login y descarga las
páginas indicadas (HTML + captura) en pc/zcode/. En modo bucle vuelve a descargarlas
cada N minutos y repite el login si la sesión caduca.

    python pc/zcode_sesion.py                 # una vez
    python pc/zcode_sesion.py --visible       # ver el navegador (útil la primera vez)
    python pc/zcode_sesion.py --bucle 30      # cada 30 minutos

Requisitos (una vez):  pip install playwright python-dotenv && python -m playwright install chromium

Uso personal de tu propia suscripción. Revisa las condiciones de ZCode: no redistribuyas
su contenido y mantén una frecuencia baja de consultas.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUT = HERE / "zcode"
STATE = HERE / ".zcode_state.json"   # cookies de sesión (excluido de git)

LOGIN_URL = os.getenv("ZCODE_LOGIN_URL", "https://zcodesystem.com/vipclub/overview.php")
DEFAULT_PAGES = ["https://zcodesystem.com/vipclub/overview.php"]


def say(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO / ".env")


def credentials() -> tuple[str, str]:
    user, pwd = os.getenv("ZCODE_USERNAME", ""), os.getenv("ZCODE_PASSWORD", "")
    if not user or not pwd:
        say("Faltan ZCODE_USERNAME / ZCODE_PASSWORD en el archivo .env de la carpeta del proyecto.")
        sys.exit(1)
    return user, pwd


def looks_logged_out(page) -> bool:
    """Hay un campo de contraseña visible = estamos en una pantalla de login."""
    try:
        return page.locator("input[type=password]").first.is_visible(timeout=1500)
    except Exception:  # noqa: BLE001
        return False


def login(page, user: str, pwd: str) -> bool:
    say("Iniciando sesión…")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    if not looks_logged_out(page):
        return True
    password = page.locator("input[type=password]").first
    form = password.locator("xpath=ancestor::form[1]")
    scope = form if form.count() else page
    # Campo de usuario: el primer email/texto visible del mismo formulario.
    username = scope.locator(
        "input[type=email], input[name*=user i], input[name*=login i], input[name*=mail i], input[type=text]"
    ).first
    username.fill(user)
    password.fill(pwd)
    submit = scope.locator("button[type=submit], input[type=submit], button:has-text('Log'), button:has-text('Sign')").first
    if submit.count():
        submit.click()
    else:
        password.press("Enter")
    page.wait_for_load_state("networkidle", timeout=30_000)
    ok = not looks_logged_out(page)
    say("Sesión iniciada." if ok else "No se pudo iniciar sesión: revisa usuario/contraseña o si pide captcha (usa --visible).")
    return ok


def snapshot(page, url: str) -> None:
    page.goto(url, wait_until="networkidle")
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    name = url.rstrip("/").rsplit("/", 1)[-1].replace(".php", "") or "inicio"
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}-{stamp}.html").write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(OUT / f"{name}-{stamp}.png"), full_page=True)
    (OUT / f"{name}-ultimo.html").write_text(page.content(), encoding="utf-8")
    say(f"Guardado {name} ({page.title()!r})")


def run_once(pw, pages: list[str], visible: bool) -> bool:
    user, pwd = credentials()
    browser = pw.chromium.launch(headless=not visible)
    ctx = browser.new_context(storage_state=str(STATE) if STATE.exists() else None,
                              locale="es-ES", viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    try:
        page.goto(pages[0], wait_until="domcontentloaded")
        if looks_logged_out(page) and not login(page, user, pwd):
            return False
        ctx.storage_state(path=str(STATE))
        for url in pages:
            snapshot(page, url)
            time.sleep(3)  # sin prisas entre páginas
        return True
    finally:
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Sesión automática ZCode System")
    ap.add_argument("--visible", action="store_true", help="muestra el navegador")
    ap.add_argument("--bucle", type=int, default=0, metavar="MIN", help="repetir cada MIN minutos (mínimo 15)")
    ap.add_argument("--pagina", action="append", help="URL adicional a guardar (repetible)")
    args = ap.parse_args()
    load_env()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        say("Instala Playwright: pip install playwright && python -m playwright install chromium")
        return 1
    pages = DEFAULT_PAGES + (args.pagina or [])
    interval = max(args.bucle, 15) * 60 if args.bucle else 0
    with sync_playwright() as pw:
        while True:
            try:
                run_once(pw, pages, args.visible)
            except Exception as e:  # noqa: BLE001 - red caída, cambio en la web…: seguir en bucle
                say(f"Error: {e}")
            if not interval:
                return 0
            say(f"Próxima consulta en {interval // 60} min (Ctrl+C para parar).")
            time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
