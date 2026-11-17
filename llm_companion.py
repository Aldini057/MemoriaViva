"""
MemoriaViva RISE - Motor Conversacional Gerontológico y Extractor Biográfico (Capa 2)
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Implementa:
1. PROMPT A: Compañero de Reminiscencia, Rescate Biográfico Suave y Validación de Naomi Feil.
   - Máximo 35 palabras por respuesta, 1 sola pregunta a la vez.
   - Jamás evidencia olvidos ('¿No se acuerda?').
   - Ante repeticiones (TF-IDF >= 0.72), redirige hacia detalles sensoriales periféricos.
   - Ante crisis o desorientación aguda, suspende preguntas y aplica Validación de Feil.
2. PROMPT B: Clasificador Silencioso JSON y Extractor de Memoria Dinámica (Biographical RAG-Lite).
   - Detecta estado emocional, emergencias Nivel 3, rescate biográfico, tema visual para
     el Álbum de Recuerdos (Opción C de UI) y persiste nuevos hechos en el perfil JSON.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import config

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False


# ==============================================================================
# Plantillas Maestras de Prompts (Blueprint Técnico RISE)
# ==============================================================================
PROMPT_UNIFIED_COMPANION_AND_EXTRACTOR = """ERES "MEMORIAVIVA", UN COMPAÑERO CONVERSACIONAL CÁLIDO, EMPÁTICO Y REAL PARA {nombre_preferido} ({edad} AÑOS).

CONTEXTO BIOGRÁFICO ACTUAL DE {nombre_preferido} (ÚSALO SOLO COMO APOYO O SI ÉL LO MENCIONA/OLVIDA):
{patient_profile_json}

HISTORIAL RECIENTE DE LA CONVERSACIÓN ACTUAL:
{recent_dialogue_history}

ESTADO DE REPETICIÓN EN ESTE TURNO: {repetition_context}

REGLAS INQUEBRANTABLES DEL MARCO RISE PARA `assistant_reply`:
1. REGLA PRIORITARIA DE CONVERSACIÓN REAL: Responde SIEMPRE de forma directa, específica y cálida a lo que {nombre_preferido} acaba de decir en su último mensaje. NO cambies de tema ni lances datos al azar de su perfil si no vienen al caso con lo que él te está contando ahora mismo. Demuestra que realmente escuchaste y entendiste su historia o comentario actual, continuando el hilo del historial reciente.
2. BREVEDAD Y CLARIDAD GERIÁTRICA: `assistant_reply` NUNCA debe superar las 35 palabras (máximo 2 o 3 oraciones cortas). Haz SIEMPRE UNA SOLA pregunta natural relacionada con lo que acaba de contar.
3. RESCATE BIOGRÁFICO SIN EVIDENCIAR OLVIDOS: Si {nombre_preferido} titubea o no recuerda el nombre de un familiar, lugar o fecha que está en su perfil biográfico, proporciónaselo con cariño dentro de la frase. PROHIBIDO decir "¿No se acuerda?" o "Ya me lo había dicho".
4. PACIENCIA INFINITA ANTE REPETICIONES: Si {nombre_preferido} cuenta la misma historia otra vez, escúchalo con entusiasmo y pídele un detalle sensorial nuevo.
5. PROTOCOLO DE VALIDACIÓN DE FEIL (CRISIS O DESORIENTACIÓN): Si expresa miedo, llanto, angustia, dolor físico, mareo o dice que no sabe dónde está:
   - SUSPENDE cualquier pregunta de memoria.
   - Valida su emoción con ternura, recuérdale que está seguro en su casa en {ciudad_residencia} y que su familiar {cuidador_nombre} ya fue avisado para llamarle.
6. RETROALIMENTACIÓN Y MEMORIA VIVA (`new_biographical_facts`): Extrae cualquier dato nuevo que {nombre_preferido} mencione en este turno (qué comió, qué hizo hoy, nombres de personas, nietos, amigos, mascotas, lugares, gustos, sentimientos o anécdotas) como frases claras para guardarlas permanentemente en su perfil JSON.

