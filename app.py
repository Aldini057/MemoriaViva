"""
MemoriaViva RISE - Aplicación Principal (Registro Único, Modo Kiosco Protector de Pantalla + PTT ESPACIO y Panel Familiar)
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Flujo de Usuario Completo:
1. VISTA A — Registro Único Inicial (si `is_registered == False`):
   Asistente de 4 pasos:
   - Paso 1: Perfil completo del adulto mayor + PIN del cuidador + Autostart Windows.
   - Paso 2: Configuración y vinculación del Bot de Telegram (`@BotFather` + QR).
   - Paso 3: Tutorial paso a paso para obtener la API Key de Google Gemini.
   - Paso 4: Carga de mínimo 10 fotografías para el protector de pantalla.
2. VISTA B — Pantalla Bloqueada del Adulto Mayor (Modo Kiosco por defecto al encender):
   - Muestra únicamente el protector de pantalla rotando sus 10+ fotografías.
   - Único control: mantener presionada la tecla `ESPACIO` para hablar (muestra el Aura
     de Respiración Emocional) y soltar `ESPACIO` para procesar y escuchar la respuesta.
   - Acceso discreto en esquina inferior derecha con PIN para desbloquear el Panel Familiar.
3. VISTA C — Panel Familiar y Médico (Desbloqueado con PIN):
   - Tablero longitudinal de 21 días, Telegram en vivo, PDF clínico, gestor de 10+ fotos,
     arranque automático con Windows y controles de demostración.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import audio_engine
import biomarkers
import config
import llm_companion
import pdf_report
import system_integration
import telegram_notifier

# ==============================================================================
# Configuración de Página e Inicio del Micro-Servidor Push-to-Talk
# ==============================================================================
st.set_page_config(
    page_title="MemoriaViva RISE",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PTT_PORT = audio_engine.start_ptt_background_server()


# ==============================================================================
# Inicialización de Estado de Sesión
# ==============================================================================
def init_session_state() -> None:
    account_cfg = system_integration.load_account_config()

    if "caregiver_unlocked" not in st.session_state:
        st.session_state.caregiver_unlocked = False
    if "show_pin_modal" not in st.session_state:
        st.session_state.show_pin_modal = False
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1
    if "onboarding_profile_id" not in st.session_state:
        st.session_state.onboarding_profile_id = "don_manuel"
    if "onboarding_profile_path" not in st.session_state:
        st.session_state.onboarding_profile_path = str(config.DEFAULT_PROFILE_FILE)
    if "onboarding_draft" not in st.session_state:
        st.session_state.onboarding_draft = {}

    if "active_profile_path" not in st.session_state:
        saved_path = Path(account_cfg.get("active_profile_path", str(config.DEFAULT_PROFILE_FILE)))
        st.session_state.active_profile_path = (
            str(saved_path) if saved_path.exists() else str(config.DEFAULT_PROFILE_FILE)
        )
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "previous_user_utterances" not in st.session_state:
        st.session_state.previous_user_utterances = []
    if "last_turn_result" not in st.session_state:
        st.session_state.last_turn_result = None
    if "last_audio_response_path" not in st.session_state:
        st.session_state.last_audio_response_path = None
    if "telegram_bridge" not in st.session_state:
        st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge()
    if "history_21_days" not in st.session_state:
        with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
            st.session_state.history_21_days = json.load(f)


init_session_state()


# ==============================================================================
# Temas Dinámicos (Modo Día Cálido vs Modo Noche Cálido + Modo Kiosco)
# ==============================================================================
def inject_global_css(is_dark: bool, kiosk_mode: bool) -> None:
    if is_dark:
        bg_main = "#1C1917"
        bg_card = "#26221F"
        bg_topbar = "#26221F"
        border_col = "#3E3731"
        text_primary = "#EDE3D5"
        text_secondary = "#B8AA99"
        tab_active = "#8FB399"
        btn_bg = "#5E7E68"
        btn_hover = "#71947C"
        input_bg = "#2A2521"
        tg1_bg, tg1_txt = "#1D2E23", "#E4EFE7"
        tg2_bg, tg2_txt = "#33291A", "#F5E9D6"
        tg3_bg, tg3_txt = "#381F1F", "#F7E1E1"
        scheme = "dark"
    else:
        bg_main = "#F7F2E9"
        bg_card = "#FFFDF9"
        bg_topbar = "#EFE8DC"
        border_col = "#E2D6C5"
        text_primary = "#3A322C"
        text_secondary = "#6E5D4F"
        tab_active = "#43624D"
        btn_bg = "#5E7E68"
        btn_hover = "#4D6B56"
        input_bg = "#FFFDF9"
        tg1_bg, tg1_txt = "#EFF7F1", "#2A362E"
        tg2_bg, tg2_txt = "#FCF5E5", "#3A3022"
        tg3_bg, tg3_txt = "#FBECEC", "#3D2020"
        scheme = "light"

    kiosk_css = (
        """
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"],
        #MainMenu,
        footer {
            display: none !important;
        }
        .block-container {
            padding-top: 0.75rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 1.4rem !important;
            padding-right: 1.4rem !important;
            max-width: 100% !important;
        }
        """
        if kiosk_mode
        else """
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        .block-container {
            padding-top: 1.6rem !important;
        }
        """
    )

    css = f"""
    <style>
        :root, html, body, [data-testid="stAppViewContainer"], .stApp {{
            color-scheme: {scheme} !important;
            background-color: {bg_main} !important;
            color: {text_primary} !important;
        }}
        {kiosk_css}

        h1, h2, h3, h4, h5, h6, p, label, span, div[data-testid="stMarkdownContainer"] {{
            color: {text_primary};
        }}
        [data-testid="stMetricValue"] {{
            color: {text_primary} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {text_secondary} !important;
        }}

        /* Botones */
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
            background-color: {btn_bg} !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.55rem 1.1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15) !important;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
            background-color: {btn_hover} !important;
            color: #FFFFFF !important;
        }}
        .stButton > button:disabled {{
            opacity: 0.45 !important;
        }}

        /* Inputs */
        input, textarea, [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            color: {text_primary} !important;
            border-color: {border_col} !important;
            border-radius: 10px !important;
        }}

        /* Ocultar el botón disparador oculto de Push-to-Talk */
        .st-key-ptt_hidden_trigger {{
            position: fixed !important;
            left: -9999px !important;
            top: -9999px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0.01 !important;
            overflow: hidden !important;
        }}

        /* Pestañas */
        button[data-baseweb="tab"] {{
            background-color: transparent !important;
            color: {text_secondary} !important;
            font-size: 1.0rem !important;
            font-weight: 600 !important;
            padding: 0.55rem 1.15rem !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {tab_active} !important;
            border-bottom: 3px solid {tab_active} !important;
        }}

        /* Barra Superior y Tarjetas */
        .mv-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: {bg_topbar};
            border: 1px solid {border_col};
            padding: 0.8rem 1.4rem;
            border-radius: 14px;
            margin-bottom: 0.7rem;
        }}
        .mv-card {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            border-radius: 16px;
            padding: 1.3rem 1.5rem;
            margin-bottom: 0.8rem;
        }}
        .positive-card {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            border-top: 4px solid #7D9D86;
            border-radius: 14px;
            padding: 1.1rem 1.3rem;
        }}
        .positive-card-amber {{
            border-top: 4px solid #D99B52;
        }}
        .tg-card-1 {{
            background-color: {tg1_bg};
            border-left: 5px solid #3FA36C;
            border-radius: 10px;
            padding: 0.85rem 1.0rem;
            margin-bottom: 0.65rem;
            font-size: 0.90rem;
            color: {tg1_txt} !important;
        }}
        .tg-card-2 {{
            background-color: {tg2_bg};
            border-left: 5px solid #D99B52;
            border-radius: 10px;
            padding: 0.85rem 1.0rem;
            margin-bottom: 0.65rem;
            font-size: 0.90rem;
            color: {tg2_txt} !important;
        }}
        .tg-card-3 {{
            background-color: {tg3_bg};
            border-left: 6px solid #D9534F;
            border-radius: 10px;
            padding: 0.9rem 1.0rem;
            margin-bottom: 0.65rem;
            font-size: 0.92rem;
            color: {tg3_txt} !important;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ==============================================================================
# Pipeline Central de Ejecución de Turno
# ==============================================================================
def execute_full_turn_pipeline(
    user_text: str | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
    demo_scenario_id: str | None = None,
    raw_audio_bytes: bytes | None = None,
    browser_transcript: str | None = None,
    browser_word_timestamps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta las 4 capas de MemoriaViva RISE sobre un turno del adulto mayor:
    Audio/Texto -> Biomarcadores -> LLM Reminiscencia/Feil -> Voz Edge-TTS -> Telegram.
    """
    profile_path = st.session_state.active_profile_path
    profile = llm_companion.load_patient_profile(profile_path)
    pac = profile.get("paciente", {})
    fam = profile.get("red_familiar_y_afectiva", {})
    patient_name = pac.get("nombre_preferido", "Don Manuel")
    caregiver_name = (
        fam.get("hija_mayor_cuidadora", {}).get("nombre")
        or profile.get("contacto_emergencia_telegram", {}).get("nombre", "Laura").split()[0]
    )

    clean_browser_text = (browser_transcript or "").strip()

    if demo_scenario_id:
        stt_res = audio_engine.transcribe_audio_with_timestamps(demo_scenario_id=demo_scenario_id)
        final_text = stt_res["text"]
        final_timestamps = stt_res["word_timestamps"]
        zero_leakage = stt_res["zero_raw_leakage_verified"]
    elif clean_browser_text:
        final_text = clean_browser_text
        zero_leakage = True
        final_timestamps = (
            list(browser_word_timestamps)
            if browser_word_timestamps
            else biomarkers.synthesize_word_timestamps_from_text(final_text)
        )
        # Si también se grabó WAV en RAM, alinear la pausa acústica real medida en la onda
        if raw_audio_bytes:
            try:
                ac = audio_engine.extract_acoustic_pauses_from_waveform(raw_audio_bytes)
                max_ac_pause = float(ac.get("max_acoustic_pause_sec", 0.0))
                if (
                    ac.get("anomic_acoustic_count", 0) > 0
                    and len(final_timestamps) >= 3
                    and max(
                        (
                            final_timestamps[i]["start"] - final_timestamps[i - 1]["end"]
                            for i in range(1, len(final_timestamps))
                        ),
                        default=0.0,
                    )
                    < config.ANOMIC_PAUSE_THRESHOLD_SEC
                ):
                    mid_idx = len(final_timestamps) // 2
                    for j in range(mid_idx, len(final_timestamps)):
                        final_timestamps[j]["start"] = round(final_timestamps[j]["start"] + max_ac_pause, 2)
                        final_timestamps[j]["end"] = round(final_timestamps[j]["end"] + max_ac_pause, 2)
            except Exception:
                pass
    elif raw_audio_bytes:
        stt_res = audio_engine.transcribe_audio_with_timestamps(audio_source=raw_audio_bytes)
        final_text = (stt_res.get("text") or "").strip()
        final_timestamps = stt_res.get("word_timestamps", [])
        zero_leakage = stt_res.get("zero_raw_leakage_verified", True)

        if not final_text:
            polite_retry = (
                f"Disculpe, {patient_name}, no alcancé a escuchar con claridad. "
                "¿Me lo puede repetir manteniendo presionada la barra espaciadora?"
            )
            tts_path = config.BASE_DIR / "temp_companion_reply.mp3"
            tts_res = audio_engine.speak_geriatric(polite_retry, output_path=tts_path)
            st.session_state.last_audio_response_path = tts_res["audio_path"]
            turn_bundle = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "user_text": "",
                "assistant_reply": polite_retry,
                "biomarkers": {
                    "mattr": 0.0,
                    "mean_pause_sec": 0.0,
                    "max_pause_sec": 0.0,
                    "anomic_count": 0,
                    "is_repetition": False,
                    "repetition_similarity": 0.0,
                },
                "extraction": {
                    "emotional_state": "tranquilo",
                    "emergency_triggered": False,
                    "biographical_rescue_triggered": False,
                    "memory_album_theme": "familia_hogar",
                },
                "persisted_new_facts": [],
                "tts": tts_res,
                "telegram": None,
                "zero_raw_leakage_verified": zero_leakage,
            }
            st.session_state.last_turn_result = turn_bundle
            return turn_bundle
    else:
        final_text = user_text or ""
        final_timestamps = word_timestamps or biomarkers.synthesize_word_timestamps_from_text(final_text)
        zero_leakage = True

    bio_res = biomarkers.analyze_turn_biomarkers(
        text=final_text,
        word_timestamps=final_timestamps,
        previous_utterances=st.session_state.previous_user_utterances,
    )
    st.session_state.previous_user_utterances.append(final_text)

    llm_res = llm_companion.process_conversation_turn(
        user_text=final_text,
        profile_path=profile_path,
        is_repetition=bio_res["is_repetition"],
        use_live_llm=True,
        conversation_history=st.session_state.conversation_history,
    )
    assistant_reply = llm_res["assistant_reply"]
    extraction = llm_res["extraction"]

    st.session_state.current_album_theme = extraction.get("memory_album_theme", "familia_hogar")

    tts_path = config.BASE_DIR / "temp_companion_reply.mp3"
    tts_res = audio_engine.speak_geriatric(assistant_reply, output_path=tts_path)
    st.session_state.last_audio_response_path = tts_res["audio_path"]

    bridge: telegram_notifier.TelegramFamilyBridge = st.session_state.telegram_bridge
    if extraction.get("emergency_triggered"):
        tg_res = bridge.send_level3_emergency_alert(
            reason=extraction.get("emergency_reason") or "Desorientación espacial aguda detectada",
            last_phrase=final_text,
            patient_name=patient_name,
            caregiver_name=caregiver_name,
        )
    else:
        tg_res = bridge.send_level1_daily_pulse(
            topic_summary=extraction.get("conversation_topic_summary", "Charla de reminiscencia positiva"),
            mattr=bio_res["mattr"],
            mean_pause=bio_res["max_pause_sec"] if bio_res["anomic_count"] > 0 else bio_res["mean_pause_sec"],
            dinner_tip=extraction.get("dinner_conversation_tip", "Pregúntale por sus recuerdos favoritos."),
            patient_name=patient_name,
            caregiver_name=caregiver_name,
        )

    turn_bundle = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "user_text": final_text,
        "assistant_reply": assistant_reply,
        "biomarkers": bio_res,
        "extraction": extraction,
        "persisted_new_facts": llm_res["persisted_new_facts"],
        "tts": tts_res,
        "telegram": tg_res,
        "zero_raw_leakage_verified": zero_leakage,
    }
    st.session_state.last_turn_result = turn_bundle
    st.session_state.conversation_history.append(turn_bundle)
    return turn_bundle


def _build_profile_dict_from_fields(
    nombre_completo: str,
    nombre_pref: str,
    edad: int,
    ciudad: str,
    ocupacion: str,
    pareja: str,
    cuidador_nombre: str,
    cuidador_parentesco: str,
    hija_menor: str,
    nietos: str,
    musica: str,
    viaje_auto: str,
    mascota: str,
    comida: str,
    chat_id: str = "",
) -> dict[str, Any]:
    """Construye el diccionario estándar del perfil biográfico del adulto mayor."""
    raw_slug = nombre_pref.lower().strip().replace(" ", "_")
    for src, dst in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        raw_slug = raw_slug.replace(src, dst)
    slug = "".join(c for c in raw_slug if c.isalnum() or c == "_") or "paciente_1"

    anchors = [
        x.strip()
        for x in [musica, viaje_auto, mascota, comida]
        if x and x.strip()
    ]
    if not anchors:
        anchors = ["Disfruta platicar de la música y tradiciones de su juventud"]

    return {
        "paciente": {
            "id": slug,
            "tipo_perfil": "real" if slug != "don_manuel" else "simulacion_clinica",
            "nombre_completo": nombre_completo.strip(),
            "nombre_preferido": nombre_pref.strip(),
            "edad": int(edad),
            "ciudad_residencia": ciudad.strip() or "México",
            "ocupacion_historica": ocupacion.strip() or "Jubilado",
        },
        "red_familiar_y_afectiva": {
            "esposa_finada": pareja.strip(),
            "hija_mayor_cuidadora": {
                "nombre": cuidador_nombre.strip() or "Familiar",
                "ciudad": ciudad.strip() or "México",
                "detalle": "Cuidador principal enlazado a MemoriaViva",
            },
            "hija_menor": {
                "nombre": hija_menor.strip() or "Rocío",
                "ciudad": "Manzanillo, Colima",
                "ocupacion": "Familiar cercano",
                "detalle": "En contacto telefónico semanal",
            },
            "nietos": [
                {
                    "nombre": nietos.strip() or "Nietos",
                    "edad": 14,
                    "gusto_compartido": "Convivencia familiar",
                }
            ],
        },
        "anclas_de_reminiscencia": anchors,
        "rutinas_salud_suaves": [
            "Tomar un vaso de agua al mediodía",
            comida.strip() or "Descanso vespertino tranquilo",
        ],
        "contacto_emergencia_telegram": {
            "nombre": cuidador_nombre.strip() or "Familiar",
            "parentesco": cuidador_parentesco.strip() or "Familiar",
            "chat_id": chat_id,
        },
    }


def _get_audio_data_uri(audio_path: str | Path | None) -> str:
    if not audio_path:
        return ""
    p = Path(audio_path)
    if not p.exists():
        return ""
    mime = "audio/mp3" if p.suffix.lower() == ".mp3" else "audio/wav"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ==============================================================================
# VISTA A: ASISTENTE DE REGISTRO INICIAL (ONBOARDING DE 4 PASOS)
# ==============================================================================
def render_onboarding_wizard() -> None:
    inject_global_css(st.session_state.dark_mode, kiosk_mode=False)

    col_h1, col_h2 = st.columns([4.2, 1.0])
    with col_h1:
        st.markdown(
            """
            <div class="mv-topbar">
                <div>
                    <div style="font-size:1.35rem; font-weight:700;">🌿 Bienvenido a MemoriaViva RISE — Configuración Inicial</div>
                    <div style="font-size:0.92rem; opacity:0.85;">Registra este equipo una sola vez para activar el protector de pantalla y el compañero por voz.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_h2:
        theme_lbl = "☀️ Modo Día" if st.session_state.dark_mode else "🌙 Modo Noche"
        if st.button(theme_lbl, width="stretch"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    step = st.session_state.onboarding_step
    steps_titles = [
        "1. Perfil y Cuenta",
        "2. Bot de Telegram",
        "3. API Key Gemini",
        "4. Fotos (Mín. 10)",
    ]
    cols_prog = st.columns(4)
    for idx, title in enumerate(steps_titles, start=1):
        with cols_prog[idx - 1]:
            if idx < step:
                st.success(f"✅ {title}")
            elif idx == step:
                st.info(f"👉 **{title}**")
            else:
                st.caption(f"⚪ {title}")

    st.divider()

    # --------------------------------------------------------------------------
    # PASO 1: PERFIL DEL ADULTO MAYOR Y CUENTA ÚNICA DEL CUIDADOR
    # --------------------------------------------------------------------------
    if step == 1:
        c_title, c_auto = st.columns([3.0, 1.5])
        with c_title:
            st.markdown("### Paso 1 de 4 — Datos del Adulto Mayor y Cuenta de Bloqueo")
        with c_auto:
            if st.button("⚡ Autocompletar Datos de Ejemplo (Don Manuel)", width="stretch"):
                st.session_state["ob_nombre_completo"] = "Manuel González Magaña"
                st.session_state["ob_nombre_pref"] = "Don Manuel"
                st.session_state["ob_edad"] = 72
                st.session_state["ob_ciudad"] = "San Pedro Tlaquepaque, Jalisco"
                st.session_state["ob_ocupacion"] = "Maquinista y mecánico en Ferrocarriles Nacionales durante 32 años"
                st.session_state["ob_pareja"] = "Doña Carmen (se conocieron en la plaza en 1975)"
                st.session_state["ob_hija_menor"] = "Rocío (maestra en Manzanillo, Colima)"
                st.session_state["ob_nietos"] = "Mateo (14 años, dominó y Atlas) y Sofía (9 años, dibujar trenes)"
                st.session_state["ob_musica"] = "Boleros del Trío Los Panchos y Agustín Lara ('Solamente una vez')"
                st.session_state["ob_viaje"] = "Viaje familiar a Miramar, Manzanillo en su Vocho azul modelo 1974"
                st.session_state["ob_mascota"] = "Perro pastor alemán llamado Sultán"
                st.session_state["ob_comida"] = "Chocolate de metate por la tarde y usar su suéter gris"
                st.session_state["ob_cuidador"] = "Laura"
                st.session_state["ob_parentesco"] = "Hija"
                st.session_state["ob_usuario"] = "laura.gonzalez"
                st.session_state["ob_pin"] = "1234"
                st.session_state["ob_pin2"] = "1234"
                st.rerun()

        with st.form("onboarding_step1_form"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 👴 Datos de la Persona Mayor")
                ob_nombre_completo = st.text_input(
                    "Nombre completo *",
                    value=st.session_state.get("ob_nombre_completo", ""),
                    placeholder="Ej. Manuel González Magaña",
                )
                ob_nombre_pref = st.text_input(
                    "¿Cómo le gusta que le llamen? *",
                    value=st.session_state.get("ob_nombre_pref", ""),
                    placeholder="Ej. Don Manuel",
                )
                ob_edad = st.number_input("Edad", min_value=55, max_value=105, value=int(st.session_state.get("ob_edad", 72)))
                ob_ciudad = st.text_input(
                    "Ciudad de residencia",
                    value=st.session_state.get("ob_ciudad", ""),
                    placeholder="Ej. Guadalajara, Jalisco",
                )
                ob_ocupacion = st.text_input(
                    "Oficio o profesión histórica",
                    value=st.session_state.get("ob_ocupacion", ""),
                    placeholder="Ej. Maquinista de ferrocarriles",
                )
                ob_pareja = st.text_input(
                    "Esposa(o) o pareja",
                    value=st.session_state.get("ob_pareja", ""),
                    placeholder="Ej. Doña Carmen",
                )
                ob_hija_menor = st.text_input(
                    "Otros hijos o familiares cercanos",
                    value=st.session_state.get("ob_hija_menor", ""),
                    placeholder="Ej. Rocío (vive en Manzanillo)",
                )
                ob_nietos = st.text_input(
                    "Nietos y gustos compartidos",
                    value=st.session_state.get("ob_nietos", ""),
                    placeholder="Ej. Mateo (dominó) y Sofía (dibujar)",
                )

            with c2:
                st.markdown("#### ❤️ Anclas de Memoria y Cuenta de Bloqueo")
                ob_musica = st.text_input(
                    "Música o cantantes favoritos",
                    value=st.session_state.get("ob_musica", ""),
                    placeholder="Ej. Boleros de Los Panchos y Agustín Lara",
                )
                ob_viaje = st.text_input(
                    "Viaje o primer auto memorable",
                    value=st.session_state.get("ob_viaje", ""),
                    placeholder="Ej. Vocho azul 1974 rumbo a Manzanillo",
                )
                ob_mascota = st.text_input(
                    "Mascota querida del pasado",
                    value=st.session_state.get("ob_mascota", ""),
                    placeholder="Ej. Perro pastor alemán llamado Sultán",
                )
                ob_comida = st.text_input(
                    "Platillo tradicional o rutina diaria",
                    value=st.session_state.get("ob_comida", ""),
                    placeholder="Ej. Chocolate de metate por la tarde",
                )
                st.divider()
                ob_cuidador = st.text_input(
                    "Nombre del Cuidador / Familiar responsable *",
                    value=st.session_state.get("ob_cuidador", ""),
                    placeholder="Ej. Laura",
                )
                ob_parentesco = st.text_input(
                    "Parentesco",
                    value=st.session_state.get("ob_parentesco", "Hija / Nieto"),
                )
                ob_usuario = st.text_input(
                    "Usuario de acceso familiar *",
                    value=st.session_state.get("ob_usuario", ""),
                    placeholder="Ej. laura.cuidadora",
                )
                pcol1, pcol2 = st.columns(2)
                with pcol1:
                    ob_pin = st.text_input(
                        "PIN o Contraseña de bloqueo *",
                        value=st.session_state.get("ob_pin", ""),
                        type="password",
                        placeholder="Mínimo 4 dígitos",
                    )
                with pcol2:
                    ob_pin2 = st.text_input(
                        "Confirmar PIN *",
                        value=st.session_state.get("ob_pin2", ""),
                        type="password",
                        placeholder="Repite tu PIN",
                    )
                ob_autostart = st.checkbox(
                    "💻 Arrancar MemoriaViva automáticamente al encender esta PC (Windows)",
                    value=bool(st.session_state.get("ob_autostart", True)),
                )

            if st.form_submit_button("Guardar Perfil y Continuar al Paso 2 (Telegram) ➡️", width="stretch"):
                if not ob_nombre_completo.strip() or not ob_nombre_pref.strip() or not ob_cuidador.strip():
                    st.error("Por favor completa el nombre del adulto mayor, cómo prefiere que le llamen y el nombre del cuidador.")
                elif len(ob_pin.strip()) < 4 or ob_pin.strip() != ob_pin2.strip():
                    st.error("El PIN o contraseña debe tener al menos 4 caracteres y coincidir en ambos campos.")
                else:
                    profile_dict = _build_profile_dict_from_fields(
                        nombre_completo=ob_nombre_completo,
                        nombre_pref=ob_nombre_pref,
                        edad=int(ob_edad),
                        ciudad=ob_ciudad,
                        ocupacion=ob_ocupacion,
                        pareja=ob_pareja,
                        cuidador_nombre=ob_cuidador,
                        cuidador_parentesco=ob_parentesco,
                        hija_menor=ob_hija_menor,
                        nietos=ob_nietos,
                        musica=ob_musica,
                        viaje_auto=ob_viaje,
                        mascota=ob_mascota,
                        comida=ob_comida,
                        chat_id=config.TELEGRAM_CHAT_ID,
                    )
                    saved_profile = llm_companion.save_patient_profile(profile_dict)
                    pid = profile_dict["paciente"]["id"]
                    st.session_state.onboarding_profile_id = pid
                    st.session_state.onboarding_profile_path = str(saved_profile)
                    st.session_state.active_profile_path = str(saved_profile)
                    st.session_state.onboarding_draft = {
                        "caregiver_name": ob_cuidador.strip(),
                        "caregiver_user": ob_usuario.strip() or ob_cuidador.strip().lower(),
                        "pin_hash": system_integration.hash_pin(ob_pin.strip()),
                        "autostart_enabled": bool(ob_autostart),
                    }
                    st.session_state.onboarding_step = 2
                    st.rerun()

    # --------------------------------------------------------------------------
    # PASO 2: REGISTRO Y VINCULACIÓN DE BOT DE TELEGRAM
    # --------------------------------------------------------------------------
    elif step == 2:
        st.markdown("### Paso 2 de 4 — Registro y Vinculación del Bot de Telegram")
        col_g, col_qr = st.columns([1.45, 1.0], gap="large")

        with col_g:
            st.markdown(
                """
                <div class="mv-card">
                    <h4>📱 Tutorial rápido: Crea tu Bot Familiar en 1 minuto</h4>
                    <ol style="line-height:1.7;">
                        <li>Abre Telegram en tu celular y busca al bot oficial <b>@BotFather</b> (con palomita azul).</li>
                        <li>Envíale el mensaje <code>/newbot</code>.</li>
                        <li>Escribe un nombre visible (ejemplo: <i>MemoriaViva Alertas</i>) y luego un usuario terminado en <code>bot</code> (ejemplo: <i>mi_abuelo_memoriaviva_bot</i>).</li>
                        <li><b>@BotFather</b> te responderá con un <b>HTTP API Token</b>. Cópialo y pégalo debajo.</li>
                        <li>Por último, abre el enlace o escanea el código QR de la derecha y presiona <b>Iniciar (<code>/start</code>)</b> en tu bot para vincular tu celular.</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )

            tg_token_in = st.text_input(
                "Token del Bot de Telegram (HTTP API Token):",
                value=config.TELEGRAM_BOT_TOKEN,
                placeholder="Ej. 1234567890:AAF...",
            )
            tg_chat_in = st.text_input(
                "Chat ID del Cuidador (se detecta automáticamente al pulsar el botón):",
                value=config.TELEGRAM_CHAT_ID,
                placeholder="Ej. 987654321",
            )

            c_save_tg, c_det_tg = st.columns(2)
            with c_save_tg:
                if st.button("💾 Guardar Token y Verificar Bot", width="stretch"):
                    config.update_env_and_runtime_keys(
                        telegram_token=tg_token_in,
                        telegram_chat_id=tg_chat_in,
                    )
                    st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge(
                        bot_token=tg_token_in,
                        chat_id=tg_chat_in,
                    )
                    info = st.session_state.telegram_bridge.get_bot_info()
                    if info.get("ok"):
                        st.success(f"✅ Bot conectado: @{info.get('username')} ({info.get('first_name')})")
                    else:
                        st.error(f"No se pudo validar el token: {info.get('error')}")
            with c_det_tg:
                if st.button("🔍 Detectar mi Chat ID automáticamente", width="stretch"):
                    config.update_env_and_runtime_keys(telegram_token=tg_token_in)
                    st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge(
                        bot_token=tg_token_in,
                        chat_id=tg_chat_in,
                    )
                    disc = st.session_state.telegram_bridge.discover_latest_chat_id()
                    if disc.get("ok"):
                        config.update_env_and_runtime_keys(telegram_chat_id=disc["chat_id"])
                        st.success(f"✅ ¡Vinculado con {disc.get('first_name')} (Chat ID: {disc['chat_id']})!")
                        st.rerun()
                    else:
                        st.warning(disc.get("error", "Abre el bot en Telegram y presiona /start."))

        with col_qr:
            bridge: telegram_notifier.TelegramFamilyBridge = st.session_state.telegram_bridge
            info = bridge.get_bot_info() if bridge.bot_token else {"ok": False}
            bot_user = info.get("username") if info.get("ok") else "BotFather"
            qr_bytes, qr_url = bridge.generate_linking_qr_bytes(bot_user)
            st.image(qr_bytes, caption=f"Escanea para abrir @{bot_user}", width="stretch")
            st.markdown(f"🔗 **Enlace directo:** [{qr_url}]({qr_url})")
            if bridge.chat_id:
                st.success(f"📱 Teléfono vinculado (`{bridge.chat_id}`)")
            else:
                st.info("Si aún no vinculas tu celular, puedes continuar y hacerlo luego desde el Panel Familiar.")

        nav1, nav2 = st.columns(2)
        with nav1:
            if st.button("⬅️ Regresar al Paso 1", width="stretch"):
                st.session_state.onboarding_step = 1
                st.rerun()
        with nav2:
            if st.button("Siguiente: API Key de Gemini ➡️", width="stretch"):
                config.update_env_and_runtime_keys(telegram_token=tg_token_in, telegram_chat_id=tg_chat_in)
                st.session_state.onboarding_step = 3
                st.rerun()

    # --------------------------------------------------------------------------
    # PASO 3: TUTORIAL PASO A PASO PARA OBTENER API KEY DE GEMINI
    # --------------------------------------------------------------------------
    elif step == 3:
        st.markdown("### Paso 3 de 4 — Cómo Obtener e Ingresar tu API Key de Google Gemini")

        st.markdown(
            """
            <div class="mv-card">
                <h4>🤖 Tutorial paso a paso (100% Gratuito en Google AI Studio)</h4>
                <ol style="line-height:1.8; font-size:1.0rem;">
                    <li>Abre en tu navegador el portal oficial de <b>Google AI Studio</b>:
                        <a href="https://aistudio.google.com/app/apikey" target="_blank">https://aistudio.google.com/app/apikey</a></li>
                    <li>Inicia sesión con tu cuenta normal de Google (Gmail).</li>
                    <li>Haz clic en el botón azul <b>"Create API key"</b> (<i>Crear clave de API</i>) y elige o crea un proyecto.</li>
                    <li>Copia el código que aparece (ejemplo: <code>AIzaSy...</code> o <code>AQ....</code>) y pégalo en el campo de abajo.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        gemini_key_in = st.text_input(
            "Pega aquí tu API Key de Google Gemini:",
            value=config.GEMINI_API_KEY,
            type="password",
            placeholder="AIzaSy... o AQ....",
        )

        if st.button("🧪 Guardar y Probar Conexión con Gemini", width="stretch"):
            config.update_env_and_runtime_keys(gemini_key=gemini_key_in)
            if not gemini_key_in.strip():
                st.warning("Ingresa una API Key primero (si no tienes una aún, el sistema usará su motor gerontológico local de respaldo).")
            else:
                try:
                    from google import genai
                    client = genai.Client(
                        api_key=gemini_key_in.strip(),
                        http_options={"timeout": config.GEMINI_TIMEOUT_MS},
                    )
                    models_list = [m.name for m in client.models.list() if "gemini" in m.name]
                    st.success(f"✅ ¡API Key válida! Se detectaron {len(models_list)} modelos Gemini disponibles.")
                except Exception as exc:
                    st.warning(f"Clave guardada en .env (nota de prueba de red: {exc}).")

        nav1, nav2 = st.columns(2)
        with nav1:
            if st.button("⬅️ Regresar al Paso 2", width="stretch"):
                st.session_state.onboarding_step = 2
                st.rerun()
        with nav2:
            if st.button("Siguiente: Subir 10 Fotos del Protector de Pantalla ➡️", width="stretch"):
                if gemini_key_in.strip():
                    config.update_env_and_runtime_keys(gemini_key=gemini_key_in)
                st.session_state.onboarding_step = 4
                st.rerun()

    # --------------------------------------------------------------------------
    # PASO 4: MÍNIMO 10 FOTOGRAFÍAS PARA EL PROTECTOR DE PANTALLA
    # --------------------------------------------------------------------------
    elif step == 4:
        profile_id = st.session_state.onboarding_profile_id
        active_p = llm_companion.load_patient_profile(st.session_state.onboarding_profile_path)
        patient_name = active_p.get("paciente", {}).get("nombre_preferido", "Don Manuel")

        st.markdown("### Paso 4 de 4 — Álbum del Protector de Pantalla (Mínimo 10 Fotos)")
        st.write(
            f"Estas fotografías serán **lo único que {patient_name} verá rotando suavemente en su pantalla** "
            "como marco de recuerdos familiares cuando la computadora esté encendida."
        )

        uploaded_imgs = st.file_uploader(
            "Selecciona al menos 10 fotografías familiares (.jpg, .jpeg, .png, .webp):",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="onboarding_photo_uploader",
        )
        if uploaded_imgs:
            saved_list = system_integration.save_uploaded_photos(profile_id, uploaded_imgs)
            if saved_list:
                st.success(f"📸 Se guardaron {len(saved_list)} fotografías nuevas en el álbum.")

        col_fill, col_info = st.columns([1.4, 2.0])
        with col_fill:
            if st.button("🖼️ Completar con 10 Fotografías Nostálgicas de Muestra", width="stretch"):
                system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=patient_name)
                st.rerun()

        photo_count = system_integration.count_profile_photos(profile_id)
        min_req = config.MIN_SCREENSAVER_PHOTOS
        with col_info:
            st.progress(min(1.0, photo_count / min_req))
            if photo_count >= min_req:
                st.success(f"✅ Fotos cargadas: **{photo_count} / {min_req}** mínimo requerido. ¡Listo para activar!")
            else:
                st.warning(f"📷 Fotos cargadas: **{photo_count} / {min_req}** mínimo requerido. Sube {min_req - photo_count} más o usa el botón de muestra.")

        # Vista previa en cuadrícula de las fotos
        photos_data = system_integration.get_photos_as_data_uris(profile_id)
        if photos_data:
            st.markdown("#### Vista previa del álbum:")
            cols = st.columns(5)
            for idx, p_item in enumerate(photos_data):
                with cols[idx % 5]:
                    st.image(p_item["path"], caption=p_item["caption"], width="stretch")

        st.divider()
        nav1, nav2 = st.columns([1.0, 2.2])
        with nav1:
            if st.button("⬅️ Regresar al Paso 3", width="stretch"):
                st.session_state.onboarding_step = 3
                st.rerun()
        with nav2:
            can_finish = photo_count >= min_req
            if st.button(
                "✅ Finalizar Registro y Activar Modo Protector de Pantalla",
                width="stretch",
                disabled=not can_finish,
            ):
                draft = st.session_state.onboarding_draft or {}
                autostart_on = bool(draft.get("autostart_enabled", True))
                system_integration.set_windows_autostart(autostart_on)

                new_cfg = {
                    "is_registered": True,
                    "kiosk_locked_for_elder": True,
                    "caregiver_name": draft.get("caregiver_name", "Familiar"),
                    "caregiver_user": draft.get("caregiver_user", "cuidador"),
                    "pin_hash": draft.get("pin_hash") or system_integration.hash_pin("1234"),
                    "active_profile_path": st.session_state.onboarding_profile_path,
                    "autostart_enabled": autostart_on,
                    "rotation_interval_sec": 6,
                }
                system_integration.save_account_config(new_cfg)
                st.session_state.active_profile_path = new_cfg["active_profile_path"]
                st.session_state.caregiver_unlocked = False
                st.session_state.show_pin_modal = False
                st.rerun()


# ==============================================================================
# VISTA B: PANTALLA BLOQUEADA DEL ADULTO MAYOR (PROTECTOR 10+ FOTOS + ESPACIO)
# ==============================================================================
def render_elder_kiosk_screensaver(account_cfg: dict[str, Any]) -> None:
    inject_global_css(st.session_state.dark_mode, kiosk_mode=True)

    active_profile = llm_companion.load_patient_profile(st.session_state.active_profile_path)
    pac_info = active_profile.get("paciente", {})
    profile_id = pac_info.get("id", "don_manuel")
    nombre_paciente = pac_info.get("nombre_preferido", "Don Manuel")

    # Garantizar mínimo 10 fotografías listas para rotar
    if system_integration.count_profile_photos(profile_id) < config.MIN_SCREENSAVER_PHOTOS:
        system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=nombre_paciente)

    photos_list = system_integration.get_photos_as_data_uris(profile_id)
    photos_json = json.dumps(
        [{"caption": p["caption"], "data_uri": p["data_uri"]} for p in photos_list],
        ensure_ascii=False,
    )
    rotation_ms = int(account_cfg.get("rotation_interval_sec", 6)) * 1000

    last_turn = st.session_state.last_turn_result
    last_user_text = (last_turn.get("user_text", "") if last_turn else "").strip()
    last_reply = (
        last_turn["assistant_reply"]
        if last_turn
        else f"Aquí estoy contigo, {nombre_paciente}. Cuando quieras platicar, mantén presionada la barra espaciadora."
    )
    learned_facts = (last_turn.get("persisted_new_facts") or []) if last_turn else []
    learned_badge = (
        f"✨ Memoria Viva actualizada: se guardó en tu perfil ({'; '.join(learned_facts)})"
        if learned_facts
        else ""
    )

    audio_data_uri = _get_audio_data_uri(st.session_state.last_audio_response_path)
    user_text_json = json.dumps(last_user_text, ensure_ascii=False)
    reply_json = json.dumps(last_reply, ensure_ascii=False)
    learned_badge_json = json.dumps(learned_badge, ensure_ascii=False)
    patient_json = json.dumps(nombre_paciente, ensure_ascii=False)
    audio_json = json.dumps(audio_data_uri)

    # Botón oculto disparado automáticamente por JavaScript al soltar la tecla ESPACIO
    if st.button("_procesar_turno_espacio", key="ptt_hidden_trigger"):
        ptt_payload = audio_engine.consume_ptt_recorded_audio()
        if ptt_payload["mode"] == "live_audio":
            execute_full_turn_pipeline(
                raw_audio_bytes=ptt_payload["wav_bytes"] or None,
                browser_transcript=ptt_payload.get("browser_transcript") or None,
                browser_word_timestamps=ptt_payload.get("browser_word_timestamps") or None,
            )
        else:
            polite_retry = (
                f"Disculpe, {nombre_paciente}, no alcancé a escuchar su voz. "
                "Mantenga presionada la tecla ESPACIO mientras habla y suéltela al terminar."
            )
            tts_path = config.BASE_DIR / "temp_companion_reply.mp3"
            tts_res = audio_engine.speak_geriatric(polite_retry, output_path=tts_path)
            st.session_state.last_audio_response_path = tts_res["audio_path"]
            st.session_state.last_turn_result = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "user_text": "",
                "assistant_reply": polite_retry,
                "persisted_new_facts": [],
                "tts": tts_res,
            }
        st.rerun()

    # Componente interactivo a pantalla completa:
    # - Rota las 10+ fotos como protector de pantalla
    # - Escucha únicamente mientras se mantiene presionada la tecla ESPACIO
    # - Muestra Aura de Respiración Emocional al mantener ESPACIO
    # - Al soltar ESPACIO detiene el audio y dispara el procesamiento automático
    screensaver_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
    <meta charset="utf-8" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #14110F;
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #FAF6F0;
            user-select: none;
        }}
        .stage {{
            position: relative;
            width: 100%;
            height: 100vh;
            border-radius: 20px;
            overflow: hidden;
            background: #14110F;
        }}
        .slide-img {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0;
            transform: scale(1.0);
            transition: opacity 1.3s ease-in-out, transform 8s ease-out;
        }}
        .slide-img.active {{
            opacity: 1;
            transform: scale(1.06);
        }}
        .scrim-top {{
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 120px;
            background: linear-gradient(to bottom, rgba(18, 15, 13, 0.78), rgba(18, 15, 13, 0));
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 20px 28px;
            z-index: 3;
        }}
        .clock-pill {{
            background: rgba(28, 24, 21, 0.65);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 245, 232, 0.18);
            border-radius: 16px;
            padding: 10px 18px;
        }}
        .clock-time {{
            font-size: 1.65rem;
            font-weight: 700;
            color: #FAF6F0;
        }}
        .clock-sub {{
            font-size: 0.92rem;
            color: #E2D5C3;
        }}
        .album-badge {{
            background: rgba(28, 24, 21, 0.65);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 245, 232, 0.18);
            border-radius: 16px;
            padding: 8px 16px;
            font-size: 0.92rem;
            color: #E8C794;
        }}
        .scrim-bottom {{
            position: absolute;
            bottom: 0; left: 0; right: 0;
            background: linear-gradient(to top, rgba(16, 13, 11, 0.93) 35%, rgba(16, 13, 11, 0.60) 75%, rgba(16, 13, 11, 0));
            padding: 40px 34px 24px 34px;
            z-index: 4;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .photo-caption {{
            font-family: Georgia, serif;
            font-style: italic;
            font-size: 1.25rem;
            color: #E8C794;
            text-shadow: 0 2px 6px rgba(0,0,0,0.8);
        }}
        .user-bubble {{
            background: rgba(24, 21, 18, 0.72);
            backdrop-filter: blur(8px);
            border-left: 4px solid #D99B52;
            border-radius: 12px;
            padding: 10px 16px;
            font-size: 1.05rem;
            line-height: 1.4;
            color: #EADBC8;
            max-width: 900px;
            display: none;
        }}
        .learned-badge {{
            background: rgba(94, 126, 104, 0.28);
            border: 1px solid rgba(143, 179, 153, 0.45);
            border-radius: 10px;
            padding: 6px 14px;
            font-size: 0.90rem;
            color: #CFE6D5;
            width: fit-content;
            display: none;
        }}
        .reply-bubble {{
            background: rgba(34, 30, 26, 0.84);
            backdrop-filter: blur(10px);
            border-left: 5px solid #7D9D86;
            border-radius: 14px;
            padding: 14px 20px;
            font-size: 1.30rem;
            line-height: 1.45;
            color: #FAF6F0;
            max-width: 900px;
        }}
        .spacebar-bar {{
            margin-top: 4px;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: rgba(94, 126, 104, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 14px;
            padding: 11px 22px;
            font-size: 1.08rem;
            font-weight: 600;
            color: #FFFFFF;
            width: fit-content;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }}
        .keycap {{
            background: #FAF6F0;
            color: #2E2620;
            padding: 3px 12px;
            border-radius: 7px;
            font-weight: 800;
            font-size: 0.95rem;
            letter-spacing: 0.8px;
        }}

        /* OVERLAY: AURA DE RESPIRACIÓN EMOCIONAL AL MANTENER ESPACIO */
        .overlay-listening, .overlay-processing {{
            position: absolute;
            inset: 0;
            z-index: 20;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 30px;
            background: radial-gradient(circle, rgba(36, 44, 38, 0.95) 0%, rgba(20, 18, 16, 0.97) 100%);
            backdrop-filter: blur(12px);
        }}
        .overlay-listening.visible, .overlay-processing.visible {{
            display: flex;
        }}
        @keyframes breatheAura {{
            0% {{
                transform: scale(0.88);
                box-shadow: 0 0 0 0 rgba(125, 157, 134, 0.55), 0 0 40px 15px rgba(217, 155, 82, 0.30);
            }}
            50% {{
                transform: scale(1.10);
                box-shadow: 0 0 0 42px rgba(125, 157, 134, 0.14), 0 0 85px 35px rgba(217, 155, 82, 0.45);
            }}
            100% {{
                transform: scale(0.88);
                box-shadow: 0 0 0 0 rgba(125, 157, 134, 0.55), 0 0 40px 15px rgba(217, 155, 82, 0.30);
            }}
        }}
        .aura-orb {{
            width: 190px;
            height: 190px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 35%, #E8B878, #7D9D86 70%, #4E6D58 100%);
            animation: breatheAura 4.0s ease-in-out infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.6rem;
            margin-bottom: 28px;
        }}
        .aura-title {{
            font-size: 2.1rem;
            font-weight: 700;
            color: #FAF6F0;
            margin-bottom: 10px;
        }}
        .aura-sub {{
            font-size: 1.3rem;
            color: #D7CCBC;
            max-width: 620px;
        }}
        .aura-timer {{
            margin-top: 18px;
            font-size: 1.15rem;
            color: #E8C794;
            font-weight: 600;
        }}
    </style>
    </head>
    <body>
        <div class="stage" id="mv-stage" tabindex="0">
            <img id="slide-a" class="slide-img active" alt="Recuerdo A" />
            <img id="slide-b" class="slide-img" alt="Recuerdo B" />

            <div class="scrim-top">
                <div class="clock-pill">
                    <div class="clock-time" id="mv-clock">--:--</div>
                    <div class="clock-sub">Compañero de <span id="mv-patient"></span></div>
                </div>
                <div class="album-badge" id="mv-album-count">🖼️ Álbum Familiar</div>
            </div>

            <div class="scrim-bottom">
                <div class="photo-caption" id="mv-caption"></div>
                <div class="user-bubble" id="mv-user-said"></div>
                <div class="reply-bubble" id="mv-reply"></div>
                <div class="learned-badge" id="mv-learned"></div>
                <div class="spacebar-bar">
                    <span class="keycap">ESPACIO</span>
                    <span>Mantén presionado para hablar · Suéltalo al terminar</span>
                </div>
            </div>

            <div class="overlay-listening" id="overlay-listen">
                <div class="aura-orb">🎙️</div>
                <div class="aura-title" id="listen-title">Te escucho con toda calma...</div>
                <div class="aura-sub">No tengas prisa. Suelta la tecla <b>ESPACIO</b> cuando hayas terminado de hablar.</div>
                <div class="aura-timer" id="listen-timer">Escuchando: 0.0 s</div>
                <div id="live-speech-preview" style="margin-top:16px; font-size:1.18rem; color:#F2E8D8; max-width:680px; min-height:28px; font-style:italic;"></div>
            </div>

            <div class="overlay-processing" id="overlay-proc">
                <div class="aura-orb" style="animation:none; width:130px; height:130px; font-size:2.6rem;">🌿</div>
                <div class="aura-title">Procesando tu recuerdo con cariño...</div>
                <div class="aura-sub">Un segundito, estoy preparando mi respuesta para ti.</div>
            </div>
        </div>

        <audio id="mv-audio-player" style="display:none;"></audio>

        <script>
            const PHOTOS = {photos_json};
            const ROTATION_MS = {rotation_ms};
            const PATIENT_NAME = {patient_json};
            const LAST_USER_TEXT = {user_text_json};
            const LAST_REPLY = {reply_json};
            const LEARNED_BADGE = {learned_badge_json};
            const AUDIO_DATA_URI = {audio_json};
            const PTT_URL = "http://127.0.0.1:{PTT_PORT}";

            document.getElementById("mv-patient").textContent = PATIENT_NAME;
            document.getElementById("listen-title").textContent = "Te escucho con toda calma, " + PATIENT_NAME + "...";

            const userSaidEl = document.getElementById("mv-user-said");
            if (LAST_USER_TEXT && LAST_USER_TEXT.length > 0) {{
                userSaidEl.textContent = "👤 Dijiste: “" + LAST_USER_TEXT + "”";
                userSaidEl.style.display = "block";
            }}

            const replyEl = document.getElementById("mv-reply");
            replyEl.innerHTML = "";
            const replyPrefix = document.createElement("b");
            replyPrefix.textContent = "🗣️ MemoriaViva: ";
            const replyBody = document.createElement("span");
            replyBody.textContent = "“" + LAST_REPLY + "”";
            replyEl.appendChild(replyPrefix);
            replyEl.appendChild(replyBody);

            const learnedEl = document.getElementById("mv-learned");
            if (LEARNED_BADGE && LEARNED_BADGE.length > 0) {{
                learnedEl.textContent = LEARNED_BADGE;
                learnedEl.style.display = "block";
            }}

            document.getElementById("mv-album-count").textContent = "🖼️ Álbum Familiar (" + PHOTOS.length + " fotos)";

            // Reloj en vivo
            function updateClock() {{
                const now = new Date();
                const hh = String(now.getHours()).padStart(2, '0');
                const mm = String(now.getMinutes()).padStart(2, '0');
                document.getElementById("mv-clock").textContent = hh + ":" + mm;
            }}
            updateClock();
            setInterval(updateClock, 10000);

            // Reproducción automática de la respuesta neural más reciente
            if (AUDIO_DATA_URI && AUDIO_DATA_URI.length > 20) {{
                const audioEl = document.getElementById("mv-audio-player");
                audioEl.src = AUDIO_DATA_URI;
                audioEl.play().catch(() => {{}});
            }}

            // Protector de pantalla rotando las 10+ fotos con crossfade suave
            let currentIdx = 0;
            let showingA = true;
            const imgA = document.getElementById("slide-a");
            const imgB = document.getElementById("slide-b");
            const capEl = document.getElementById("mv-caption");

            function showPhoto(idx) {{
                if (!PHOTOS.length) return;
                const item = PHOTOS[idx % PHOTOS.length];
                capEl.textContent = item.caption || "";
                if (showingA) {{
                    imgB.src = item.data_uri;
                    imgB.classList.add("active");
                    imgA.classList.remove("active");
                }} else {{
                    imgA.src = item.data_uri;
                    imgA.classList.add("active");
                    imgB.classList.remove("active");
                }}
                showingA = !showingA;
            }}

            if (PHOTOS.length > 0) {{
                imgA.src = PHOTOS[0].data_uri;
                capEl.textContent = PHOTOS[0].caption || "";
                setInterval(() => {{
                    currentIdx = (currentIdx + 1) % PHOTOS.length;
                    showPhoto(currentIdx);
                }}, ROTATION_MS);
            }}

            // Push-to-Talk exclusivo con barra ESPACIADORA + Web SpeechRecognition en vivo
            let isSpaceHeld = false;
            let listenStartMs = 0;
            let timerInterval = null;
            let recognition = null;
            let finalTranscriptParts = [];
            let interimTranscript = "";
            let wordTimestamps = [];
            let lastSegmentEndSec = 0.0;

            const listenOverlay = document.getElementById("overlay-listen");
            const procOverlay = document.getElementById("overlay-proc");
            const timerEl = document.getElementById("listen-timer");
            const liveSpeechEl = document.getElementById("live-speech-preview");

            function startBrowserSpeechRecognition() {{
                finalTranscriptParts = [];
                interimTranscript = "";
                wordTimestamps = [];
                lastSegmentEndSec = 0.0;
                liveSpeechEl.textContent = "";

                const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRec) return;

                try {{
                    recognition = new SpeechRec();
                    recognition.lang = "es-MX";
                    recognition.continuous = true;
                    recognition.interimResults = true;

                    recognition.onresult = (event) => {{
                        let interim = "";
                        for (let i = event.resultIndex; i < event.results.length; i++) {{
                            const textSeg = (event.results[i][0].transcript || "").trim();
                            if (!textSeg) continue;
                            if (event.results[i].isFinal) {{
                                finalTranscriptParts.push(textSeg);
                                const nowSec = Math.max(lastSegmentEndSec + 0.05, (Date.now() - listenStartMs) / 1000);
                                const words = textSeg.split(/\\s+/);
                                const approxStart = Math.max(lastSegmentEndSec, nowSec - words.length * 0.32);
                                const step = (nowSec - approxStart) / Math.max(1, words.length);
                                words.forEach((w, idx) => {{
                                    const s = Number((approxStart + idx * step).toFixed(2));
                                    const e = Number((approxStart + (idx + 0.85) * step).toFixed(2));
                                    wordTimestamps.push({{ word: w, start: s, end: e }});
                                }});
                                lastSegmentEndSec = nowSec;
                            }} else {{
                                interim += textSeg + " ";
                            }}
                        }}
                        interimTranscript = interim.trim();
                        const preview = (finalTranscriptParts.join(" ") + " " + interimTranscript).trim();
                        if (preview) {{
                            liveSpeechEl.textContent = "🗣️ “" + preview + "”";
                        }}
                    }};
                    recognition.onerror = () => {{}};
                    recognition.start();
                }} catch (err) {{
                    recognition = null;
                }}
            }}

            function isTypingInField(ev) {{
                let activeTag = "";
                try {{
                    activeTag = (window.parent.document.activeElement?.tagName || "").toUpperCase();
                }} catch (e) {{}}
                const targetTag = (ev.target && ev.target.tagName) ? ev.target.tagName.toUpperCase() : "";
                return ["INPUT", "TEXTAREA", "SELECT"].includes(activeTag) || ["INPUT", "TEXTAREA", "SELECT"].includes(targetTag);
            }}

            function triggerStreamlitProcessing() {{
                try {{
                    const parentDoc = window.parent.document;
                    const btns = Array.from(parentDoc.querySelectorAll("button"));
                    const hiddenBtn = btns.find(b => b.innerText && b.innerText.includes("_procesar_turno_espacio"));
                    if (hiddenBtn) {{
                        hiddenBtn.click();
                    }}
                }} catch (err) {{
                    console.error("Error disparando procesamiento Streamlit:", err);
                }}
            }}

            function handleKeyDown(ev) {{
                if (isTypingInField(ev)) return;
                if (ev.code === "Space" || ev.key === " ") {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    if (ev.repeat || isSpaceHeld) return;
                    isSpaceHeld = true;

                    // Detener audio actual si estaba hablando
                    const audioEl = document.getElementById("mv-audio-player");
                    if (audioEl) {{ try {{ audioEl.pause(); }} catch (e) {{}} }}

                    listenStartMs = Date.now();
                    timerEl.textContent = "Escuchando: 0.0 s";
                    listenOverlay.classList.add("visible");
                    if (timerInterval) clearInterval(timerInterval);
                    timerInterval = setInterval(() => {{
                        const secs = ((Date.now() - listenStartMs) / 1000).toFixed(1);
                        timerEl.textContent = "Escuchando: " + secs + " s";
                    }}, 100);

                    fetch(PTT_URL + "/ptt/start", {{ method: "POST" }}).catch(() => {{}});
                    startBrowserSpeechRecognition();
                }}
            }}

            function handleKeyUp(ev) {{
                if (!isSpaceHeld) return;
                if (ev.code === "Space" || ev.key === " ") {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    isSpaceHeld = false;
                    if (timerInterval) clearInterval(timerInterval);
                    listenOverlay.classList.remove("visible");
                    procOverlay.classList.add("visible");

                    if (recognition) {{
                        try {{ recognition.stop(); }} catch (e) {{}}
                    }}

                    setTimeout(() => {{
                        const combinedTranscript = (finalTranscriptParts.join(" ") + " " + interimTranscript).trim();
                        fetch(PTT_URL + "/ptt/stop", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{
                                browser_transcript: combinedTranscript,
                                browser_word_timestamps: wordTimestamps
                            }})
                        }})
                            .then(() => triggerStreamlitProcessing())
                            .catch(() => triggerStreamlitProcessing());
                    }}, 180);
                }}
            }}

            // Limpiar listeners previos en parent al recargar Streamlit
            try {{
                if (window.parent.__mvPttCleanup) {{
                    window.parent.__mvPttCleanup();
                }}
            }} catch (e) {{}}

            window.addEventListener("keydown", handleKeyDown, true);
            window.addEventListener("keyup", handleKeyUp, true);

            try {{
                const pDoc = window.parent.document;
                pDoc.addEventListener("keydown", handleKeyDown, true);
                pDoc.addEventListener("keyup", handleKeyUp, true);
                window.parent.__mvPttCleanup = () => {{
                    pDoc.removeEventListener("keydown", handleKeyDown, true);
                    pDoc.removeEventListener("keyup", handleKeyUp, true);
                }};
            }} catch (e) {{}}

            // Mantener foco para escuchar la tecla ESPACIO inmediatamente
            document.getElementById("mv-stage").focus();
        </script>
    </body>
    </html>
    """
    components.html(screensaver_html, height=580, scrolling=False)

    # Acceso discreto del cuidador en esquina inferior derecha (protegido con PIN)
    _, col_lock = st.columns([3.8, 1.3])
    with col_lock:
        if not st.session_state.show_pin_modal:
            if st.button("🔒 Desbloquear Panel Familiar (PIN)", width="stretch"):
                st.session_state.show_pin_modal = True
                st.rerun()
        else:
            with st.form("unlock_pin_form"):
                st.markdown("##### 🔐 Ingresa el PIN del Cuidador")
                pin_input = st.text_input("PIN / Contraseña:", type="password", placeholder="****")
                c_ok, c_can = st.columns(2)
                with c_ok:
                    if st.form_submit_button("🔓 Entrar", width="stretch"):
                        if system_integration.verify_pin(pin_input, account_cfg.get("pin_hash", "")):
                            st.session_state.caregiver_unlocked = True
                            st.session_state.show_pin_modal = False
                            st.rerun()
                        else:
                            st.error("PIN incorrecto.")
                with c_can:
                    if st.form_submit_button("Cancelar", width="stretch"):
                        st.session_state.show_pin_modal = False
                        st.rerun()


# ==============================================================================
# VISTA C: PANEL FAMILIAR Y MÉDICO DESBLOQUEADO (SOLO CON PIN)
# ==============================================================================
def render_caregiver_panel(account_cfg: dict[str, Any]) -> None:
    inject_global_css(st.session_state.dark_mode, kiosk_mode=False)

    active_profile = llm_companion.load_patient_profile(st.session_state.active_profile_path)
    pac_info = active_profile.get("paciente", {})
    fam_info = active_profile.get("red_familiar_y_afectiva", {})
    profile_id = pac_info.get("id", "don_manuel")
    nombre_paciente = pac_info.get("nombre_preferido", "Don Manuel")
    nombre_cuidador = (
        fam_info.get("hija_mayor_cuidadora", {}).get("nombre")
        or account_cfg.get("caregiver_name")
        or "Laura"
    )

    # Barra Superior del Panel Familiar
    col_info, col_theme, col_lock = st.columns([3.0, 1.0, 1.4])
    with col_info:
        autostart_txt = "🟢 Inicio con Windows: Activo" if system_integration.is_windows_autostart_enabled() else "⚪ Inicio con Windows: Inactivo"
        st.markdown(
            f"""
            <div class="mv-topbar">
                <div>
                    <div style="font-size:1.25rem; font-weight:700;">🌿 MemoriaViva RISE — Panel de {nombre_cuidador}</div>
                    <div style="font-size:0.88rem; opacity:0.85;">Paciente: <b>{pac_info.get('nombre_completo', nombre_paciente)}</b> · {autostart_txt}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_theme:
        theme_lbl = "☀️ Modo Día" if st.session_state.dark_mode else "🌙 Modo Noche"
        if st.button(theme_lbl, width="stretch"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with col_lock:
        if st.button("🔒 Bloquear Pantalla para el Abuelo", width="stretch"):
            account_cfg["kiosk_locked_for_elder"] = True
            system_integration.save_account_config(account_cfg)
            st.session_state.caregiver_unlocked = False
            st.session_state.show_pin_modal = False
            st.rerun()

    tab_board, tab_photos, tab_settings = st.tabs(
        [
            "📊 Tablero Longitudinal (21 Días, Telegram y PDF)",
            f"🖼️ Protector de Pantalla ({system_integration.count_profile_photos(profile_id)} Fotos)",
            "⚙️ Perfil, Credenciales, Windows y Demo",
        ]
    )

    # --------------------------------------------------------------------------
    # PESTAÑA 1: TABLERO LONGITUDINAL + TELEGRAM + PDF
    # --------------------------------------------------------------------------
    with tab_board:
        trend_data = biomarkers.evaluate_longitudinal_trend(st.session_state.history_21_days)
        pos_cats = trend_data.get("positive_categories", {})

        c_vit, c_mem, c_rit = st.columns(3)
        with c_vit:
            st.markdown(
                f"""
                <div class="positive-card">
                    <div style="font-size:0.92rem; opacity:0.85; font-weight:600;">🌿 Vitalidad Conversacional</div>
                    <div style="font-size:1.3rem; font-weight:700; margin:0.25rem 0;">{pos_cats.get('vitalidad_conversacional')}</div>
                    <div style="font-size:0.84rem; opacity:0.8;">Ánimo e interés durante la reminiscencia.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_mem:
            st.markdown(
                f"""
                <div class="positive-card positive-card-amber">
                    <div style="font-size:0.92rem; opacity:0.85; font-weight:600;">🧠 Agilidad de Memoria (MATTR)</div>
                    <div style="font-size:1.3rem; font-weight:700; margin:0.25rem 0;">{trend_data.get('recent_mattr')} <span style="font-size:0.9rem; font-weight:400;">(Base: {trend_data.get('baseline_mattr')})</span></div>
                    <div style="font-size:0.84rem; opacity:0.8;">{pos_cats.get('agilidad_memoria')} (-{trend_data.get('mattr_drop_pct')}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_rit:
            st.markdown(
                f"""
                <div class="positive-card positive-card-amber">
                    <div style="font-size:0.92rem; opacity:0.85; font-weight:600;">⏱️ Ritmo del Habla (Pausas)</div>
                    <div style="font-size:1.3rem; font-weight:700; margin:0.25rem 0;">{trend_data.get('recent_pause')}s <span style="font-size:0.9rem; font-weight:400;">(Base: {trend_data.get('baseline_pause')}s)</span></div>
                    <div style="font-size:0.84rem; opacity:0.8;">{pos_cats.get('ritmo_del_habla')} (+{trend_data.get('pause_increase_pct')}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")
        col_charts, col_tg = st.columns([1.8, 1.0], gap="large")

        with col_charts:
            df_hist = pd.DataFrame(st.session_state.history_21_days)
            chart_paper = "#26221F" if st.session_state.dark_mode else "#FFFDF9"
            chart_plot = "#1C1917" if st.session_state.dark_mode else "#FAF6F0"
            chart_text = "#EDE3D5" if st.session_state.dark_mode else "#3A322C"
            chart_grid = "#3A332C" if st.session_state.dark_mode else "#E6DDD0"

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_hist["day"],
                    y=df_hist["mattr"],
                    name="Riqueza Léxica (MATTR)",
                    mode="lines+markers",
                    line=dict(color="#7D9D86", width=3),
                    yaxis="y1",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_hist["day"],
                    y=df_hist["mean_pause"],
                    name="Pausa Promedio (seg)",
                    mode="lines+markers",
                    line=dict(color="#D99B52", width=3),
                    yaxis="y2",
                )
            )
            fig.update_layout(
                title="Seguimiento Longitudinal de 21 Días (Línea Base Personalizada)",
                paper_bgcolor=chart_paper,
                plot_bgcolor=chart_plot,
                font=dict(color=chart_text),
                height=340,
                margin=dict(l=20, r=20, t=42, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor=chart_grid),
                yaxis=dict(title="MATTR", range=[0.40, 0.90], gridcolor=chart_grid),
                yaxis2=dict(title="Pausa (seg)", overlaying="y", side="right", range=[0.5, 3.6]),
            )
            st.plotly_chart(fig, width="stretch")

            b_pdf, b_warn = st.columns(2)
            with b_pdf:
                pdf_bytes = pdf_report.generate_clinical_pdf_bytes(
                    profile=active_profile,
                    trend_summary=trend_data,
                    history_records=st.session_state.history_21_days,
                )
                st.download_button(
                    label="📄 Descargar Reporte PDF para el Geriatra",
                    data=pdf_bytes,
                    file_name=f"Reporte_MemoriaViva_{profile_id}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
            with b_warn:
                if st.button("🟡 Enviar Aviso Preventivo Nivel 2 a Telegram", width="stretch"):
                    st.session_state.telegram_bridge.send_level2_clinical_trend_warning(
                        baseline_pause=trend_data["baseline_pause"],
                        recent_pause=trend_data["recent_pause"],
                        baseline_mattr=trend_data["baseline_mattr"],
                        recent_mattr=trend_data["recent_mattr"],
                        patient_name=nombre_paciente,
                        caregiver_name=nombre_cuidador,
                    )
                    st.rerun()

        with col_tg:
            st.markdown(f"#### 📱 Notificaciones a {nombre_cuidador}")
            msg_log = list(reversed(st.session_state.telegram_bridge.message_log))
            if not msg_log:
                st.markdown(
                    f"""
                    <div class="tg-card-1">
                        <b>🟢 Puente Familiar Listo</b><br>
                        Cuando {nombre_paciente} platique con la barra espaciadora, aquí aparecerá su resumen y tema sugerido para la cena.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                for item in msg_log[:3]:
                    lvl = item["level"]
                    css_cls = "tg-card-1" if lvl == 1 else ("tg-card-2" if lvl == 2 else "tg-card-3")
                    clean_html_msg = item["message"].replace("\n", "<br>")
                    st.markdown(
                        f"""
                        <div class="{css_cls}">
                            <div style="font-size:0.75rem; opacity:0.8; margin-bottom:4px;">
                                ⏰ {item['timestamp']} · Latencia: {item['latency_ms']} ms
                            </div>
                            <div>{clean_html_msg}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # --------------------------------------------------------------------------
    # PESTAÑA 2: GESTOR DE LAS 10+ FOTOS DEL PROTECTOR DE PANTALLA
    # --------------------------------------------------------------------------
    with tab_photos:
        st.markdown("#### 🖼️ Fotos del Protector de Pantalla del Adulto Mayor")
        p_count = system_integration.count_profile_photos(profile_id)
        st.progress(min(1.0, p_count / config.MIN_SCREENSAVER_PHOTOS))
        st.caption(f"Actualmente hay **{p_count}** fotografías (mínimo recomendado: {config.MIN_SCREENSAVER_PHOTOS}).")

        c_up, c_rot = st.columns([2.2, 1.0])
        with c_up:
            more_imgs = st.file_uploader(
                "Agregar más fotografías familiares:",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="caregiver_photo_uploader",
            )
            if more_imgs:
                added = system_integration.save_uploaded_photos(profile_id, more_imgs)
                if added:
                    st.success(f"Se agregaron {len(added)} fotografías al protector de pantalla.")
        with c_rot:
            rot_sec = st.slider(
                "Segundos por foto:",
                min_value=4,
                max_value=15,
                value=int(account_cfg.get("rotation_interval_sec", 6)),
            )
            if rot_sec != int(account_cfg.get("rotation_interval_sec", 6)):
                account_cfg["rotation_interval_sec"] = rot_sec
                system_integration.save_account_config(account_cfg)

            if st.button("🖼️ Completar Mínimo 10 Fotos de Muestra", width="stretch"):
                system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=nombre_paciente)
                st.rerun()

        photos_data = system_integration.get_photos_as_data_uris(profile_id)
        if photos_data:
            grid = st.columns(4)
            for idx, p_item in enumerate(photos_data):
                with grid[idx % 4]:
                    st.image(p_item["path"], caption=p_item["caption"], width="stretch")
                    if len(photos_data) > config.MIN_SCREENSAVER_PHOTOS:
                        if st.button("🗑️ Quitar", key=f"del_photo_{p_item['filename']}", width="stretch"):
                            system_integration.delete_profile_photo(profile_id, p_item["filename"])
                            st.rerun()

    # --------------------------------------------------------------------------
    # PESTAÑA 3: PERFIL, CREDENCIALES, ARRANQUE WINDOWS Y DEMO FAIL-SAFE
    # --------------------------------------------------------------------------
    with tab_settings:
        col_s1, col_s2 = st.columns(2, gap="large")

        with col_s1:
            st.markdown("#### 💻 Arranque Automático con Windows y Perfil Activo")
            available_profiles = llm_companion.list_available_profiles()
            labels = [f"{p['nombre_preferido']} ({p['edad']} años)" for p in available_profiles]
            cur_idx = next(
                (i for i, p in enumerate(available_profiles) if p["path"] == st.session_state.active_profile_path),
                0,
            )
            sel_idx = st.selectbox(
                "Paciente Activo en el Protector de Pantalla:",
                options=range(len(available_profiles)),
                format_func=lambda i: labels[i],
                index=cur_idx,
            )
            if available_profiles and available_profiles[sel_idx]["path"] != st.session_state.active_profile_path:
                st.session_state.active_profile_path = available_profiles[sel_idx]["path"]
                account_cfg["active_profile_path"] = st.session_state.active_profile_path
                system_integration.save_account_config(account_cfg)
                st.rerun()

            win_auto = st.checkbox(
                "💻 Arrancar MemoriaViva automáticamente al encender esta PC",
                value=system_integration.is_windows_autostart_enabled(),
            )
            if st.button("Aplicar Configuración de Inicio en Windows", width="stretch"):
                res_auto = system_integration.set_windows_autostart(win_auto)
                account_cfg["autostart_enabled"] = win_auto
                system_integration.save_account_config(account_cfg)
                if res_auto["enabled"]:
                    st.success(f"✅ Arranque automático activado en Startup de Windows.")
                else:
                    st.info("Arranque automático deshabilitado.")

            st.divider()
            st.markdown("#### 🎭 Pruebas Rápidas y Demo del Pitch")
            d1, d2, d3 = st.columns(3)
            with d1:
                if st.button("🟢 Demo 1", width="stretch"):
                    execute_full_turn_pipeline(demo_scenario_id="demo_1_rescate")
                    st.rerun()
            with d2:
                if st.button("🟡 Demo 2", width="stretch"):
                    execute_full_turn_pipeline(demo_scenario_id="demo_2_anomia")
                    st.rerun()
            with d3:
                if st.button("🔴 Demo 3", width="stretch"):
                    execute_full_turn_pipeline(demo_scenario_id="demo_3_crisis")
                    st.rerun()

            if st.button("🔄 Restablecer Registro Inicial (Volver al Onboarding)", width="stretch"):
                account_cfg["is_registered"] = False
                system_integration.save_account_config(account_cfg)
                st.session_state.onboarding_step = 1
                st.session_state.caregiver_unlocked = False
                st.rerun()

        with col_s2:
            st.markdown("#### 🔑 Credenciales de Telegram y Google Gemini")
            new_gemini = st.text_input("API Key de Gemini:", value=config.GEMINI_API_KEY, type="password")
            new_tg_tok = st.text_input("Token Bot de Telegram:", value=config.TELEGRAM_BOT_TOKEN)
            new_tg_cid = st.text_input("Chat ID de Telegram:", value=config.TELEGRAM_CHAT_ID)

            c_cred1, c_cred2 = st.columns(2)
            with c_cred1:
                if st.button("💾 Actualizar Credenciales", width="stretch"):
                    config.update_env_and_runtime_keys(
                        gemini_key=new_gemini,
                        telegram_token=new_tg_tok,
                        telegram_chat_id=new_tg_cid,
                    )
                    st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge(
                        bot_token=new_tg_tok,
                        chat_id=new_tg_cid,
                    )
                    st.success("✅ Credenciales guardadas en .env.")
            with c_cred2:
                if st.button("🔍 Detectar Chat ID", width="stretch"):
                    disc = st.session_state.telegram_bridge.discover_latest_chat_id()
                    if disc.get("ok"):
                        config.update_env_and_runtime_keys(telegram_chat_id=disc["chat_id"])
                        st.success(f"Vinculado: {disc['chat_id']}")
                        st.rerun()
                    else:
                        st.warning(disc.get("error"))

            bridge = st.session_state.telegram_bridge
            qr_bytes, qr_url = bridge.generate_linking_qr_bytes()
            st.image(qr_bytes, caption=f"QR de vinculación: {qr_url}", width=170)


# ==============================================================================
# Enrutador Principal de Vistas
# ==============================================================================
def main() -> None:
    account_cfg = system_integration.load_account_config()

    if not account_cfg.get("is_registered", False):
        # VISTA A: Registro Único Inicial (si aún no hay cuenta en este equipo)
        render_onboarding_wizard()
    elif not st.session_state.caregiver_unlocked and account_cfg.get("kiosk_locked_for_elder", True):
        # VISTA B: Pantalla Bloqueada del Adulto Mayor (Protector 10+ Fotos + Tecla ESPACIO)
        render_elder_kiosk_screensaver(account_cfg)
    else:
        # VISTA C: Panel Familiar y Médico Desbloqueado
        render_caregiver_panel(account_cfg)


main()
