"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Cliente de tu suscripción ZCode System: inicia sesión con ZCODE_USERNAME / ZCODE_PASSWORD
del archivo .env, conserva la sesión y lee las páginas del área de miembros como texto
limpio (títulos, tablas y enlaces) para que Claude pueda analizarlas.

Lo usan pc/zcode_mcp.py (herramientas para la app de Claude) y pc/zcode_sesion.py (bucle).
Uso personal de tu propia suscripción: consultas espaciadas y sin redistribuir contenido.
"""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUT = HERE / "zcode"
STATE = HERE / ".zcode_state.json"   # cookies de sesión (excluido de git)

DEFAULT_START = "https://zcodesystem.com/vipclub/overview.php"
PAGE_DELAY = 2.5                     # segundos entre páginas: no saturar el sitio
SKIP_LINK = re.compile(r"logout|log-out|signout|sign-out|unsubscribe|cancel|delete|billing|payment|checkout",
                       re.I)

# JavaScript que convierte la página en texto legible y tablas en filas.
_EXTRACT_JS = r"""
() => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const tables = [...document.querySelectorAll('table')].slice(0, 40).map(t =>
    [...t.querySelectorAll('tr')].slice(0, 300).map(r =>
      [...r.querySelectorAll('th,td')].map(c => clean(c.innerText))
    ).filter(r => r.some(c => c))
  ).filter(t => t.length);
  const links = [...document.querySelectorAll('a[href]')].map(a => ({
    text: clean(a.innerText).slice(0, 120), href: a.href
  })).filter(l => l.href.startsWith('http'));
  const headings = [...document.querySelectorAll('h1,h2,h3')].map(h => clean(h.innerText)).filter(Boolean);
  return { title: document.title, text: document.body ? document.body.innerText : '',
           tables, links, headings };
}
"""


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO / ".env")


class ZCodeError(RuntimeError):
    pass


class ZCodeClient:
    """Navegador Chromium con la sesión de ZCode. Usar con `async with ZCodeClient() as z:`."""

    def __init__(self, visible: bool = False):
        load_env()
        self.visible = visible
        self.start_url = os.getenv("ZCODE_LOGIN_URL", DEFAULT_START)
        self.user = os.getenv("ZCODE_USERNAME", "")
        self.password = os.getenv("ZCODE_PASSWORD", "")
        self._pw = self._browser = self._ctx = self._page = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ ciclo de vida
    async def __aenter__(self) -> "ZCodeClient":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def start(self) -> None:
        if self._page:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise ZCodeError("Falta Playwright: pip install playwright && python -m playwright install chromium") from e
        self._pw = await async_playwright().start()
        exe = os.getenv("ZCODE_CHROMIUM_PATH") or None
        self._browser = await self._pw.chromium.launch(headless=not self.visible, executable_path=exe)
        self._ctx = await self._browser.new_context(
            storage_state=str(STATE) if STATE.exists() else None,
            locale="es-ES", viewport={"width": 1366, "height": 900})
        self._page = await self._ctx.new_page()

    async def close(self) -> None:
        for obj in (self._ctx, self._browser):
            try:
                if obj:
                    await obj.close()
            except Exception:  # noqa: BLE001
                pass
        if self._pw:
            await self._pw.stop()
        self._pw = self._browser = self._ctx = self._page = None

    # ------------------------------------------------------------------ sesión
    async def _logged_out(self) -> bool:
        try:
            return await self._page.locator("input[type=password]").first.is_visible(timeout=1500)
        except Exception:  # noqa: BLE001
            return False

    async def login(self, force: bool = False) -> bool:
        """Entra en ZCode si hace falta. Devuelve True si queda la sesión iniciada."""
        if not self.user or not self.password:
            raise ZCodeError("Faltan ZCODE_USERNAME / ZCODE_PASSWORD en el archivo .env del proyecto.")
        page = self._page
        await page.goto(self.start_url, wait_until="domcontentloaded")
        if not force and not await self._logged_out():
            return True
        password = page.locator("input[type=password]").first
        form = password.locator("xpath=ancestor::form[1]")
        scope = form if await form.count() else page
        username = scope.locator(
            "input[type=email], input[name*=user i], input[name*=login i], input[name*=mail i], "
            "input[id*=user i], input[id*=mail i], input[type=text]").first
        await username.fill(self.user)
        await password.fill(self.password)
        submit = scope.locator("button[type=submit], input[type=submit], button:has-text('Log'), "
                               "button:has-text('Sign'), button:has-text('Entrar')").first
        if await submit.count():
            await submit.click()
        else:
            await password.press("Enter")
        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:  # noqa: BLE001 - algunas webs nunca quedan "idle"
            pass
        ok = not await self._logged_out()
        if ok:
            await self._ctx.storage_state(path=str(STATE))
        return ok

    # ------------------------------------------------------------------ lectura
    async def read(self, url: str | None = None, save: bool = True) -> dict:
        """Abre una página del área de miembros (relogin automático) y devuelve su contenido."""
        async with self._lock:
            url = urljoin(self.start_url, url) if url else self.start_url
            page = self._page
            await page.goto(url, wait_until="domcontentloaded")
            if await self._logged_out():
                if not await self.login():
                    raise ZCodeError("No se pudo iniciar sesión (revisa usuario/contraseña, o si pide captcha "
                                     "ejecuta: python pc/zcode_sesion.py --visible).")
                await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:  # noqa: BLE001
                pass
            data = await page.evaluate(_EXTRACT_JS)
            data["url"] = page.url
            data["read_at"] = datetime.now().isoformat(timespec="seconds")
            host = urlparse(self.start_url).netloc
            data["links"] = [l for l in data["links"] if urlparse(l["href"]).netloc == host]
            if save:
                self._save(page.url, await page.content())
            return data

    async def crawl(self, start: str | None = None, max_pages: int = 25, prefix: str | None = None) -> list[dict]:
        """Lee la página inicial y sigue los enlaces internos del área de miembros (máx. max_pages)."""
        start_url = urljoin(self.start_url, start) if start else self.start_url
        prefix = prefix or start_url.rsplit("/", 1)[0] + "/"
        queue, seen, pages = [start_url], set(), []
        while queue and len(pages) < max_pages:
            url = queue.pop(0).split("#")[0]
            if url in seen:
                continue
            seen.add(url)
            try:
                data = await self.read(url)
            except ZCodeError:
                raise
            except Exception as e:  # noqa: BLE001 - una página rota no detiene el resto
                pages.append({"url": url, "error": str(e)})
                continue
            pages.append(data)
            for link in data["links"]:
                href = link["href"].split("#")[0]
                if href.startswith(prefix) and href not in seen and not SKIP_LINK.search(href):
                    queue.append(href)
            await asyncio.sleep(PAGE_DELAY)
        return pages

    @staticmethod
    def _save(url: str, html: str) -> None:
        OUT.mkdir(exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9_-]+", "_", urlparse(url).path.strip("/") or "inicio")[:80]
        (OUT / f"{name}.html").write_text(html, encoding="utf-8")


def as_markdown(data: dict, max_chars: int = 15_000) -> str:
    """Resumen legible de una página para Claude: texto, tablas y enlaces internos."""
    if data.get("error"):
        return f"## {data['url']}\nError: {data['error']}\n"
    out = [f"## {data.get('title') or data['url']}", f"URL: {data['url']} · leído {data.get('read_at', '')}", ""]
    text = re.sub(r"\n{3,}", "\n\n", data.get("text", "")).strip()
    out.append(text[:max_chars] + ("\n…(recortado)" if len(text) > max_chars else ""))
    for i, table in enumerate(data.get("tables", [])[:15], 1):
        out += ["", f"### Tabla {i}"]
        for row in table[:120]:
            out.append("| " + " | ".join(c.replace("|", "/") for c in row) + " |")
    links = data.get("links", [])[:60]
    if links:
        out += ["", "### Enlaces del área de miembros"]
        out += [f"- {l['text'] or '(sin texto)'}: {l['href']}" for l in links]
    return "\n".join(out)
