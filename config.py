"""
MemoriaViva RISE - Configuración Centralizada
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ==============================================================================
# 1. Rutas de Archivos y Directorios
# ==============================================================================
DATA_DIR = BASE_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
DEMO_AUDIOS_DIR = DATA_DIR / "demo_audios"
PHOTOS_DIR = DATA_DIR / "photos"
HISTORY_FILE = DATA_DIR / "history_21_days.json"
DEFAULT_PROFILE_FILE = PROFILES_DIR / "don_manuel_simulacion.json"
ACCOUNT_CONFIG_FILE = DATA_DIR / "account_config.json"

# Asegurar directorios
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
DEMO_AUDIOS_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Configuración de Protector de Pantalla y Push-to-Talk
MIN_SCREENSAVER_PHOTOS = 10
PTT_SERVER_PORT = 8765

# ==============================================================================
# 2. Umbrales Clínicos y Parámetros de Detección (Marco Científico)
# ==============================================================================
# Umbral de silencio para cierre de turno conversacional adaptativo (VAD)
SILENCE_THRESHOLD_SEC = 3.8

# Umbral de pausa anómica intra-oración (acceso léxico)
ANOMIC_PAUSE_THRESHOLD_SEC = 2.0

# Tamaño de ventana para Moving-Average Type-Token Ratio (MATTR)
MATTR_WINDOW_SIZE = 20

# Umbral de similitud coseno TF-IDF para detectar bucles semánticos (repetición)
SEMANTIC_REPEAT_THRESHOLD = 0.72

# Línea base para disparo de alerta preventiva Nivel 2 (variación sostenida)
CLINICAL_ALERT_PAUSE_INCREASE_PCT = 0.25  # 25% de incremento sostenido en pausas
CLINICAL_ALERT_MATTR_DROP_PCT = 0.20      # 20% de caída en riqueza léxica

# ==============================================================================
# 3. Parámetros de Síntesis de Voz Geriátrica (Edge-TTS)
# ==============================================================================
TTS_VOICE_MALE = "es-MX-JorgeNeural"
TTS_VOICE_FEMALE = "es-MX-DaliaNeural"
DEFAULT_TTS_VOICE = TTS_VOICE_MALE

# Compensación prosódica para presbiacusia y velocidad de procesamiento
TTS_RATE = "-15%"    # ~120 palabras/minuto
TTS_PITCH = "-5Hz"   # Tono ligeramente más grave para mayor audibilidad

# ==============================================================================
# 4. Modelos de Lenguaje e Inteligencia Artificial
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_COMPANION = "gemini-3.1-flash-lite"
GEMINI_MODEL_FALLBACK = "gemini-3.6-flash"
GEMINI_TIMEOUT_MS = 12000

# ==============================================================================
# 5. Configuración de Telegram (Canal Familiar)
# ==============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==============================================================================
# 6. Estados Visuales del "Modo Compañero" (UX/UI Adulto Mayor)
# ==============================================================================
# Escuchando al paciente -> Opción B: Aura de Respiración Emocional (entrainment calmante)
UI_MODE_LISTENING = "aura_respiracion"
# Respondiendo o en Standby -> Opción C: Álbum de Recuerdos Dinámico (fotogramas de reminiscencia)
UI_MODE_SPEAKING_STANDBY = "album_reuerdos"

# Paleta de colores cálida hogareña (prohibida estética hospitalaria fría)
COLOR_BG_CREAM = "#FAF6F0"
COLOR_SAGE_GREEN = "#7D9D86"
COLOR_WARM_AMBER = "#D99B52"
COLOR_SOFT_WOOD = "#8C6D53"
COLOR_TEXT_DARK = "#3A322C"


def update_env_and_runtime_keys(
    gemini_key: str | None = None,
    telegram_token: str | None = None,
    telegram_chat_id: str | None = None,
) -> None:
    """Actualiza el archivo .env y las variables en tiempo de ejecución en caliente."""
    global GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    env_path = BASE_DIR / ".env"
    existing: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    if gemini_key is not None:
        clean_g = gemini_key.strip()
        existing["GEMINI_API_KEY"] = clean_g
        GEMINI_API_KEY = clean_g
        os.environ["GEMINI_API_KEY"] = clean_g

    if telegram_token is not None:
        clean_t = telegram_token.strip()
        existing["TELEGRAM_BOT_TOKEN"] = clean_t
        TELEGRAM_BOT_TOKEN = clean_t
        os.environ["TELEGRAM_BOT_TOKEN"] = clean_t

    if telegram_chat_id is not None:
        clean_c = telegram_chat_id.strip()
        existing["TELEGRAM_CHAT_ID"] = clean_c
        TELEGRAM_CHAT_ID = clean_c
        os.environ["TELEGRAM_CHAT_ID"] = clean_c

    ordered_keys = ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    lines = ["# MemoriaViva RISE - Variables de Entorno"]
    for k in ordered_keys:
        lines.append(f"{k}={existing.get(k, '')}")
    for k, v in existing.items():
        if k not in ordered_keys:
            lines.append(f"{k}={v}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

