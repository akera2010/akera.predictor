# Publicar AKERATEN v.0.1 en Aptoide

Guía paso a paso para generar el APK de release firmado de **AKERATEN v.0.1**
(`com.akeraten.valuebetmonitor`, versionName `0.1.0`, versionCode `1`) y publicarlo en Aptoide.
Autora: Sandra Blanco (España | 2026).

---

## 0. Requisitos

- JDK 17 (`java -version`).
- Android SDK con `build-tools` 34.0.0 o superior (incluye `apksigner` y `zipalign`).
  Variable `ANDROID_HOME` apuntando al SDK.
- Este repositorio clonado. Todos los comandos se ejecutan desde `android/`.

---

## 1. Crear el keystore de release (solo una vez)

```bash
keytool -genkeypair -v \
  -keystore akeraten-release.jks \
  -storetype PKCS12 \
  -keyalg RSA -keysize 4096 \
  -validity 10000 \
  -alias akeraten \
  -dname "CN=Sandra Blanco, O=AKERATEN, L=Madrid, C=ES"
```

`keytool` pedirá la contraseña del almacén (con PKCS12 la contraseña de la clave es la misma).

> **Guarda el `.jks` y sus contraseñas en un lugar seguro y con copia de seguridad.**
> Todas las actualizaciones futuras deben firmarse con la MISMA clave; si la pierdes no
> podrás actualizar la app en Aptoide (ni en ninguna otra tienda).
> El `.jks` está excluido de git (`*.jks` en `.gitignore`). Nunca lo subas al repositorio.

Obtén las huellas del certificado (las necesitarás para Aptoide y para la verificación de desarrollador de Google):

```bash
keytool -list -v -keystore akeraten-release.jks -alias akeraten | grep -E "SHA1|SHA256"
```

---

## 2. Compilar el APK de release firmado

El `app/build.gradle.kts` lee la firma desde variables de entorno. Si no existen, el release se
firma con la clave de *debug* (útil para CI, **no apto para publicar**).

```bash
cd android
export AKERATEN_KEYSTORE_PATH="$PWD/../akeraten-release.jks"   # ruta absoluta recomendada
export AKERATEN_KEYSTORE_PASSWORD='tu-contraseña'
export AKERATEN_KEY_ALIAS='akeraten'
export AKERATEN_KEY_PASSWORD='tu-contraseña'                   # igual que la del almacén con PKCS12

./gradlew clean assembleRelease
```

Resultado: `android/app/build/outputs/apk/release/app-release.apk`
(R8/minify y shrinkResources activados).

En Windows (PowerShell): `$env:AKERATEN_KEYSTORE_PATH="C:\ruta\akeraten-release.jks"` etc. y `.\gradlew.bat assembleRelease`.

---

## 3. Verificar la firma

```bash
"$ANDROID_HOME/build-tools/34.0.0/apksigner" verify --verbose --print-certs \
  app/build/outputs/apk/release/app-release.apk
```

Comprueba que:

- `Verified using v2 scheme (APK Signature Scheme v2): true` (y/o v3).
- El `Signer #1 certificate SHA-256 digest` coincide con la huella SHA256 del paso 1.
- **No** aparece `CN=Android Debug` (eso significaría que se firmó con la clave de debug porque
  faltaban variables de entorno).

Opcional — revisar metadatos del paquete:

```bash
"$ANDROID_HOME/build-tools/34.0.0/aapt2" dump badging app/build/outputs/apk/release/app-release.apk | head -5
```

Debe mostrar `package: name='com.akeraten.valuebetmonitor' versionCode='1' versionName='0.1.0'`.

Instalación de prueba en un dispositivo: `adb install -r app/build/outputs/apk/release/app-release.apk`.

---

## 4. (Opcional) Firmar en GitHub Actions

El workflow `.github/workflows/android.yml` compila `assembleDebug` y `assembleRelease` en cada push
y sube ambos APK como artefactos. Para que el release salga firmado con tu clave, crea estos
*secrets* en **Settings → Secrets and variables → Actions**:

| Secret | Valor |
| --- | --- |
| `KEYSTORE_BASE64` | `base64 -w0 akeraten-release.jks` (macOS: `base64 -i akeraten-release.jks`) |
| `AKERATEN_KEYSTORE_PASSWORD` | contraseña del almacén |
| `AKERATEN_KEY_ALIAS` | `akeraten` |
| `AKERATEN_KEY_PASSWORD` | contraseña de la clave |

