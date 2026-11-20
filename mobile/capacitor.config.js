const rawUrl = (process.env.APP_SERVER_URL || "").trim().replace(/\/+$/, "");

/** @type {import('@capacitor/cli').CapacitorConfig} */
const config = {
  appId: "org.memoriaviva.rise",
  appName: "MemoriaViva RISE",
  webDir: "www",
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false
  }
};

if (rawUrl) {
  config.server = {
    url: rawUrl,
    cleartext: rawUrl.startsWith("http://"),
    androidScheme: rawUrl.startsWith("http://") ? "http" : "https",
    errorPath: "index.html"
  };
}

module.exports = config;
