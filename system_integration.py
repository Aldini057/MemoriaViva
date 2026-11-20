"""
MemoriaViva RISE - Integración de Sistema, Registro Único, Fotos y Arranque Windows
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Módulo encargado de:
1. Gestión de cuenta única del cuidador y bloqueo de pantalla en modo kiosco (`account_config.json`).
2. Gestión, redimensionamiento y generación de mínimo 10 fotografías para el protector de pantalla.
3. Configuración de arranque automático al encender Windows (carpeta Startup + Registro HKCU\\Run).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

import config

if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore

STARTUP_CMD_NAME = "MemoriaViva_RISE_Autostart.cmd"
REG_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "MemoriaVivaRISE"

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

SAMPLE_POSTCARD_TEMPLATES: list[dict[str, Any]] = [
    {
        "filename": "foto_01_locomotora.jpg",
        "caption": "1. Locomotora en la Sierra de Manzanillo",
        "subtitle": "Recuerdos de los años en Ferrocarriles Nacionales",
        "palette": [(68, 48, 36), (178, 122, 74)],
        "motif": "train",
    },
    {
        "filename": "foto_02_vocho_azul.jpg",
        "caption": "2. El Vocho Azul Modelo 1974",
        "subtitle": "Aventuras y paseos en carretera con toda la familia",
        "palette": [(38, 66, 94), (125, 157, 134)],
        "motif": "car",
    },
    {
        "filename": "foto_03_perro_sultan.jpg",
        "caption": "3. Nuestro Perro Pastor Alemán Sultán",
        "subtitle": "Siempre fiel esperando junto a la puerta del patio",
        "palette": [(60, 76, 54), (186, 150, 96)],
        "motif": "dog",
    },
    {
        "filename": "foto_04_playa_miramar.jpg",
        "caption": "4. Vacaciones en Playa Miramar",
        "subtitle": "El mar de Manzanillo, Colima y las cabañas San Pedrito",
        "palette": [(34, 88, 108), (222, 165, 98)],
        "motif": "sea",
    },
    {
        "filename": "foto_05_tlaquepaque.jpg",
        "caption": "5. Tardes en San Pedro Tlaquepaque",
        "subtitle": "El jardín, los portales y el aire fresco de la tarde",
        "palette": [(96, 62, 46), (217, 155, 82)],
        "motif": "arch",
    },
    {
        "filename": "foto_06_boleros.jpg",
        "caption": "6. Boleros del Trío Los Panchos",
        "subtitle": "Melodías de Agustín Lara y 'Solamente una vez' en la radio",
        "palette": [(78, 44, 52), (195, 146, 98)],
        "motif": "music",
    },
    {
        "filename": "foto_07_chocolate_metate.jpg",
        "caption": "7. Chocolate de Metate en Familia",
        "subtitle": "Sobremesas cálidas con pan dulce recién salido del horno",
        "palette": [(74, 46, 30), (168, 118, 78)],
        "motif": "cup",
    },
    {
        "filename": "foto_08_domino_nietos.jpg",
        "caption": "8. Partida de Dominó con los Nietos",
        "subtitle": "Tardes de martes riendo y platicando en la mesa",
        "palette": [(48, 72, 60), (205, 178, 134)],
        "motif": "domino",
    },
    {
        "filename": "foto_09_reloj_jubilacion.jpg",
        "caption": "9. El Reloj de Jubilación Ferroviaria",
        "subtitle": "32 años de esfuerzo, orgullo y compañerismo",
        "palette": [(54, 52, 62), (198, 156, 92)],
        "motif": "clock",
    },
    {
        "filename": "foto_10_dona_carmen.jpg",
        "caption": "10. Recuerdos con Doña Carmen",
        "subtitle": "Aquel encuentro inolvidable en la plaza desde 1975",
        "palette": [(94, 56, 64), (218, 174, 138)],
        "motif": "hearts",
    },
]


# ==============================================================================
# 1. Gestión de Cuenta Única, PIN y Bloqueo en Modo Kiosco
# ==============================================================================
def hash_pin(pin: str) -> str:
    """Genera un hash SHA-256 seguro para el PIN/contraseña del cuidador."""
    clean = (pin or "").strip()
    return hashlib.sha256(f"MemoriaVivaRISE::{clean}".encode("utf-8")).hexdigest()


def verify_pin(pin: str, stored_hash: str) -> bool:
    """Verifica el PIN/contraseña ingresada por el cuidador contra el hash guardado."""
    if not stored_hash:
        return True
    return hash_pin(pin) == stored_hash


def get_default_account_config() -> dict[str, Any]:
    """Devuelve la estructura inicial por defecto de cuenta no registrada."""
    return {
        "is_registered": False,
        "kiosk_locked_for_elder": True,
        "caregiver_name": "",
        "caregiver_user": "",
        "pin_hash": "",
        "active_profile_path": str(config.DEFAULT_PROFILE_FILE),
        "autostart_enabled": False,
        "rotation_interval_sec": 6,
    }


def load_account_config() -> dict[str, Any]:
    """Carga la configuración de cuenta y bloqueo de equipo desde account_config.json."""
    default_cfg = get_default_account_config()
    if not config.ACCOUNT_CONFIG_FILE.exists():
        return default_cfg

    try:
        data = json.loads(config.ACCOUNT_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**default_cfg, **data}
    except Exception:
        pass
    return default_cfg


def save_account_config(cfg: dict[str, Any]) -> Path:
    """Guarda en disco la configuración de cuenta y bloqueo de equipo."""
    config.ACCOUNT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged = {**get_default_account_config(), **cfg}
    config.ACCOUNT_CONFIG_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config.ACCOUNT_CONFIG_FILE


# ==============================================================================
# 2. Gestión y Generación de Mínimo 10 Fotografías del Protector de Pantalla
# ==============================================================================
def get_profile_photos_dir(profile_id: str) -> Path:
    """Obtiene (y crea si no existe) el directorio de fotos de un perfil."""
    safe_id = "".join(c for c in (profile_id or "don_manuel") if c.isalnum() or c in ("_", "-")).strip() or "don_manuel"
    pdir = config.PHOTOS_DIR / safe_id
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def _load_captions_map(photos_dir: Path) -> dict[str, str]:
    cap_file = photos_dir / "captions.json"
    if cap_file.exists():
        try:
            data = json.loads(cap_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_captions_map(photos_dir: Path, captions: dict[str, str]) -> None:
    cap_file = photos_dir / "captions.json"
    cap_file.write_text(json.dumps(captions, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_photo_files(photos_dir: Path) -> list[Path]:
    if not photos_dir.exists():
        return []
    return sorted(
        [
            p
            for p in photos_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS
        ],
        key=lambda x: x.name.lower(),
    )


def count_profile_photos(profile_id: str) -> int:
    """Cuenta cuántas fotografías válidas tiene el perfil para el protector de pantalla."""
    pdir = get_profile_photos_dir(profile_id)
    return len(_list_photo_files(pdir))


def save_uploaded_photos(profile_id: str, uploaded_files: list[Any]) -> list[str]:
    """
    Guarda imágenes subidas desde Streamlit en data/photos/<profile_id>/,
    redimensionadas a un máximo de 1280x720 en formato JPEG para transición fluida.
    """
    if not uploaded_files:
        return []

    pdir = get_profile_photos_dir(profile_id)
    captions = _load_captions_map(pdir)
    saved_paths: list[str] = []

    for idx, up in enumerate(uploaded_files, start=1):
        try:
            raw_name = getattr(up, "name", f"foto_familiar_{idx}.jpg")
            stem = Path(raw_name).stem
            clean_stem = "".join(c for c in stem if c.isalnum() or c in ("_", "-", " ")).strip().replace(" ", "_")
            if not clean_stem:
                clean_stem = f"recuerdo_{idx}"

            out_name = f"user_{clean_stem}.jpg"
            out_path = pdir / out_name
            counter = 1
            while out_path.exists():
                out_name = f"user_{clean_stem}_{counter}.jpg"
                out_path = pdir / out_name
                counter += 1

            raw_bytes = up.getvalue() if hasattr(up, "getvalue") else up.read()
            img = Image.open(io.BytesIO(raw_bytes))
            img = img.convert("RGB")
            img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
            img.save(out_path, format="JPEG", quality=88, optimize=True)

            captions[out_name] = stem.replace("_", " ").replace("-", " ").title()
            saved_paths.append(str(out_path))
        except Exception:
            continue

    _save_captions_map(pdir, captions)
    return saved_paths


def delete_profile_photo(profile_id: str, filename: str) -> bool:
    """Elimina una fotografía específica del protector de pantalla."""
    pdir = get_profile_photos_dir(profile_id)
    target = pdir / Path(filename).name
    if target.exists() and target.is_file():
        target.unlink()
        captions = _load_captions_map(pdir)
        captions.pop(target.name, None)
        _save_captions_map(pdir, captions)
        return True
    return False


def _get_font(size: int, italic: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carga tipografía legible en Linux y Windows con fallback seguro."""
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
            r"C:\Windows\Fonts\georgiai.ttf",
            r"C:\Windows\Fonts\ariali.ttf",
        ]
        if italic
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            r"C:\Windows\Fonts\georgiab.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ]
    )
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _draw_motif(draw: ImageDraw.ImageDraw, motif: str, w: int, h: int) -> None:
    """Dibuja una silueta cálida ilustrada en el centro superior de la postal."""
    cx, cy = w // 2, int(h * 0.37)
    fg = (250, 240, 224)
    accent = (232, 184, 120)

    if motif == "train":
        draw.rectangle([cx - 170, cy - 35, cx + 110, cy + 55], outline=fg, width=5, fill=(75, 58, 45))
        draw.rectangle([cx + 45, cy - 80, cx + 125, cy + 55], outline=fg, width=5, fill=(88, 66, 50))
        draw.rectangle([cx - 140, cy - 90, cx - 105, cy - 35], outline=fg, width=4, fill=accent)
        for wx in (-125, -45, 35, 95):
            draw.ellipse([cx + wx - 24, cy + 40, cx + wx + 24, cy + 88], outline=accent, width=5, fill=(45, 34, 28))
        draw.line([cx - 260, cy + 92, cx + 260, cy + 92], fill=fg, width=5)
    elif motif == "car":
        draw.arc([cx - 130, cy - 75, cx + 130, cy + 65], start=180, end=360, fill=fg, width=6)
        draw.rectangle([cx - 165, cy + 5, cx + 165, cy + 55], outline=fg, width=5, fill=(66, 102, 134))
        for wx in (-105, 105):
            draw.ellipse([cx + wx - 28, cy + 34, cx + wx + 28, cy + 90], outline=accent, width=6, fill=(36, 36, 40))
    elif motif == "dog":
        draw.ellipse([cx - 75, cy - 25, cx + 75, cy + 65], outline=fg, width=5, fill=(138, 104, 68))
        draw.ellipse([cx + 35, cy - 75, cx + 110, cy - 5], outline=fg, width=5, fill=(150, 114, 74))
        draw.polygon([(cx + 50, cy - 68), (cx + 62, cy - 110), (cx + 78, cy - 65)], fill=accent)
        draw.polygon([(cx + 80, cy - 65), (cx + 96, cy - 106), (cx + 104, cy - 60)], fill=accent)
        draw.line([cx - 60, cy + 50, cx - 60, cy + 95], fill=fg, width=6)
        draw.line([cx + 50, cy + 50, cx + 50, cy + 95], fill=fg, width=6)
    elif motif == "sea":
        draw.ellipse([cx - 55, cy - 85, cx + 55, cy + 25], fill=accent)
        for offset, y_wave in enumerate([cy + 20, cy + 48, cy + 76]):
            for x_pos in range(cx - 240, cx + 240, 60):
                draw.arc([x_pos + offset * 12, y_wave - 14, x_pos + 60 + offset * 12, y_wave + 14], 0, 180, fill=fg, width=5)
    elif motif == "arch":
        for ax in (-130, 0, 130):
            draw.arc([cx + ax - 55, cy - 75, cx + ax + 55, cy + 35], 180, 360, fill=fg, width=5)
            draw.line([cx + ax - 55, cy - 20, cx + ax - 55, cy + 80], fill=fg, width=5)
            draw.line([cx + ax + 55, cy - 20, cx + ax + 55, cy + 80], fill=fg, width=5)
        draw.line([cx - 220, cy + 80, cx + 220, cy + 80], fill=accent, width=5)
    elif motif == "music":
        draw.ellipse([cx - 95, cy + 15, cx - 35, cy + 65], fill=accent, outline=fg, width=4)
        draw.ellipse([cx + 25, cy - 5, cx + 85, cy + 45], fill=accent, outline=fg, width=4)
        draw.line([cx - 38, cy + 35, cx - 38, cy - 85], fill=fg, width=6)
        draw.line([cx + 82, cy + 15, cx + 82, cy - 100], fill=fg, width=6)
        draw.line([cx - 38, cy - 85, cx + 82, cy - 100], fill=fg, width=9)
    elif motif == "cup":
        draw.rounded_rectangle([cx - 75, cy - 45, cx + 75, cy + 65], radius=24, outline=fg, width=5, fill=(104, 68, 46))
        draw.arc([cx + 60, cy - 25, cx + 115, cy + 35], 270, 90, fill=fg, width=6)
        draw.line([cx - 115, cy + 75, cx + 115, cy + 75], fill=accent, width=6)
        for sx in (-35, 0, 35):
            draw.arc([cx + sx - 12, cy - 95, cx + sx + 12, cy - 55], 90, 270, fill=accent, width=4)
    elif motif == "domino":
        for dx, dy in [(-95, -55), (15, -35)]:
            draw.rounded_rectangle([cx + dx, cy + dy, cx + dx + 80, cy + dy + 135], radius=12, fill=fg, outline=accent, width=4)
            draw.line([cx + dx + 8, cy + dy + 67, cx + dx + 72, cy + dy + 67], fill=(60, 50, 44), width=3)
            draw.ellipse([cx + dx + 32, cy + dy + 25, cx + dx + 48, cy + dy + 41], fill=(50, 45, 40))
            draw.ellipse([cx + dx + 18, cy + dy + 88, cx + dx + 34, cy + dy + 104], fill=(50, 45, 40))
            draw.ellipse([cx + dx + 46, cy + dy + 102, cx + dx + 62, cy + dy + 118], fill=(50, 45, 40))
    elif motif == "clock":
        draw.ellipse([cx - 85, cy - 85, cx + 85, cy + 85], outline=accent, width=8, fill=(58, 52, 48))
        draw.ellipse([cx - 72, cy - 72, cx + 72, cy + 72], outline=fg, width=3)
        draw.line([cx, cy, cx, cy - 48], fill=fg, width=6)
        draw.line([cx, cy, cx + 38, cy + 18], fill=accent, width=5)
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=fg)
    else:  # hearts
        for ox, oy, col in [(-38, 0, fg), (38, -14, accent)]:
            draw.ellipse([cx + ox - 36, cy + oy - 36, cx + ox, cy + oy], fill=col)
            draw.ellipse([cx + ox, cy + oy - 36, cx + ox + 36, cy + oy], fill=col)
            draw.polygon([(cx + ox - 35, cy + oy - 12), (cx + ox + 35, cy + oy - 12), (cx + ox, cy + oy + 44)], fill=col)