Analiza el último mensaje de {nombre_preferido} y devuelve EXCLUSIVAMENTE un objeto JSON válido con esta estructura exacta:
{{
  "assistant_reply": "Respuesta cálida, directa y contextual a lo que acaba de decir {nombre_preferido} (máximo 35 palabras)",
  "emotional_state": "tranquilo | alegre | nostalgico | frustrado | crisis_desorientacion",
  "emergency_triggered": false,
  "emergency_reason": null,
  "biographical_rescue_triggered": false,
  "rescued_entity": null,
  "conversation_topic_summary": "Resumen cálido en 1 línea de lo que platicó hoy",
  "dinner_conversation_tip": "Sugerencia concreta de 1 pregunta para que {cuidador_nombre} le haga hoy en la cena sobre lo que contó en esta charla",
  "new_biographical_facts": ["Frase(s) con datos nuevos que mencionó en este turno"],
  "memory_album_theme": "ferrocarril | musica_boleros | playa_manzanillo | familia_hogar | mascotas"
}}
"""


# ==============================================================================
# Gestión de Perfiles Biográficos en JSON (Biographical RAG-Lite)
# ==============================================================================
def load_patient_profile(profile_path: str | Path | None = None) -> dict[str, Any]:
    """Carga el perfil biográfico JSON activo del adulto mayor."""
    target = Path(profile_path) if profile_path else config.DEFAULT_PROFILE_FILE
    if not target.exists():
        target = config.DEFAULT_PROFILE_FILE
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def save_patient_profile(profile_data: dict[str, Any], profile_path: str | Path | None = None) -> Path:
    """Guarda un perfil biográfico en disco (data/profiles/)."""
    if profile_path:
        target = Path(profile_path)
    else:
        pid = profile_data.get("paciente", {}).get("id", "paciente_custom")
        target = config.PROFILES_DIR / f"{pid}.json"

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)
    return target


def list_available_profiles() -> list[dict[str, Any]]:
    """Lista todos los perfiles de pacientes disponibles en data/profiles/."""
    profiles: list[dict[str, Any]] = []
    for p in sorted(config.PROFILES_DIR.glob("*.json")):
        try:
            data = load_patient_profile(p)
            pac = data.get("paciente", {})
            profiles.append(
                {
                    "path": str(p),
                    "filename": p.name,
                    "id": pac.get("id", p.stem),
                    "nombre_preferido": pac.get("nombre_preferido", pac.get("nombre_completo", p.stem)),
                    "nombre_completo": pac.get("nombre_completo", p.stem),
                    "edad": pac.get("edad", 72),
                    "tipo_perfil": pac.get("tipo_perfil", "real"),
                }
            )
        except Exception:
            continue
    return profiles


def update_profile_with_new_facts(
    new_facts: list[str],
    profile_path: str | Path | None = None,
) -> list[str]:
    """
    Retroalimenta el perfil JSON del paciente guardando nuevos recuerdos descubiertos
    tanto en `anclas_de_reminiscencia` como en `memorias_aprendidas_en_charlas`
    con marca de fecha y hora, evitando duplicados.
    """
    if not new_facts:
        return []

    target = Path(profile_path) if profile_path else config.DEFAULT_PROFILE_FILE
    profile = load_patient_profile(target)
    anchors: list[str] = profile.setdefault("anclas_de_reminiscencia", [])
    learned_log: list[dict[str, str]] = profile.setdefault("memorias_aprendidas_en_charlas", [])
    existing_lower = [a.lower() for a in anchors]

    added: list[str] = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    for fact in new_facts:
        clean_fact = str(fact).strip()
        if not clean_fact or len(clean_fact) < 4:
            continue
        if not any(clean_fact.lower() in ex or ex in clean_fact.lower() for ex in existing_lower):
            anchors.append(clean_fact)
            learned_log.append({"fecha": now_str, "recuerdo": clean_fact})
            existing_lower.append(clean_fact.lower())
            added.append(clean_fact)

    if added:
        save_patient_profile(profile, target)
    return added


# ==============================================================================
# Detección Heurística Instantánea de Crisis, Rescate y Tema Visual
# ==============================================================================
CRISIS_KEYWORDS: list[str] = [
    "no sé qué hago aquí",
    "no se que hago aqui",
    "no conozco esta casa",
    "no sé dónde estoy",
    "no se donde estoy",
    "me quiero ir a mi casa",
    "mareado",
    "asustado",
    "tengo miedo",
    "dónde está carmen",
    "donde esta carmen",
    "me duele el pecho",
    "ayuda por favor",
]


def detect_crisis_or_disorientation(text: str) -> tuple[bool, str | None]:
    """Detecta de inmediato señales de desorientación espacial aguda o angustia."""
    lower = text.lower()
    for kw in CRISIS_KEYWORDS:
        if kw in lower:
            return (
                True,
                "Episodio de desorientación espacial aguda o angustia reportado en vivo.",
            )
    return False, None


def infer_memory_album_theme(text: str) -> str:
    """
    Determina qué fotograma nostálgico mostrar en el 'Álbum de Recuerdos Dinámico'
    (Opción C de la interfaz del adulto mayor) según el tema de conversación.
    """
    lower = text.lower()
    if any(w in lower for w in ["tren", "trenes", "ferrocarril", "riel", "rieles", "locomotora", "maquinista", "llave"]):
        return "ferrocarril"
    if any(w in lower for w in ["perro", "sultán", "sultan", "mascota", "pastor alemán", "cachorro"]):
        return "mascotas"
    if any(w in lower for w in ["bolero", "música", "musica", "lara", "panchos", "canción", "cantar", "radio"]):
        return "musica_boleros"
    if any(w in lower for w in ["mar", "manzanillo", "colima", "playa", "miramar", "costa", "vocho", "viaje"]):
        return "playa_manzanillo"
    return "familia_hogar"


# ==============================================================================
# Motor Conversacional Principal (Gemini API + Respaldo Gerontológico Determinista)
# ==============================================================================
def _enforce_word_limit(text: str, max_words: int = 35) -> str:
    """Garantiza que la respuesta nunca supere las 35 palabras (Regla 1 RISE)."""
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    truncated = " ".join(words[:max_words])
    # Cerrar limpiamente en la última puntuación si es posible
    last_punct = max(truncated.rfind("."), truncated.rfind("?"), truncated.rfind("!"))
    if last_punct > len(truncated) // 2:
        return truncated[: last_punct + 1].strip()
    return truncated.rstrip(",;:") + "."


def _extract_free_topic_keywords(text: str) -> list[str]:
    """Extrae palabras de contenido clave de una frase libre para responder con contexto real."""
    ignore = {
        "hola", "oye", "fijate", "fíjate", "ayer", "hoy", "mañana", "tarde", "noche",
        "estuvo", "estaba", "estaban", "fuimos", "fui", "estoy", "tengo", "mucho", "mucha",
        "muy", "para", "como", "cuando", "donde", "porque", "pero", "este", "esta", "esto",
        "eso", "unos", "unas", "con", "por", "sin", "sobre", "que", "qué", "bien", "rico", "rica",
    }
    words = re.findall(r"\b[a-záéíóúüñ]{4,}\b", text.lower())
    seen: list[str] = []
    for w in words:
        if w not in ignore and w not in seen:
            seen.append(w)
    return seen[:4]


def _deterministic_companion_response(
    user_text: str,
    profile: dict[str, Any],
    is_repetition: bool = False,
) -> str:
    """
    Generador gerontológico determinista de respaldo si la red falla:
    conserva los 3 actos teatrales y para cualquier otro tema responde retomando
    directamente las palabras clave que acaba de mencionar el adulto mayor.
    """
    pac = profile.get("paciente", {})
    fam = profile.get("red_familiar_y_afectiva", {})
    nombre = pac.get("nombre_preferido", "Don Manuel")
    ciudad = pac.get("ciudad_residencia", "San Pedro Tlaquepaque").split(",")[0]
    cuidador = (
        fam.get("hija_mayor_cuidadora", {}).get("nombre")
        or profile.get("contacto_emergencia_telegram", {}).get("nombre", "Laura").split()[0]
    )
    hija_menor = fam.get("hija_menor", {}).get("nombre", "Rocío")

    lower = user_text.lower()

    # 1. Protocolo de Validación de Feil (Escenario 3: Crisis / Desorientación)
    is_crisis, _ = detect_crisis_or_disorientation(user_text)
    if is_crisis:
        return (
            f"Tranquilo, {nombre}, respire despacio conmigo. Está usted seguro en su casa "
            f"de {ciudad}. Todo está bien. Ya le avisé a {cuidador} para que le llame. "
            "Aquí estoy con usted."
        )

    # 2. Rescate Biográfico Suave (Escenario 1: Olvido del nombre de su hija Rocío)
    if ("hija" in lower or "maestra" in lower or "colima" in lower) and (
        "cómo es que se llama" in lower
        or "como se llama" in lower
        or "se me fue el nombre" in lower
        or "rocío" in lower
    ):
        if "sultán" in lower or "sultan" in lower or "perro" in lower:
            return (
                f"Le habló su hija {hija_menor}, {nombre}. ¡Qué bonito recuerdo el de su "
                "perro Sultán! Oiga, ¿qué travesuras hacía Sultán cuando usted llegaba a casa?"
            )
        return (
            f"Le habló su hija {hija_menor}, {nombre}. Qué alegría que platicó con {hija_menor} "
            "desde Manzanillo. Oiga, ¿y usted qué le platicó a ella?"
        )

    # 3. Gestión Empática de Repetición Temática (Caso de Uso 2: Vocho / Colima)
    if is_repetition or ("llanta" in lower and "colima" in lower) or ("rueda" in lower and "colima" in lower):
        return (
            f"¡Qué gran anécdota esa del viaje a Colima, {nombre}! Me encanta escucharla. "
            "Oiga, ¿quién iba con usted en el asiento del copiloto ese día?"
        )

    # 4. Reminiscencia Ferroviaria (Escenario 2: Trenes y llave de cruz)
    if any(w in lower for w in ["tren", "trenes", "rieles", "llave", "reloj", "locomotora", "vapor"]):
        return (
            f"Qué orgullo tantos años en los ferrocarriles, {nombre}, cuidando cada riel con "
            "esa llave de cruz. Oiga, ¿qué paisaje le gustaba más ver desde la máquina?"
        )

    # 5. Respuesta contextual directa sobre lo que acaba de contar el usuario
    topic_words = _extract_free_topic_keywords(user_text)
    if topic_words:
        tema = ", ".join(topic_words[:2])
        return (
            f"Qué gusto escuchar eso sobre {tema}, {nombre}. Se nota que lo disfrutó mucho. "
            f"Cuénteme, ¿qué fue lo que más le gustó de ese momento?"
        )

    return (
        f"Qué gusto platicar con usted, {nombre}. Me alegra escucharlo. "
        "¿Qué más le gustaría contarme de su día hoy?"
    )


def _deterministic_structured_extraction(
    user_text: str,
    assistant_reply: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Extractor estructurado de respaldo para garantizar que el JSON de salida
    siempre tenga todos los campos requeridos por el Tablero y Telegram.
    """
    pac = profile.get("paciente", {})
    fam = profile.get("red_familiar_y_afectiva", {})
    nombre = pac.get("nombre_preferido", "Don Manuel")
    hija_menor = fam.get("hija_menor", {}).get("nombre", "Rocío")

    lower = user_text.lower()
    is_crisis, crisis_reason = detect_crisis_or_disorientation(user_text)
    theme = infer_memory_album_theme(user_text + " " + assistant_reply)

    if is_crisis:
        return {
            "emotional_state": "crisis_desorientacion",
            "emergency_triggered": True,
            "emergency_reason": crisis_reason,
            "biographical_rescue_triggered": False,
            "rescued_entity": None,
            "conversation_topic_summary": f"Episodio de desorientación espacial aguda; se aplicó Validación de Feil para calmar a {nombre}.",
            "dinner_conversation_tip": f"Acompáñalo con calma y muéstrale fotografías familiares de su casa y de Doña Carmen.",
            "new_biographical_facts": [],
            "memory_album_theme": "familia_hogar",
        }

    rescue_triggered = False
    rescued_entity = None
    if any(p in lower for p in ["se me fue el nombre", "cómo es que se llama", "como se llama"]) and (
        "hija" in lower or "colima" in lower or "maestra" in lower
    ):
        rescue_triggered = True
        rescued_entity = f"{hija_menor} (Hija menor - Manzanillo, Colima)"

    new_facts: list[str] = []
    if "sultán" in lower or "sultan" in lower:
        new_facts.append("Tenía en casa un perro pastor alemán llamado Sultán")
    if "reloj" in lower and "jubil" in lower:
        new_facts.append("Cuando se jubiló de los ferrocarriles le regalaron un reloj conmemorativo")

    if not new_facts and len(user_text.split()) >= 5 and not rescue_triggered:
        clean_snippet = user_text.strip().rstrip(".!?")
        if len(clean_snippet) > 120:
            clean_snippet = clean_snippet[:117] + "..."
        new_facts.append(f"Comentó en charla: {clean_snippet}")

    if theme == "ferrocarril":
        summary = "Recordó sus años de trabajo en los Ferrocarriles de Guadalajara y las herramientas del riel."
        tip = "Pregúntale hoy en la cena cómo era el reloj que le regalaron cuando se jubiló de los trenes."
    elif theme == "mascotas" or rescue_triggered:
        summary = f"Platicó sobre la llamada de su hija {hija_menor} desde Manzanillo y recordó a su perro Sultán."
        tip = "Pregúntale en la cena cómo entrenó a su perro pastor alemán Sultán cuando era joven."
    elif theme == "playa_manzanillo":
        summary = "Recordó con entusiasmo sus viajes por carretera rumbo a la costa de Colima y Manzanillo."
        tip = "Pregúntale qué música escuchaban en la carretera cuando viajaban en el Vocho azul."
    else:
        topic_words = _extract_free_topic_keywords(user_text)
        tema_str = ", ".join(topic_words[:3]) if topic_words else "su día"
        summary = f"Conversó con buen ánimo sobre {tema_str}."
        tip = f"Pregúntale hoy en la cena cómo le fue con lo que platicó sobre {tema_str}."

    return {
        "emotional_state": "nostalgico" if "acordé" in lower else "alegre",
        "emergency_triggered": False,
        "emergency_reason": None,
        "biographical_rescue_triggered": rescue_triggered,
        "rescued_entity": rescued_entity,
        "conversation_topic_summary": summary,
        "dinner_conversation_tip": tip,
        "new_biographical_facts": new_facts,
        "memory_album_theme": theme,
    }


