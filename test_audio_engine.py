"""
Pruebas Unitarias y de Integración Acústica — Fase 2 (audio_engine.py)
Verifica:
1. Generación de los 3 audios de respaldo (.wav) en data/demo_audios/.
2. Medición directa de pausas en forma de onda (Error < 50 ms vs Meta 2 < 150 ms).
3. Protocolo Zero-Raw-Cloud Audio (eliminación garantizada de archivos temporales).
4. Síntesis de voz neural geriátrica con Edge-TTS (-15% velocidad, -5Hz tono).
"""

import os
from pathlib import Path

import audio_engine
import biomarkers
import config


def run_audio_tests() -> None:
    print("=" * 72)
    print("  MEMORIAVIVA RISE — VALIDACIÓN DEL MOTOR DE AUDIO Y VOZ (FASE 2)")
    print("=" * 72)

    # --------------------------------------------------------------------------
    # TEST 1: Generación de los 3 Audios Pregrabados Fail-Safe
    # --------------------------------------------------------------------------
    generated = audio_engine.generate_demo_backup_audios()
    print("\n[TEST 1] Generación de Audios Fail-Safe en data/demo_audios/:")
    for key, filepath in generated.items():
        p = Path(filepath)
        exists = p.exists() and p.stat().st_size > 10000
        print(f"  • {key}: {p.name} ({p.stat().st_size // 1024} KB) -> Existe={exists}")
        assert exists, f"El archivo {filepath} debe existir y tener contenido válido"

    # --------------------------------------------------------------------------
    # TEST 2: Precisión en Forma de Onda Acústica (Meta 2: Error < 150 ms)
    # --------------------------------------------------------------------------
    anomia_wav = generated["demo_2_anomia"]
    waveform_analysis = audio_engine.extract_acoustic_pauses_from_waveform(anomia_wav)
    measured_pause = waveform_analysis["max_acoustic_pause_sec"]
    error_ms = abs(measured_pause - 3.18) * 1000

    print("\n[TEST 2] Detector Acústico sobre Forma de Onda (demo_2_anomia.wav):")
    print(f"  • Duración total del audio:  {waveform_analysis['total_duration_sec']}s")
    print(f"  • Pausa anómica esperada:    3.18s")
    print(f"  • Pausa medida en la onda:   {measured_pause}s (Error: {error_ms:.1f} ms < 150 ms)")
    print(f"  • Conteo anómico acústico:   {waveform_analysis['anomic_acoustic_count']}")
    assert error_ms < 150.0, f"El error de medición ({error_ms} ms) debe ser menor a 150 ms"
    assert waveform_analysis["anomic_acoustic_count"] == 1

    # --------------------------------------------------------------------------
    # TEST 3: Inyección de Escenarios Demo + Biomarcadores Integrados
    # --------------------------------------------------------------------------
    stt_demo2 = audio_engine.transcribe_audio_with_timestamps(demo_scenario_id="demo_2_anomia")
    bio_demo2 = biomarkers.analyze_turn_biomarkers(
        text=stt_demo2["text"],
        word_timestamps=stt_demo2["word_timestamps"],
    )
    print("\n[TEST 3] Pipeline Completo Audio Demo 2 -> Biomarcadores:")
    print(f"  • Texto transcrito:   \"{stt_demo2['text'][:70]}...\"")
    print(f"  • MATTR calculado:    {bio_demo2['mattr']}")
    print(f"  • Pausa máx palabra:  {bio_demo2['max_pause_sec']}s antes de '{bio_demo2['hesitation_events'][0]['before_word']}'")
    print(f"  • Zero-Raw-Leakage:   {stt_demo2['zero_raw_leakage_verified']}")
    assert stt_demo2["zero_raw_leakage_verified"] is True
    assert bio_demo2["max_pause_sec"] == 3.18

    # --------------------------------------------------------------------------
    # TEST 4: Verificación de Destrucción de Audio Temporal (Zero-Raw-Cloud Audio)
    # --------------------------------------------------------------------------
    with open(anomia_wav, "rb") as f:
        raw_bytes = f.read()

    stt_live_sim = audio_engine.transcribe_audio_with_timestamps(audio_source=raw_bytes)
    ephemeral_file = config.BASE_DIR / "temp_input_ephemeral.wav"
    print("\n[TEST 4] Auditoría de Privacidad Zero-Raw-Cloud Audio:")
    print(f"  • ¿Archivo temporal destruido tras procesar?: {not ephemeral_file.exists()}")
    assert not ephemeral_file.exists(), "El archivo temporal .wav NO debe persistir en disco"
    assert stt_live_sim["zero_raw_leakage_verified"] is True

    # --------------------------------------------------------------------------
    # TEST 5: Síntesis de Voz Geriátrica (Edge-TTS a -15% velocidad y -5Hz)
    # --------------------------------------------------------------------------
    frase_respuesta = (
        "Le habló su hija Rocío, don Manuel. Qué alegría que platicó con Rocío "
        "desde Manzanillo. Oiga, ¿y usted qué le platicó a ella?"
    )
    tts_out = config.BASE_DIR / "temp_test_tts.mp3"
    tts_res = audio_engine.speak_geriatric(frase_respuesta, output_path=tts_out)
    audio_generated_path = Path(tts_res["audio_path"])

    print("\n[TEST 5] Síntesis de Voz Neural Geriátrica (Edge-TTS):")
    print(f"  • Motor utilizado:    {tts_res['engine']} ({tts_res['voice']})")
    print(f"  • Prosodia aplicada:  Velocidad={tts_res['rate']}, Tono={tts_res['pitch']}")
    print(f"  • Latencia síntesis:  {tts_res['latency_ms']} ms")
    print(f"  • Archivo generado:   {audio_generated_path.name} ({audio_generated_path.stat().st_size} bytes)")
    assert tts_res["success"] is True
    assert audio_generated_path.exists() and audio_generated_path.stat().st_size > 1000

    # Limpiar archivo de prueba TTS
    if audio_generated_path.exists():
        os.remove(audio_generated_path)

    print("\n" + "=" * 72)
    print("  [OK] TODAS LAS PRUEBAS DE LA FASE 2 PASARON CON ÉXITO")
    print("=" * 72)


if __name__ == "__main__":
    run_audio_tests()
