import fs from "node:fs";
import path from "node:path";

const androidDir = path.resolve("android");
if (!fs.existsSync(androidDir)) {
  console.error("No existe mobile/android/. Ejecuta primero: npx cap add android");
  process.exit(1);
}

// 1. Permisos AndroidManifest.xml (Micrófono, Audio y Pantalla Encendida para Modo Kiosco)
const manifestPath = path.join(androidDir, "app", "src", "main", "AndroidManifest.xml");
let manifest = fs.readFileSync(manifestPath, "utf8");
const requiredPermissions = [
  "android.permission.INTERNET",
  "android.permission.RECORD_AUDIO",
  "android.permission.MODIFY_AUDIO_SETTINGS",
  "android.permission.WAKE_LOCK"
];

for (const perm of requiredPermissions) {
  if (!manifest.includes(perm)) {
    manifest = manifest.replace(
      "<application",
      `    <uses-permission android:name="${perm}" />\n\n    <application`
    );
  }
}
fs.writeFileSync(manifestPath, manifest, "utf8");
console.log("[OK] AndroidManifest.xml actualizado con permisos de audio y kiosco.");

// 2. MainActivity.java: permiso runtime RECORD_AUDIO, WebView getUserMedia y pantalla siempre encendida
const mainActivityPath = path.join(
  androidDir,
  "app",
  "src",
  "main",
  "java",
  "org",
  "memoriaviva",
  "rise",
  "MainActivity.java"
);

const mainActivityJava = `package org.memoriaviva.rise;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private static final int REQ_RECORD_AUDIO = 1001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Mantener pantalla encendida en Modo Kiosco (Protector de pantalla familiar)
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // Modo inmersivo limpio (oculta barras del sistema sin bloquear gestos)
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        WindowInsetsControllerCompat controller =
            WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
        if (controller != null) {
            controller.setSystemBarsBehavior(
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            );
            controller.hide(WindowInsetsCompat.Type.systemBars());
        }

        // Solicitar permiso de micrófono en tiempo de ejecución
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                new String[]{Manifest.permission.RECORD_AUDIO},
                REQ_RECORD_AUDIO
            );
        }
    }

    @Override
    public void onStart() {
        super.onStart();
        if (this.bridge != null && this.bridge.getWebView() != null) {
            final WebChromeClient originalClient = this.bridge.getWebView().getWebChromeClient();
            this.bridge.getWebView().setWebChromeClient(new WebChromeClient() {
                @Override
                public void onPermissionRequest(final PermissionRequest request) {
                    runOnUiThread(() -> request.grant(request.getResources()));
                }

                @Override
                public void onProgressChanged(android.webkit.WebView view, int newProgress) {
                    if (originalClient != null) {
                        originalClient.onProgressChanged(view, newProgress);
                    }
                }
            });
        }
    }
}
`;

fs.mkdirSync(path.dirname(mainActivityPath), { recursive: true });
fs.writeFileSync(mainActivityPath, mainActivityJava, "utf8");
console.log("[OK] MainActivity.java configurado (RECORD_AUDIO + WebView mic + FLAG_KEEP_SCREEN_ON).");

// 3. Inyectar soporte de firma Release vía variables de entorno en android/app/build.gradle
const appGradlePath = path.join(androidDir, "app", "build.gradle");
let appGradle = fs.readFileSync(appGradlePath, "utf8");

if (!appGradle.includes("signingConfigs")) {
  const signingSnippet = `    signingConfigs {
        release {
            if (System.getenv("ANDROID_KEYSTORE_PATH")) {
                storeFile file(System.getenv("ANDROID_KEYSTORE_PATH"))
                storePassword System.getenv("ANDROID_KEYSTORE_PASS")
                keyAlias System.getenv("ANDROID_KEY_ALIAS")
                keyPassword System.getenv("ANDROID_KEY_PASS")
            }
        }
    }
    buildTypes {`;

  appGradle = appGradle.replace("    buildTypes {", signingSnippet);
  appGradle = appGradle.replace(
    "        release {",
    `        release {\n            if (System.getenv("ANDROID_KEYSTORE_PATH")) {\n                signingConfig signingConfigs.release\n            }`
  );
  fs.writeFileSync(appGradlePath, appGradle, "utf8");
  console.log("[OK] android/app/build.gradle configurado para firma Release en CI.");
}
