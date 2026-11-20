"""
MemoriaViva RISE - Sistema de Diseño UX/UI (Clínico Moderno)
Global RISE AI Hackathon 2026

Encapsula:
- Paletas semánticas Clínico Moderno (Modo Día y Modo Noche).
- Librería de íconos vectoriales SVG minimalistas (sin emojis crudos).
- CSS global para Streamlit con jerarquía clara de botones, tarjetas y formularios.
- Stepper horizontal, tarjetas KPI y feed de Telegram estilizados.
- Gráfica longitudinal Plotly de 21 días con selector de métrica y banda de línea base.
- Componente HTML/JS inmersivo del Modo Kiosco (Protector de Pantalla + PTT Dual + PIN Trigger).
"""

from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ==============================================================================
# 1. Tokens Semánticos — Dirección Visual: Clínico Moderno
# ==============================================================================
def get_palette(is_dark: bool) -> dict[str, str]:
    if is_dark:
        return {
            "scheme": "dark",
            "bg": "#0F1419",
            "surface": "#171E26",
            "surface_subtle": "#1E2732",
            "border": "#26313E",
            "border_strong": "#364556",
            "text": "#F1F5F9",
            "text_muted": "#94A3B8",
            "text_soft": "#64748B",
            "primary": "#22B8CF",
            "primary_hover": "#3BC9DB",
            "primary_soft": "#12323D",
            "primary_soft_text": "#67E8F9",
            "primary_fg": "#082026",
            "amber": "#F59E0B",
            "amber_soft": "#2C2210",
            "amber_text": "#FCD34D",
            "emerald": "#10B981",
            "emerald_soft": "#0D2B23",
            "emerald_text": "#6EE7B7",
            "danger": "#EF4444",
            "danger_soft": "#311619",
            "danger_text": "#FCA5A5",
            "shadow": "0 1px 3px rgba(0, 0, 0, 0.35)",
            "shadow_md": "0 6px 20px rgba(0, 0, 0, 0.38)",
        }
    return {
        "scheme": "light",
        "bg": "#F6F8FA",
        "surface": "#FFFFFF",
        "surface_subtle": "#F1F5F9",
        "border": "#E2E8F0",
        "border_strong": "#CBD5E1",
        "text": "#0F172A",
        "text_muted": "#475569",
        "text_soft": "#64748B",
        "primary": "#0E7490",
        "primary_hover": "#155E75",
        "primary_soft": "#ECFEFF",
        "primary_soft_text": "#155E75",
        "primary_fg": "#FFFFFF",
        "amber": "#D97706",
        "amber_soft": "#FFFBEB",
        "amber_text": "#92400E",
        "emerald": "#059669",
        "emerald_soft": "#ECFDF5",
        "emerald_text": "#065F46",
        "danger": "#DC2626",
        "danger_soft": "#FEF2F2",
        "danger_text": "#991B1B",
        "shadow": "0 1px 2px rgba(15, 23, 42, 0.05)",
        "shadow_md": "0 6px 18px rgba(15, 23, 42, 0.07)",
    }


# ==============================================================================
# 2. Librería de Íconos Vectoriales SVG Minimalistas
# ==============================================================================
_SVG_PATHS: dict[str, str] = {
    "pulse": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "activity": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
    "sliders": (
        '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/>'
    ),
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "mic": (
        '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>'
        '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>'
    ),
    "bell": (
        '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
        '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'
    ),
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "brain": (
        '<path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 '
        '3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>'
        '<path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 '
        '3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "heart": (
        '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 '
        '2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>'
    ),
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "sparkles": (
        '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 '
        '21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/>'
    ),
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "key": (
        '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/>'
        '<path d="m15.5 7.5 3 3L22 7l-3-3"/>'
    ),
}


def _compact_html(raw: str) -> str:
    """Normaliza HTML sin sangría ni líneas vacías para evitar que CommonMark lo parsee como código."""
    return " ".join(line.strip() for line in raw.splitlines() if line.strip())


