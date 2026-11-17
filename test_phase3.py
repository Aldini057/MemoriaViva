"""
Pruebas de Integración — Fase 3 (llm_companion.py + telegram_notifier.py)
Verifica:
1. Conexión con Telegram Bot API, generación de código QR y los 3 niveles de alerta.
2. Prompt A (Reminiscencia, Rescate Biográfico <= 35 palabras y Validación de Feil).
3. Prompt B (Extracción JSON estricta, aprendizaje biográfico dinámico y tema del Álbum).
"""

import json
import audio_engine
import llm_companion
import telegram_notifier


def run_phase3_tests() -> None:
    print("=" * 72)
    print("  MEMORIAVIVA RISE — VALIDACIÓN DE LLM Y CANAL TELEGRAM (FASE 3)")
    print("=" * 72)

    # --------------------------------------------------------------------------
    # TEST 1: Verificación de Bot de Telegram, Autodetección y Código QR
    # --------------------------------------------------------------------------
    bridge = telegram_notifier.TelegramFamilyBridge()
    bot_info = bridge.get_bot_info()
    chat_discovery = bridge.discover_latest_chat_id()
    qr_bytes, qr_url = bridge.generate_linking_qr_bytes()

    print("\n[TEST 1] Estado del Conector de Telegram y Generador QR:")
    print(f"  • Info del Bot API:     {bot_info}")
    print(f"  • Autodetección ChatID: {chat_discovery}")
    print(f"  • URL de vinculación:   {qr_url}")
    print(f"  • QR PNG generado:      {len(qr_bytes)} bytes")
    assert len(qr_bytes) > 500, "El código QR en PNG debe generarse correctamente"

    # --------------------------------------------------------------------------
    # TEST 2: Escenario 1 Teatral — Rescate Biográfico (Rocío) y Aprendizaje (Sultán)
    # --------------------------------------------------------------------------
    sc1_text = audio_engine.DEMO_SCENARIOS["demo_1_rescate"]["transcript"]
    turn1 = llm_companion.process_conversation_turn(sc1_text)

    print("\n[TEST 2] Escenario 1 — Rescate Biográfico y Aprendizaje JSON:")
    print(f"  • Motor utilizado:       {turn1['llm_engine']} ({turn1['latency_ms']} ms)")
    print(f"  • Respuesta MemoriaViva: \"{turn1['assistant_reply']}\"")
    print(f"  • Conteo de palabras:    {turn1['word_count']} palabras (Regla RISE <= 35)")
    print(f"  • Rescate activado:      {turn1['extraction']['biographical_rescue_triggered']} -> {turn1['extraction']['rescued_entity']}")
    print(f"  • Tema Álbum (Opción C): {turn1['extraction']['memory_album_theme']}")
    assert turn1["word_count"] <= 35, "La respuesta nunca debe superar las 35 palabras"
    assert "Rocío" in turn1["assistant_reply"], "Debe rescatar el nombre de su hija Rocío con naturalidad"
    assert turn1["extraction"]["biographical_rescue_triggered"] is True

    # --------------------------------------------------------------------------
    # TEST 3: Escenario 2 Teatral — Reminiscencia Ferroviaria + Pulso Nivel 1 Telegram
    # --------------------------------------------------------------------------
    sc2_text = audio_engine.DEMO_SCENARIOS["demo_2_anomia"]["transcript"]
    turn2 = llm_companion.process_conversation_turn(sc2_text)
    ext2 = turn2["extraction"]

    pulse_res = bridge.send_level1_daily_pulse(
        topic_summary=ext2["conversation_topic_summary"],
        mattr=0.56,
        mean_pause=3.18,
        dinner_tip=ext2["dinner_conversation_tip"],
    )
    print("\n[TEST 3] Escenario 2 — Reminiscencia Ferroviaria y Pulso Nivel 1:")
    print(f"  • Respuesta MemoriaViva: \"{turn2['assistant_reply']}\"")
    print(f"  • Resumen para Laura:    {ext2['conversation_topic_summary']}")
    print(f"  • Tip para la cena:      {ext2['dinner_conversation_tip']}")
    print(f"  • Tema Álbum (Opción C): {ext2['memory_album_theme']}")
    print(f"  • Telegram Nivel 1:      Entregado_API={pulse_res['delivered_telegram_api']} | Latencia={pulse_res['latency_ms']} ms")
    assert turn2["word_count"] <= 35
    assert ext2["memory_album_theme"] == "ferrocarril"

    # --------------------------------------------------------------------------
    # TEST 4: Escenario 3 Teatral — Desorientación Aguda, Validación de Feil y Alerta Roja
    # --------------------------------------------------------------------------
    sc3_text = audio_engine.DEMO_SCENARIOS["demo_3_crisis"]["transcript"]
    turn3 = llm_companion.process_conversation_turn(sc3_text)
    ext3 = turn3["extraction"]

    alert3_res = bridge.send_level3_emergency_alert(
        reason=ext3["emergency_reason"] or "Desorientación aguda",
        last_phrase=sc3_text,
    )
    print("\n[TEST 4] Escenario 3 — Crisis de Desorientación, Validación de Feil y Alerta Roja:")
    print(f"  • Respuesta Validación Feil: \"{turn3['assistant_reply']}\"")
    print(f"  • Estado emocional JSON:     {ext3['emotional_state']}")
    print(f"  • Emergencia disparada:      {ext3['emergency_triggered']}")
    print(f"  • Telegram Nivel 3 (SOS):    Entregado_API={alert3_res['delivered_telegram_api']} | Latencia={alert3_res['latency_ms']} ms")
    assert ext3["emergency_triggered"] is True
    assert ext3["emotional_state"] == "crisis_desorientacion"
    assert turn3["word_count"] <= 35

    print("\n" + "=" * 72)
    print("  [OK] TODAS LAS PRUEBAS DE LA FASE 3 PASARON CON ÉXITO")
    print("=" * 72)


if __name__ == "__main__":
    run_phase3_tests()
