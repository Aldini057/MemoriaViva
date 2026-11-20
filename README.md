# MemoriaViva RISE

**Plataforma Conversacional de Terapia de Reminiscencia y Detección Temprana No Invasiva de Deterioro Cognitivo Leve para Adultos Mayores**  
*Global RISE AI Hackathon 2026 — University of Notre Dame (Lucy Family Institute for Data & Society), Universidad de Guadalajara*

---

## 1. Visión y Propósito

**MemoriaViva RISE** combate el aislamiento social del adulto mayor y supera la *"paradoja de la evaluación clínica"* (el estrés agudo o síndrome de bata blanca que provocan pruebas como MoCA o Folstein en un consultorio).

A través de charlas cálidas por voz basadas en **Terapia de Reminiscencia** (música de juventud, oficios históricos, viajes familiares) y **Terapia de Validación de Naomi Feil**, el sistema acompaña al adulto mayor mientras evalúa pasivamente en segundo plano **3 biomarcadores neuropsicológicos del habla**:

1. **Riqueza Léxica Invariante a la Longitud (`MATTR` — Ventana móvil de 20 palabras de contenido):** *Covington & McFall (2010); Fraser et al. (2016)*.
2. **Pausas Anómicas Intra-Oracionales (`> 2.0 segundos`):** *Pistono et al. (2016); Toth et al. (2018)*.
3. **Bucle Semántico / Repetición Intra-Sesión (`TF-IDF Cosine >= 0.72`):** *Guinn & Habash (2012)*.

---

## 2. Alineación con los 4 Pilares del Marco RISE

| Pilar RISE | Implementación Técnica Verificable en MemoriaViva RISE |
| :--- | :--- |
| **R — Responsible** *(Responsable)* | **Apoyo Clínico No Diagnóstico:** Evalúa al paciente contra su propia línea base histórica de 21 días (*Z-Score Personal Baseline*) y genera un reporte PDF auditable para el geriatra sin usar etiquetas patologizantes. |
| **I — Inclusive** *(Inclusivo)* | **Diseño Fonocéntrico y Descanso Visual:** Espera adaptativa de fin de turno de **3.8s** (`Extended VAD`), síntesis de voz neural a **-15% de velocidad y -5Hz** para presbiacusia, **Aura de Respiración Emocional**, **Álbum de Recuerdos Dinámico** y conmutador **☀️ Modo Día / 🌙 Modo Noche Cálido** para fotofobia o cataratas. |
| **S — Safe** *(Seguro y Privado)* | **Zero-Raw-Cloud Audio:** Los fragmentos `.wav` se destruyen inmediatamente tras su procesamiento (`os.remove()`). Ante desorientación aguda, activa contención emocional de Feil y dispara una **Alerta Roja S.O.S. (Nivel 3)** en Telegram. |
| **E — Empowering** *(Empoderador)* | **Puente Intergeneracional:** Envía diariamente al celular del familiar (`@Memoria_viva_bot`) el recuerdo evocado y una pregunta sugerida para fortalecer la plática durante la cena familiar. |

---

## 3. Estructura del Proyecto

```text
Memoria-Viva/
├── app.py                        # Interfaz principal en Streamlit (Modo Compañero + Tablero + Registro)
├── config.py                     # Umbrales clínicos (VAD 3.8s, Anomia 2.0s, MATTR 20, TF-IDF 0.72)
├── biomarkers.py                 # Motor matemático MATTR, Pausas Anómicas, TF-IDF y Z-Score 21 días
├── audio_engine.py               # Captura VAD 3.8s, análisis acústico RMS, Edge-TTS (-15%) y Zero-Raw-Leakage
├── llm_companion.py              # Prompts gerontológicos (Reminiscencia, Validación de Feil y RAG-Lite JSON)
├── telegram_notifier.py          # Conector de 3 niveles con @Memoria_viva_bot y generador QR
├── pdf_report.py                 # Generador de Reporte Clínico en PDF para el médico geriatra
├── iniciar_memoriaviva.bat       # Lanzador automático de 1 clic para Windows
├── empacar_ejecutable.py         # Script para compilar ejecutable portátil (.exe) con PyInstaller
├── Dockerfile                    # Imagen de contenedor lista para despliegue
├── docker-compose.yml            # Orquestación Docker en 1 comando
├── requirements.txt              # Dependencias del sistema
├── data/
│   ├── profiles/
│   │   └── don_manuel_simulacion.json  # Perfil biográfico vivo (se auto-actualiza en cada charla)
│   ├── history_21_days.json            # Serie longitudinal de 21 días para gráficas Plotly
│   └── demo_audios/                    # 3 archivos .wav precalibrados para modo Fail-Safe
└── test_e2e_theatrical_demo.py   # Suite de validación extremo a extremo de los 3 actos del pitch
```

---

## 4. Formas de Ejecución

### Opción A: Inicio Rápido en 1 Clic (Windows)
Haz doble clic sobre **`iniciar_memoriaviva.bat`** o ejecuta en terminal:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
La aplicación se abrirá en **`http://localhost:8501`**.

### Opción B: Despliegue con Docker
```bash
docker compose up --build
```

### Opción C: Generar Ejecutable `.exe` Independiente (Windows)
```powershell
.\.venv\Scripts\python.exe empacar_ejecutable.py
```

---

## 5. Ejecución de Pruebas Automatizadas (Fases 1 a 5)

```powershell
.\.venv\Scripts\python.exe -X utf8 test_biomarkers.py           # Fase 1: Matemática y Biomarcadores
.\.venv\Scripts\python.exe -X utf8 test_audio_engine.py         # Fase 2: Audio, Onda Acústica y Edge-TTS
.\.venv\Scripts\python.exe -X utf8 test_phase3.py               # Fase 3: LLM Gerontológico y Telegram Bot
.\.venv\Scripts\python.exe -X utf8 test_phase4.py               # Fase 4: Interfaz Streamlit y Reporte PDF
.\.venv\Scripts\python.exe -X utf8 test_e2e_theatrical_demo.py  # Fase 5: Simulacro E2E de los 3 Escenarios
```
