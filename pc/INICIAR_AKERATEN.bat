@echo off
REM AKERATEN v.0.1 - Sandra Blanco (Espana | 2026)
REM Doble clic para arrancar el backend en tu PC y dejarlo en bucle.
REM Opcional: INICIAR_AKERATEN.bat --tunnel   (URL https publica con cloudflared)
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% --version >nul 2>nul || (
  echo No encuentro Python. Instala Python 3.11+ desde https://www.python.org/downloads/
  echo y marca "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual .venv ...
  %PY% -m venv .venv || (pause & exit /b 1)
)
set "VPY=.venv\Scripts\python.exe"

REM Reinstala dependencias solo si requirements.txt ha cambiado
fc /b backend\requirements.txt .venv\.req_installed >nul 2>nul || (
  echo Instalando dependencias ...
  "%VPY%" -m pip install --upgrade pip >nul
  "%VPY%" -m pip install -r backend\requirements.txt qrcode || (pause & exit /b 1)
  copy /y backend\requirements.txt .venv\.req_installed >nul
)

if not exist ".env" if exist ".env.example" copy .env.example .env >nul

REM Abre el puerto en el firewall de Windows (necesita admin; si falla, Windows preguntara al arrancar)
netsh advfirewall firewall show rule name="AKERATEN 8000" >nul 2>nul || (
  netsh advfirewall firewall add rule name="AKERATEN 8000" dir=in action=allow protocol=TCP localport=8000 profile=private >nul 2>nul
  netsh advfirewall firewall add rule name="AKERATEN discovery" dir=out action=allow protocol=UDP remoteport=47800 profile=private >nul 2>nul
)

"%VPY%" pc\run_pc.py %*
pause
