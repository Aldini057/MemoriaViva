"""
MemoriaViva RISE - Generador de Reporte Clínico Longitudinal en PDF (No Diagnóstico)
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Cumple con el Pilar RESPONSIBLE del marco RISE:
- Incluye cláusula explícita de Apoyo a la Decisión Clínica No Diagnóstico.
- Presenta la calibración auto-referenciada (Línea Base Personal de 14 días vs Ventana Reciente).
- Emplea terminología constructiva y auditable para el médico geriatra o neurólogo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fpdf import FPDF


def _latin1_safe(text: str) -> str:
    """Convierte caracteres Unicode fuera de Latin-1 para las fuentes base de FPDF."""
    replacements = {
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "-",
        "…": "...",
        "🌿": "[Vitalidad]",
        "🧠": "[Memoria]",
        "⏱️": "[Ritmo]",
        "🟢": "[Nivel 1]",
        "🟡": "[Nivel 2]",
        "🔴": "[Nivel 3]",
    }
    out = str(text)
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out.encode("latin-1", errors="replace").decode("latin-1")


class MemoriaVivaPDFReport(FPDF):
    def header(self) -> None:
        self.set_fill_color(125, 157, 134)  # Verde salvia cálido (#7D9D86)
        self.rect(0, 0, 210, 24, style="F")
        self.set_y(6)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.cell(
            0,
            7,
            _latin1_safe("MemoriaViva RISE - Reporte Longitudinal de Habla Espontanea"),
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.set_font("Helvetica", "I", 9)
        self.cell(
            0,
            5,
            _latin1_safe(
                "Apoyo Clinico No Diagnostico | Terapia de Reminiscencia y Biomarcadores Linguisticos"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(
            0,
            10,
            _latin1_safe(
                f"MemoriaViva RISE (Global RISE AI Hackathon 2026) - Pagina {self.page_no()}"
            ),
            align="C",
        )


def generate_clinical_pdf_bytes(
    profile: dict[str, Any],
    trend_summary: dict[str, Any],
    history_records: list[dict[str, Any]],
) -> bytes:
    """
    Genera en memoria un documento PDF estructurado con el seguimiento de 21 días
    para entregar al médico geriatra o neurólogo de cabecera.
    """
    pdf = MemoriaVivaPDFReport()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pac = profile.get("paciente", {})
    fam = profile.get("red_familiar_y_afectiva", {})
    cuidador = (
        fam.get("hija_mayor_cuidadora", {}).get("nombre")
        or profile.get("contacto_emergencia_telegram", {}).get("nombre", "Familiar")
    )

    # 1. Ficha de Identificación
    pdf.set_text_color(58, 50, 44)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        8,
        _latin1_safe("1. Datos de Identificacion del Adulto Mayor"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    info_lines = [
        f"Paciente: {pac.get('nombre_completo', 'Manuel Gonzalez')} ({pac.get('nombre_preferido', 'Don Manuel')})",
        f"Edad: {pac.get('edad', 72)} anos | Residencia: {pac.get('ciudad_residencia', 'Jalisco')}",
        f"Ocupacion historica: {pac.get('ocupacion_historica', 'N/D')}",
        f"Familiar de enlace: {cuidador} | Fecha de emision: {fecha_str}",
    ]
    for line in info_lines:
        pdf.cell(0, 6, _latin1_safe(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 2. Cláusula Ética No Diagnóstica (Pilar Responsible)
    pdf.set_fill_color(250, 246, 240)
    pdf.set_draw_color(217, 155, 82)
    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(
        0,
        5,
        _latin1_safe(
            "NOTA ETICA Y MEDICA (MARCO RISE): Este documento NO constituye un diagnostico medico "
            "definitivo de deterioro cognitivo ni demencia. Presenta mediciones acusticas y "
            "linguisticas pasivas recolectadas durante sesiones de terapia de reminiscencia en el "
            "hogar, comparadas contra la linea base individual del propio paciente (Z-Score). "
            "Las variaciones pueden asociarse a fatiga, estado animico, sueno o medicacion."
        ),
        border=1,
        fill=True,
    )
    pdf.ln(4)

    # 3. Resumen Comparativo (Línea Base 14 días vs. Últimos 5 días)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        8,
        _latin1_safe("2. Comparativa Longitudinal Auto-Referenciada (21 Dias)"),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 224, 214)
    col_widths = [65, 40, 40, 45]
    headers = ["Biomarcador Evaluado", "Linea Base (D1-14)", "Reciente (Ult. 5d)", "Variacion / Z-Score"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, _latin1_safe(h), border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    rows = [
        [
            "Diversidad Lexica (MATTR)",
            str(trend_summary.get("baseline_mattr", 0.75)),
            str(trend_summary.get("recent_mattr", 0.60)),
            f"-{trend_summary.get('mattr_drop_pct', 0)}% (Z={trend_summary.get('mattr_z_score', 0)})",
        ],
        [
            "Pausa Intra-Oracional Promedio",
            f"{trend_summary.get('baseline_pause', 1.10)} s",
            f"{trend_summary.get('recent_pause', 2.58)} s",
            f"+{trend_summary.get('pause_increase_pct', 0)}% (Z=+{trend_summary.get('pause_z_score', 0)})",
        ],
        [
            "Pausas Anomicas (>2.0s) Recientes",
            "0 - 1 / sesion",
            f"{trend_summary.get('recent_total_anomic_pauses', 0)} acum.",
            "Acceso lexico (Pistono 2016)",
        ],
        [
            "Repeticion Semantica (TF-IDF>0.72)",
            "0 / sesion",
            f"{trend_summary.get('recent_total_repetitions', 0)} acum.",
            "Memoria de trabajo (Guinn 2012)",
        ],
    ]
    for row in rows:
        for w, val in zip(col_widths, row):
            pdf.cell(w, 6, _latin1_safe(val), border=1, align="C")
        pdf.ln()
    pdf.ln(3)

    # Recomendación
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        _latin1_safe(f"Observacion longitudinal: {trend_summary.get('ethical_recommendation', '')}"),
    )
    pdf.ln(3)

    # 4. Registro Diario de las Últimas 21 Sesiones
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(
        0,
        7,
        _latin1_safe("3. Bitacora de Sesiones Diarias (21 Dias)"),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "B", 8)
    h_widths = [38, 32, 38, 38, 44]
    h_cols = ["Dia / Fecha", "Indice MATTR", "Pausa Media (s)", "Pausas > 2.0s", "Estado Afectivo"]
    for w, c in zip(h_widths, h_cols):
        pdf.cell(w, 6, _latin1_safe(c), border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for rec in history_records[-21:]:
        row_vals = [
            str(rec.get("day", "")),
            str(rec.get("mattr", "")),
            f"{rec.get('mean_pause', '')} s",
            str(rec.get("anomic_pauses", 0)),
            str(rec.get("mood", "Tranquilo")),
        ]
        for w, val in zip(h_widths, row_vals):
            pdf.cell(w, 5.2, _latin1_safe(val), border=1, align="C")
        pdf.ln()

    return bytes(pdf.output())