Sin `KEYSTORE_BASE64` el workflow sigue funcionando, pero el APK de release va firmado con debug.

---

## 5. Subir a Aptoide (https://connect.aptoide.com)

1. Entra en **https://connect.aptoide.com** y crea/inicia sesión en tu cuenta de desarrollador
   (puedes usar la misma cuenta de Aptoide). Completa el perfil de desarrollador
   (nombre público: *Sandra Blanco*, país: España, email de contacto).
2. **Apps → Upload app / Add new app** y sube `app-release.apk` (firmado con tu clave, no con debug).
   Aptoide detecta automáticamente el paquete `com.akeraten.valuebetmonitor`, versión `0.1.0 (1)`.
3. Rellena la ficha con los textos de esta carpeta:
   - Título: `es/title.txt` · `en/title.txt`
   - Descripción corta: `es/short_description.txt` · `en/short_description.txt`
   - Descripción completa: `es/full_description.txt` · `en/full_description.txt`
   - Novedades (changelog): `es/changelog.txt` · `en/changelog.txt`
   - Idioma principal: Español (es-ES); añade Inglés (en-US) como traducción.
4. **Categoría:** *Deportes* (Sports). **Clasificación de edad:** 18+ (contenido relacionado con apuestas).
   Palabras clave: ver `metadata.json` (`keywords_es`, `keywords_en`).
5. **Gráficos:**
   - Icono 512×512 PNG (exporta el icono adaptativo `app/src/main/res/drawable/ic_launcher_foreground.xml`
     sobre el fondo `#070D1C`, p. ej. con *Android Studio → Image Asset* o capturando el launcher).
   - Al menos 3–4 capturas de pantalla (En Vivo, Value Bets, Análisis completo, Ajustes). El modo
     demo sin conexión permite hacerlas sin backend.
   - Opcional: imagen destacada 1024×500.
6. **Política de privacidad:** publica `privacy-policy.md` en una URL pública (GitHub Pages, Gist o
   web propia) e indica la URL en la ficha.
7. Indica que la app **no contiene anuncios ni compras integradas** y que **no acepta apuestas con
   dinero real** (es una herramienta informativa). Si Aptoide solicita documentación adicional para
   contenido de apuestas, aporta esta aclaración y el aviso de juego responsable.
8. Envía a revisión. Aptoide analiza el APK (antimalware y firma) antes de publicarlo; puedes seguir el
   estado en el panel de Connect.

### Actualizaciones

1. Incrementa `versionCode` (y `versionName`) en `app/build.gradle.kts`.
2. Recompila con **la misma clave** (pasos 2–3).
3. En Connect sube el nuevo APK sobre la app existente y actualiza el changelog.

---

## 6. Nota: verificación de desarrolladores de Google (Android Developer Verification)

Google ha anunciado que, a partir de 2026, las apps instaladas en dispositivos Android certificados
deberán estar asociadas a un **desarrollador verificado**, **también cuando se distribuyen fuera de
Google Play** (tiendas alternativas como Aptoide o instalación directa del APK). El despliegue es
progresivo (primeros países desde septiembre de 2026 y ampliación global posterior), por lo que
conviene revisar el estado actual en la documentación oficial de Android Developers antes de publicar.

Pasos recomendados:

1. Crear una cuenta en la **Android Developer Console** (o usar la cuenta de Google Play Console si ya
   existe) y completar la **verificación de identidad** (persona física: documento de identidad;
   organización: datos de la entidad y D-U-N-S si se solicita).
2. **Registrar el nombre de paquete** `com.akeraten.valuebetmonitor` y demostrar la propiedad
   aportando la huella **SHA-256** del certificado de firma (paso 1) o subiendo un APK firmado con él.
3. Mantener siempre la misma clave de firma: el registro vincula paquete + clave + desarrollador.
4. Sin esta verificación, en los países donde ya sea obligatoria Android podría bloquear la
   instalación del APK descargado desde Aptoide.

---

## 7. Checklist final

- [ ] APK firmado con la clave de release (no `CN=Android Debug`).
- [ ] `apksigner verify` OK y SHA-256 anotado.
- [ ] versionCode/versionName correctos.
- [ ] Textos ES/EN, categoría Deportes, edad 18+.
- [ ] URL de la política de privacidad publicada.
- [ ] Aviso visible: *"Las apuestas conllevan riesgo. No se garantizan ganancias. +18. Juega con responsabilidad."*
- [ ] Verificación de desarrollador de Google completada (si aplica en los países de distribución).
