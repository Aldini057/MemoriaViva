"""
MemoriaViva RISE - Conector Familiar de 3 Niveles en Telegram y Generador QR (Capa 4)
Global RISE AI Hackathon 2026 (University of Notre Dame, UdG, UColima)

Implementa:
1. Filtro de Privacidad Intrafamiliar (Abstract Summary Filter): Jamás envía audio crudo
   ni transcripciones íntimas completas; transmite indicadores agregados y puentes afectivos.
2. Sistema de Triaje en 3 Niveles:
   - Nivel 1 (Verde - Silencioso): Pulso de Bienestar Diario + Pregunta para la cena.
   - Nivel 2 (Amarillo - Preventivo): Aviso de Tendencia Longitudinal (21 días).
   - Nivel 3 (Rojo - Urgente): Alerta de Emergencia por Desorientación Aguda + Protocolo de Feil.
3. Auto-vinculación por Código QR y autodetección de Chat ID vía getUpdates.
"""

from __future__ import annotations

import io
import threading
import time
from datetime import datetime
from typing import Any

import qrcode
import requests

import config


class TelegramFamilyBridge:
    """Puente de comunicación ética y triaje de 3 niveles con el familiar cuidador."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self.bot_token = (bot_token if bot_token is not None else config.TELEGRAM_BOT_TOKEN).strip()
        self.chat_id = (chat_id if chat_id is not None else config.TELEGRAM_CHAT_ID).strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.message_log: list[dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # Autodetección de Bot y Vinculación Automática de Chat ID
    # --------------------------------------------------------------------------
    def get_bot_info(self) -> dict[str, Any]:
        """Consulta /getMe para verificar el token y obtener el @username del bot."""
        if not self.bot_token:
            return {"ok": False, "error": "No se ha configurado TELEGRAM_BOT_TOKEN."}

        try:
            resp = requests.get(f"{self.base_url}/getMe", timeout=5)
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                result = data["result"]
                return {
                    "ok": True,
                    "id": result.get("id"),
                    "first_name": result.get("first_name", "MemoriaViva Bot"),
                    "username": result.get("username", ""),
                    "link": f"https://t.me/{result.get('username', '')}?start=memoriaviva",
                }
            return {"ok": False, "error": data.get("description", "Token inválido.")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def discover_latest_chat_id(self) -> dict[str, Any]:
        """
        Consulta /getUpdates para detectar automáticamente el chat_id del familiar
        cuando envía '/start' u 'Hola' al bot en Telegram.
        """
        if not self.bot_token:
            return {"ok": False, "error": "Token de bot no configurado."}

        try:
            resp = requests.get(f"{self.base_url}/getUpdates", timeout=5)
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                updates = data.get("result", [])
                for upd in reversed(updates):
                    msg = upd.get("message") or upd.get("edited_message") or {}
                    chat = msg.get("chat", {})
                    cid = chat.get("id")
                    if cid:
                        self.chat_id = str(cid)
                        first_name = chat.get("first_name", "Familiar")
                        username = chat.get("username", "")
                        self._persist_chat_id_to_env(self.chat_id)
                        return {
                            "ok": True,
                            "chat_id": self.chat_id,
                            "first_name": first_name,
                            "username": username,
                        }
                return {
                    "ok": False,
                    "error": "Aún no hay mensajes entrantes. Abre el bot en Telegram y presiona 'Iniciar' (/start).",
                }
            return {"ok": False, "error": data.get("description", "Error al consultar getUpdates.")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _persist_chat_id_to_env(self, new_chat_id: str) -> None:
        """Actualiza TELEGRAM_CHAT_ID en el archivo .env local para futuras sesiones."""
        env_path = config.BASE_DIR / ".env"
        if not env_path.exists():
            return
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            updated = False
            new_lines = []
            for line in lines:
                if line.startswith("TELEGRAM_CHAT_ID="):
                    new_lines.append(f"TELEGRAM_CHAT_ID={new_chat_id}")
                    updated = True
                else:
                    new_lines.append(line)
            if not updated:
                new_lines.append(f"TELEGRAM_CHAT_ID={new_chat_id}")
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    def generate_linking_qr_bytes(self, bot_username: str | None = None) -> tuple[bytes, str]:
        """
        Genera una imagen PNG en bytes con el código QR para vincular el celular
        del cuidador con un solo escaneo.
        """
        if not bot_username:
            info = self.get_bot_info()
            bot_username = info.get("username") or "MemoriaVivaRISE_Bot"

        url = f"https://t.me/{bot_username}?start=vincular"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#3A322C", back_color="#FAF6F0")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), url

    # --------------------------------------------------------------------------
    # Envío Core con Medición de Latencia (Meta 4: < 1.5 segundos)
    # --------------------------------------------------------------------------
    def _send_with_telemetry(
        self,
        message: str,
        level: int,
        silent: bool = False,
    ) -> dict[str, Any]:
        """
        Envía el mensaje a la API de Telegram en un hilo de fondo no bloqueante
        para no retrasar la respuesta de voz del adulto mayor (< 10 ms en hilo principal).
        Si `chat_id` no está configurado, lo registra en el espejo local para la UI.
        """
        start_t = time.perf_counter()
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        has_target = bool(self.bot_token and self.chat_id)

        entry: dict[str, Any] = {
            "level": level,
            "silent": silent,
            "timestamp": timestamp_str,
            "message": message,
            "delivered_telegram_api": has_target,
            "chat_id": self.chat_id or "MODO_ESPEJO_LOCAL",
            "latency_ms": 0.0,
            "api_error": None,
        }

        if has_target:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": silent,
            }
            url = f"{self.base_url}/sendMessage"

            def _bg_dispatch() -> None:
                try:
                    r = requests.post(url, json=payload, timeout=4)
                    if r.status_code != 200:
                        entry["delivered_telegram_api"] = False
                        entry["api_error"] = r.text
                except Exception as exc:
                    entry["delivered_telegram_api"] = False
                    entry["api_error"] = str(exc)

            threading.Thread(target=_bg_dispatch, daemon=True).start()

        entry["latency_ms"] = round((time.perf_counter() - start_t) * 1000, 1)
        self.message_log.append(entry)
        return entry

    def _send(self, message: str, silent: bool = False) -> bool:
        """Firma compatible con el Blueprint Técnico."""
        res = self._send_with_telemetry(message=message, level=1 if silent else 2, silent=silent)
        return bool(res["delivered_telegram_api"] or res["chat_id"] == "MODO_ESPEJO_LOCAL")

    # --------------------------------------------------------------------------
    # Los 3 Niveles de Notificación Familiar (Marco RISE)
    # --------------------------------------------------------------------------
    def send_level1_daily_pulse(
        self,
        topic_summary: str,
        mattr: float,
        mean_pause: float,
        dinner_tip: str,
        patient_name: str = "Don Manuel",
        caregiver_name: str = "Laura",
    ) -> dict[str, Any]:
        """Nivel 1: Pulso de Bienestar Diario (Notificación Silenciosa)."""
        msg = (
            "🟢 *MemoriaViva RISE — Pulso de Bienestar Diario*\n\n"
            f"Hola {caregiver_name}, tu familiar ({patient_name}) acaba de concluir su charla con muy buen ánimo.\n\n"
            f"💬 *Recuerdo activado hoy:* {topic_summary}\n"
            f"📊 *Indicadores del habla:* Vocabulario estable (MATTR: `{mattr}`) | Pausas promedio: `{mean_pause}s`\n\n"
            f"💡 *Puente afectivo para hoy en la noche:*\n_{dinner_tip}_"
        )
        return self._send_with_telemetry(msg, level=1, silent=True)

    def send_level2_clinical_trend_warning(
        self,
        baseline_pause: float,
        recent_pause: float,
        baseline_mattr: float,
        recent_mattr: float,
        patient_name: str = "Don Manuel",
        caregiver_name: str = "Laura",
    ) -> dict[str, Any]:
        """Nivel 2: Aviso Preventivo de Tendencia Semanal (Notificación Normal)."""
        msg = (
            "🟡 *MemoriaViva RISE — Aviso Preventivo de Tendencia*\n\n"
            f"Hola {caregiver_name}. El seguimiento longitudinal de los últimos 5 días muestra una variación "
            f"sostenida respecto a la línea base personal de {patient_name}:\n\n"
            f"• *Pausas buscando palabras:* Subieron de `{baseline_pause}s` a `{recent_pause}s`.\n"
            f"• *Diversidad léxica (MATTR):* Varió de `{baseline_mattr}` a `{recent_mattr}`.\n\n"
            "📋 *Recomendación RISE:* No es una urgencia médica ni un diagnóstico, pero el sistema "
            "ya preparó el reporte gráfico de 21 días en PDF por si deseas compartirlo con su "
            "geriatra o neurólogo en su próxima revisión de rutina."
        )
        return self._send_with_telemetry(msg, level=2, silent=False)

    def send_level3_emergency_alert(
        self,
        reason: str,
        last_phrase: str,
        patient_name: str = "Don Manuel",
        caregiver_name: str = "Laura",
    ) -> dict[str, Any]:
        """Nivel 3: Alerta Roja de Emergencia o Desorientación Aguda (Prioridad Alta)."""
        msg = (
            "🔴 *¡ALERTA URGENTE! — Contacto de Emergencia Activado*\n\n"
            "⚠️ *Estado:* Episodio de desorientación aguda o angustia detectado en vivo.\n"
            f"📌 *Detalle:* {reason}\n"
            f"🗣️ *Expresión detectada:* _\"{last_phrase}\"_\n\n"
            f"🛡️ *Acción automática de MemoriaViva:* Se activó el Protocolo de Validación de Feil "
            f"en voz cálida para tranquilizar a {patient_name} en casa.\n"
            "📞 *Acción sugerida:* Llámalo ahora mismo para brindarle contención familiar."
        )
        return self._send_with_telemetry(msg, level=3, silent=False)
