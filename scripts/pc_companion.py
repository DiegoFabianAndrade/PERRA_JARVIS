"""
PERRA_JARVIS - Local Windows Companion Daemon
Se ejecuta en segundo plano cuando el computador de Diego está encendido.
Envía señal de vida (Heartbeat) al núcleo 24/7 en Azure y ejecuta órdenes locales de hardware.
"""

import os
import sys
import time
import json
import socket
import logging
import urllib.request
import urllib.parse
from pathlib import Path

# Agregar raíz al path para importar módulos locales
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID

AZURE_BASE_URL = os.getenv("AZURE_BASE_URL", "https://func-perra-jarvis.azurewebsites.net")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "temp" / "pc_companion.log", encoding="utf-8")
    ]
)

def get_system_telemetry():
    """Obtiene métricas de hardware de la máquina local."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        b_str = f"{battery.percent}% {'(Cargando)' if battery.power_plugged else '(Batería)'}" if battery else "AC"
        return {
            "status": "online",
            "hostname": socket.gethostname(),
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "battery": b_str,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "online",
            "hostname": socket.gethostname(),
            "cpu": 0,
            "ram": 0,
            "battery": "N/A",
            "timestamp": time.time()
        }

def send_heartbeat():
    """Envía señal de vida a Azure Function."""
    url = f"{AZURE_BASE_URL}/api/pc/heartbeat"
    try:
        data = json.dumps(get_system_telemetry()).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception as e:
        logging.debug(f"Heartbeat fallido (reintentando): {e}")
        return False

def get_pending_orders():
    """Consulta órdenes pendientes en Azure Function."""
    url = f"{AZURE_BASE_URL}/api/pc/orders"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception:
        return []

def mark_order_completed(order_id: int):
    """Marca la orden como terminada en Azure Function."""
    url = f"{AZURE_BASE_URL}/api/pc/orders/complete"
    try:
        data = json.dumps({"order_id": order_id}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception as e:
        logging.error(f"Error marcando orden completada: {e}")
        return False

def send_telegram_photo(photo_path: str, caption: str = ""):
    """Envía una foto directamente a Telegram."""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": ALLOWED_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            requests.post(url, files=files, data=data, timeout=15)
    except Exception as e:
        logging.error(f"Error enviando foto a Telegram: {e}")

def send_telegram_msg(text: str):
    """Envía un mensaje de texto a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": ALLOWED_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        logging.error(f"Error enviando mensaje: {e}")

def execute_order(order: dict):
    """Ejecuta una acción local en el computador de Diego."""
    action = order.get("action")
    params = order.get("params", {})
    order_id = order.get("id")

    logging.info(f"Ejecutando orden local: {action} (ID: {order_id})")

    try:
        if action == "screenshot":
            from modules import pc_controller
            img_path = pc_controller.take_screenshot("pc_screen_capture.png")
            send_telegram_photo(str(img_path), "📸 Captura de pantalla de tu computador en tiempo real.")

        elif action == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            send_telegram_msg("🔒 Computador bloqueado de inmediato.")

        elif action == "test":
            proj = params.get("project", "PERRA_JARVIS")
            from modules import remote_test_runner
            res = remote_test_runner.run_project_tests(proj)
            send_telegram_msg(f"🧪 *Resultado de Tests en `{proj}`:*\n{res.get('message', '')}")

        elif action == "git":
            proj = params.get("project", "PERRA_JARVIS")
            from modules import git_agent
            overview = git_agent.get_repo_overview(proj)
            send_telegram_msg(overview)

        else:
            send_telegram_msg(f"⚡ Orden `{action}` procesada en PC local.")

    except Exception as e:
        logging.error(f"Error ejecutando orden {action}: {e}")
        send_telegram_msg(f"⚠️ Error ejecutando orden `{action}` en PC: {e}")
    finally:
        mark_order_completed(order_id)


def run_companion():
    """Bucle principal del companion."""
    logging.info("🚀 PERRA_JARVIS Local Windows Companion Iniciado.")
    logging.info(f"Conectado a Azure Core: {AZURE_BASE_URL}")

    last_hb = 0
    while True:
        try:
            now = time.time()
            # Enviar heartbeat cada 25 segundos
            if now - last_hb >= 25:
                send_heartbeat()
                last_hb = now

            # Revisar órdenes pendientes cada 3 segundos
            orders = get_pending_orders()
            for order in orders:
                execute_order(order)

            time.sleep(3)
        except KeyboardInterrupt:
            logging.info("Companion detenido por el usuario.")
            break
        except Exception as e:
            logging.error(f"Excepción en bucle companion: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_companion()
