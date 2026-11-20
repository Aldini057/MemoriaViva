# MemoriaViva RISE — Empaquetado Android APK (Capacitor + GitHub Actions)

Esta carpeta contiene el wrapper híbrido de **Capacitor** para generar un `.apk` liviano (~8–15 MB) que conecta el dispositivo Android con tu despliegue HTTPS de MemoriaViva RISE, manteniendo captura de voz en el dispositivo (`MediaRecorder` + `SpeechRecognition`), permiso de micrófono en WebView y pantalla siempre encendida para el Modo Kiosco.

---

## 1. Configurar la URL del Servidor (Variable de Repositorio)

1. Despliega el contenedor Docker (`Dockerfile`) en tu proveedor cloud con HTTPS (Railway, Render, Fly.io o VPS). El contenedor escucha automáticamente en `$PORT` (por defecto `8501`) y enruta tanto Streamlit como `/ptt/*` en el mismo puerto.
2. En GitHub, ve a **Settings → Secrets and variables → Actions → Variables** y crea:
   - `APP_SERVER_URL`: `https://tu-servidor-memoriaviva.up.railway.app` *(sin barra diagonal al final)*.

> En cada `push` a `main` o ejecución manual (`Actions → Build Android APK → Run workflow`), GitHub Actions generará y subirá **`MemoriaViva-RISE-debug-apk`** listo para instalar en Android.

---

## 2. Configurar Firma para Releases (`v*.*.*`)

Para publicar APKs firmados automáticamente en **GitHub Releases** al crear un tag (por ejemplo `git tag v1.0.0 && git push origin v1.0.0`):

1. Genera tu keystore una sola vez en tu computadora:
   ```bash
   keytool -genkeypair -v -keystore memoriaviva-release.keystore \
     -alias memoriaviva -keyalg RSA -keysize 2048 -validity 10000
   ```
2. Conviértelo a Base64:
   ```bash
   base64 -w 0 memoriaviva-release.keystore
   ```
3. En GitHub (**Settings → Secrets and variables → Actions → Secrets**), agrega estos 4 secrets:
   - `ANDROID_KEYSTORE_BASE64`: salida en Base64 del paso anterior
   - `ANDROID_KEYSTORE_PASS`: contraseña del keystore
   - `ANDROID_KEY_ALIAS`: `memoriaviva`
   - `ANDROID_KEY_PASS`: contraseña de la clave
