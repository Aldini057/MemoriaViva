"""
MemoriaViva RISE - Aplicación Principal
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Flujo de Usuario Completo (Diseño Clínico Moderno):
1. VISTA A — Registro Único Inicial (si `is_registered == False`):
   Asistente centrado de 4 pasos con divulgación progresiva:
   - Paso 1: Datos esenciales del adulto mayor + PIN del cuidador (detalles biográficos opcionales colapsables).
   - Paso 2: Vinculación del Bot Familiar de Telegram + QR (guía @BotFather colapsable).
   - Paso 3: Clave API de Google Gemini (guía rápida colapsable).
   - Paso 4: Álbum de mínimo 10 fotografías para el protector de pantalla.
2. VISTA B — Modo Kiosco del Adulto Mayor (Protector de Pantalla Inmersivo):
   - Fotografía a pantalla completa con reloj discreto y tarjeta translúcida limpia.
   - Control de voz dual: mantener presionada la tecla ESPACIO o el botón táctil/clic.
   - Ícono discreto de candado en esquina superior derecha (o Ctrl+Shift+L) que abre modal PIN.
3. VISTA C — Panel Familiar y Médico (Desbloqueado con PIN):
   - 4 secciones claras: Resumen Clínico, Álbum Familiar, Configuración y Simulador Demo.
"""

from __future__ import annotations

import base64
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

import audio_engine
import biomarkers
import config
import llm_companion
import pdf_report
import system_integration
import telegram_notifier
import ui_design

