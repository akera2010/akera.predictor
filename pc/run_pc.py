#!/usr/bin/env python3
"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Bucle de servicio para tu PC: arranca el backend, lo vigila y lo reinicia si se cae,
para que la app Android (y el dashboard web) se conecten siempre a tu ordenador.

    python pc/run_pc.py                 # red local (Wi-Fi de casa)
    python pc/run_pc.py --tunnel        # además, URL https pública vía cloudflared
    python pc/run_pc.py --port 8080

Solo usa la biblioteca estándar de Python (qrcode es opcional).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
LOG_DIR = Path(__file__).resolve().parent / "logs"

HEALTH_EVERY = 10        # segundos entre comprobaciones de salud
MAX_FAILED_CHECKS = 3    # fallos seguidos antes de reiniciar
BACKOFF_MIN, BACKOFF_MAX = 2, 60

stop_requested = threading.Event()


def say(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with open(LOG_DIR / "akeraten-pc.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def health(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=4) as r:
            return json.loads(r.read().decode())
    except Exception:  # noqa: BLE001 - any failure means "not healthy"
        return None


def lan_urls(port: int) -> list[str]:
    sys.path.insert(0, str(BACKEND))
    try:
        from akeraten.discovery import lan_ips
        return [f"http://{ip}:{port}/" for ip in lan_ips()]
    except Exception:  # noqa: BLE001
        return []


def print_qr(url: str) -> None:
    try:
        import qrcode  # opcional: pip install qrcode
    except ImportError:
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.print_ascii(invert=True)


def banner(port: int, tunnel_url: str | None) -> None:
    urls = lan_urls(port)
    print("\n" + "=" * 62)
    print("  AKERATEN v.0.1  ·  Sandra Blanco (España | 2026)")
    print("=" * 62)
    print(f"  En este PC:        http://localhost:{port}/")
    for u in urls:
        print(f"  Móvil (misma Wi-Fi): {u}")
    if tunnel_url:
        print(f"  Desde cualquier red: {tunnel_url}")
    print("  La app Android encuentra este PC sola (Ajustes → Buscar mi PC).")
    print("  Ctrl+C para parar.")
    print("=" * 62 + "\n", flush=True)
    target = tunnel_url or (urls[0] if urls else None)
    if target:
        print_qr(target)


def start_backend(port: int) -> subprocess.Popen:
    env = dict(os.environ, AKERATEN_PORT=str(port), PYTHONUNBUFFERED="1")
    LOG_DIR.mkdir(exist_ok=True)
    out = open(LOG_DIR / "backend.log", "a", encoding="utf-8")
    cmd = [sys.executable, "-m", "uvicorn", "akeraten.main:app", "--host", "0.0.0.0", "--port", str(port)]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(cmd, cwd=BACKEND, env=env, stdout=out, stderr=subprocess.STDOUT,
                            creationflags=flags)


def stop_process(p: subprocess.Popen | None) -> None:
    if p is None or p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=8)
    except subprocess.TimeoutExpired:
        p.kill()


class Tunnel:
    """Túnel https gratuito de Cloudflare (no necesita cuenta). Se reinicia si se cae."""

    URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def __init__(self, port: int):
        self.port = port
        self.url: str | None = None
        self.proc: subprocess.Popen | None = None
        self.exe = shutil.which("cloudflared")

    def ensure(self) -> None:
        if not self.exe or (self.proc and self.proc.poll() is None):
            return
        self.url = None
        self.proc = subprocess.Popen(
            [self.exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{self.port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            m = self.URL_RE.search(line)
            if m and not self.url:
                self.url = m.group(0)
                say(f"Túnel público activo: {self.url}  (ponlo en la app: Ajustes → URL del backend)")

    def stop(self) -> None:
        stop_process(self.proc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Bucle de servicio AKERATEN para tu PC")
    ap.add_argument("--port", type=int, default=int(os.getenv("AKERATEN_PORT", "8000")))
    ap.add_argument("--tunnel", action="store_true", help="publica una URL https con cloudflared")
    args = ap.parse_args()

    def _sig(*_):
        stop_requested.set()
    signal.signal(signal.SIGINT, _sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sig)

    tunnel = Tunnel(args.port) if args.tunnel else None
    if tunnel and not tunnel.exe:
        say("cloudflared no está instalado: sigo solo en red local. "
            "Instálalo desde https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        tunnel = None

    backoff = BACKOFF_MIN
    restarts = 0
    while not stop_requested.is_set():
        if health(args.port):
            say(f"Ya hay un AKERATEN respondiendo en el puerto {args.port}; lo vigilo sin arrancar otro.")
            proc = None
        else:
            say(f"Arrancando backend en el puerto {args.port}…" + (f" (reinicio #{restarts})" if restarts else ""))
            proc = start_backend(args.port)

        # Espera a que responda (máx. 60 s)
        ready = False
        for _ in range(60):
            if stop_requested.is_set() or (proc and proc.poll() is not None):
                break
            if health(args.port):
                ready = True
                break
            time.sleep(1)

        if ready:
            info = health(args.port) or {}
            say(f"Backend listo · modo {str(info.get('mode', '?')).upper()} · "
                f"{info.get('n_matches', 0)} partidos · {info.get('n_value_bets', 0)} value bets")
            if tunnel:
                tunnel.ensure()
                for _ in range(20):
                    if tunnel.url:
                        break
                    time.sleep(1)
            banner(args.port, tunnel.url if tunnel else None)
            backoff = BACKOFF_MIN

            # Bucle de vigilancia
            failed = 0
            while not stop_requested.is_set():
                stop_requested.wait(HEALTH_EVERY)
                if stop_requested.is_set():
                    break
                if proc and proc.poll() is not None:
                    say(f"El backend se ha cerrado (código {proc.returncode}).")
                    break
                if health(args.port):
                    failed = 0
                else:
                    failed += 1
                    say(f"Sin respuesta ({failed}/{MAX_FAILED_CHECKS})…")
                    if failed >= MAX_FAILED_CHECKS:
                        say("Backend bloqueado: reiniciando.")
                        break
                if tunnel:
                    tunnel.ensure()  # relanza el túnel si se ha caído
        else:
            if not stop_requested.is_set():
                say(f"No arrancó. Revisa {LOG_DIR / 'backend.log'}")

        stop_process(proc)
        if stop_requested.is_set():
            break
        restarts += 1
        say(f"Reintento en {backoff} s…")
        stop_requested.wait(backoff)
        backoff = min(backoff * 2, BACKOFF_MAX)

    if tunnel:
        tunnel.stop()
    say("AKERATEN detenido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
