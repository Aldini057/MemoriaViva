@echo off
title MemoriaViva RISE - Lanzador
echo ===================================================
echo     Iniciando MemoriaViva RISE (Plataforma Geriátrica)
echo ===================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creando entorno virtual .venv...
    python -m venv .venv
    echo [INFO] Instalando dependencias...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo [INFO] Abriendo MemoriaViva RISE en tu navegador...
streamlit run app.py
pause