# ==============================================================================
# Configuración de Página e Inicio del Micro-Servidor Push-to-Talk
# ==============================================================================
st.set_page_config(
    page_title="MemoriaViva RISE",
    page_icon=":material/monitor_heart:",
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
                "¿Me lo puede repetir manteniendo presionado el botón o la barra espaciadora?"
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


def _fill_onboarding_sample_don_manuel() -> None:
    """Rellena los datos de ejemplo de Don Manuel en el estado de sesión."""
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
    st.session_state["ob_autostart"] = True


# ==============================================================================
# VISTA A: ASISTENTE DE REGISTRO INICIAL (ONBOARDING CENTRADO EN 4 PASOS)
# ==============================================================================
def render_onboarding_wizard() -> None:
    is_dark = st.session_state.dark_mode
    ui_design.inject_design_system_css(is_dark, kiosk_mode=False, narrow_onboarding=True)

    step = st.session_state.onboarding_step

    # Cabecera minimalista centrada
    col_brand, col_theme = st.columns([3.6, 1.1], vertical_alignment="center")
    with col_brand:
        st.markdown(
            ui_design.render_brand_header_html(
                title="MemoriaViva",
                subtitle=f"Configuración inicial · Paso {step} de 4",
                badge_text="RISE",
            ),
            unsafe_allow_html=True,
        )
    with col_theme:
        theme_lbl = "Día" if is_dark else "Noche"
        theme_icon = ":material/light_mode:" if is_dark else ":material/dark_mode:"
        if st.button(theme_lbl, icon=theme_icon, type="secondary", width="stretch"):
            st.session_state.dark_mode = not is_dark
            st.rerun()

    st.markdown(
        ui_design.render_stepper_html(
            current_step=step,
            labels=["Perfil esencial", "Telegram", "Gemini AI", "Álbum (10 fotos)"],
            is_dark=is_dark,
        ),
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # PASO 1: DATOS ESENCIALES + DIVULGACIÓN PROGRESIVA
    # --------------------------------------------------------------------------
    if step == 1:
        hdr_c1, hdr_c2 = st.columns([2.6, 1.4], vertical_alignment="center")
        with hdr_c1:
            st.markdown(
                ui_design.render_section_header_html(
                    title="Perfil esencial y bloqueo familiar",
                    subtitle="Solo pedimos lo indispensable para iniciar. Puedes ampliar su historia en el desplegable.",
                    icon_name="user",
                ),
                unsafe_allow_html=True,
            )
        with hdr_c2:
            if st.button(
                "Cargar ejemplo",
                icon=":material/auto_awesome:",
                type="secondary",
                width="stretch",
                help="Completa los datos de demostración de Don Manuel",
            ):
                _fill_onboarding_sample_don_manuel()
                st.rerun()

        with st.form("onboarding_step1_form"):
            c1, c2 = st.columns(2)
            with c1:
                ob_nombre_completo = st.text_input(
                    "Nombre completo del adulto mayor *",
                    value=st.session_state.get("ob_nombre_completo", ""),
                    placeholder="Ej. Manuel González Magaña",
                )
                ob_cuidador = st.text_input(
                    "Nombre del familiar responsable *",
                    value=st.session_state.get("ob_cuidador", ""),
                    placeholder="Ej. Laura",
                )
                ob_pin = st.text_input(
                    "PIN de desbloqueo familiar (mín. 4) *",
                    value=st.session_state.get("ob_pin", ""),
                    type="password",
                    placeholder="Ej. 1234",
                )
            with c2:
                ob_nombre_pref = st.text_input(
                    "¿Cómo prefiere que le llamen? *",
                    value=st.session_state.get("ob_nombre_pref", ""),
                    placeholder="Ej. Don Manuel",
                )
                ob_usuario = st.text_input(
                    "Usuario de acceso familiar *",
                    value=st.session_state.get("ob_usuario", ""),
                    placeholder="Ej. laura.cuidadora",
                )
                ob_pin2 = st.text_input(
                    "Confirmar PIN *",
                    value=st.session_state.get("ob_pin2", ""),
                    type="password",
                    placeholder="Repite tu PIN",
                )

            with st.expander("Detalles biográficos, recuerdos favoritos y equipo (opcional)", expanded=False):
                st.caption("Esta información enriquece las conversaciones de Terapia de Reminiscencia.")
                e1, e2 = st.columns(2)
                with e1:
                    ob_edad = st.number_input(
                        "Edad",
                        min_value=55,
                        max_value=105,
                        value=int(st.session_state.get("ob_edad", 72)),
                    )
                    ob_ciudad = st.text_input(
                        "Ciudad de residencia",
                        value=st.session_state.get("ob_ciudad", ""),
                        placeholder="Ej. San Pedro Tlaquepaque, Jalisco",
                    )
                    ob_ocupacion = st.text_input(
                        "Oficio o profesión histórica",
                        value=st.session_state.get("ob_ocupacion", ""),
                        placeholder="Ej. Maquinista en Ferrocarriles Nacionales",
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
                with e2:
                    ob_parentesco = st.text_input(
                        "Parentesco del cuidador",
                        value=st.session_state.get("ob_parentesco", "Hija / Familiar"),
                    )
                    ob_musica = st.text_input(
                        "Música o cantantes favoritos",
                        value=st.session_state.get("ob_musica", ""),
                        placeholder="Ej. Boleros del Trío Los Panchos",
                    )
                    ob_viaje = st.text_input(
                        "Viaje o primer auto memorable",
                        value=st.session_state.get("ob_viaje", ""),
                        placeholder="Ej. Vocho azul 1974 rumbo a Manzanillo",
                    )
                    ob_mascota = st.text_input(
                        "Mascota querida del pasado",
                        value=st.session_state.get("ob_mascota", ""),
                        placeholder="Ej. Pastor alemán llamado Sultán",
                    )
                    ob_comida = st.text_input(
                        "Platillo tradicional o rutina diaria",
                        value=st.session_state.get("ob_comida", ""),
                        placeholder="Ej. Chocolate de metate por la tarde",
                    )
                    ob_autostart = st.checkbox(
                        "Arrancar MemoriaViva automáticamente al encender esta PC (Windows)",
                        value=bool(st.session_state.get("ob_autostart", True)),
                    )

            st.write("")
            if st.form_submit_button(
                "Guardar perfil y continuar",
                icon=":material/arrow_forward:",
                type="primary",
                width="stretch",
            ):
                if not ob_nombre_completo.strip() or not ob_nombre_pref.strip() or not ob_cuidador.strip():
                    st.error("Completa el nombre del adulto mayor, cómo prefiere que le llamen y el familiar responsable.")
                elif len(ob_pin.strip()) < 4 or ob_pin.strip() != ob_pin2.strip():
                    st.error("El PIN debe tener al menos 4 caracteres y coincidir en ambos campos.")
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
    # PASO 2: VINCULACIÓN DEL BOT FAMILIAR DE TELEGRAM
    # --------------------------------------------------------------------------
    elif step == 2:
        with st.container(border=True):
            st.markdown(
                ui_design.render_section_header_html(
                    title="Puente Familiar en Telegram",
                    subtitle="Recibe el pulso diario de reminiscencia y alertas de seguridad en tu celular. Puedes configurarlo después.",
                    icon_name="send",
                ),
                unsafe_allow_html=True,
            )

            col_g, col_qr = st.columns([1.5, 1.0], gap="large")
            with col_g:
                tg_token_in = st.text_input(
                    "Token HTTP API del Bot (@BotFather)",
                    value=config.TELEGRAM_BOT_TOKEN,
                    placeholder="Ej. 1234567890:AAF...",
                )
                tg_chat_in = st.text_input(
                    "Chat ID del Cuidador (opcional: se detecta al pulsar el botón)",
                    value=config.TELEGRAM_CHAT_ID,
                    placeholder="Ej. 987654321",
                )

                c_save_tg, c_det_tg = st.columns(2)
                with c_save_tg:
                    if st.button("Verificar bot", icon=":material/save:", type="secondary", width="stretch"):
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
                            st.success(f"Bot conectado: @{info.get('username')} ({info.get('first_name')})")
                        else:
                            st.error(f"No se pudo validar el token: {info.get('error')}")
                with c_det_tg:
                    if st.button("Detectar Chat ID", icon=":material/search:", type="secondary", width="stretch"):
                        config.update_env_and_runtime_keys(telegram_token=tg_token_in)
                        st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge(
                            bot_token=tg_token_in,
                            chat_id=tg_chat_in,
                        )
                        disc = st.session_state.telegram_bridge.discover_latest_chat_id()
                        if disc.get("ok"):
                            config.update_env_and_runtime_keys(telegram_chat_id=disc["chat_id"])
                            st.success(f"Vinculado con {disc.get('first_name')} ({disc['chat_id']})")
                            st.rerun()
                        else:
                            st.warning(disc.get("error", "Abre el bot en Telegram y presiona /start."))

                with st.expander("Cómo crear tu bot familiar en 1 minuto (@BotFather)", expanded=False):
                    st.markdown(
                        """
                        1. Abre Telegram y busca el bot oficial **@BotFather**.
                        2. Envía el comando `/newbot` y elige un nombre y usuario terminado en `bot`.
                        3. Copia el **HTTP API Token** que te entrega y pégalo arriba.
                        4. Escanea el código QR de la derecha y pulsa **Iniciar (`/start`)** para detectar tu Chat ID.
                        """
                    )

            with col_qr:
                bridge: telegram_notifier.TelegramFamilyBridge = st.session_state.telegram_bridge
                info = bridge.get_bot_info() if bridge.bot_token else {"ok": False}
                bot_user = info.get("username") if info.get("ok") else "BotFather"
                qr_bytes, qr_url = bridge.generate_linking_qr_bytes(bot_user)
                st.image(qr_bytes, caption=f"Escanea para abrir @{bot_user}", width="stretch")
                st.caption(f"Enlace directo: [{qr_url}]({qr_url})")
                if bridge.chat_id:
                    st.success(f"Teléfono vinculado ({bridge.chat_id})")
                else:
                    st.caption("Sin vincular aún — puedes continuar sin bloqueo.")

            st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
            nav1, nav2 = st.columns([1.0, 2.0])
            with nav1:
                if st.button("Anterior", icon=":material/arrow_back:", type="secondary", width="stretch"):
                    st.session_state.onboarding_step = 1
                    st.rerun()
            with nav2:
                if st.button("Continuar a Gemini AI", icon=":material/arrow_forward:", type="primary", width="stretch"):
                    config.update_env_and_runtime_keys(telegram_token=tg_token_in, telegram_chat_id=tg_chat_in)
                    st.session_state.onboarding_step = 3
                    st.rerun()

    # --------------------------------------------------------------------------
    # PASO 3: API KEY DE GOOGLE GEMINI
    # --------------------------------------------------------------------------
    elif step == 3:
        with st.container(border=True):
            st.markdown(
                ui_design.render_section_header_html(
                    title="Motor Conversacional (Google Gemini)",
                    subtitle="Opcional: conecta tu clave gratuita de Google AI Studio. Sin clave, el sistema opera con respaldo local.",
                    icon_name="key",
                ),
                unsafe_allow_html=True,
            )

            gemini_key_in = st.text_input(
                "API Key de Google Gemini",
                value=config.GEMINI_API_KEY,
                type="password",
                placeholder="AIzaSy... o AQ....",
            )

            if st.button("Guardar y probar conexión", icon=":material/science:", type="secondary", width="stretch"):
                config.update_env_and_runtime_keys(gemini_key=gemini_key_in)
                if not gemini_key_in.strip():
                    st.info("No se ingresó clave. MemoriaViva usará su motor gerontológico local de respaldo.")
                else:
                    try:
                        from google import genai
                        client = genai.Client(
                            api_key=gemini_key_in.strip(),
                            http_options={"timeout": config.GEMINI_TIMEOUT_MS},
                        )
                        models_list = [m.name for m in client.models.list() if "gemini" in m.name]
                        st.success(f"Conexión válida: {len(models_list)} modelos Gemini disponibles.")
                    except Exception as exc:
                        st.warning(f"Clave guardada en .env (nota de red: {exc}).")

            with st.expander("Guía rápida: cómo obtener tu API Key gratuita en Google AI Studio", expanded=False):
                st.markdown(
                    """
                    1. Abre [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) e inicia sesión con Google.
                    2. Haz clic en **Create API key** y selecciona o crea un proyecto.
                    3. Copia la clave generada (`AIzaSy...`) y pégala en el campo superior.
                    """
                )

            st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
            nav1, nav2 = st.columns([1.0, 2.0])
            with nav1:
                if st.button("Anterior", icon=":material/arrow_back:", type="secondary", width="stretch"):
                    st.session_state.onboarding_step = 2
                    st.rerun()
            with nav2:
                if st.button("Continuar al Álbum de Fotos", icon=":material/arrow_forward:", type="primary", width="stretch"):
                    if gemini_key_in.strip():
                        config.update_env_and_runtime_keys(gemini_key=gemini_key_in)
                    st.session_state.onboarding_step = 4
                    st.rerun()

    # --------------------------------------------------------------------------
    # PASO 4: ÁLBUM DEL PROTECTOR DE PANTALLA (MÍNIMO 10 FOTOS)
    # --------------------------------------------------------------------------
    elif step == 4:
        profile_id = st.session_state.onboarding_profile_id
        active_p = llm_companion.load_patient_profile(st.session_state.onboarding_profile_path)
        patient_name = active_p.get("paciente", {}).get("nombre_preferido", "Don Manuel")

        with st.container(border=True):
            st.markdown(
                ui_design.render_section_header_html(
                    title="Álbum del Protector de Pantalla",
                    subtitle=f"Estas fotografías formarán el entorno visual sereno de {patient_name}. Mínimo {config.MIN_SCREENSAVER_PHOTOS} imágenes.",
                    icon_name="image",
                ),
                unsafe_allow_html=True,
            )

            uploaded_imgs = st.file_uploader(
                "Selecciona fotografías familiares (JPG, PNG o WebP)",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="onboarding_photo_uploader",
            )
            if uploaded_imgs:
                saved_list = system_integration.save_uploaded_photos(profile_id, uploaded_imgs)
                if saved_list:
                    st.success(f"Se guardaron {len(saved_list)} fotografías nuevas en el álbum.")

            photo_count = system_integration.count_profile_photos(profile_id)
            min_req = config.MIN_SCREENSAVER_PHOTOS

            col_prog, col_fill = st.columns([1.8, 1.2], vertical_alignment="center")
            with col_prog:
                st.progress(min(1.0, photo_count / min_req))
                if photo_count >= min_req:
                    st.caption(f"Listo: {photo_count} de {min_req} fotografías requeridas.")
                else:
                    st.caption(f"Progreso: {photo_count} de {min_req} fotografías. Sube {min_req - photo_count} más o usa postales de muestra.")
            with col_fill:
                if st.button(
                    "Completar con muestras",
                    icon=":material/photo_library:",
                    type="secondary",
                    width="stretch",
                ):
                    system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=patient_name)
                    st.rerun()

            photos_data = system_integration.get_photos_as_data_uris(profile_id)
            if photos_data:
                st.write("")
                cols = st.columns(5)
                for idx, p_item in enumerate(photos_data):
                    with cols[idx % 5]:
                        st.image(p_item["path"], width="stretch")
                        st.markdown(
                            f'<div class="mv-photo-cap" title="{html.escape(p_item["caption"])}">{html.escape(p_item["caption"])}</div>',
                            unsafe_allow_html=True,
                        )

            st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
            nav1, nav2 = st.columns([1.0, 2.0])
            with nav1:
                if st.button("Anterior", icon=":material/arrow_back:", type="secondary", width="stretch"):
                    st.session_state.onboarding_step = 3
                    st.rerun()
            with nav2:
                can_finish = photo_count >= min_req
                if st.button(
                    "Finalizar y activar Modo Kiosco",
                    icon=":material/check:",
                    type="primary",
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
# DIÁLOGO MODAL DE DESBLOQUEO FAMILIAR (DESDE MODO KIOSCO)
# ==============================================================================
@st.dialog("Acceso Familiar")
def show_caregiver_pin_dialog(account_cfg: dict[str, Any]) -> None:
    st.caption("Ingresa tu PIN para abrir el Panel Clínico y Familiar.")
    with st.form("unlock_pin_dialog_form"):
        pin_input = st.text_input("PIN de cuidador", type="password", placeholder="••••")
        c_cancel, c_ok = st.columns(2)
        with c_cancel:
            cancel_clicked = st.form_submit_button("Cancelar", type="secondary", width="stretch")
        with c_ok:
            submit_clicked = st.form_submit_button(
                "Desbloquear",
                icon=":material/lock_open:",
                type="primary",
                width="stretch",
            )

        if cancel_clicked:
            st.rerun()
        if submit_clicked:
            if system_integration.verify_pin(pin_input, account_cfg.get("pin_hash", "")):
                st.session_state.caregiver_unlocked = True
                st.session_state.show_pin_modal = False
                st.rerun()
            else:
                st.error("PIN incorrecto. Intenta nuevamente.")


# ==============================================================================
# VISTA B: PANTALLA BLOQUEADA DEL ADULTO MAYOR (MODO KIOSCO INMERSIVO)
# ==============================================================================
def render_elder_kiosk_screensaver(account_cfg: dict[str, Any]) -> None:
    is_dark = st.session_state.dark_mode
    ui_design.inject_design_system_css(is_dark, kiosk_mode=True)

    active_profile = llm_companion.load_patient_profile(st.session_state.active_profile_path)
    pac_info = active_profile.get("paciente", {})
    profile_id = pac_info.get("id", "don_manuel")
    nombre_paciente = pac_info.get("nombre_preferido", "Don Manuel")

    if system_integration.count_profile_photos(profile_id) < config.MIN_SCREENSAVER_PHOTOS:
        system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=nombre_paciente)

    photos_list = system_integration.get_photos_as_data_uris(profile_id)
    rotation_ms = int(account_cfg.get("rotation_interval_sec", 6)) * 1000

    last_turn = st.session_state.last_turn_result
    last_reply = (
        last_turn["assistant_reply"]
        if last_turn
        else f"Aquí estoy contigo, {nombre_paciente}. Cuando quieras platicar, mantén presionado el botón de abajo o la barra espaciadora."
    )
    learned_facts = (last_turn.get("persisted_new_facts") or []) if last_turn else []
    learned_badge = (
        f"Memoria actualizada: {'; '.join(learned_facts)}"
        if learned_facts
        else ""
    )
    audio_data_uri = _get_audio_data_uri(st.session_state.last_audio_response_path)

    # Disparador oculto 1: Push-to-Talk (al soltar ESPACIO o el botón táctil)
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
                "Mantenga presionado el botón o la tecla ESPACIO mientras habla y suéltelo al terminar."
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

    # Disparador oculto 2: Botón discreto de candado en la esquina superior derecha del Kiosco
    if st.button("_abrir_modal_pin", key="kiosk_unlock_trigger"):
        show_caregiver_pin_dialog(account_cfg)

    screensaver_html = ui_design.build_kiosk_screensaver_html(
        photos_list=photos_list,
        rotation_ms=rotation_ms,
        patient_name=nombre_paciente,
        last_reply=last_reply,
        learned_badge=learned_badge,
        audio_data_uri=audio_data_uri,
        ptt_port=PTT_PORT,
        is_dark=is_dark,
    )
    components.html(screensaver_html, height=680, scrolling=False)


# ==============================================================================
# VISTA C: PANEL FAMILIAR Y MÉDICO DESBLOQUEADO (4 SECCIONES CLARAS)
# ==============================================================================
def render_caregiver_panel(account_cfg: dict[str, Any]) -> None:
    is_dark = st.session_state.dark_mode
    ui_design.inject_design_system_css(is_dark, kiosk_mode=False, narrow_onboarding=False)

    active_profile = llm_companion.load_patient_profile(st.session_state.active_profile_path)
    pac_info = active_profile.get("paciente", {})
    fam_info = active_profile.get("red_familiar_y_afectiva", {})
    profile_id = pac_info.get("id", "don_manuel")
    nombre_paciente = pac_info.get("nombre_preferido", "Don Manuel")
    nombre_completo = pac_info.get("nombre_completo", nombre_paciente)
    nombre_cuidador = (
        fam_info.get("hija_mayor_cuidadora", {}).get("nombre")
        or account_cfg.get("caregiver_name")
        or "Laura"
    )

    # Barra Superior Unificada
    autostart_active = system_integration.is_windows_autostart_enabled()
    status_pill = ("Inicio automático activo", "emerald") if autostart_active else ("Inicio manual", "neutral")

    col_brand, col_theme, col_lock = st.columns([3.2, 0.9, 1.3], vertical_alignment="center")
    with col_brand:
        st.markdown(
            ui_design.render_brand_header_html(
                title="MemoriaViva",
                subtitle=f"Panel de {nombre_cuidador} · Paciente: {nombre_completo}",
                badge_text="RISE",
                status_pill=status_pill,
            ),
            unsafe_allow_html=True,
        )
    with col_theme:
        theme_lbl = "Día" if is_dark else "Noche"
        theme_icon = ":material/light_mode:" if is_dark else ":material/dark_mode:"
        if st.button(theme_lbl, icon=theme_icon, type="secondary", width="stretch"):
            st.session_state.dark_mode = not is_dark
            st.rerun()
    with col_lock:
        if st.button("Activar Modo Kiosco", icon=":material/lock:", type="primary", width="stretch"):
            account_cfg["kiosk_locked_for_elder"] = True
            system_integration.save_account_config(account_cfg)
            st.session_state.caregiver_unlocked = False
            st.session_state.show_pin_modal = False
            st.rerun()

    st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)

    photo_count = system_integration.count_profile_photos(profile_id)
    tab_board, tab_photos, tab_settings, tab_demo = st.tabs(
        [
            "Resumen Clínico",
            f"Álbum Familiar ({photo_count})",
            "Configuración",
            "Simulador Demo",
        ]
    )

    # --------------------------------------------------------------------------
    # SECCIÓN 1: RESUMEN CLÍNICO (KPIs + GRÁFICA 21 DÍAS + TELEGRAM + PDF)
    # --------------------------------------------------------------------------
    with tab_board:
        trend_data = biomarkers.evaluate_longitudinal_trend(st.session_state.history_21_days)
        pos_cats = trend_data.get("positive_categories", {})

        mattr_drop = float(trend_data.get("mattr_drop_pct", 0.0))
        pause_inc = float(trend_data.get("pause_increase_pct", 0.0))

        c_vit, c_mem, c_rit = st.columns(3, gap="medium")
        with c_vit:
            st.markdown(
                ui_design.render_kpi_card_html(
                    label="Vitalidad Conversacional",
                    value=str(pos_cats.get("vitalidad_conversacional", "Estable")),
                    subtitle="Ánimo e interés durante sesiones de reminiscencia.",
                    badge_text="Positiva",
                    badge_variant="emerald",
                    icon_name="heart",
                ),
                unsafe_allow_html=True,
            )
        with c_mem:
            mem_variant = "amber" if mattr_drop >= 15.0 else "emerald"
            mem_badge = f"-{mattr_drop:.1f}% vs base" if mattr_drop > 0 else "Estable"
            st.markdown(
                ui_design.render_kpi_card_html(
                    label="Riqueza Léxica (MATTR)",
                    value=f"{trend_data.get('recent_mattr', 0):.2f}",
                    baseline_text=f"Base: {trend_data.get('baseline_mattr', 0):.2f}",
                    subtitle=str(pos_cats.get("agilidad_memoria", "Seguimiento continuo de vocabulario.")),
                    badge_text=mem_badge,
                    badge_variant=mem_variant,
                    icon_name="brain",
                ),
                unsafe_allow_html=True,
            )
        with c_rit:
            rit_variant = "amber" if pause_inc >= 20.0 else "emerald"
            rit_badge = f"+{pause_inc:.1f}% vs base" if pause_inc > 0 else "Estable"
            st.markdown(
                ui_design.render_kpi_card_html(
                    label="Ritmo del Habla (Pausas)",
                    value=f"{trend_data.get('recent_pause', 0):.2f} s",
                    baseline_text=f"Base: {trend_data.get('baseline_pause', 0):.2f} s",
                    subtitle=str(pos_cats.get("ritmo_del_habla", "Duración de pausas intra-oracionales.")),
                    badge_text=rit_badge,
                    badge_variant=rit_variant,
                    icon_name="clock",
                ),
                unsafe_allow_html=True,
            )

        st.write("")
        col_charts, col_tg = st.columns([1.85, 1.0], gap="large")

        with col_charts:
            with st.container(border=True):
                ch_top1, ch_top2 = st.columns([1.5, 1.3], vertical_alignment="center")
                with ch_top1:
                    st.markdown(
                        ui_design.render_section_header_html(
                            title="Tendencia Longitudinal (21 días)",
                            subtitle="Comparativa auto-referenciada frente a la línea base personal.",
                            icon_name="activity",
                        ),
                        unsafe_allow_html=True,
                    )
                with ch_top2:
                    chart_options = {
                        "Combinada": "combined",
                        "MATTR": "mattr",
                        "Pausas": "pause",
                    }
                    if hasattr(st, "segmented_control"):
                        selected_lbl = st.segmented_control(
                            "Vista de gráfica",
                            options=list(chart_options.keys()),
                            default="Combinada",
                            label_visibility="collapsed",
                            key="chart_metric_selector",
                        ) or "Combinada"
                    else:
                        selected_lbl = st.radio(
                            "Vista de gráfica",
                            options=list(chart_options.keys()),
                            horizontal=True,
                            label_visibility="collapsed",
                            key="chart_metric_selector",
                        )
                    chart_mode = chart_options.get(selected_lbl, "combined")

                fig = ui_design.build_longitudinal_chart(
                    history_21_days=st.session_state.history_21_days,
                    trend_data=trend_data,
                    mode=chart_mode,
                    is_dark=is_dark,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

                st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
                b_pdf, b_warn = st.columns(2)
                with b_pdf:
                    pdf_bytes = pdf_report.generate_clinical_pdf_bytes(
                        profile=active_profile,
                        trend_summary=trend_data,
                        history_records=st.session_state.history_21_days,
                    )
                    st.download_button(
                        label="Descargar Reporte Clínico (PDF)",
                        icon=":material/download:",
                        data=pdf_bytes,
                        file_name=f"Reporte_MemoriaViva_{profile_id}.pdf",
                        mime="application/pdf",
                        type="primary",
                        width="stretch",
                    )
                with b_warn:
                    if st.button(
                        "Enviar Aviso Preventivo Nivel 2",
                        icon=":material/notifications:",
                        type="secondary",
                        width="stretch",
                    ):
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
            with st.container(border=True):
                bridge: telegram_notifier.TelegramFamilyBridge = st.session_state.telegram_bridge
                st.markdown(
                    ui_design.render_telegram_panel_header_html(
                        caregiver_name=nombre_cuidador,
                        is_connected=bool(bridge.chat_id),
                    ),
                    unsafe_allow_html=True,
                )

                msg_log = list(reversed(bridge.message_log))
                if not msg_log:
                    st.markdown(
                        ui_design.render_telegram_card_html(
                            level=1,
                            message=(
                                f"Puente familiar listo. Cuando {nombre_paciente} platique en el Modo Kiosco "
                                "o ejecutes un escenario en el Simulador Demo, aquí aparecerá el resumen y tema sugerido para la cena."
                            ),
                            timestamp="En espera",
                            latency_ms=0,
                            is_dark=is_dark,
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    for item in msg_log[:4]:
                        st.markdown(
                            ui_design.render_telegram_card_html(
                                level=int(item.get("level", 1)),
                                message=str(item.get("message", "")),
                                timestamp=str(item.get("timestamp", "")),
                                latency_ms=item.get("latency_ms", 0),
                                is_dark=is_dark,
                            ),
                            unsafe_allow_html=True,
                        )

    # --------------------------------------------------------------------------
    # SECCIÓN 2: ÁLBUM FAMILIAR (GESTOR DE FOTOS DEL PROTECTOR DE PANTALLA)
    # --------------------------------------------------------------------------
    with tab_photos:
        with st.container(border=True):
            st.markdown(
                ui_design.render_section_header_html(
                    title="Álbum del Protector de Pantalla",
                    subtitle=f"{photo_count} fotografías activas para {nombre_paciente} (mínimo recomendado: {config.MIN_SCREENSAVER_PHOTOS}).",
                    icon_name="image",
                ),
                unsafe_allow_html=True,
            )
            st.progress(min(1.0, photo_count / config.MIN_SCREENSAVER_PHOTOS))

            c_up, c_rot = st.columns([2.0, 1.1], gap="large")
            with c_up:
                more_imgs = st.file_uploader(
                    "Agregar fotografías familiares (JPG, PNG, WebP)",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key="caregiver_photo_uploader",
                )
                if more_imgs:
                    added = system_integration.save_uploaded_photos(profile_id, more_imgs)
                    if added:
                        st.success(f"Se agregaron {len(added)} fotografías al álbum.")
            with c_rot:
                rot_sec = st.slider(
                    "Intervalo de rotación (segundos)",
                    min_value=4,
                    max_value=15,
                    value=int(account_cfg.get("rotation_interval_sec", 6)),
                )
                if rot_sec != int(account_cfg.get("rotation_interval_sec", 6)):
                    account_cfg["rotation_interval_sec"] = rot_sec
                    system_integration.save_account_config(account_cfg)

                if st.button(
                    "Completar con muestras",
                    icon=":material/photo_library:",
                    type="secondary",
                    width="stretch",
                ):
                    system_integration.ensure_minimum_10_sample_photos(profile_id, patient_name=nombre_paciente)
                    st.rerun()

        st.write("")
        photos_data = system_integration.get_photos_as_data_uris(profile_id)
        if photos_data:
            grid = st.columns(4, gap="medium")
            for idx, p_item in enumerate(photos_data):
                with grid[idx % 4]:
                    with st.container(border=True):
                        st.image(p_item["path"], width="stretch")
                        st.markdown(
                            f'<div class="mv-photo-cap" title="{html.escape(p_item["caption"])}">{html.escape(p_item["caption"])}</div>',
                            unsafe_allow_html=True,
                        )
                        if len(photos_data) > config.MIN_SCREENSAVER_PHOTOS:
                            if st.button(
                                "Quitar",
                                icon=":material/delete:",
                                key=f"del_photo_{p_item['filename']}",
                                type="secondary",
                                width="stretch",
                            ):
                                system_integration.delete_profile_photo(profile_id, p_item["filename"])
                                st.rerun()

    # --------------------------------------------------------------------------
    # SECCIÓN 3: CONFIGURACIÓN (PACIENTE, EQUIPO E INTEGRACIONES)
    # --------------------------------------------------------------------------
    with tab_settings:
        col_s1, col_s2 = st.columns(2, gap="large")

        with col_s1:
            with st.container(border=True):
                st.markdown(
                    ui_design.render_section_header_html(
                        title="Paciente y Equipo",
                        subtitle="Perfil activo en el Modo Kiosco y comportamiento de arranque en Windows.",
                        icon_name="sliders",
                    ),
                    unsafe_allow_html=True,
                )

                available_profiles = llm_companion.list_available_profiles()
                labels = [f"{p['nombre_preferido']} ({p['edad']} años)" for p in available_profiles]
                cur_idx = next(
                    (i for i, p in enumerate(available_profiles) if p["path"] == st.session_state.active_profile_path),
                    0,
                )
                sel_idx = st.selectbox(
                    "Perfil activo en el Protector de Pantalla",
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
                    "Arrancar MemoriaViva automáticamente al encender esta PC (Windows)",
                    value=system_integration.is_windows_autostart_enabled(),
                )
                if st.button("Aplicar configuración de inicio", icon=":material/save:", type="primary", width="stretch"):
                    res_auto = system_integration.set_windows_autostart(win_auto)
                    account_cfg["autostart_enabled"] = win_auto
                    system_integration.save_account_config(account_cfg)
                    if res_auto["enabled"]:
                        st.success("Arranque automático activado en Startup de Windows.")
                    else:
                        st.info("Arranque automático deshabilitado.")

                st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
                st.markdown(
                    ui_design.render_section_header_html(
                        title="Zona de restablecimiento",
                        subtitle="Permite repetir el asistente inicial de registro sin borrar tus perfiles guardados.",
                        icon_name="shield",
                    ),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Restablecer asistente inicial",
                    icon=":material/refresh:",
                    key="reset_onboarding_btn",
                    type="secondary",
                    width="stretch",
                ):
                    account_cfg["is_registered"] = False
                    system_integration.save_account_config(account_cfg)
                    st.session_state.onboarding_step = 1
                    st.session_state.caregiver_unlocked = False
                    st.rerun()

        with col_s2:
            with st.container(border=True):
                st.markdown(
                    ui_design.render_section_header_html(
                        title="Integraciones (Gemini y Telegram)",
                        subtitle="Credenciales almacenadas localmente en el archivo .env.",
                        icon_name="key",
                    ),
                    unsafe_allow_html=True,
                )

                new_gemini = st.text_input("API Key de Google Gemini", value=config.GEMINI_API_KEY, type="password")
                new_tg_tok = st.text_input("Token del Bot de Telegram", value=config.TELEGRAM_BOT_TOKEN)
                new_tg_cid = st.text_input("Chat ID de Telegram", value=config.TELEGRAM_CHAT_ID)

                c_cred1, c_cred2 = st.columns(2)
                with c_cred1:
                    if st.button("Guardar credenciales", icon=":material/save:", type="primary", width="stretch"):
                        config.update_env_and_runtime_keys(
                            gemini_key=new_gemini,
                            telegram_token=new_tg_tok,
                            telegram_chat_id=new_tg_cid,
                        )
                        st.session_state.telegram_bridge = telegram_notifier.TelegramFamilyBridge(
                            bot_token=new_tg_tok,
                            chat_id=new_tg_cid,
                        )
                        st.success("Credenciales guardadas en .env.")
                with c_cred2:
                    if st.button("Detectar Chat ID", icon=":material/search:", type="secondary", width="stretch"):
                        disc = st.session_state.telegram_bridge.discover_latest_chat_id()
                        if disc.get("ok"):
                            config.update_env_and_runtime_keys(telegram_chat_id=disc["chat_id"])
                            st.success(f"Vinculado: {disc['chat_id']}")
                            st.rerun()
                        else:
                            st.warning(disc.get("error"))

                st.markdown('<div class="mv-divider"></div>', unsafe_allow_html=True)
                bridge = st.session_state.telegram_bridge
                qr_bytes, qr_url = bridge.generate_linking_qr_bytes()
                q1, q2 = st.columns([1.0, 1.8], vertical_alignment="center")
                with q1:
                    st.image(qr_bytes, width=140)
                with q2:
                    st.markdown("**Código QR de vinculación**")
                    st.caption(f"Escanea desde Telegram o abre el enlace directo: [{qr_url}]({qr_url})")

    # --------------------------------------------------------------------------
    # SECCIÓN 4: SIMULADOR DEMO (PITCH FAIL-SAFE SEPARADO DE CONFIGURACIÓN)
    # --------------------------------------------------------------------------
    with tab_demo:
        st.markdown(
            ui_design.render_section_header_html(
                title="Simulador de Escenarios Clínicos (Pitch Fail-Safe)",
                subtitle="Ejecuta los 3 actos precalibrados sin depender de micrófono ni red, manteniendo la configuración real despejada.",
                icon_name="play",
            ),
            unsafe_allow_html=True,
        )

        scenarios = [
            {
                "id": "demo_1_rescate",
                "badge": "Acto 1 · Nivel 1",
                "variant": "emerald",
                "title": "Rescate Biográfico",
                "desc": "Charla de reminiscencia fluida con MATTR estable. Actualiza el perfil vivo y envía el tema sugerido para la cena a Telegram.",
                "btn": "Ejecutar Acto 1",
            },
            {
                "id": "demo_2_anomia",
                "badge": "Acto 2 · Nivel 2",
                "variant": "amber",
                "title": "Pausa Anómica",
                "desc": "Simula una pausa intra-oracional mayor a 2.0 segundos y vacilación léxica para validar el motor de biomarcadores.",
                "btn": "Ejecutar Acto 2",
            },
            {
                "id": "demo_3_crisis",
                "badge": "Acto 3 · Nivel 3 S.O.S.",
                "variant": "danger",
                "title": "Contención de Crisis",
                "desc": "Activa contención empática (Validación de Naomi Feil) y dispara una alerta inmediata Nivel 3 al celular familiar.",
                "btn": "Ejecutar Acto 3",
            },
        ]

        d_cols = st.columns(3, gap="medium")
        for col, sc in zip(d_cols, scenarios):
            with col:
                with st.container(border=True):
                    st.markdown(
                        ui_design.render_demo_scenario_card_html(
                            badge=sc["badge"],
                            variant=sc["variant"],
                            title=sc["title"],
                            desc=sc["desc"],
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        sc["btn"],
                        icon=":material/play_arrow:",
                        key=f"btn_{sc['id']}",
                        type="secondary",
                        width="stretch",
                    ):
                        execute_full_turn_pipeline(demo_scenario_id=sc["id"])
                        st.rerun()

        last_turn = st.session_state.last_turn_result
        if last_turn and last_turn.get("biomarkers"):
            st.write("")
            with st.container(border=True):
                bio = last_turn["biomarkers"]
                ext = last_turn.get("extraction", {})
                is_sos = bool(ext.get("emergency_triggered"))
                badge_var = "danger" if is_sos else ("amber" if bio.get("anomic_count", 0) > 0 else "emerald")
                badge_lbl = "Alerta Nivel 3 S.O.S." if is_sos else ("Pausa anómica detectada" if bio.get("anomic_count", 0) > 0 else "Turno saludable")

                st.markdown(
                    ui_design.render_turn_result_header_html(
                        timestamp=str(last_turn.get("timestamp", "")),
                        badge_label=badge_lbl,
                        badge_variant=badge_var,
                    ),
                    unsafe_allow_html=True,
                )

                r1, r2 = st.columns([1.6, 1.0], gap="large")
                with r1:
                    if last_turn.get("user_text"):
                        st.markdown(f"**Adulto mayor:** “{last_turn['user_text']}”")
                    st.markdown(f"**MemoriaViva:** “{last_turn.get('assistant_reply', '')}”")
                with r2:
                    m1, m2 = st.columns(2)
                    m1.metric("MATTR", f"{bio.get('mattr', 0):.2f}")
                    m2.metric("Pausa máx.", f"{bio.get('max_pause_sec', 0):.2f} s")
                    st.caption(
                        f"Pausas anómicas (>2.0s): {bio.get('anomic_count', 0)} · "
                        f"Repetición semántica: {'Sí' if bio.get('is_repetition') else 'No'}"
                    )


# ==============================================================================
# Enrutador Principal de Vistas
# ==============================================================================
def main() -> None:
    account_cfg = system_integration.load_account_config()

    if not account_cfg.get("is_registered", False):
        render_onboarding_wizard()
    elif not st.session_state.caregiver_unlocked and account_cfg.get("kiosk_locked_for_elder", True):
        render_elder_kiosk_screensaver(account_cfg)
    else:
        render_caregiver_panel(account_cfg)


main()
