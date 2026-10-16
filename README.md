# AKERATEN v.0.1

**Sandra Blanco (España | 2026)**

Monitor en tiempo real de partidos de **tenis** (ATP, WTA, Challenger, ITF) y **tenis de mesa** (WTT, ITTF, ligas) que detecta **apuestas de valor**: compara la probabilidad propia (ensemble Elo + ML + Monte Carlo + consenso de expertos) con las cuotas de las casas y propone un stake **Half-Kelly** con nivel de confianza.

> ⚠️ Herramienta de análisis estadístico. **No se garantizan ganancias.** Apostar implica riesgo de pérdida. Solo +18. Juega con responsabilidad.

## Componentes

| Carpeta | Qué es |
|---|---|
| [`backend/`](backend/README.md) | Python + FastAPI: ingesta de 8 APIs, expert tracker, modelos, value detector, scheduler, REST + WebSocket |
| [`web/`](web/index.html) | Dashboard web (se sirve en `/` desde el backend, o funciona solo con simulador integrado) |
| [`android/`](android/aptoide/PUBLISHING.md) | App Android Kotlin + Jetpack Compose (Material 3), lista para Aptoide |
| [`pc/`](pc/LEEME.md) | Bucle para tu PC: arranca y vigila el backend, lo reinicia si cae y lo anuncia en la Wi-Fi para que la app lo encuentre sola |
| `.mcp.json` | Servidores MCP de datos deportivos para Claude Code |
| `.github/workflows/` | CI: tests + reentrenamiento con datos reales (backend), build de APK firmado (Android) |

## Arranque rápido

**En tu PC (recomendado):** doble clic en `pc\INICIAR_AKERATEN.bat` (Windows) o `./pc/iniciar_akeraten.sh` (macOS/Linux). En la app: **Ajustes → Buscar mi PC**. Detalles en [`pc/LEEME.md`](pc/LEEME.md).

Manual:

```bash
cp .env.example .env            # añade tus claves (sin claves = modo DEMO)
cd backend && pip install -r requirements.txt
uvicorn akeraten.main:app --host 0.0.0.0 --port 8000
# Dashboard: http://localhost:8000   ·   API docs: http://localhost:8000/docs
```

O con Docker: `docker compose up --build` (backend + Redis + Postgres).

## Lógica de valor

- Probabilidad implícita `1/cuota` (y probabilidad justa sin margen)
- `edge = p_modelo × cuota − 1`
- Kelly `f* = (b·p − q)/b`, `b = cuota − 1`; stake = bankroll × f* × 0.5 (Half-Kelly), con tope
- Umbrales: tenis 1,5 % · tenis de mesa 2,5 % · edge > 8 % ⇒ **SOSPECHOSA**
- Validación a largo plazo con **CLV** = cuota entrada / cuota cierre − 1

## Estado y limitaciones conocidas

- **Modelos:** el entorno de desarrollo no tenía acceso a los datos de JeffSackmann, así que los artefactos incluidos se entrenaron con datos **sintéticos** (marcados en `backend/data/model_metrics.json`). El workflow `backend.yml` reentrena con datos reales ATP/WTA 2015–2024 en GitHub Actions; usa ese artefacto (o ejecuta `python backend/scripts/train_models.py` con red) antes de usarlo en serio.
- **APIs externas:** los formatos de algunas APIs (LiveTennisAPI, SportAPI, Apify, Sportmicro) están escritos sin verificar contra su documentación; revisa cada cliente al añadir la clave.
- **APK:** se compila en CI (`android.yml`). Firma con tu keystore mediante los secretos `KEYSTORE_BASE64`, `AKERATEN_KEYSTORE_PASSWORD`, `AKERATEN_KEY_ALIAS`, `AKERATEN_KEY_PASSWORD`. Publicación en Aptoide: ver `android/aptoide/PUBLISHING.md`.
- **Repos de modelos externos:** `backend/scripts/clone_repos.sh` los clona; sus wrappers tienen peso 0 hasta que se añada un adaptador.