def svg_icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    path = _SVG_PATHS.get(name, _SVG_PATHS["pulse"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block; vertical-align:middle; flex-shrink:0;">{path}</svg>'
    )


# ==============================================================================
# 3. Sistema CSS Global para Streamlit
# ==============================================================================
def inject_design_system_css(
    is_dark: bool,
    kiosk_mode: bool = False,
    narrow_onboarding: bool = False,
) -> None:
    p = get_palette(is_dark)

    if kiosk_mode:
        layout_css = """
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stAppDeployButton"],
        .stAppDeployButton,
        header[data-testid="stHeader"],
        #MainMenu,
        footer {
            display: none !important;
        }
        .block-container {
            padding: 0.6rem 0.75rem !important;
            max-width: 100% !important;
        }
        div[data-testid="stElementContainer"] iframe {
            height: calc(100vh - 20px) !important;
            min-height: 540px !important;
            border-radius: 20px !important;
            display: block !important;
        }
        """
    elif narrow_onboarding:
        layout_css = """
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stAppDeployButton"],
        .stAppDeployButton,
        #MainMenu,
        footer {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            height: 0.5rem !important;
        }
        .block-container {
            max-width: 780px !important;
            padding-top: 1.75rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
        }
        """
    else:
        layout_css = """
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stAppDeployButton"],
        .stAppDeployButton,
        #MainMenu,
        footer {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            height: 0.5rem !important;
        }
        .block-container {
            max-width: 1240px !important;
            padding-top: 1.4rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        """

    css = f"""
    <style>
        :root, html, body, [data-testid="stAppViewContainer"], .stApp {{
            color-scheme: {p['scheme']} !important;
            background-color: {p['bg']} !important;
            color: {p['text']} !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }}
        {layout_css}

        /* Tipografía base */
        h1, h2, h3, h4, h5, h6 {{
            color: {p['text']} !important;
            letter-spacing: -0.02em;
            font-weight: 600 !important;
        }}
        p, label, [data-testid="stMarkdownContainer"] {{
            color: {p['text']};
        }}
        small, .stCaption, [data-testid="stCaptionContainer"] p {{
            color: {p['text_soft']} !important;
        }}

        /* Jerarquía de Botones: Primario vs Secundario */
        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {{
            border-radius: 10px !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.875rem !important;
            font-weight: 600 !important;
            transition: all 0.16s ease !important;
            line-height: 1.3 !important;
            min-height: 2.45rem !important;
        }}

        /* Primarios (Teal sólido) */
        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"],
        button[data-testid="baseButton-primary"],
        button[data-testid="stBaseButton-primaryFormSubmit"] {{
            background-color: {p['primary']} !important;
            color: {p['primary_fg']} !important;
            border: 1px solid {p['primary']} !important;
            box-shadow: {p['shadow']} !important;
        }}
        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover,
        button[data-testid="baseButton-primary"]:hover,
        button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{
            background-color: {p['primary_hover']} !important;
            border-color: {p['primary_hover']} !important;
            color: {p['primary_fg']} !important;
        }}

        /* Secundarios (Superficie limpia con borde sutil) */
        .stButton > button[kind="secondary"],
        .stDownloadButton > button[kind="secondary"],
        .stFormSubmitButton > button[kind="secondary"],
        button[data-testid="stBaseButton-secondary"],
        button[data-testid="baseButton-secondary"],
        button[data-testid="stBaseButton-secondaryFormSubmit"] {{
            background-color: {p['surface']} !important;
            color: {p['text']} !important;
            border: 1px solid {p['border_strong']} !important;
            box-shadow: none !important;
        }}
        .stButton > button[kind="secondary"]:hover,
        .stDownloadButton > button[kind="secondary"]:hover,
        .stFormSubmitButton > button[kind="secondary"]:hover,
        button[data-testid="stBaseButton-secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover,
        button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
            background-color: {p['surface_subtle']} !important;
            border-color: {p['primary']} !important;
            color: {p['text']} !important;
        }}
        .stButton > button:disabled,
        .stDownloadButton > button:disabled,
        .stFormSubmitButton > button:disabled {{
            opacity: 0.42 !important;
        }}

        /* Botón de acción destructiva / restablecimiento */
        .st-key-reset_onboarding_btn button {{
            background-color: {p['danger_soft']} !important;
            color: {p['danger_text']} !important;
            border: 1px solid {p['danger']} !important;
        }}
        .st-key-reset_onboarding_btn button:hover {{
            background-color: {p['danger']} !important;
            color: #FFFFFF !important;
        }}

        /* Inputs, Textareas y Selectboxes */
        input, textarea,
        [data-baseweb="input"],
        [data-baseweb="base-input"],
        [data-baseweb="textarea"],
        [data-baseweb="select"] > div {{
            background-color: {p['bg']} !important;
            color: {p['text']} !important;
            border-color: {p['border']} !important;
            border-radius: 10px !important;
        }}
        [data-baseweb="input"]:focus-within,
        [data-baseweb="textarea"]:focus-within,
        [data-baseweb="select"] > div:focus-within {{
            border-color: {p['primary']} !important;
            box-shadow: 0 0 0 2px {p['primary_soft']} !important;
        }}

        /* Contenedores con borde nativos (st.container(border=True) y st.form) */
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stForm"] {{
            background-color: {p['surface']} !important;
            border: 1px solid {p['border']} !important;
            border-radius: 16px !important;
            box-shadow: {p['shadow']} !important;
        }}

        /* Expanders limpios */
        [data-testid="stExpander"] {{
            background-color: {p['bg']} !important;
            border: 1px solid {p['border']} !important;
            border-radius: 12px !important;
            overflow: hidden;
        }}
        [data-testid="stExpander"] summary {{
            color: {p['text']} !important;
            font-weight: 500 !important;
        }}

        /* File uploader */
        [data-testid="stFileUploaderDropzone"] {{
            background-color: {p['bg']} !important;
            border: 1.5px dashed {p['border_strong']} !important;
            border-radius: 14px !important;
        }}

        /* Dialog modal (@st.dialog) */
        [data-testid="stDialog"] [role="dialog"] {{
            background-color: {p['surface']} !important;
            border: 1px solid {p['border']} !important;
            border-radius: 18px !important;
            color: {p['text']} !important;
        }}

        /* Pestañas superiores estilo navegación limpia */
        [data-baseweb="tab-list"] {{
            gap: 0.4rem !important;
            border-bottom: 1px solid {p['border']} !important;
            padding-bottom: 0.45rem !important;
            margin-bottom: 1.25rem !important;
        }}
        button[data-baseweb="tab"] {{
            background-color: transparent !important;
            color: {p['text_muted']} !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            padding: 0.45rem 0.95rem !important;
            border-radius: 9px !important;
            border: 1px solid transparent !important;
            transition: all 0.15s ease !important;
        }}
        button[data-baseweb="tab"]:hover {{
            background-color: {p['surface_subtle']} !important;
            color: {p['text']} !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: {p['surface']} !important;
            color: {p['primary']} !important;
            border: 1px solid {p['border']} !important;
            font-weight: 600 !important;
            box-shadow: {p['shadow']} !important;
        }}
        [data-baseweb="tab-highlight"] {{
            display: none !important;
        }}

        /* Radio horizontal estilizado como segmented control */
        div[role="radiogroup"][aria-orientation="horizontal"] {{
            background-color: {p['surface_subtle']} !important;
            padding: 3px !important;
            border-radius: 10px !important;
            border: 1px solid {p['border']} !important;
            display: inline-flex !important;
            gap: 2px !important;
        }}
        div[role="radiogroup"][aria-orientation="horizontal"] label {{
            padding: 0.25rem 0.7rem !important;
            border-radius: 7px !important;
            margin: 0 !important;
            font-size: 0.82rem !important;
        }}

        /* Progress bar */
        [data-testid="stProgress"] > div > div > div {{
            background-color: {p['primary']} !important;
        }}

        /* Ocultar disparadores internos de Push-to-Talk y Modal PIN */
        .st-key-ptt_hidden_trigger,
        .st-key-kiosk_unlock_trigger {{
            position: fixed !important;
            left: -9999px !important;
            top: -9999px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0.01 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }}

        /* Tarjetas y Componentes Custom */
        .mv-brand-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .mv-brand-icon {{
            width: 38px;
            height: 38px;
            border-radius: 11px;
            background-color: {p['primary_soft']};
            color: {p['primary_soft_text']};
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .mv-brand-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {p['text']};
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            line-height: 1.2;
        }}
        .mv-brand-sub {{
            font-size: 0.82rem;
            color: {p['text_soft']};
            margin-top: 2px;
        }}
        .mv-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 2px 9px;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 600;
            line-height: 1.5;
        }}
        .mv-pill-primary {{
            background-color: {p['primary_soft']};
            color: {p['primary_soft_text']};
        }}
        .mv-pill-emerald {{
            background-color: {p['emerald_soft']};
            color: {p['emerald_text']};
        }}
        .mv-pill-amber {{
            background-color: {p['amber_soft']};
            color: {p['amber_text']};
        }}
        .mv-pill-danger {{
            background-color: {p['danger_soft']};
            color: {p['danger_text']};
        }}
        .mv-pill-neutral {{
            background-color: {p['surface_subtle']};
            color: {p['text_muted']};
        }}

        .mv-divider {{
            height: 1px;
            background-color: {p['border']};
            margin: 0.85rem 0 1.25rem 0;
        }}

        /* Stepper horizontal del Onboarding */
        .mv-stepper {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.65rem;
            margin: 0.5rem 0 1.4rem 0;
        }}
        .mv-step-bar {{
            height: 5px;
            border-radius: 999px;
            margin-bottom: 0.45rem;
        }}
        .mv-step-label {{
            font-size: 0.78rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Tarjetas KPI del Panel Familiar */
        .mv-kpi {{
            background-color: {p['surface']};
            border: 1px solid {p['border']};
            border-radius: 14px;
            padding: 1.05rem 1.2rem;
            box-shadow: {p['shadow']};
            height: 100%;
        }}
        .mv-kpi-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.55rem;
        }}
        .mv-kpi-label {{
            font-size: 0.8rem;
            font-weight: 500;
            color: {p['text_muted']};
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .mv-kpi-value {{
            font-size: 1.45rem;
            font-weight: 700;
            color: {p['text']};
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}
        .mv-kpi-base {{
            font-size: 0.8rem;
            font-weight: 500;
            color: {p['text_soft']};
            margin-left: 0.35rem;
            font-variant-numeric: tabular-nums;
        }}
        .mv-kpi-sub {{
            font-size: 0.78rem;
            color: {p['text_soft']};
            margin-top: 0.4rem;
            line-height: 1.4;
        }}

        /* Tarjetas de Telegram */
        .mv-tg-item {{
            background-color: {p['bg']};
            border: 1px solid {p['border']};
            border-radius: 11px;
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.65rem;
            font-size: 0.84rem;
            line-height: 1.5;
            color: {p['text']};
        }}
        .mv-tg-meta {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.74rem;
            color: {p['text_soft']};
            margin-bottom: 0.35rem;
        }}

        /* Encabezados de sección */
        .mv-sec-title {{
            font-size: 0.98rem;
            font-weight: 600;
            color: {p['text']};
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.15rem;
        }}
        .mv-sec-sub {{
            font-size: 0.82rem;
            color: {p['text_soft']};
            margin-bottom: 0.85rem;
        }}

        /* Tarjeta de Foto en Galería */
        .mv-photo-cap {{
            font-size: 0.78rem;
            color: {p['text_muted']};
            margin-top: 0.35rem;
            margin-bottom: 0.4rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
    """
    st.markdown(css.strip(), unsafe_allow_html=True)


# ==============================================================================
# 4. Constructores de Bloques HTML Limpios
# ==============================================================================
def render_brand_header_html(
    title: str,
    subtitle: str,
    badge_text: str = "RISE",
    status_pill: tuple[str, str] | None = None,
) -> str:
    """Genera el bloque de marca con ícono vectorial y subtítulo limpio."""
    status_html = ""
    if status_pill:
        pill_label, pill_variant = status_pill
        status_html = f'<span class="mv-pill mv-pill-{pill_variant}">{html.escape(pill_label)}</span>'

    return _compact_html(
        f"""
        <div class="mv-brand-row">
            <div class="mv-brand-icon">{svg_icon("pulse", 19)}</div>
            <div>
                <div class="mv-brand-title">
                    <span>{html.escape(title)}</span>
                    <span class="mv-pill mv-pill-primary">{html.escape(badge_text)}</span>
                    {status_html}
                </div>
                <div class="mv-brand-sub">{html.escape(subtitle)}</div>
            </div>
        </div>
        """
    )


def render_stepper_html(current_step: int, labels: list[str], is_dark: bool) -> str:
    """Genera un stepper horizontal minimalista de 4 pasos."""
    p = get_palette(is_dark)
    items_html = []
    for idx, label in enumerate(labels, start=1):
        if idx < current_step:
            bar_color = p["primary"]
            bar_opacity = "0.48"
            txt_color = p["text_muted"]
            weight = "500"
        elif idx == current_step:
            bar_color = p["primary"]
            bar_opacity = "1"
            txt_color = p["text"]
            weight = "600"
        else:
            bar_color = p["border"]
            bar_opacity = "1"
            txt_color = p["text_soft"]
            weight = "500"

        items_html.append(
            _compact_html(
                f"""
                <div>
                    <div class="mv-step-bar" style="background:{bar_color}; opacity:{bar_opacity};"></div>
                    <div class="mv-step-label" style="color:{txt_color}; font-weight:{weight};">
                        {idx}. {html.escape(label)}
                    </div>
                </div>
                """
            )
        )
    return f'<div class="mv-stepper">{"".join(items_html)}</div>'


def render_kpi_card_html(
    label: str,
    value: str,
    subtitle: str,
    badge_text: str,
    badge_variant: str = "primary",
    icon_name: str = "activity",
    baseline_text: str = "",
) -> str:
    base_html = f'<span class="mv-kpi-base">{html.escape(baseline_text)}</span>' if baseline_text else ""
    return _compact_html(
        f"""
        <div class="mv-kpi">
            <div class="mv-kpi-top">
                <span class="mv-kpi-label">{svg_icon(icon_name, 14)} {html.escape(label)}</span>
                <span class="mv-pill mv-pill-{badge_variant}">{html.escape(badge_text)}</span>
            </div>
            <div>
                <span class="mv-kpi-value">{html.escape(value)}</span>{base_html}
            </div>
            <div class="mv-kpi-sub">{html.escape(subtitle)}</div>
        </div>
        """
    )


def render_telegram_card_html(
    level: int,
    message: str,
    timestamp: str,
    latency_ms: int | float,
    is_dark: bool,
) -> str:
    p = get_palette(is_dark)
    if level == 1:
        accent = p["emerald"]
        lbl = "Nivel 1 · Pulso Diario"
        lbl_col = p["emerald_text"]
    elif level == 2:
        accent = p["amber"]
        lbl = "Nivel 2 · Tendencia"
        lbl_col = p["amber_text"]
    else:
        accent = p["danger"]
        lbl = "Nivel 3 · Alerta S.O.S."
        lbl_col = p["danger_text"]

    safe_msg = html.escape(message).replace("\n", "<br>")
    return _compact_html(
        f"""
        <div class="mv-tg-item" style="border-left: 3.5px solid {accent};">
            <div class="mv-tg-meta">
                <span style="font-weight:600; color:{lbl_col};">{lbl}</span>
                <span>{html.escape(str(timestamp))} · {int(latency_ms)} ms</span>
            </div>
            <div>{safe_msg}</div>
        </div>
        """
    )


def render_section_header_html(title: str, subtitle: str, icon_name: str = "activity") -> str:
    return _compact_html(
        f"""
        <div class="mv-sec-title">{svg_icon(icon_name, 16)} <span>{html.escape(title)}</span></div>
        <div class="mv-sec-sub">{html.escape(subtitle)}</div>
        """
    )


def render_telegram_panel_header_html(caregiver_name: str, is_connected: bool) -> str:
    status_label, status_variant = ("Conectado", "emerald") if is_connected else ("Modo local", "neutral")
    return _compact_html(
        f"""
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:0.5rem; margin-bottom:0.75rem;">
            <div>
                <div class="mv-sec-title">{svg_icon("send", 15)} <span>Puente Familiar</span></div>
                <div style="font-size:0.8rem; opacity:0.7;">Notificaciones a {html.escape(caregiver_name)} vía Telegram</div>
            </div>
            <span class="mv-pill mv-pill-{status_variant}">{status_label}</span>
        </div>
        """
    )


def render_demo_scenario_card_html(badge: str, variant: str, title: str, desc: str) -> str:
    return _compact_html(
        f"""
        <div style="margin-bottom:0.55rem;">
            <span class="mv-pill mv-pill-{variant}">{html.escape(badge)}</span>
        </div>
        <div style="font-size:1rem; font-weight:600; margin-bottom:0.35rem;">{html.escape(title)}</div>
        <div style="font-size:0.83rem; opacity:0.78; line-height:1.5; min-height:66px; margin-bottom:0.75rem;">
            {html.escape(desc)}
        </div>
        """
    )


def render_turn_result_header_html(timestamp: str, badge_label: str, badge_variant: str) -> str:
    return _compact_html(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.8rem;">
            <div class="mv-sec-title">{svg_icon("activity", 15)} <span>Resultado del último turno ({html.escape(timestamp)})</span></div>
            <span class="mv-pill mv-pill-{badge_variant}">{html.escape(badge_label)}</span>
        </div>
        """
    )


# ==============================================================================
# 5. Gráfica Longitudinal Plotly (21 Días + Selector + Banda Línea Base)
# ==============================================================================
def build_longitudinal_chart(
    history_21_days: list[dict[str, Any]],
    trend_data: dict[str, Any],
    mode: str = "combined",
    is_dark: bool = False,
) -> go.Figure:
    p = get_palette(is_dark)
    df = pd.DataFrame(history_21_days)
    short_days = [f"D{i + 1}" for i in range(len(df))]
    full_days = df["day"].tolist()
    baseline_end_idx = min(13, max(0, len(df) - 1))

    fig = go.Figure()

    # Banda visual sombreada de línea base personal (Días 1-14)
    if len(df) >= 14:
        fig.add_vrect(
            x0=short_days[0],
            x1=short_days[baseline_end_idx],
            fillcolor=p["primary"],
            opacity=0.06 if not is_dark else 0.09,
            layer="below",
            line_width=0,
            annotation_text="Línea base personal (D1–D14)",
            annotation_position="top left",
            annotation_font=dict(size=11, color=p["text_soft"]),
        )

    show_mattr = mode in ("combined", "mattr")
    show_pause = mode in ("combined", "pause")

    if show_mattr:
        fig.add_trace(
            go.Scatter(
                x=short_days,
                y=df["mattr"],
                customdata=full_days,
                name="Riqueza Léxica (MATTR)",
                mode="lines+markers",
                line=dict(color=p["primary"], width=2.8, shape="spline", smoothing=0.5),
                marker=dict(size=5.5, color=p["primary"]),
                fill="tozeroy" if mode == "mattr" else None,
                fillcolor="rgba(14, 116, 144, 0.10)" if not is_dark else "rgba(34, 184, 207, 0.12)",
                yaxis="y1",
                hovertemplate="<b>%{customdata}</b><br>MATTR: %{y:.2f}<extra></extra>",
            )
        )
        if mode == "mattr" and trend_data.get("baseline_mattr"):
            base_m = float(trend_data["baseline_mattr"])
            fig.add_hline(
                y=base_m,
                line_dash="dot",
                line_color=p["primary"],
                opacity=0.65,
                annotation_text=f"Base personal ({base_m:.2f})",
                annotation_position="bottom right",
                annotation_font=dict(size=11, color=p["text_muted"]),
            )

    if show_pause:
        target_axis = "y2" if mode == "combined" else "y1"
        fig.add_trace(
            go.Scatter(
                x=short_days,
                y=df["mean_pause"],
                customdata=full_days,
                name="Pausa Promedio (s)",
                mode="lines+markers",
                line=dict(
                    color=p["amber"],
                    width=2.5,
                    dash="dash" if mode == "combined" else "solid",
                    shape="spline",
                    smoothing=0.5,
                ),
                marker=dict(size=5.5, color=p["amber"]),
                fill="tozeroy" if mode == "pause" else None,
                fillcolor="rgba(217, 119, 6, 0.10)" if not is_dark else "rgba(245, 158, 11, 0.12)",
                yaxis=target_axis,
                hovertemplate="<b>%{customdata}</b><br>Pausa promedio: %{y:.2f} s<extra></extra>",
            )
        )
        if mode == "pause":
            if trend_data.get("baseline_pause"):
                base_p = float(trend_data["baseline_pause"])
                fig.add_hline(
                    y=base_p,
                    line_dash="dot",
                    line_color=p["amber"],
                    opacity=0.7,
                    annotation_text=f"Base personal ({base_p:.2f} s)",
                    annotation_position="bottom right",
                    annotation_font=dict(size=11, color=p["text_muted"]),
                )
            fig.add_hline(
                y=2.0,
                line_dash="dash",
                line_color=p["danger"],
                opacity=0.5,
                annotation_text="Umbral anómico (2.0 s)",
                annotation_position="top right",
                annotation_font=dict(size=11, color=p["danger_text"]),
            )

    layout_kwargs: dict[str, Any] = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            color=p["text_muted"],
            size=12,
        ),
        height=330,
        margin=dict(l=12, r=12, t=28, b=16),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=p["surface"],
            bordercolor=p["border_strong"],
            font=dict(color=p["text"], size=12),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12, color=p["text_muted"]),
        ),
        xaxis=dict(
            showgrid=False,
            linecolor=p["border"],
            tickfont=dict(size=11, color=p["text_soft"]),
            nticks=8,
        ),
    )

    if mode == "combined":
        layout_kwargs["yaxis"] = dict(
            title=dict(text="MATTR", font=dict(size=11, color=p["primary"])),
            range=[0.42, 0.88],
            gridcolor=p["border"],
            zeroline=False,
            tickfont=dict(size=11, color=p["text_soft"]),
        )
        layout_kwargs["yaxis2"] = dict(
            title=dict(text="Pausa (s)", font=dict(size=11, color=p["amber"])),
            overlaying="y",
            side="right",
            range=[0.5, 3.6],
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=11, color=p["text_soft"]),
        )
    elif mode == "mattr":
        layout_kwargs["yaxis"] = dict(
            title=dict(text="Índice MATTR", font=dict(size=11, color=p["primary"])),
            range=[0.42, 0.88],
            gridcolor=p["border"],
            zeroline=False,
            tickfont=dict(size=11, color=p["text_soft"]),
        )
    else:
        layout_kwargs["yaxis"] = dict(
            title=dict(text="Pausa Promedio (s)", font=dict(size=11, color=p["amber"])),
            range=[0.5, 3.6],
            gridcolor=p["border"],
            zeroline=False,
            tickfont=dict(size=11, color=p["text_soft"]),
        )

    fig.update_layout(**layout_kwargs)
    return fig


# ==============================================================================
# 6. Componente HTML/JS Inmersivo del Modo Kiosco (Vista B)
# ==============================================================================
def build_kiosk_screensaver_html(
    photos_list: list[dict[str, str]],
    rotation_ms: int,
    patient_name: str,
    last_reply: str,
    learned_badge: str,
    audio_data_uri: str,
    ptt_port: int,
    is_dark: bool,
) -> str:
    p = get_palette(is_dark)
    photos_json = json.dumps(
        [{"caption": item.get("caption", ""), "data_uri": item["data_uri"]} for item in photos_list],
        ensure_ascii=False,
    )
    patient_json = json.dumps(patient_name, ensure_ascii=False)
    reply_json = json.dumps(last_reply, ensure_ascii=False)
    learned_json = json.dumps(learned_badge, ensure_ascii=False)
    audio_json = json.dumps(audio_data_uri)

    primary_bg = p["primary"]
    primary_fg = p["primary_fg"]

    return f"""
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
            background: #0F1419;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #F8FAFC;
            user-select: none;
            -webkit-user-select: none;
        }}
        .stage {{
            position: relative;
            width: 100%;
            height: 100vh;
            border-radius: 20px;
            overflow: hidden;
            background: #0F1419;
            outline: none;
        }}
        .slide-img {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0;
            transform: scale(1.0);
            transition: opacity 1.4s ease-in-out, transform 9s ease-out;
        }}
        .slide-img.active {{
            opacity: 1;
            transform: scale(1.05);
        }}

        /* Scrims suaves para legibilidad sin aplastar la foto */
        .scrim-top {{
            position: absolute;
            top: 0; left: 0; right: 0;
            padding: 22px 26px;
            background: linear-gradient(to bottom, rgba(10, 15, 22, 0.65) 0%, rgba(10, 15, 22, 0) 100%);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            z-index: 4;
        }}
        .clock-pill {{
            background: rgba(15, 23, 42, 0.48);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 16px;
            padding: 10px 18px;
        }}
        .clock-time {{
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            font-variant-numeric: tabular-nums;
            color: #F8FAFC;
            line-height: 1.1;
        }}
        .clock-sub {{
            font-size: 0.85rem;
            color: rgba(241, 245, 249, 0.78);
            margin-top: 3px;
        }}

        .top-right-controls {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .photo-indicator {{
            background: rgba(15, 23, 42, 0.44);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 999px;
            padding: 7px 14px;
            font-size: 0.8rem;
            font-weight: 500;
            color: rgba(241, 245, 249, 0.85);
            font-variant-numeric: tabular-nums;
        }}
        .lock-btn {{
            width: 40px;
            height: 40px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.46);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.16);
            color: rgba(248, 250, 252, 0.82);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.18s ease;
        }}
        .lock-btn:hover {{
            background: rgba(15, 23, 42, 0.78);
            color: #FFFFFF;
            border-color: rgba(103, 232, 249, 0.55);
            transform: scale(1.04);
        }}

        /* Dock Inferior Minimalista */
        .scrim-bottom {{
            position: absolute;
            bottom: 0; left: 0; right: 0;
            padding: 48px 28px 24px 28px;
            background: linear-gradient(to top, rgba(10, 15, 22, 0.88) 28%, rgba(10, 15, 22, 0.48) 72%, rgba(10, 15, 22, 0) 100%);
            z-index: 4;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}
        .bottom-inner {{
            width: 100%;
            max-width: 780px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 11px;
        }}
        .photo-caption {{
            font-size: 0.92rem;
            font-weight: 500;
            letter-spacing: 0.01em;
            color: rgba(226, 232, 240, 0.88);
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.75);
            text-align: center;
        }}
        .reply-card {{
            width: 100%;
            background: rgba(15, 23, 42, 0.68);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 18px;
            padding: 16px 22px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
        }}
        .reply-label {{
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #67E8F9;
            margin-bottom: 5px;
        }}
        .reply-text {{
            font-size: 1.2rem;
            line-height: 1.5;
            color: #F8FAFC;
            font-weight: 400;
        }}
        .learned-chip {{
            display: none;
            align-items: center;
            gap: 7px;
            background: rgba(16, 185, 129, 0.20);
            border: 1px solid rgba(110, 231, 183, 0.35);
            border-radius: 999px;
            padding: 5px 14px;
            font-size: 0.82rem;
            color: #A7F3D0;
            max-width: 100%;
        }}
        .ptt-pill {{
            display: inline-flex;
            align-items: center;
            gap: 11px;
            background: {primary_bg};
            color: {primary_fg};
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            padding: 12px 24px;
            font-size: 0.98rem;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.34);
            transition: transform 0.14s ease, box-shadow 0.14s ease;
            touch-action: none;
        }}
        .ptt-pill:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.42);
        }}
        .ptt-pill:active {{
            transform: scale(0.98);
        }}
        .keycap {{
            background: rgba(255, 255, 255, 0.22);
            color: {primary_fg};
            padding: 3px 10px;
            border-radius: 7px;
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 0.06em;
        }}

        /* OVERLAY: AURA DE RESPIRACIÓN EMOCIONAL */
        .overlay-listening, .overlay-processing {{
            position: absolute;
            inset: 0;
            z-index: 20;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 32px;
            background: radial-gradient(circle, rgba(14, 74, 92, 0.94) 0%, rgba(15, 20, 25, 0.97) 100%);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }}
        .overlay-listening.visible, .overlay-processing.visible {{
            display: flex;
        }}
        @keyframes breatheAura {{
            0% {{
                transform: scale(0.90);
                box-shadow: 0 0 0 0 rgba(34, 184, 207, 0.50), 0 0 42px 12px rgba(14, 116, 144, 0.28);
            }}
            50% {{
                transform: scale(1.08);
                box-shadow: 0 0 0 38px rgba(34, 184, 207, 0.10), 0 0 76px 28px rgba(245, 158, 11, 0.24);
            }}
            100% {{
                transform: scale(0.90);
                box-shadow: 0 0 0 0 rgba(34, 184, 207, 0.50), 0 0 42px 12px rgba(14, 116, 144, 0.28);
            }}
        }}
        .aura-orb {{
            width: 164px;
            height: 164px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 35%, #67E8F9, #0E7490 70%, #083344 100%);
            animation: breatheAura 4.0s ease-in-out infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #082026;
            margin-bottom: 26px;
        }}
        .aura-title {{
            font-size: 1.95rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #F8FAFC;
            margin-bottom: 8px;
        }}
        .aura-sub {{
            font-size: 1.1rem;
            color: #CBD5E1;
            max-width: 560px;
            line-height: 1.5;
        }}
        .aura-timer {{
            margin-top: 16px;
            font-size: 1.02rem;
            color: #67E8F9;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }}
        #live-speech-preview {{
            margin-top: 16px;
            font-size: 1.12rem;
            color: #F1F5F9;
            max-width: 640px;
            min-height: 28px;
            font-style: italic;
            opacity: 0.92;
        }}
    </style>
    </head>
    <body>
        <div class="stage" id="mv-stage" tabindex="0">
            <img id="slide-a" class="slide-img active" alt="Recuerdo familiar A" />
            <img id="slide-b" class="slide-img" alt="Recuerdo familiar B" />

            <div class="scrim-top">
                <div class="clock-pill">
                    <div class="clock-time" id="mv-clock">--:--</div>
                    <div class="clock-sub"><span id="mv-day"></span> · Compañero de <span id="mv-patient"></span></div>
                </div>
                <div class="top-right-controls">
                    <div class="photo-indicator" id="mv-album-count">1 / 10</div>
                    <button id="mv-lock-btn" class="lock-btn" title="Acceso Familiar (PIN)" aria-label="Desbloquear Panel Familiar">
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    </button>
                </div>
            </div>

            <div class="scrim-bottom">
                <div class="bottom-inner">
                    <div class="photo-caption" id="mv-caption"></div>
                    <div class="reply-card">
                        <div class="reply-label">MemoriaViva</div>
                        <div class="reply-text" id="mv-reply"></div>
                    </div>
                    <div class="learned-chip" id="mv-learned"></div>
                    <button type="button" class="ptt-pill" id="mv-ptt-btn">
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>
                        </svg>
                        <span>Mantén presionado aquí o</span>
                        <span class="keycap">ESPACIO</span>
                        <span>para hablar</span>
                    </button>
                </div>
            </div>

            <div class="overlay-listening" id="overlay-listen">
                <div class="aura-orb">
                    <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>
                    </svg>
                </div>
                <div class="aura-title" id="listen-title">Te escucho con toda calma...</div>
                <div class="aura-sub">Tómate tu tiempo. Suelta el botón o la tecla <b>ESPACIO</b> cuando termines.</div>
                <div class="aura-timer" id="listen-timer">Escuchando · 0.0 s</div>
                <div id="live-speech-preview"></div>
            </div>

            <div class="overlay-processing" id="overlay-proc">
                <div class="aura-orb" style="animation:none; width:124px; height:124px;">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                </div>
                <div class="aura-title">Preparando tu respuesta...</div>
                <div class="aura-sub">Un momento, estoy guardando este recuerdo con cuidado.</div>
            </div>
        </div>

        <audio id="mv-audio-player" style="display:none;"></audio>

        <script>
            const PHOTOS = {photos_json};
            const ROTATION_MS = {rotation_ms};
            const PATIENT_NAME = {patient_json};
            const LAST_REPLY = {reply_json};
            const LEARNED_BADGE = {learned_json};
            const AUDIO_DATA_URI = {audio_json};
            const PTT_PORT = {ptt_port};

            function getParentOrigin() {{
                try {{
                    if (window.parent && window.parent.location && window.parent.location.origin && window.parent.location.origin !== "null") {{
                        return window.parent.location.origin;
                    }}
                }} catch (e) {{}}
                return window.location.origin || "http://127.0.0.1:8501";
            }}

            function getParentHostname() {{
                try {{
                    if (window.parent && window.parent.location && window.parent.location.hostname) {{
                        return window.parent.location.hostname;
                    }}
                }} catch (e) {{}}
                return window.location.hostname || "127.0.0.1";
            }}

            async function pttFetch(path, options) {{
                const origin = getParentOrigin();
                const isHttps = origin.startsWith("https://");
                try {{
                    const res = await fetch(origin + path, options);
                    if (res.ok) return res;
                }} catch (e) {{}}
                if (!isHttps) {{
                    const directUrl = "http://" + getParentHostname() + ":" + PTT_PORT + path;
                    return fetch(directUrl, options);
                }}
                throw new Error("PTT endpoint unreachable over HTTPS");
            }}

            document.getElementById("mv-patient").textContent = PATIENT_NAME;
            document.getElementById("listen-title").textContent = "Te escucho con toda calma, " + PATIENT_NAME + "...";
            document.getElementById("mv-reply").textContent = "“" + LAST_REPLY + "”";

            const learnedEl = document.getElementById("mv-learned");
            if (LEARNED_BADGE && LEARNED_BADGE.length > 0) {{
                learnedEl.textContent = LEARNED_BADGE;
                learnedEl.style.display = "inline-flex";
            }}

            // Reloj y día de la semana
            const DAYS_ES = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
            function updateClock() {{
                const now = new Date();
                const hh = String(now.getHours()).padStart(2, '0');
                const mm = String(now.getMinutes()).padStart(2, '0');
                document.getElementById("mv-clock").textContent = hh + ":" + mm;
                document.getElementById("mv-day").textContent = DAYS_ES[now.getDay()];
            }}
            updateClock();
            setInterval(updateClock, 10000);

            // Audio neural automático
            if (AUDIO_DATA_URI && AUDIO_DATA_URI.length > 20) {{
                const audioEl = document.getElementById("mv-audio-player");
                audioEl.src = AUDIO_DATA_URI;
                audioEl.play().catch(() => {{}});
            }}

            // Carrusel de fotos con crossfade suave
            let currentIdx = 0;
            let showingA = true;
            const imgA = document.getElementById("slide-a");
            const imgB = document.getElementById("slide-b");
            const capEl = document.getElementById("mv-caption");
            const countEl = document.getElementById("mv-album-count");

            function showPhoto(idx) {{
                if (!PHOTOS.length) return;
                const safeIdx = idx % PHOTOS.length;
                const item = PHOTOS[safeIdx];
                capEl.textContent = item.caption || "";
                countEl.textContent = (safeIdx + 1) + " / " + PHOTOS.length;
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
                countEl.textContent = "1 / " + PHOTOS.length;
                setInterval(() => {{
                    currentIdx = (currentIdx + 1) % PHOTOS.length;
                    showPhoto(currentIdx);
                }}, ROTATION_MS);
            }}

            // Helper para disparar botones ocultos de Streamlit en el documento padre
            function clickParentHiddenButton(matchText) {{
                try {{
                    const parentDoc = window.parent.document;
                    const btns = Array.from(parentDoc.querySelectorAll("button"));
                    const targetBtn = btns.find(b => b.innerText && b.innerText.includes(matchText));
                    if (targetBtn) {{
                        targetBtn.click();
                    }}
                }} catch (err) {{
                    console.error("Error comunicando con Streamlit:", err);
                }}
            }}

            // Botón discreto de candado -> abre modal PIN en Streamlit
            document.getElementById("mv-lock-btn").addEventListener("click", (ev) => {{
                ev.preventDefault();
                ev.stopPropagation();
                clickParentHiddenButton("_abrir_modal_pin");
            }});

            // Push-to-Talk dual (Tecla ESPACIO + Botón táctil/clic) + Captura MediaRecorder en dispositivo
            let isListening = false;
            let listenStartMs = 0;
            let timerInterval = null;
            let recognition = null;
            let mediaRecorder = null;
            let mediaStream = null;
            let audioChunks = [];
            let finalTranscriptParts = [];
            let interimTranscript = "";
            let wordTimestamps = [];
            let lastSegmentEndSec = 0.0;

            const listenOverlay = document.getElementById("overlay-listen");
            const procOverlay = document.getElementById("overlay-proc");
            const timerEl = document.getElementById("listen-timer");
            const liveSpeechEl = document.getElementById("live-speech-preview");

            async function startDeviceMediaRecorder() {{
                audioChunks = [];
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === "undefined") {{
                    return;
                }}
                try {{
                    mediaStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                    if (!isListening) {{
                        mediaStream.getTracks().forEach(t => t.stop());
                        mediaStream = null;
                        return;
                    }}
                    const mimeCandidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
                    const chosenMime = mimeCandidates.find(m => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m));
                    mediaRecorder = chosenMime ? new MediaRecorder(mediaStream, {{ mimeType: chosenMime }}) : new MediaRecorder(mediaStream);
                    mediaRecorder.ondataavailable = (ev) => {{
                        if (ev.data && ev.data.size > 0) audioChunks.push(ev.data);
                    }};
                    mediaRecorder.start(250);
                }} catch (err) {{
                    mediaRecorder = null;
                    mediaStream = null;
                }}
            }}

            function stopDeviceMediaRecorderToBase64() {{
                return new Promise((resolve) => {{
                    const cleanupTracks = () => {{
                        if (mediaStream) {{
                            try {{ mediaStream.getTracks().forEach(t => t.stop()); }} catch (e) {{}}
                            mediaStream = null;
                        }}
                    }};
                    if (!mediaRecorder || mediaRecorder.state === "inactive") {{
                        cleanupTracks();
                        resolve(null);
                        return;
                    }}
                    const recorderRef = mediaRecorder;
                    mediaRecorder = null;
                    recorderRef.onstop = () => {{
                        cleanupTracks();
                        if (!audioChunks.length) {{
                            resolve(null);
                            return;
                        }}
                        const blob = new Blob(audioChunks, {{ type: recorderRef.mimeType || "audio/webm" }});
                        audioChunks = [];
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(typeof reader.result === "string" ? reader.result : null);
                        reader.onerror = () => resolve(null);
                        reader.readAsDataURL(blob);
                    }};
                    try {{
                        recorderRef.stop();
                    }} catch (e) {{
                        cleanupTracks();
                        resolve(null);
                    }}
                }});
            }}

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
                            liveSpeechEl.textContent = "“" + preview + "”";
                        }}
                    }};
                    recognition.onerror = () => {{}};
                    recognition.start();
                }} catch (err) {{
                    recognition = null;
                }}
            }}

            function startListening() {{
                if (isListening) return;
                isListening = true;

                const audioEl = document.getElementById("mv-audio-player");
                if (audioEl) {{ try {{ audioEl.pause(); }} catch (e) {{}} }}

                listenStartMs = Date.now();
                timerEl.textContent = "Escuchando · 0.0 s";
                listenOverlay.classList.add("visible");
                if (timerInterval) clearInterval(timerInterval);
                timerInterval = setInterval(() => {{
                    const secs = ((Date.now() - listenStartMs) / 1000).toFixed(1);
                    timerEl.textContent = "Escuchando · " + secs + " s";
                }}, 100);

                pttFetch("/ptt/start", {{ method: "POST" }}).catch(() => {{}});
                startBrowserSpeechRecognition();
                startDeviceMediaRecorder();
            }}

            async function stopListening() {{
                if (!isListening) return;
                isListening = false;
                if (timerInterval) clearInterval(timerInterval);
                listenOverlay.classList.remove("visible");
                procOverlay.classList.add("visible");

                if (recognition) {{
                    try {{ recognition.stop(); }} catch (e) {{}}
                }}

                const audioBase64 = await stopDeviceMediaRecorderToBase64();

                setTimeout(() => {{
                    const combinedTranscript = (finalTranscriptParts.join(" ") + " " + interimTranscript).trim();
                    const payload = {{
                        browser_transcript: combinedTranscript,
                        browser_word_timestamps: wordTimestamps
                    }};
                    if (audioBase64) {{
                        payload.audio_base64 = audioBase64;
                    }}
                    pttFetch("/ptt/stop", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify(payload)
                    }})
                        .then(() => clickParentHiddenButton("_procesar_turno_espacio"))
                        .catch(() => clickParentHiddenButton("_procesar_turno_espacio"));
                }}, 180);
            }}

            function isTypingInField(ev) {{
                let activeTag = "";
                try {{
                    activeTag = (window.parent.document.activeElement?.tagName || "").toUpperCase();
                }} catch (e) {{}}
                const targetTag = (ev.target && ev.target.tagName) ? ev.target.tagName.toUpperCase() : "";
                return ["INPUT", "TEXTAREA", "SELECT"].includes(activeTag) || ["INPUT", "TEXTAREA", "SELECT"].includes(targetTag);
            }}

            // Botón táctil / clic mantener presionado
            const pttBtn = document.getElementById("mv-ptt-btn");
            pttBtn.addEventListener("pointerdown", (ev) => {{
                ev.preventDefault();
                try {{ pttBtn.setPointerCapture(ev.pointerId); }} catch (e) {{}}
                startListening();
            }});
            pttBtn.addEventListener("pointerup", (ev) => {{
                ev.preventDefault();
                stopListening();
            }});
            pttBtn.addEventListener("pointercancel", () => stopListening());

            function handleKeyDown(ev) {{
                if (isTypingInField(ev)) return;
                // Atajo discreto de teclado para abrir modal de PIN: Ctrl+Shift+L
                if (ev.ctrlKey && ev.shiftKey && (ev.key === "L" || ev.key === "l")) {{
                    ev.preventDefault();
                    clickParentHiddenButton("_abrir_modal_pin");
                    return;
                }}
                if (ev.code === "Space" || ev.key === " ") {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    if (ev.repeat || isListening) return;
                    startListening();
                }}
            }}

            function handleKeyUp(ev) {{
                if (!isListening) return;
                if (ev.code === "Space" || ev.key === " ") {{
                    ev.preventDefault();
                    ev.stopPropagation();
                    stopListening();
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

            document.getElementById("mv-stage").focus();
        </script>
    </body>
    </html>
    """
