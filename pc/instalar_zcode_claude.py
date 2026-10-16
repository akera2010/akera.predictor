#!/usr/bin/env python3
"""AKERATEN v.0.1 · Sandra Blanco (España | 2026)

Configura en tu PC todo lo necesario para que la app de Claude lea tu suscripción ZCode:

  1. Te pide usuario y contraseña de ZCode (la contraseña no se ve al escribir) y los guarda
     en el archivo .env del proyecto (nunca se sube a GitHub).
  2. Instala Playwright + Chromium y el SDK de MCP en el entorno .venv.
  3. Registra el servidor "zcode" en Claude Desktop (claude_desktop_config.json) y, si tienes
     Claude Code, también con `claude mcp add`.

Uso (desde la carpeta akera.predictor):
    Windows:      py pc\\instalar_zcode_claude.py
    macOS/Linux:  python3 pc/instalar_zcode_claude.py
"""
from __future__ import annotations

import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
VENV = REPO / ".venv"
SERVER = REPO / "pc" / "zcode_mcp.py"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def write_env(user: str, password: str) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(("ZCODE_USERNAME=", "ZCODE_PASSWORD="))]
    lines += [f"ZCODE_USERNAME={user}", f"ZCODE_PASSWORD={password}"]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name != "nt":
        ENV.chmod(0o600)


def ask_credentials() -> None:
    step("Credenciales de ZCode (se guardan solo en tu PC, en .env)")
    current = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    if "ZCODE_USERNAME=" in current and "ZCODE_PASSWORD=" in current:
        if input("Ya hay credenciales guardadas. ¿Cambiarlas? [s/N]: ").strip().lower() not in ("s", "si", "sí"):
            return
    user = input("Usuario / email de ZCode: ").strip()
    password = getpass.getpass("Contraseña de ZCode (no se verá al escribir): ")
    if not user or not password:
        sys.exit("Usuario y contraseña son obligatorios.")
    write_env(user, password)
    print(f"Guardado en {ENV}")


def ensure_venv() -> None:
    step("Preparando el entorno Python (.venv)")
    if not venv_python().exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    py = str(venv_python())
    subprocess.check_call([py, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    subprocess.check_call([py, "-m", "pip", "install", "-q", "mcp>=1.10,<2", "playwright", "python-dotenv"])
    step("Descargando Chromium para Playwright (solo la primera vez)")
    subprocess.check_call([py, "-m", "playwright", "install", "chromium"])


def desktop_config_path() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def register_desktop() -> None:
    step("Registrando el servidor 'zcode' en Claude Desktop")
    cfg_path = desktop_config_path()
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            backup = cfg_path.with_suffix(".json.bak")
            shutil.copy(cfg_path, backup)
            print(f"El archivo tenía errores; copia de seguridad en {backup}")
        else:
            shutil.copy(cfg_path, cfg_path.with_suffix(".json.bak"))
    cfg.setdefault("mcpServers", {})["zcode"] = {"command": str(venv_python()), "args": [str(SERVER)]}
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Configurado: {cfg_path}")


def register_claude_code() -> None:
    claude = shutil.which("claude")
    if not claude:
        return
    step("Registrando el servidor 'zcode' en Claude Code")
    subprocess.call([claude, "mcp", "remove", "zcode", "-s", "user"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc = subprocess.call([claude, "mcp", "add", "zcode", "-s", "user", "--", str(venv_python()), str(SERVER)])
    print("Listo en Claude Code." if rc == 0 else "No se pudo registrar en Claude Code (hazlo a mano, ver pc/LEEME.md).")


def main() -> None:
    print("AKERATEN v.0.1 · Conectar ZCode con la app de Claude")
    ask_credentials()
    ensure_venv()
    register_desktop()
    register_claude_code()
    print("\n✔ Hecho. Cierra Claude Desktop del todo y vuelve a abrirlo.\n"
          "  Luego pídele: «Usa zcode_leer_todo y resúmeme los pronósticos de tenis de hoy».")


if __name__ == "__main__":
    main()
