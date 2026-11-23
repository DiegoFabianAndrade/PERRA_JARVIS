"""
PERRA_JARVIS - Local Windows Companion Daemon (Producción)
Se ejecuta en segundo plano cuando el computador de Diego está encendido.
Sincroniza con el núcleo 24/7 de Azure Blob Storage y ejecuta todas las órdenes físicas y de desarrollo.
"""

import os
import sys
import time
import json
import socket
import logging
import datetime
import subprocess
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
AZURE_STORAGE_CONN = os.getenv("AZURE_STORAGE_CONN", os.getenv("AzureWebJobsStorage", ""))

os.makedirs(BASE_DIR / "temp", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "temp" / "pc_companion.log", encoding="utf-8")
    ]
)

# ─────────────────────────────────────────────────────────────
# 1. CLIENTE AZURE BLOB STORAGE VÍA HTTPS REST (PERSISTENCIA 100%)
# ─────────────────────────────────────────────────────────────
AZURE_BLOB_SAS_URL = os.getenv("AZURE_BLOB_SAS_URL", "https://stperrajarvis125.blob.core.windows.net/jarvis-state")
AZURE_BLOB_SAS_QUERY = os.getenv("AZURE_BLOB_SAS_QUERY", "")


def get_blob_orders_direct() -> list:
    """Lee las órdenes directamente de Azure Blob Storage vía HTTPS REST."""
    url = f"{AZURE_BLOB_SAS_URL}/orders.json?{AZURE_BLOB_SAS_QUERY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                return [o for o in data if o.get("status") == "pending"]
    except Exception as e:
        logging.debug(f"Direct blob read bypassed: {e}")
    return []

def mark_blob_order_complete_direct(order_id: int, result_text: str = ""):
    """Marca la orden como completada directamente en Azure Blob Storage vía HTTPS REST."""
    url = f"{AZURE_BLOB_SAS_URL}/orders.json?{AZURE_BLOB_SAS_QUERY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                for o in data:
                    if o.get("id") == order_id:
                        o["status"] = "completed"
                        o["completed_at"] = time.time()
                        o["result"] = result_text
                
                raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                put_req = urllib.request.Request(
                    url,
                    data=raw,
                    headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "application/json"},
                    method="PUT"
                )
                urllib.request.urlopen(put_req, timeout=6)
                logging.info(f"Orden #{order_id} marcada completada directamente en Blob Storage.")
    except Exception as e:
        logging.error(f"Error marcando orden en Blob directo: {e}")


# ─────────────────────────────────────────────────────────────
# 2. COMUNICACIÓN CON AZURE Y TELEGRAM
# ─────────────────────────────────────────────────────────────
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
    except Exception:
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
        with urllib.request.urlopen(req, timeout=6) as res:
            return res.status == 200
    except Exception as e:
        logging.debug(f"Heartbeat fallido (reintentando): {e}")
        return False

def get_pending_orders():
    """Consulta órdenes pendientes en Azure."""
    url = f"{AZURE_BASE_URL}/api/pc/orders"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=6) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception:
        # Fallback a Blob Storage directo
        return get_blob_orders_direct()

