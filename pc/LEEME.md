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

## ZCode System en la app de Claude

Un servidor MCP (`pc/zcode_mcp.py`) que corre en tu PC permite que Claude Desktop o Claude Code
entren en tu suscripción y lean su contenido. Tus credenciales se quedan en el `.env` de tu PC.

**Instalación (una vez), desde la carpeta `akera.predictor`:**

```
py pc\instalar_zcode_claude.py          (Windows)
python3 pc/instalar_zcode_claude.py     (macOS / Linux)
```

El instalador:
1. te pide usuario y contraseña de ZCode y los guarda en `.env` (la contraseña no se ve al escribir);
2. instala Playwright, Chromium y el SDK de MCP en `.venv`;
3. registra el servidor `zcode` en Claude Desktop y, si lo tienes, en Claude Code.

Cierra Claude Desktop del todo y vuelve a abrirlo. Después puedes pedirle, por ejemplo:
- «Usa zcode_leer_todo y resúmeme los pronósticos de tenis de hoy»
- «Lee la página de picks de ZCode y compárala con las value bets de AKERATEN»
- «Busca en ZCode todo lo que haya sobre Sinner»

| Herramienta | Qué hace |
|---|---|
| `zcode_login` | Inicia sesión (o confirma que ya está iniciada) |
| `zcode_leer_pagina` | Lee una página (por defecto el resumen del VIP Club): texto, tablas y enlaces |
| `zcode_leer_todo` | Recorre el área de miembros (hasta 60 páginas, con pausa entre ellas) |
| `zcode_buscar` | Busca un jugador, equipo o torneo en lo ya leído |

Nunca sigue enlaces de cerrar sesión, pagos ni bajas. Si ZCode pide captcha, entra una vez con
`.venv\Scripts\python pc\zcode_sesion.py --visible`; la sesión queda guardada.

**Sin Claude, desde la terminal:** `.venv\Scripts\python pc\zcode_sesion.py --todo` guarda todo en
`pc/zcode/ultimo.md` (`--bucle 30` para repetir cada 30 min).

Es para uso personal de tu suscripción: respeta las condiciones de ZCode y no compartas su contenido.
