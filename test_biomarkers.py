"""
Pruebas Unitarias y de Validación Científica — Fase 1 (biomarkers.py)
Verifica todos los KPIs matemáticos del Blueprint Técnico de MemoriaViva RISE.
"""

import json
import biomarkers
import config


def run_all_tests() -> None:
    print("=" * 72)
    print("  MEMORIAVIVA RISE — VALIDACIÓN MATEMÁTICA DE BIOMARCADORES (FASE 1)")
    print("=" * 72)

    # --------------------------------------------------------------------------
    # TEST 1: Sujeto Control (Habla fluida y vocabulario diverso)
    # --------------------------------------------------------------------------
    texto_fluido = (
        "En la sierra de Manzanillo la neblina matutina cubría completamente el riel "
        "ferroviario.Revisábamos las balatas metálicas utilizando linternas de petróleo "
        "mientras escuchábamos boleros antiguos de Agustín Lara en la cabina."
    )
    res_fluido = biomarkers.analyze_turn_biomarkers(texto_fluido)
    print("\n[TEST 1] Habla Fluida Estándar (Control):")
    print(f"  • MATTR calculado:       {res_fluido['mattr']} (Esperado >= 0.70)")
    print(f"  • Palabras de contenido: {res_fluido['content_words_count']}")
    print(f"  • Pausas anómicas (>2s): {res_fluido['anomic_count']} (Esperado: 0)")
    assert res_fluido["mattr"] >= 0.70, "El MATTR de habla fluida debe ser alto (>=0.70)"
    assert res_fluido["anomic_count"] == 0, "No debe haber pausas anómicas en habla fluida"

    # --------------------------------------------------------------------------
    # TEST 2: Escenario 2 del Guion Teatral (Pausa Anómica de 3.18s antes de 'llave')
    # --------------------------------------------------------------------------
    timestamps_escenario2 = [
        {"word": "Cuando", "start": 0.00, "end": 0.35},
        {"word": "trabajaba", "start": 0.45, "end": 1.05},
        {"word": "en", "start": 1.10, "end": 1.25},
        {"word": "los", "start": 1.30, "end": 1.48},
        {"word": "trenes", "start": 1.55, "end": 2.00},
        {"word": "usábamos", "start": 2.15, "end": 2.70},
        {"word": "una", "start": 2.80, "end": 3.05},
        {"word": "herramienta", "start": 3.15, "end": 3.80},
        {"word": "pesada", "start": 3.90, "end": 4.35},
        {"word": "una", "start": 4.50, "end": 4.82},
        # Silencio continuo de 3.18 segundos buscando el sustantivo "llave"
        {"word": "llave", "start": 8.00, "end": 8.45},
        {"word": "de", "start": 8.50, "end": 8.65},
        {"word": "cruz", "start": 8.70, "end": 9.10},
        {"word": "grande", "start": 9.20, "end": 9.65},
    ]
    texto_escenario2 = (
        "Cuando trabajaba en los trenes de Guadalajara, usábamos una herramienta "
        "pesada para apretar los rieles... este... una llave de cruz grande."
    )
    res_anomia = biomarkers.analyze_turn_biomarkers(
        text=texto_escenario2,
        word_timestamps=timestamps_escenario2,
    )
    print("\n[TEST 2] Escenario 2 Teatral — Detección de Pausa Anómica:")
    print(f"  • Pausas anómicas detectadas: {res_anomia['anomic_count']}")
    print(f"  • Duración máxima de pausa:   {res_anomia['max_pause_sec']}s")
    print(f"  • Detalle del evento:         {res_anomia['hesitation_events']}")
    print(f"  • Muletillas detectadas:      {res_anomia['detected_fillers']}")
    assert res_anomia["anomic_count"] == 1, "Debe detectar exactamente 1 pausa anómica"
    assert abs(res_anomia["max_pause_sec"] - 3.18) < 0.05, "La pausa debe medir 3.18s"
    assert res_anomia["hesitation_events"][0]["before_word"] == "llave"

    # --------------------------------------------------------------------------
    # TEST 3: Síntesis de Timestamps con Marcador de Pausa en Texto
    # --------------------------------------------------------------------------
    texto_con_marcador = (
        "Ayer fui al mercado a comprar [PAUSA 3.2s] manzanas rojas para la cena."
    )
    res_marcador = biomarkers.analyze_turn_biomarkers(texto_con_marcador)
    print("\n[TEST 3] Síntesis de Timestamps desde Marcador '[PAUSA 3.2s]':")
    print(f"  • Pausa máxima medida: {res_marcador['max_pause_sec']}s antes de '{res_marcador['hesitation_events'][0]['before_word']}'")
    assert res_marcador["anomic_count"] == 1
    assert res_marcador["hesitation_events"][0]["before_word"] == "manzanas"

    # --------------------------------------------------------------------------
    # TEST 4: Detección de Repetición Semántica Intra-Sesión (TF-IDF Cosine >= 0.72)
    # --------------------------------------------------------------------------
    turnos_previos = [
        "En 1975 se me ponchó la llanta delantera de mi Vocho azul yendo por la carretera hacia Colima.",
        "Mi esposa Carmen preparaba un mole de olla delicioso los domingos por la tarde.",
    ]
    turno_repetido = (
        "Oye, ¿ya te conté cuando se ponchó la llanta de mi Vocho azul yendo en la carretera a Colima?"
    )
    turno_nuevo = (
        "A mi nieto Mateo le encanta jugar dominó conmigo los martes y platicar de los partidos del Atlas."
    )

    rep_positiva = biomarkers.analyze_semantic_repetition(turno_repetido, turnos_previos)
    rep_negativa = biomarkers.analyze_semantic_repetition(turno_nuevo, turnos_previos)

    print("\n[TEST 4] Detección de Bucle Semántico (TF-IDF Cosine):")
    print(f"  • Historia repetida (Vocho/Colima): is_repetition={rep_positiva['is_repetition']} (Similitud: {rep_positiva['max_similarity']})")
    print(f"  • Historia nueva (Nieto/Dominó):    is_repetition={rep_negativa['is_repetition']} (Similitud: {rep_negativa['max_similarity']})")
    assert rep_positiva["is_repetition"] is True, "Debe detectar la anécdota repetida del Vocho"
    assert rep_negativa["is_repetition"] is False, "No debe marcar falso positivo en una anécdota nueva"

    # --------------------------------------------------------------------------
    # TEST 5: Seguimiento Longitudinal de 21 Días (Línea Base Personalizada Z-Score)
    # --------------------------------------------------------------------------
    trend = biomarkers.evaluate_longitudinal_trend()
    print("\n[TEST 5] Evaluación Longitudinal Auto-Referenciada (21 Días):")
    print(f"  • MATTR Línea Base (Días 1-14): {trend['baseline_mattr']}  -> Reciente (Últimos 5 días): {trend['recent_mattr']} (-{trend['mattr_drop_pct']}%)")
    print(f"  • Pausa Línea Base (Días 1-14): {trend['baseline_pause']}s -> Reciente (Últimos 5 días): {trend['recent_pause']}s (+{trend['pause_increase_pct']}%)")
    print(f"  • Z-Score MATTR: {trend['mattr_z_score']} | Z-Score Pausas: +{trend['pause_z_score']}")
    print(f"  • Nivel de Alerta Activado:     Nivel {trend['alert_level']} (Aviso Preventivo={trend['trend_warning_triggered']})")
    print(f"  • Categorías Positivas UI:      {json.dumps(trend['positive_categories'], ensure_ascii=False)}")
    assert trend["trend_warning_triggered"] is True, "Los 21 días simulados deben activar el aviso preventivo Nivel 2"
    assert trend["alert_level"] == 2

    print("\n" + "=" * 72)
    print("  [OK] TODAS LAS PRUEBAS DE LA FASE 1 PASARON CON PRECISIÓN QUIRÚRGICA")
    print("=" * 72)


if __name__ == "__main__":
    run_all_tests()