def _format_recent_history(conversation_history: list[dict[str, Any]] | None, max_turns: int = 5) -> str:
    """Formatea los últimos turnos de la charla actual para dar continuidad real al LLM."""
    if not conversation_history:
        return "Inicio de la conversación actual (primer turno)."
    lines: list[str] = []
    for turn in conversation_history[-max_turns:]:
        u_txt = str(turn.get("user_text", "")).strip()
        a_txt = str(turn.get("assistant_reply", "")).strip()
        if u_txt:
            lines.append(f"- Adulto Mayor: \"{u_txt}\"")
        if a_txt:
            lines.append(f"- MemoriaViva: \"{a_txt}\"")
    return "\n".join(lines) if lines else "Inicio de la conversación actual (primer turno)."


def process_conversation_turn(
    user_text: str,
    profile_path: str | Path | None = None,
    is_repetition: bool = False,
    use_live_llm: bool = True,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Procesa un turno completo del adulto mayor con contexto conversacional real multi-turno:
    1. Responde directamente a lo que el paciente dijo usando el historial reciente y su perfil.
    2. Extrae hechos nuevos en JSON y retroalimenta permanentemente su archivo de perfil.
    """
    start_t = time.perf_counter()
    profile = load_patient_profile(profile_path)
    pac = profile.get("paciente", {})
    fam = profile.get("red_familiar_y_afectiva", {})

    nombre_preferido = pac.get("nombre_preferido", "Don Manuel")
    edad = pac.get("edad", 72)
    ciudad_residencia = pac.get("ciudad_residencia", "San Pedro Tlaquepaque, Jalisco")
    cuidador_nombre = (
        fam.get("hija_mayor_cuidadora", {}).get("nombre")
        or profile.get("contacto_emergencia_telegram", {}).get("nombre", "Laura").split()[0]
    )

    profile_json_str = json.dumps(profile, ensure_ascii=False, indent=2)
    recent_dialogue_str = _format_recent_history(conversation_history, max_turns=5)
    repetition_context = (
        "ATENCIÓN: El detector TF-IDF indica que el paciente está repitiendo una anécdota ya contada en esta sesión. "
        "Aplica la Regla 4: NO le digas que ya lo contó; celebra la historia y pregúntale un detalle sensorial nuevo."
        if is_repetition
        else "Discurso nuevo (sin repetición intra-sesión)."
    )

    # Base determinista por seguridad y para anclar escenarios teatrales
    fallback_reply = _deterministic_companion_response(user_text, profile, is_repetition=is_repetition)
    fallback_extraction = _deterministic_structured_extraction(user_text, fallback_reply, profile)

    assistant_reply = fallback_reply
    extraction = fallback_extraction
    llm_engine_used = "deterministic_gerontological_engine"

    # Llamada en vivo unificada a Google Gemini (timeout >= 10000 ms requerido por la API)
    if use_live_llm and GENAI_AVAILABLE and config.GEMINI_API_KEY:
        client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options={"timeout": config.GEMINI_TIMEOUT_MS},
        )
        system_instruction = PROMPT_UNIFIED_COMPANION_AND_EXTRACTOR.format(
            nombre_preferido=nombre_preferido,
            edad=edad,
            patient_profile_json=profile_json_str,
            recent_dialogue_history=recent_dialogue_str,
            repetition_context=repetition_context,
            ciudad_residencia=ciudad_residencia,
            cuidador_nombre=cuidador_nombre,
        )

        for candidate_model in [config.GEMINI_MODEL_COMPANION, config.GEMINI_MODEL_FALLBACK]:
            try:
                resp = client.models.generate_content(
                    model=candidate_model,
                    contents=user_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.45,
                        response_mime_type="application/json",
                    ),
                )
                raw_json = (resp.text or "").strip()
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict) and parsed.get("assistant_reply"):
                    assistant_reply = _enforce_word_limit(str(parsed["assistant_reply"]), max_words=35)
                    # Garantizar que en Rescate Biográfico (Escenario 1) el nombre de Rocío esté presente
                    if fallback_extraction["biographical_rescue_triggered"] and "rocío" not in assistant_reply.lower():
                        assistant_reply = fallback_reply

                    llm_engine_used = candidate_model

                    if fallback_extraction["emergency_triggered"]:
                        parsed["emergency_triggered"] = True
                        parsed["emotional_state"] = "crisis_desorientacion"
                        parsed["emergency_reason"] = fallback_extraction["emergency_reason"]
                    if fallback_extraction["biographical_rescue_triggered"]:
                        parsed["biographical_rescue_triggered"] = True
                        parsed["rescued_entity"] = parsed.get("rescued_entity") or fallback_extraction["rescued_entity"]

                    llm_facts = parsed.get("new_biographical_facts") or []
                    if not isinstance(llm_facts, list):
                        llm_facts = []
                    if not llm_facts and fallback_extraction["new_biographical_facts"]:
                        parsed["new_biographical_facts"] = fallback_extraction["new_biographical_facts"]

                    if not parsed.get("memory_album_theme"):
                        parsed["memory_album_theme"] = fallback_extraction["memory_album_theme"]
                    extraction = {**fallback_extraction, **parsed}
                    break
            except Exception:
                continue
        else:
            assistant_reply = fallback_reply
            extraction = fallback_extraction
            llm_engine_used = "deterministic_gerontological_fallback"

    # Persistir nuevos datos biográficos aprendidos en el JSON
    new_facts_list = extraction.get("new_biographical_facts") or []
    persisted_facts = update_profile_with_new_facts(new_facts_list, profile_path=profile_path)

    latency_ms = round((time.perf_counter() - start_t) * 1000, 1)
    return {
        "assistant_reply": assistant_reply,
        "word_count": len(assistant_reply.split()),
        "extraction": extraction,
        "persisted_new_facts": persisted_facts,
        "llm_engine": llm_engine_used,
        "latency_ms": latency_ms,
    }
