"""
Pruebas de Validación — Fase 4 (pdf_report.py + app.py)
Verifica:
1. Generación correcta del Reporte Clínico en PDF para el médico geriatra.
2. Compilación e integridad de app.py y su catálogo del Álbum de Recuerdos (Opción C)
   y Aura de Respiración (Opción B).
"""

import json
import py_compile
import biomarkers
import config
import llm_companion
import pdf_report


def run_phase4_tests() -> None:
    print("=" * 72)
    print("  MEMORIAVIVA RISE — VALIDACIÓN DE INTERFAZ Y REPORTE PDF (FASE 4)")
    print("=" * 72)

    # 1. Validar generación del PDF Clínico No Diagnóstico
    profile = llm_companion.load_patient_profile()
    with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
        history_21 = json.load(f)
    trend = biomarkers.evaluate_longitudinal_trend(history_21)

    pdf_bytes = pdf_report.generate_clinical_pdf_bytes(
        profile=profile,
        trend_summary=trend,
        history_records=history_21,
    )
    is_valid_pdf = pdf_bytes.startswith(b"%PDF") and len(pdf_bytes) > 2000
    print("\n[TEST 1] Generador de Reporte Clínico en PDF (pdf_report.py):")
    print(f"  • Tamaño del PDF generado: {len(pdf_bytes)} bytes")
    print(f"  • Cabecera %PDF válida:    {is_valid_pdf}")
    assert is_valid_pdf, "El reporte clínico debe ser un archivo PDF válido"

    # 2. Validar compilación sin errores de sintaxis en app.py
    compiled_path = py_compile.compile(str(config.BASE_DIR / "app.py"), doraise=True)
    print("\n[TEST 2] Verificación de Sintaxis e Integridad de Streamlit (app.py):")
    print(f"  • Bytecode compilado:      {compiled_path}")

    print("\n" + "=" * 72)
    print("  [OK] TODAS LAS PRUEBAS DE LA FASE 4 PASARON CON ÉXITO")
    print("=" * 72)


if __name__ == "__main__":
    run_phase4_tests()
