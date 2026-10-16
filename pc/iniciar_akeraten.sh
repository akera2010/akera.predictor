#!/usr/bin/env bash
# AKERATEN v.0.1 - Sandra Blanco (España | 2026)
# Arranca el backend en tu PC (macOS / Linux) y lo deja en bucle.
#   ./pc/iniciar_akeraten.sh            red local
#   ./pc/iniciar_akeraten.sh --tunnel   + URL https pública (cloudflared)
set -euo pipefail
cd "$(dirname "$0")/.."

PY=$(command -v python3 || command -v python || true)
[ -n "$PY" ] || { echo "Instala Python 3.11+ (https://www.python.org/downloads/)"; exit 1; }

[ -x .venv/bin/python ] || { echo "Creando entorno virtual .venv ..."; "$PY" -m venv .venv; }
VPY=.venv/bin/python
if ! cmp -s backend/requirements.txt .venv/.req_installed; then
  echo "Instalando dependencias ..."
  "$VPY" -m pip install --upgrade pip >/dev/null
  "$VPY" -m pip install -r backend/requirements.txt qrcode
  cp backend/requirements.txt .venv/.req_installed
fi
[ -f .env ] || { [ -f .env.example ] && cp .env.example .env; }

exec "$VPY" pc/run_pc.py "$@"
