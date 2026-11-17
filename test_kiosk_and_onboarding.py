"""
Pruebas Exhaustivas — Paso 6: Registro Único, Modo Kiosco, 10+ Fotos, PTT ESPACIO, Autostart y .exe
Global RISE AI Hackathon 2026
"""

from __future__ import annotations

import json
import py_compile
import time
from pathlib import Path

import requests

import audio_engine
import config
import system_integration


def run_kiosk_and_onboarding_tests() -> None:
    print("=" * 76)
    print("  MEMORIAVIVA RISE — VALIDACIÓN KIOSCO, ONBOARDING, 10+ FOTOS Y PTT")
    print("=" * 76)

    # Respaldar estado previo de account_config.json y autostart si existían
    prev_account_exists = config.ACCOUNT_CONFIG_FILE.exists()
    prev_account_raw = (
        config.ACCOUNT_CONFIG_FILE.read_text(encoding="utf-8") if prev_account_exists else None
    )
    prev_autostart = system_integration.is_windows_autostart_enabled()

    try:
        # ----------------------------------------------------------------------
        # TEST 1: Mínimo 10 Fotografías para Protector de Pantalla
        # ----------------------------------------------------------------------
        photos = system_integration.ensure_minimum_10_sample_photos("don_manuel", "Don Manuel")
        count = system_integration.count_profile_photos("don_manuel")
        uris = system_integration.get_photos_as_data_uris("don_manuel")

        print("\n[TEST 1] Álbum del Protector de Pantalla (Mínimo 10 Fotos):")
        print(f"  • Fotos en data/photos/don_manuel/: {count}")
        print(f"  • Data URIs listos para rotar:      {len(uris)}")
        print(f"  • Primera postal:                   {uris[0]['caption']}")
        assert count >= config.MIN_SCREENSAVER_PHOTOS, "Debe haber al menos 10 fotos"
        assert len(uris) >= config.MIN_SCREENSAVER_PHOTOS
        assert uris[0]["data_uri"].startswith("data:image/jpeg;base64,")

        # ----------------------------------------------------------------------
        # TEST 2: Registro Único, Hash y Verificación de PIN de Bloqueo
        # ----------------------------------------------------------------------
        pin_hash = system_integration.hash_pin("2026")
        test_cfg = {
            "is_registered": True,
            "kiosk_locked_for_elder": True,
            "caregiver_name": "Laura",
            "caregiver_user": "laura.cuidadora",
            "pin_hash": pin_hash,
            "active_profile_path": str(config.DEFAULT_PROFILE_FILE),
            "autostart_enabled": False,
            "rotation_interval_sec": 6,
        }
        system_integration.save_account_config(test_cfg)
        loaded_cfg = system_integration.load_account_config()

        pin_ok = system_integration.verify_pin("2026", loaded_cfg["pin_hash"])
        pin_bad = system_integration.verify_pin("0000", loaded_cfg["pin_hash"])
        print("\n[TEST 2] Cuenta Única y Verificación de PIN Kiosco:")
        print(f"  • Cuenta guardada (is_registered): {loaded_cfg['is_registered']}")
        print(f"  • Bloqueo al encender:             {loaded_cfg['kiosk_locked_for_elder']}")
        print(f"  • PIN correcto ('2026'):           {pin_ok}")
        print(f"  • PIN incorrecto ('0000'):         {pin_bad}")
        assert loaded_cfg["is_registered"] is True
        assert loaded_cfg["kiosk_locked_for_elder"] is True
        assert pin_ok is True and pin_bad is False

        # ----------------------------------------------------------------------
        # TEST 3: Micro-Servidor Push-to-Talk (Tecla ESPACIO: /ptt/start -> /ptt/stop)
        # ----------------------------------------------------------------------
        ptt_port = audio_engine.start_ptt_background_server()
        base_url = f"http://127.0.0.1:{ptt_port}"

        r_start = requests.post(f"{base_url}/ptt/start", timeout=3)
        assert r_start.status_code == 200 and r_start.json().get("status") == "listening"

        r_stat = requests.get(f"{base_url}/ptt/status", timeout=3)
        assert r_stat.status_code == 200 and r_stat.json().get("is_recording") is True

        time.sleep(0.2)
        r_stop = requests.post(f"{base_url}/ptt/stop", timeout=3)
        assert r_stop.status_code == 200 and r_stop.json().get("status") == "stopped"

        consumed = audio_engine.consume_ptt_recorded_audio()
        r_after = requests.get(f"{base_url}/ptt/status", timeout=3)
        assert r_after.json().get("has_audio") is False

        print("\n[TEST 3] Servidor Push-to-Talk Controlado por ESPACIO:")
        print(f"  • Puerto HTTP activo:             {ptt_port}")
        print(f"  • Ciclo /ptt/start -> /ptt/stop:  OK")
        print(f"  • Resultado consumo RAM:          mode={consumed['mode']}")
        print(f"  • Buffer limpiado tras consumir:  {not r_after.json()['has_audio']}")

        # ----------------------------------------------------------------------
        # TEST 4: Creación y Remoción Limpia de Inicio Automático con Windows
        # ----------------------------------------------------------------------
        res_on = system_integration.set_windows_autostart(True)
        cmd_path = system_integration.get_windows_startup_cmd_path()
        enabled_check = system_integration.is_windows_autostart_enabled() and cmd_path.exists()

        res_off = system_integration.set_windows_autostart(False)
        disabled_check = (not system_integration.is_windows_autostart_enabled()) and (not cmd_path.exists())

        print("\n[TEST 4] Arranque Automático con Windows (Startup + HKCU\\Run):")
        print(f"  • Activado correctamente:         {enabled_check} ({res_on['startup_cmd']})")
        print(f"  • Remoción limpia:                {disabled_check}")
        assert enabled_check is True
        assert disabled_check is True

        # ----------------------------------------------------------------------
        # TEST 5: Compilación de app.py y Existencia de MemoriaViva_RISE.exe
        # ----------------------------------------------------------------------
        compiled = py_compile.compile(str(config.BASE_DIR / "app.py"), doraise=True)
        exe_path = config.BASE_DIR / "MemoriaViva_RISE.exe"
        exe_exists = exe_path.exists() and exe_path.stat().st_size > 1_000_000

        print("\n[TEST 5] Integridad de app.py y Ejecutable Windows (.exe):")
        print(f"  • Bytecode app.py:                {compiled}")
        print(f"  • Ejecutable MemoriaViva_RISE.exe:{exe_exists} ({exe_path.stat().st_size // (1024*1024) if exe_exists else 0} MB)")
        assert exe_exists, "El archivo MemoriaViva_RISE.exe debe existir y ser válido"

        print("\n" + "=" * 76)
        print("  [OK] TODAS LAS PRUEBAS DEL MODO KIOSCO, ONBOARDING Y .EXE PASARON")
        print("=" * 76)
    finally:
        # Restaurar estado original para no dejar cuenta ficticia de test si no existía
        system_integration.set_windows_autostart(prev_autostart)
        if prev_account_exists and prev_account_raw is not None:
            config.ACCOUNT_CONFIG_FILE.write_text(prev_account_raw, encoding="utf-8")
        elif config.ACCOUNT_CONFIG_FILE.exists():
            config.ACCOUNT_CONFIG_FILE.unlink()


if __name__ == "__main__":
    run_kiosk_and_onboarding_tests()
