"""
MemoriaViva RISE - Motor Matemático de Biomarcadores Lingüísticos y Acústicos (Capa 3)
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Fundamentación Científica:
1. MATTR (Moving-Average Type-Token Ratio): Covington & McFall (2010); Fraser et al. (2016).
   Evalúa la riqueza léxica invariante a la longitud del texto sobre palabras de contenido.
2. Pausas Anómicas Intra-Oración (> 2.0s): Pistono et al. (2016); Toth et al. (2018).
   Mide retrasos en el acceso al léxico semántico (circuitos temporomediales).
3. Similitud Semántica Intra-Sesión (TF-IDF Cosine > 0.72): Guinn & Habash (2012).
   Detecta bucles temáticos o reiteración narrativa en la memoria episódica de trabajo.
4. Línea Base Personalizada (Z-Score Baseline): Calibración auto-referenciada libre de
   sesgos educativos o socioeconómicos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

# ==============================================================================
# Lista curada de palabras funcionales/vacías (stopwords) en español
# No aportan riqueza semántica al almacén léxico de contenido
# ==============================================================================
STOPWORDS_ES: set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", "en",
    "con", "por", "para", "sin", "sobre", "y", "e", "o", "u", "pero", "mas", "más", "sino",
    "que", "qué", "como", "cómo", "cuando", "cuándo", "donde", "dónde", "quien", "quién",
    "cual", "cuál", "mi", "tu", "su", "mis", "tus", "sus", "me", "te", "se", "nos", "le",
    "les", "lo", "es", "son", "fue", "era", "eran", "estar", "esta", "está", "estaba",
    "estaban", "este", "esto", "eso", "esa", "esos", "esas", "aquel", "aquella", "aqui",
    "aquí", "ahi", "ahí", "alli", "allí", "allá", "alla", "muy", "ya", "si", "sí", "no",
    "pues", "eh", "este", "mm", "mmm", "ay", "uy", "ah", "oh", "bueno", "entonces", "así",
    "asi", "también", "tambien", "todo", "toda", "todos", "todas", "otro", "otra", "otros",
    "otras", "mismo", "misma", "tan", "tanto", "tanta", "porque", "porqué", "cuando", "donde",
    "hacer", "hace", "hizo", "había", "habia", "hay", "tener", "tiene", "tenía", "tenia",
    "ir", "iba", "fueron", "ser", "soy", "eres", "somos", "del", "al", "unos", "unas",
    "yo", "tú", "tu", "él", "el", "ella", "nosotros", "ustedes", "ellos", "ellas", "usted"
}

# Patrones de muletillas o circunloquios frecuentes en afasia anómica
ANOMIC_FILLERS_PATTERNS: list[str] = [
    r"\beste\b",
    r"\beh+\b",
    r"\bmmm+\b",
    r"cómo se llama",
    r"como se llama",
    r"la cosa esa",
    r"el aparato ese",
    r"se me fue el nombre",
    r"no me acuerdo cómo",
    r"eso que sirve para",
]


# ==============================================================================
# 1. Riqueza Léxica Invariante a la Longitud (MATTR)
# ==============================================================================
def calculate_mattr(
    text: str,
    window_size: int = config.MATTR_WINDOW_SIZE,
) -> float:
    """
    Calcula el Moving-Average Type-Token Ratio (MATTR) sobre palabras de contenido.
    Elimina el sesgo por longitud de la respuesta (Meta 3: Varianza < 3%).

    Args:
        text: Transcripción de la intervención del adulto mayor.
        window_size: Tamaño de la ventana móvil de palabras de contenido (default: 20).

    Returns:
        Índice MATTR normalizado entre 0.0 y 1.0 (redondeado a 3 decimales).
    """
    if not text or not text.strip():
        return 0.0

    words = re.findall(r"\b[a-záéíóúüñ]+\b", text.lower())
    content_words = [w for w in words if w not in STOPWORDS_ES and len(w) > 2]

    if len(content_words) == 0:
        return 0.0

    if len(content_words) < window_size:
        return round(len(set(content_words)) / len(content_words), 3)

    ratios = []
    for i in range(len(content_words) - window_size + 1):
        window = content_words[i : i + window_size]
        ratios.append(len(set(window)) / window_size)

    return round(float(np.mean(ratios)), 3)


def analyze_lexical_details(
    text: str,
    window_size: int = config.MATTR_WINDOW_SIZE,
) -> dict[str, Any]:
    """
    Devuelve el desglose léxico completo (MATTR, conteo de palabras totales,
    palabras de contenido, vocabulario único y muletillas de vacilación detectadas).
    """
    words = re.findall(r"\b[a-záéíóúüñ]+\b", text.lower()) if text else []
    content_words = [w for w in words if w not in STOPWORDS_ES and len(w) > 2]
    mattr_score = calculate_mattr(text, window_size=window_size)

    lower_text = text.lower() if text else ""
    detected_fillers: list[str] = []
    for pattern in ANOMIC_FILLERS_PATTERNS:
        matches = re.findall(pattern, lower_text)
        detected_fillers.extend(matches)

    return {
        "mattr": mattr_score,
        "total_words": len(words),
        "content_words_count": len(content_words),
        "unique_content_words": len(set(content_words)),
        "filler_count": len(detected_fillers),
        "detected_fillers": detected_fillers,
    }


# ==============================================================================
# 2. Detección de Pausas Anómicas Intra-Oración (> 2.0s)
# ==============================================================================
def analyze_anomic_pauses(
    word_timestamps: list[dict[str, Any]],
    pause_threshold: float = config.ANOMIC_PAUSE_THRESHOLD_SEC,
) -> dict[str, Any]:
    """
    Recibe una lista de dicts [{'word': str, 'start': float, 'end': float}]
    proveniente de Whisper (word_timestamps=True) y detecta pausas anómicas (> 2.0s)
    dentro del discurso.

    Fórmula: Pausa_i = max(0.0, start_i - end_{i-1})

    Args:
        word_timestamps: Lista de palabras con marcas temporales en segundos.
        pause_threshold: Umbral en segundos para catalogar pausa anómica (default 2.0s).

    Returns:
        Diccionario con promedio de pausa, pausa máxima, conteo anómico y eventos detallados.
    """
    if not word_timestamps or len(word_timestamps) < 2:
        return {
            "mean_pause_sec": 0.0,
            "max_pause_sec": 0.0,
            "anomic_count": 0,
            "hesitation_events": [],
        }

    pauses: list[float] = []
    anomic_events: list[dict[str, Any]] = []

    for i in range(1, len(word_timestamps)):
        prev_item = word_timestamps[i - 1]
        curr_item = word_timestamps[i]

        prev_end = float(prev_item.get("end", 0.0))
        curr_start = float(curr_item.get("start", prev_end))
        gap = round(max(0.0, curr_start - prev_end), 2)
        pauses.append(gap)

        if gap >= pause_threshold:
            clean_word = str(curr_item.get("word", "")).strip()
            prev_word = str(prev_item.get("word", "")).strip()
            anomic_events.append(
                {
                    "after_word": prev_word,
                    "before_word": clean_word,
                    "duration_sec": gap,
                    "start_sec": round(prev_end, 2),
                    "end_sec": round(curr_start, 2),
                }
            )

    return {
        "mean_pause_sec": round(float(np.mean(pauses)), 2) if pauses else 0.0,
        "max_pause_sec": round(float(np.max(pauses)), 2) if pauses else 0.0,
        "anomic_count": len(anomic_events),
        "hesitation_events": anomic_events,
    }


def synthesize_word_timestamps_from_text(
    text: str,
    avg_word_duration: float = 0.38,
    normal_gap: float = 0.15,
) -> list[dict[str, Any]]:
    """
    Utilidad de respaldo para pruebas o modo texto: genera una secuencia de
    word_timestamps a partir de un texto que puede contener marcadores explícitos
    como '[PAUSA 3.2s]', '[SILENCIO 3.2s]' o puntos suspensivos '...'.
    """
    if not text or not text.strip():
        return []

    tokens = re.split(r"(\[(?:PAUSA|SILENCIO)\s+\d+(?:\.\d+)?s?\]|\.{3,})", text, flags=re.IGNORECASE)
    timestamps: list[dict[str, Any]] = []
    current_time = 0.0
    pending_extra_pause = 0.0

    for token in tokens:
        token_str = token.strip()
        if not token_str:
            continue

        # Marcador explícito [PAUSA X.Xs] o [SILENCIO X.Xs]
        pause_match = re.match(
            r"\[(?:PAUSA|SILENCIO)\s+(\d+(?:\.\d+)?)s?\]",
            token_str,
            flags=re.IGNORECASE,
        )
        if pause_match:
            pending_extra_pause += float(pause_match.group(1))
            continue

        # Puntos suspensivos '...' representan vacilación (~1.1s si están solos)
        if re.match(r"^\.{3,}$", token_str):
            pending_extra_pause += 0.85
            continue

        words = re.findall(r"\b[a-záéíóúüñ0-9]+\b", token_str, flags=re.IGNORECASE)
        for word in words:
            gap = normal_gap + pending_extra_pause
            pending_extra_pause = 0.0
            start_t = round(current_time + (gap if timestamps else 0.0), 2)
            end_t = round(start_t + avg_word_duration, 2)
            timestamps.append({"word": word, "start": start_t, "end": end_t})
            current_time = end_t

    return timestamps


# ==============================================================================
# 3. Detección de Repetición Semántica Intra-Sesión (TF-IDF Cosine)
# ==============================================================================
CONVERSATIONAL_FRAMING_WORDS: set[str] = {
    "oye", "oiga", "fijate", "fíjate", "conte", "conté", "contaba", "dije",
    "decia", "decía", "acuerdo", "acuerdas", "hacia", "allá", "alla", "ayer",
    "hoy", "rato", "ratito", "vez", "veces", "cuando", "como", "cómo",
}


def _normalize_for_tfidf(text: str) -> str:
    """Limpia puntuación, muletillas de apertura y normaliza minúsculas conservando raíces semánticas."""
    words = re.findall(r"\b[a-záéíóúüñ]+\b", text.lower())
    meaningful = [
        w
        for w in words
        if w not in STOPWORDS_ES
        and w not in CONVERSATIONAL_FRAMING_WORDS
        and len(w) > 2
    ]
    return " ".join(meaningful) if meaningful else text.lower().strip()


def detect_semantic_repetition(
    current_utterance: str,
    previous_utterances: list[str],
    threshold: float = config.SEMANTIC_REPEAT_THRESHOLD,
) -> bool:
    """
    Detecta si el paciente está repitiendo la misma anécdota o pregunta dentro de
    la misma sesión mediante similitud coseno TF-IDF (umbral >= 0.72).

    Mantiene la firma exacta del Blueprint Técnico devolviendo bool.
    """
    details = analyze_semantic_repetition(
        current_utterance=current_utterance,
        previous_utterances=previous_utterances,
        threshold=threshold,
    )
    return bool(details["is_repetition"])


def analyze_semantic_repetition(
    current_utterance: str,
    previous_utterances: list[str],
    threshold: float = config.SEMANTIC_REPEAT_THRESHOLD,
) -> dict[str, Any]:
    """
    Versión enriquecida del detector de repetición semántica: devuelve tanto el
    booleano como el puntaje máximo de similitud y cuál fue el turno previo repetido.
    """
    if not previous_utterances or not current_utterance or len(current_utterance.split()) < 5:
        return {
            "is_repetition": False,
            "max_similarity": 0.0,
            "matched_utterance": None,
            "matched_index": None,
        }

    valid_prev = [u for u in previous_utterances if u and len(u.split()) >= 4]
    if not valid_prev:
        return {
            "is_repetition": False,
            "max_similarity": 0.0,
            "matched_utterance": None,
            "matched_index": None,
        }

    normalized_corpus = [_normalize_for_tfidf(u) for u in valid_prev] + [
        _normalize_for_tfidf(current_utterance)
    ]

    try:
        vectorizer = TfidfVectorizer().fit_transform(normalized_corpus)
        similarities = cosine_similarity(vectorizer[-1], vectorizer[:-1]).flatten()
        max_idx = int(np.argmax(similarities))
        max_sim = round(float(similarities[max_idx]), 3)
        is_rep = bool(max_sim >= threshold)

        return {
            "is_repetition": is_rep,
            "max_similarity": max_sim,
            "matched_utterance": valid_prev[max_idx] if is_rep else None,
            "matched_index": max_idx if is_rep else None,
        }
    except ValueError:
        return {
            "is_repetition": False,
            "max_similarity": 0.0,
            "matched_utterance": None,
            "matched_index": None,
        }


# ==============================================================================
# 4. Evaluación Longitudinal Auto-Referenciada (Z-Score Personal Baseline)
# ==============================================================================
def evaluate_longitudinal_trend(
    history_records: list[dict[str, Any]] | None = None,
    baseline_days: int = 14,
    recent_days: int = 5,
) -> dict[str, Any]:
    """
    Evalúa la evolución longitudinal comparando la ventana reciente del paciente
    contra su propia línea base histórica inicial (Primeros 14 días), evitando
    sesgos normativos externos (Pilar Responsible de RISE).

    Dispara alerta preventiva Nivel 2 si:
    - Las pausas promedio suben >= 25% o Z-score >= 2.0
    - El índice MATTR cae >= 20% o Z-score <= -2.0
    """
    if history_records is None:
        if config.HISTORY_FILE.exists():
            with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
                history_records = json.load(f)
        else:
            history_records = []

    if not history_records or len(history_records) < 5:
        return {
            "has_sufficient_data": False,
            "trend_warning_triggered": False,
            "alert_level": 1,
            "status_label": "Estable (Calibrando línea base)",
        }

    baseline_slice = history_records[:baseline_days]
    recent_slice = history_records[-recent_days:]

    base_mattr_vals = [float(r["mattr"]) for r in baseline_slice]
    base_pause_vals = [float(r["mean_pause"]) for r in baseline_slice]

    rec_mattr_vals = [float(r["mattr"]) for r in recent_slice]
    rec_pause_vals = [float(r["mean_pause"]) for r in recent_slice]
    rec_anomic_vals = [int(r.get("anomic_pauses", 0)) for r in recent_slice]
    rec_rep_vals = [int(r.get("repetitions", 0)) for r in recent_slice]

    baseline_mattr = round(float(np.mean(base_mattr_vals)), 3)
    baseline_mattr_std = max(0.01, float(np.std(base_mattr_vals)))
    baseline_pause = round(float(np.mean(base_pause_vals)), 2)
    baseline_pause_std = max(0.05, float(np.std(base_pause_vals)))

    recent_mattr = round(float(np.mean(rec_mattr_vals)), 3)
    recent_pause = round(float(np.mean(rec_pause_vals)), 2)

    # Porcentajes de cambio respecto a la línea base personal
    pause_increase_pct = round((recent_pause - baseline_pause) / max(0.1, baseline_pause), 3)
    mattr_drop_pct = round((baseline_mattr - recent_mattr) / max(0.1, baseline_mattr), 3)

    # Z-Scores personalizados
    pause_z_score = round((recent_pause - baseline_pause) / baseline_pause_std, 2)
    mattr_z_score = round((recent_mattr - baseline_mattr) / baseline_mattr_std, 2)

    # Condición de aviso preventivo Nivel 2
    trend_warning = bool(
        pause_increase_pct >= config.CLINICAL_ALERT_PAUSE_INCREASE_PCT
        or mattr_drop_pct >= config.CLINICAL_ALERT_MATTR_DROP_PCT
        or pause_z_score >= 2.0
        or mattr_z_score <= -2.0
    )

    # Categorías constructivas para el Tablero Familiar (prohibido lenguaje patologizante)
    agilidad_memoria_estado = (
        "En observación preventiva" if mattr_drop_pct >= config.CLINICAL_ALERT_MATTR_DROP_PCT else "Óptima y diversa"
    )
    ritmo_habla_estado = (
        "Pausas de búsqueda frecuentes" if pause_increase_pct >= config.CLINICAL_ALERT_PAUSE_INCREASE_PCT else "Continuo y fluido"
    )
    vitalidad_estado = (
        "Requiere acompañamiento cercano" if trend_warning else "Participación activa y cálida"
    )

    return {
        "has_sufficient_data": True,
        "trend_warning_triggered": trend_warning,
        "alert_level": 2 if trend_warning else 1,
        "baseline_mattr": baseline_mattr,
        "recent_mattr": recent_mattr,
        "mattr_drop_pct": round(mattr_drop_pct * 100, 1),
        "mattr_z_score": mattr_z_score,
        "baseline_pause": baseline_pause,
        "recent_pause": recent_pause,
        "pause_increase_pct": round(pause_increase_pct * 100, 1),
        "pause_z_score": pause_z_score,
        "recent_total_anomic_pauses": int(np.sum(rec_anomic_vals)),
        "recent_total_repetitions": int(np.sum(rec_rep_vals)),
        "positive_categories": {
            "vitalidad_conversacional": vitalidad_estado,
            "agilidad_memoria": agilidad_memoria_estado,
            "ritmo_del_habla": ritmo_habla_estado,
        },
        "ethical_recommendation": (
            "Sugerencia preventiva: Hemos notado una mayor dificultad recurrente para "
            "recordar sustantivos cotidianos y pausas más prolongadas en las charlas "
            "recientes. Sería muy valioso compartir este reporte con su médico geriatra "
            "en su próxima cita de rutina."
            if trend_warning
            else "Los indicadores lingüísticos de las charlas recientes se mantienen "
                 "dentro del rango habitual de su línea base personal."
        ),
    }


# ==============================================================================
# 5. Función Integradora de Turno Conversacional
# ==============================================================================
def analyze_turn_biomarkers(
    text: str,
    word_timestamps: list[dict[str, Any]] | None = None,
    previous_utterances: list[str] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta en un solo paso el análisis completo de un turno del adulto mayor:
    1. Riqueza léxica MATTR y conteo de palabras de contenido.
    2. Pausas anómicas (>2.0s) usando timestamps reales o sintetizados.
    3. Detección de repetición semántica (TF-IDF Cosine > 0.72) frente a turnos previos.
    """
    if word_timestamps is None:
        word_timestamps = synthesize_word_timestamps_from_text(text)

    if previous_utterances is None:
        previous_utterances = []

    lexical = analyze_lexical_details(text)
    pauses = analyze_anomic_pauses(word_timestamps)
    repetition = analyze_semantic_repetition(text, previous_utterances)

    return {
        "text": text,
        "mattr": lexical["mattr"],
        "total_words": lexical["total_words"],
        "content_words_count": lexical["content_words_count"],
        "unique_content_words": lexical["unique_content_words"],
        "filler_count": lexical["filler_count"],
        "detected_fillers": lexical["detected_fillers"],
        "mean_pause_sec": pauses["mean_pause_sec"],
        "max_pause_sec": pauses["max_pause_sec"],
        "anomic_count": pauses["anomic_count"],
        "hesitation_events": pauses["hesitation_events"],
        "is_repetition": repetition["is_repetition"],
        "repetition_similarity": repetition["max_similarity"],
        "matched_previous_utterance": repetition["matched_utterance"],
    }
