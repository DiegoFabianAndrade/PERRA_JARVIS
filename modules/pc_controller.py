"""
Módulo de control de PC Windows para PERRA_JARVIS.
Permite interactuar directamente con el hardware y sistema operativo:
- Métricas del sistema (CPU, RAM, Disco, Batería)
- Capturas de pantalla en tiempo real (Screenshots)
- Bloqueo y control de energía
- Control de multimedia (Volumen, Play/Pausa)
- Apertura de aplicaciones comunes
- Navegación y envío de archivos locales
- Ejecución remota de comandos de terminal
"""

import os
import sys
import time
import ctypes
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import psutil
from PIL import ImageGrab

from config import TEMP_DIR

# Constantes de teclas virtuales de Windows
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def _ensure_desktop_access() -> bool:
    """Asegura que el hilo actual tenga acceso al escritorio interactivo de Windows."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return True
    except Exception:
        pass
    return False


def get_system_stats() -> Dict[str, Any]:
    """Obtiene telemetría completa del sistema."""
    cpu_percent = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    battery = psutil.sensors_battery()
    boot_time = psutil.boot_time()
    uptime_hours = (time.time() - boot_time) / 3600

    battery_info = None
    if battery:
        battery_info = {
            "percent": battery.percent,
            "plugged": battery.power_plugged,
            "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
        }

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024 ** 3), 1),
        "ram_total_gb": round(ram.total / (1024 ** 3), 1),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "battery": battery_info,
        "uptime_hours": round(uptime_hours, 1)
    }


def format_stats_message(stats: Dict[str, Any]) -> str:
    """Formatea las estadísticas para un mensaje limpio y elegante en Telegram."""
    b = stats.get("battery")
    if b:
        estado_bat = "⚡ Conectado a corriente" if b["plugged"] else "🔋 En batería"
        bat_str = f"{estado_bat}: {b['percent']}%"
    else:
        bat_str = "🔌 Sin batería (PC de escritorio)"

    msg = (
        "💻 *TELEMETRÍA EN TIEMPO REAL - PC*\n"
        "─────────────────────────────\n"
        f"⚡ *CPU:* `{stats['cpu_percent']}%`\n"
        f"🧠 *RAM:* `{stats['ram_percent']}%` ({stats['ram_used_gb']} GB / {stats['ram_total_gb']} GB)\n"
        f"💾 *Disco C:* `{stats['disk_percent']}%` ({stats['disk_free_gb']} GB libres de {stats['disk_total_gb']} GB)\n"
        f"{bat_str}\n"
        f"⏱️ *Tiempo Encendido:* `{stats['uptime_hours']} horas`\n"
        "─────────────────────────────"
    )
    return msg


def take_screenshot(filename: str = "screenshot.png") -> Path:
    """Captura la pantalla completa de Windows y guarda en la carpeta temporal."""
    _ensure_desktop_access()
    output_path = TEMP_DIR / filename
    img = ImageGrab.grab(all_screens=True)
    img.save(output_path, "PNG")
    return output_path


def lock_pc() -> bool:
    """Bloquea la sesión actual de Windows inmediatamente."""
    try:
        return bool(ctypes.windll.user32.LockWorkStation())
    except Exception:
        return False


def send_media_key(vk_code: int):
    """Envía un evento de tecla multimedia."""
    user32 = ctypes.windll.user32
    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def media_control(action: str) -> str:
    """Controla la reproducción y volumen del sistema."""
    act = action.lower().strip()
    if act in ("mute", "silenciar"):
        send_media_key(VK_VOLUME_MUTE)
        return "🔇 Audio silenciado / restaurado."
    elif act in ("up", "subir"):
        for _ in range(5):
            send_media_key(VK_VOLUME_UP)
            time.sleep(0.02)
        return "🔊 Volumen subido (+10%)."
    elif act in ("down", "bajar"):
        for _ in range(5):
            send_media_key(VK_VOLUME_DOWN)
            time.sleep(0.02)
        return "🔉 Volumen bajado (-10%)."
    elif act in ("play", "pause", "playpause", "pausa"):
        send_media_key(VK_MEDIA_PLAY_PAUSE)
        return "⏯️ Reproducción alternada (Play/Pausa)."
    return "Acción de multimedia no reconocida (opciones: subir, bajar, silenciar, play)."


def open_application(app_name: str) -> str:
    """Abre aplicaciones comunes en Windows."""
    app = app_name.lower().strip()
    shortcuts = {
        "chrome": "start chrome",
        "navegador": "start chrome",
        "spotify": "start spotify:",
        "musica": "start spotify:",
        "vscode": "code",
        "code": "code",
        "calc": "calc.exe",
        "calculadora": "calc.exe",
        "notepad": "notepad.exe",
        "notas": "notepad.exe",
        "descargas": f'explorer.exe "{Path.home() / "Downloads"}"',
        "terminal": "start wt",
        "cmd": "start cmd",
    }

    cmd = shortcuts.get(app, f"start {app_name}")
    try:
        subprocess.Popen(cmd, shell=True)
        return f"🚀 Aplicación solicitada lanzada: `{app_name}`"
    except Exception as e:
        return f"⚠️ Error al intentar abrir {app_name}: {str(e)}"


def run_command(command: str, timeout: int = 15) -> str:
    """Ejecuta un comando en PowerShell y retorna la salida (con límite de tamaño para Telegram)."""
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = res.stdout if res.stdout else res.stderr
        if not output:
            output = "Comando ejecutado sin salida en consola."
        if len(output) > 3000:
            output = output[:3000] + "\n... [Salida truncada]"
        return output
    except subprocess.TimeoutExpired:
        return "⏰ Tiempo de espera agotado (timeout de 15s)."
    except Exception as e:
        return f"⚠️ Error al ejecutar comando: {str(e)}"


def list_downloads(limit: int = 8) -> List[Dict[str, Any]]:
    """Lista los archivos más recientes en la carpeta Descargas."""
    dl_path = Path.home() / "Downloads"
    if not dl_path.exists():
        return []
    
    files = []
    for item in dl_path.iterdir():
        if item.is_file():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item.resolve()),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime
                })
            except Exception:
                continue

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files[:limit]
