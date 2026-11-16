"""
Módulo de WhatsApp para PERRA_JARVIS.
Permite:
- Enviar mensajes y abrir chats en WhatsApp Desktop desde Telegram sin riesgo de baneo.
- Detección de estado de WhatsApp en Windows.
"""

import urllib.parse
import subprocess
import psutil
from typing import Dict, Any


def is_whatsapp_running() -> bool:
    """Verifica si la aplicación de WhatsApp está abierta en el computador."""
    for p in psutil.process_iter(["name"]):
        try:
            if "whatsapp" in p.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def send_whatsapp_message(phone: str, message: str) -> str:
    """
    Despacha un mensaje a WhatsApp Desktop en Windows.
    Abre la conversación con el número indicado y el texto listo o enviado.
    """
    clean_phone = "".join(filter(str.isdigit, phone))
    # Si tiene 10 dígitos (Colombia celular común: 3XXXXXXXXX), anteponer 57
    if len(clean_phone) == 10:
        clean_phone = "57" + clean_phone

    encoded_msg = urllib.parse.quote(message)
    # URI oficial de WhatsApp para Windows
    uri = f"whatsapp://send?phone={clean_phone}&text={encoded_msg}"

    try:
        subprocess.Popen(f'start "" "{uri}"', shell=True)
        return (
            f"💬 *WhatsApp Despachado:*\n"
            f"📱 Destino: `+{clean_phone}`\n"
            f"✉️ Mensaje: _{message}_\n"
            f"✅ Se abrió la conversación en tu WhatsApp de escritorio."
        )
    except Exception as e:
        return f"⚠️ Error abriendo WhatsApp: {e}"


def get_whatsapp_status_report() -> str:
    """Genera reporte de estado del módulo WhatsApp."""
    running = is_whatsapp_running()
    status_str = "🟢 En ejecución en segundo plano" if running else "⚪ No iniciado (se abrirá al enviar mensaje)"
    return (
        "💬 *MÓDULO WHATSAPP DESKTOP*\n"
        "─────────────────────────────\n"
        f"🖥️ *Estado en PC:* {status_str}\n\n"
        "✨ *Comando para enviar mensajes desde Telegram:*\n"
        "• `/wapp <número> <mensaje>`\n"
        "• Ejemplo: `/wapp 3101234567 Hola, ya voy saliendo`\n"
        "─────────────────────────────"
    )