def ensure_minimum_10_sample_photos(
    profile_id: str,
    patient_name: str = "Don Manuel",
) -> list[str]:
    """
    Asegura que el perfil cuente con al menos `MIN_SCREENSAVER_PHOTOS` (10) fotografías
    en `data/photos/<profile_id>/`. Genera postales nostálgicas en JPEG con degradados
    cálidos y marcos tipo álbum familiar para completar hasta llegar a 10.
    """
    pdir = get_profile_photos_dir(profile_id)
    captions = _load_captions_map(pdir)
    existing_files = _list_photo_files(pdir)
    created_paths: list[str] = []

    if len(existing_files) >= config.MIN_SCREENSAVER_PHOTOS:
        return [str(p) for p in existing_files]

    w, h = 1280, 720
    title_font = _get_font(42, italic=False)
    sub_font = _get_font(26, italic=True)
    badge_font = _get_font(20, italic=False)

    needed = config.MIN_SCREENSAVER_PHOTOS - len(existing_files)
    for tpl in SAMPLE_POSTCARD_TEMPLATES:
        if needed <= 0:
            break
        out_path = pdir / tpl["filename"]
        if out_path.exists():
            continue

        c1, c2 = tpl["palette"]
        # Crear degradado vertical suave rápido usando línea 1xH escalada
        grad = Image.new("RGB", (1, h))
        for y in range(h):
            ratio = y / max(1, h - 1)
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            grad.putpixel((0, y), (r, g, b))
        img = grad.resize((w, h), Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(img)

        # Marco cálido estilo postal familiar
        draw.rectangle([28, 28, w - 28, h - 28], outline=(245, 232, 212), width=4)
        draw.rectangle([42, 42, w - 42, h - 42], outline=(217, 155, 82), width=2)

        _draw_motif(draw, tpl["motif"], w, h)

        # Textos centrados
        badge_txt = f"ÁLBUM DE RECUERDOS DE {patient_name.upper()}"
        draw.text((w // 2, int(h * 0.62)), badge_txt, fill=(232, 184, 120), font=badge_font, anchor="mm")
        draw.text((w // 2, int(h * 0.71)), tpl["caption"], fill=(255, 248, 238), font=title_font, anchor="mm")
        draw.text((w // 2, int(h * 0.80)), tpl["subtitle"], fill=(235, 222, 204), font=sub_font, anchor="mm")

        img.save(out_path, format="JPEG", quality=88, optimize=True)
        captions[tpl["filename"]] = tpl["caption"]
        created_paths.append(str(out_path))
        needed -= 1

    _save_captions_map(pdir, captions)
    return [str(p) for p in _list_photo_files(pdir)]


def get_photos_as_data_uris(profile_id: str) -> list[dict[str, str]]:
    """
    Devuelve todas las fotos del perfil codificadas como data URIs base64
    para que el protector de pantalla rote en el navegador sin latencia de red.
    """
    pdir = get_profile_photos_dir(profile_id)
    captions = _load_captions_map(pdir)
    files = _list_photo_files(pdir)

    result: list[dict[str, str]] = []
    for p in files:
        ext = p.suffix.lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
        caption = captions.get(p.name, p.stem.replace("_", " ").title())
        result.append(
            {
                "filename": p.name,
                "path": str(p),
                "caption": caption,
                "data_uri": f"data:{mime};base64,{b64}",
            }
        )
    return result


# ==============================================================================
# 3. Inicio Automático al Encender Windows (Startup Folder + HKCU\Run)
# ==============================================================================
def get_windows_startup_cmd_path() -> Path:
    """Devuelve la ruta exacta del script de inicio en la carpeta Startup de Windows."""
    appdata = os.getenv("APPDATA")
    if appdata:
        startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    else:
        startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup_dir / STARTUP_CMD_NAME


def _resolve_launch_target() -> str:
    """Determina si lanzar MemoriaViva_RISE.exe o iniciar_memoriaviva.bat."""
    exe_path = config.BASE_DIR / "MemoriaViva_RISE.exe"
    if exe_path.exists():
        return f'"{exe_path}"'
    bat_path = config.BASE_DIR / "iniciar_memoriaviva.bat"
    return f'"{bat_path}"'


def is_windows_autostart_enabled() -> bool:
    """Verifica si MemoriaViva RISE está configurado para arrancar al encender la PC."""
    cmd_exists = get_windows_startup_cmd_path().exists()
    reg_exists = False
    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, REG_VALUE_NAME)
                reg_exists = True
        except OSError:
            reg_exists = False
    return cmd_exists or reg_exists


def set_windows_autostart(enabled: bool) -> dict[str, Any]:
    """
    Habilita o deshabilita el arranque automático de MemoriaViva RISE cuando se
    enciende la computadora en Windows (sin requerir privilegios de administrador).
    """
    cmd_path = get_windows_startup_cmd_path()
    launch_target = _resolve_launch_target()

    if enabled:
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_content = (
            "@echo off\r\n"
            f'cd /d "{config.BASE_DIR}"\r\n'
            f"start \"\" {launch_target}\r\n"
        )
        cmd_path.write_text(cmd_content, encoding="utf-8")

        reg_ok = False
        if winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, launch_target)
                reg_ok = True
            except OSError:
                reg_ok = False

        return {
            "ok": True,
            "enabled": True,
            "startup_cmd": str(cmd_path),
            "registry_set": reg_ok,
        }

    # Deshabilitar limpiamente
    if cmd_path.exists():
        try:
            cmd_path.unlink()
        except OSError:
            pass

    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, REG_VALUE_NAME)
                except FileNotFoundError:
                    pass
        except OSError:
            pass

    return {
        "ok": True,
        "enabled": False,
        "startup_cmd": str(cmd_path),
        "registry_set": False,
    }
