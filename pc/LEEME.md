# Conectar AKERATEN a tu PC

Tu PC hace de servidor: ejecuta el backend (modelos, cuotas, value bets) y la app Android
y el dashboard web se conectan a él. El PC guarda las claves de las APIs; el móvil no.

## 1. Arrancar el servidor en bucle

**Windows:** doble clic en `pc\INICIAR_AKERATEN.bat`

**macOS / Linux:** `./pc/iniciar_akeraten.sh`

La primera vez crea un entorno `.venv`, instala dependencias y copia `.env.example` a `.env`
(ahí pones tus claves; sin claves funciona en modo DEMO). Después:

- arranca el backend en `0.0.0.0:8000`;
- comprueba `/api/health` cada 10 s y **lo reinicia solo** si se cae o se bloquea
  (espera 2 s, 4 s, 8 s… hasta 60 s entre reintentos);
- anuncia el PC en la Wi-Fi (UDP 47800) para que la app lo encuentre sola;
- muestra las direcciones y un código QR para abrir el dashboard en el móvil;
- guarda el registro en `pc/logs/`.

Ctrl+C lo detiene.

Si Windows pregunta por el firewall, marca **Redes privadas** y acepta.

## 2. Conectar el móvil

1. Móvil y PC en la **misma Wi-Fi**.
2. Abre la app. Si no encuentra el servidor, vuelve a buscar el PC en cada reintento (de 2 a 30 s).
3. O ve a **Ajustes → Buscar mi PC**: escucha el aviso del PC y, si el router lo bloquea,
   prueba las 254 direcciones de tu red en el puerto 8000.
4. También puedes escribir la URL a mano (la que muestra la ventana del PC, p. ej.
   `http://192.168.1.20:8000/`).

Dashboard web en el móvil: abre esa misma URL en el navegador o escanea el QR.

## 3. Fuera de casa (opcional)

Instala [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) y arranca con:

```
pc\INICIAR_AKERATEN.bat --tunnel        (Windows)
./pc/iniciar_akeraten.sh --tunnel       (macOS / Linux)
```

Aparece una URL `https://….trycloudflare.com`. Ponla en la app (**Ajustes → URL del backend**).
Esa URL cambia en cada arranque y cualquiera que la tenga ve tu dashboard; no la compartas.

## 4. Arranque automático con el PC (opcional)

**Windows:** pulsa `Win+R`, escribe `shell:startup` y crea ahí un acceso directo a
`INICIAR_AKERATEN.bat`.

**Linux (systemd de usuario):**

```
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/akeraten.service <<EOF
[Unit]
Description=AKERATEN
[Service]
ExecStart=%h/akera.predictor/pc/iniciar_akeraten.sh
Restart=always
[Install]
WantedBy=default.target
EOF
systemctl --user enable --now akeraten
```

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| La app sigue en "MODO DEMO SIN CONEXIÓN" | Misma Wi-Fi; firewall en "Redes privadas"; prueba la URL del PC en el navegador del móvil |
| "Buscar mi PC" no lo encuentra | Algunas Wi-Fi de invitados aíslan dispositivos: usa la red principal o `--tunnel` |
| Puerto ocupado | `INICIAR_AKERATEN.bat --port 8080` y pon ese puerto en la URL de la app |
| No arranca | Mira `pc/logs/backend.log` |

## ZCode System (sesión automática)

1. En el archivo `.env` de tu PC rellena `ZCODE_USERNAME` y `ZCODE_PASSWORD`. Ese archivo no se sube nunca a GitHub.
2. Una vez: `.venv\Scripts\python -m pip install playwright` y `.venv\Scripts\python -m playwright install chromium`.
3. Primera vez, viendo el navegador: `.venv\Scripts\python pc\zcode_sesion.py --visible`
4. En bucle cada 30 min: `.venv\Scripts\python pc\zcode_sesion.py --bucle 30`

Guarda la sesión (no repite el login) y descarga las páginas en `pc/zcode/` (HTML + captura).
Todavía no extrae los pronósticos: falta ver la estructura real de las páginas una vez dentro.
Es para uso personal de tu suscripción; respeta las condiciones de ZCode.
