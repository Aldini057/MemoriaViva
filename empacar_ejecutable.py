"""
MemoriaViva RISE - Empaquetador de Ejecutable Portátil (.exe) para Windows
Global RISE AI Hackathon 2026

Compila un lanzador autónomo (`MemoriaViva_RISE.exe`) mediante PyInstaller para
arrancar MemoriaViva RISE con doble clic o automáticamente al encender Windows.

Uso:
    .venv\\Scripts\\python.exe empacar_ejecutable.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LAUNCHER_SCRIPT = BASE_DIR / "launcher_desktop.py"


LAUNCHER_CODE = '''"""Lanzador de escritorio y modo kiosco para MemoriaViva RISE."""
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def _is_port_open(port: int = 8501) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _open_app_window(url: str) -> None:
    """Abre la aplicación en ventana limpia tipo escritorio (Edge/Chrome --app) si está disponible."""
    edge_candidates = [
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    ]
    chrome_candidates = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    for browser_exe in edge_candidates + chrome_candidates:
        if os.path.exists(browser_exe):
            try:
                subprocess.Popen([browser_exe, f"--app={url}", "--start-maximized"])
                return
            except Exception:
                pass
    webbrowser.open(url)


def main() -> None:
    base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    os.chdir(base_dir)
    url = "http://localhost:8501"

    if _is_port_open(8501):
        _open_app_window(url)
        return

    venv_streamlit = base_dir / ".venv" / "Scripts" / "streamlit.exe"
    if venv_streamlit.exists():
        cmd = [str(venv_streamlit), "run", "app.py", "--server.port=8501", "--server.headless=true"]
    else:
        st_bin = shutil.which("streamlit") or "streamlit"
        cmd = [st_bin, "run", "app.py", "--server.port=8501", "--server.headless=true"]

    print("===================================================")
    print("  Iniciando MemoriaViva RISE en", url)
    print("===================================================")
    creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.Popen(cmd, cwd=str(base_dir), creationflags=creation_flags)

    for _ in range(30):
        if _is_port_open(8501):
            break
        time.sleep(0.5)

    _open_app_window(url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
'''


def build_executable() -> None:
    LAUNCHER_SCRIPT.write_text(LAUNCHER_CODE, encoding="utf-8")
    print("[1/2] Verificando PyInstaller en el entorno virtual...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    print("[2/2] Generando ejecutable MemoriaViva_RISE.exe...")
    build_tmp = BASE_DIR / "_pyinstaller_build"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--noconsole",
            "--name",
            "MemoriaViva_RISE",
            "--distpath",
            str(BASE_DIR),
            "--workpath",
            str(build_tmp),
            "--specpath",
            str(build_tmp),
            str(LAUNCHER_SCRIPT),
        ],
        check=True,
    )
    if build_tmp.exists():
        shutil.rmtree(build_tmp, ignore_errors=True)
    if LAUNCHER_SCRIPT.exists():
        LAUNCHER_SCRIPT.unlink()

    print("\n[OK] Ejecutable creado con éxito en:", BASE_DIR / "MemoriaViva_RISE.exe")


if __name__ == "__main__":
    build_executable()