def mark_order_completed(order_id: int, result_text: str = ""):
    """Marca la orden como terminada en Azure Function y Blob Storage."""
    url = f"{AZURE_BASE_URL}/api/pc/orders/complete"
    try:
        data = json.dumps({"order_id": order_id, "result": result_text}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as res:
            if res.status == 200:
                return True
    except Exception as e:
        logging.warning(f"Error marcando orden vía HTTP, usando fallback directo a Blob: {e}")
    
    mark_blob_order_complete_direct(order_id, result_text)
    return True

def send_telegram_photo(photo_path: str, caption: str = ""):
    """Envía una foto directamente a Telegram."""
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
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
        logging.error(f"Error enviando mensaje a Telegram: {e}")


# ─────────────────────────────────────────────────────────────
# 3. MOTOR DE EJECUCIÓN DE ÓRDENES EN WINDOWS
# ─────────────────────────────────────────────────────────────
def execute_order(order: dict):
    """Ejecuta una acción local en el computador personal de Diego."""
    action = order.get("action")
    params = order.get("params", {})
    order_id = order.get("id")
    repo = order.get("repo", "PERRA_JARVIS")
    instruction = params.get("instruction") or order.get("raw_text", "")

    logging.info(f"⚡ Ejecutando orden #{order_id}: {action} en {repo} -> {instruction}")

    result_summary = "Completado con éxito."

    try:
        # A. Captura de pantalla
        if action == "screenshot":
            from modules import pc_controller
            img_path = pc_controller.take_screenshot(f"screen_{order_id}.png")
            send_telegram_photo(
                str(img_path),
                f"📸 *Captura de Pantalla Ejecutada (Orden #{order_id})*\n"
                f"💻 Tomada en tiempo real en tu equipo."
            )
            result_summary = f"Screenshot guardado en {img_path}"

        # B. Bloquear PC
        elif action == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            send_telegram_msg(f"🔒 *Orden #{order_id}:* Sesión de Windows bloqueada exitosamente.")
            result_summary = "PC bloqueado con LockWorkStation."

        # C. Apagar o reiniciar PC
        elif action == "shutdown":
            send_telegram_msg(f"🛑 *Orden #{order_id}:* Apagando computador en 10 segundos...")
            os.system("shutdown /s /t 10")
            result_summary = "Shutdown programado."

        elif action == "restart":
            send_telegram_msg(f"🔄 *Orden #{order_id}:* Reiniciando computador en 10 segundos...")
            os.system("shutdown /r /t 10")
            result_summary = "Restart programado."

        # D. Ejecutar Pruebas Unitarias
        elif action == "test":
            from modules import remote_test_runner
            res = remote_test_runner.run_project_tests(repo)
            diag = res.get("diagnosis", "")
            diag_str = f"\n\n🧠 *Diagnóstico IA:*\n{diag}" if diag else ""
            msg = (
                f"🧪 *RESULTADO DE PRUEBAS UNITARIAS (Orden #{order_id})*\n"
                "─────────────────────────────\n"
                f"📦 *Proyecto:* `{repo}`\n"
                f"🚦 *Estado:* {'🟢 Éxito' if res.get('success') else '🔴 Fallaron tests'}\n"
                f"📝 *Detalle:* {res.get('message', '')}"
                f"{diag_str}\n"
                "─────────────────────────────"
            )
            send_telegram_msg(msg)
            result_summary = res.get("message", "")

        # E. Consulta de Git
        elif action == "git":
            from modules import git_agent
            overview = git_agent.get_repo_overview(repo)
            send_telegram_msg(f"📦 *Estado Git (Orden #{order_id}):*\n\n{overview}")
            result_summary = "Git overview enviado."

        # F. Abrir aplicación
        elif action == "open_app":
            app_name = params.get("app", "chrome")
            from modules import pc_controller
            res_txt = pc_controller.open_application(app_name)
            send_telegram_msg(f"🚀 *Orden #{order_id}:* {res_txt}")
            result_summary = res_txt

        # G. Control de medios
        elif action == "media":
            act = params.get("action", "play")
            from modules import pc_controller
            res_txt = pc_controller.media_control(act)
            send_telegram_msg(f"🎵 *Orden #{order_id}:* {res_txt}")
            result_summary = res_txt

        # H. Orden de Desarrollo / Antigravity
        elif action == "code_order":
            from modules import antigravity_bridge
            antigravity_bridge.queue_remote_order(instruction, repo)
            msg = (
                f"🧑‍💻 *ORDEN DE CÓDIGO EJECUTADA EN TU PC (Orden #{order_id})*\n"
                "─────────────────────────────\n"
                f"📦 *Repositorio:* `{repo}`\n"
                f"📌 *Instrucción:* _{instruction}_\n\n"
                f"✅ Registrada formalmente en `REMOTE_ORDERS.jsonl` y en el Dashboard de tu editor.\n"
                "─────────────────────────────"
            )
            send_telegram_msg(msg)
            result_summary = f"Orden #{order_id} agregada al log de Antigravity."

        # I. Comando genérico de consola
        elif action == "command":
            cmd = params.get("cmd", "")
            from modules import antigravity_bridge
            out = antigravity_bridge.run_project_command(repo, cmd)
            send_telegram_msg(f"💻 *Comando Ejecutado (Orden #{order_id}):*\n```\n{out}\n```")
            result_summary = out[:200]

        else:
            send_telegram_msg(f"⚡ *Orden #{order_id} [{action}]* procesada en tu PC local.")

    except Exception as e:
        logging.error(f"Error procesando orden #{order_id}: {e}")
        send_telegram_msg(f"⚠️ Error procesando orden #{order_id} en PC: {str(e)}")
        result_summary = f"Error: {str(e)}"
    finally:
        mark_order_completed(order_id, result_summary)
        logging.info(f"✅ Orden #{order_id} finalizada y marcada en Azure.")


# ─────────────────────────────────────────────────────────────
# 4. BUCLE PRINCIPAL PERMANENTE
# ─────────────────────────────────────────────────────────────
def run_companion():
    """Bucle principal permanente del companion en Windows."""
    logging.info("=" * 60)
    logging.info("🚀 PERRA_JARVIS Local Windows Companion Iniciado.")
    logging.info(f"🌐 Conectado a Azure Core: {AZURE_BASE_URL}")
    logging.info(f"💾 Conectado a Azure Blob Storage: stperrajarvis125")
    logging.info("=" * 60)

    # Enviar heartbeat inicial inmediato
    send_heartbeat()

    last_hb = time.time()

    while True:
        try:
            now = time.time()

            # Enviar heartbeat cada 25 segundos
            if now - last_hb >= 25:
                send_heartbeat()
                last_hb = now

            # Revisar órdenes pendientes cada 3 segundos
            orders = get_pending_orders()
            if orders:
                logging.info(f"📥 Se detectaron {len(orders)} órdenes pendientes en la nube.")
                for order in orders:
                    execute_order(order)

            time.sleep(3)
        except KeyboardInterrupt:
            logging.info("Companion detenido manualmente.")
            break
        except Exception as e:
            logging.error(f"Excepción en bucle companion: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_companion()
