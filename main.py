"""
Punto de entrada principal para PERRA_JARVIS.
Arquitectura Híbrida 24/7:
- Núcleo Nube Serverless (Azure Functions - $0.00 USD): Atiende Telegram 24/7 incluso con el PC apagado.
- Local Windows Companion: Sincroniza hardware, capturas y pruebas unitarias cuando el PC está encendido.
"""

import sys
import argparse
import asyncio
import logging
import urllib.request
import json
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ASSISTANT_NAME, DEBUG
from modules.telegram_ui import register_handlers
from modules.proactive_monitor import monitor
from modules import reminder_service
from modules import antigravity_bridge
from scripts import pc_companion

# Configuración de logs
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=log_level
)
logger = logging.getLogger(ASSISTANT_NAME)


def check_webhook_status() -> dict:
    """Verifica si el Webhook 24/7 de Azure está activo en Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        with urllib.request.urlopen(url, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("result", {})
    except Exception as e:
        logger.warning(f"No se pudo consultar el estado del webhook: {e}")
        return {}


async def proactive_background_task(app):
    """Tarea proactiva en segundo plano para modo Polling local."""
    await asyncio.sleep(5)
    logger.info("🛡️ Monitor proactivo en segundo plano iniciado.")
    battery_counter = 0

    while True:
        try:
            # 1. Revisar recordatorios
            due_reminders = reminder_service.check_due_reminders()
            for r in due_reminders:
                msg = (
                    "🔔 *¡RECORDATORIO PUNTUAL!* 🔔\n"
                    "─────────────────────────────\n"
                    f"📌 *Tarea:* _{r['text']}_\n"
                    f"⏰ *Programado:* `{r.get('time_str', 'Ahora')}`\n"
                    "─────────────────────────────"
                )
                await app.bot.send_message(
                    chat_id=ALLOWED_CHAT_ID,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN
                )

            # 2. Revisar resultados de agentes de código
            new_results = antigravity_bridge.check_undelivered_results()
            for res in new_results:
                await app.bot.send_message(
                    chat_id=ALLOWED_CHAT_ID,
                    text=res["result"],
                    parse_mode=ParseMode.MARKDOWN
                )

            # 3. Revisar batería
            battery_counter += 1
            if battery_counter >= 4:
                battery_counter = 0
                alert = monitor.check_battery()
                if alert:
                    await app.bot.send_message(
                        chat_id=ALLOWED_CHAT_ID,
                        text=alert,
                        parse_mode=ParseMode.MARKDOWN
                    )

        except Exception as e:
            logger.error(f"Error en monitor proactivo: {e}")

        await asyncio.sleep(30)


async def post_init_callback(app):
    """Lanzador de tareas asíncronas de fondo."""
    asyncio.create_task(proactive_background_task(app))


def run_legacy_polling():
    """Ejecuta el bot en modo polling tradicional (elimina el webhook de la nube)."""
    print("\n⚠️ AVISO: El modo polling sobrescribirá el webhook 24/7 de Azure.")
    print("Cuando apagues tu PC, el bot dejará de responder hasta que lo vuelvas a encender.\n")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init_callback).build()
    register_handlers(app)
    app.run_polling(drop_pending_updates=True)


def main():
    parser = argparse.ArgumentParser(description=f"{ASSISTANT_NAME} - Asistente Personal Ejecutivo")
    parser.add_argument("--polling", action="store_true", help="Forzar modo Polling local (sobrescribe Webhook nube)")
    parser.add_argument("--status", action="store_true", help="Ver estado de conexión nube y local")
    args = parser.parse_args()

    if not TELEGRAM_BOT_TOKEN or "tu_token" in TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN no configurado en el archivo .env")
        sys.exit(1)

    wh_info = check_webhook_status()
    webhook_url = wh_info.get("url", "")

    if args.status:
        print("=" * 60)
        print(f"📊 ESTADO DEL SISTEMA {ASSISTANT_NAME}")
        print("=" * 60)
        print(f"🌐 Webhook Nube: {'ACTIVO' if webhook_url else 'INACTIVO'}")
        if webhook_url:
            print(f"🔗 URL: {webhook_url}")
            print(f"📦 Mensajes en Cola: {wh_info.get('pending_update_count', 0)}")
        print(f"👤 Dueño Autorizado: {ALLOWED_CHAT_ID}")
        print("=" * 60)
        return

    if args.polling:
        run_legacy_polling()
        return

    # Si hay un Webhook activo en Azure, ejecutar en modo COMPANION local
    if webhook_url and "azurewebsites.net" in webhook_url:
        print("=" * 60)
        print(f"☁️ PERRA_JARVIS 24/7 CLOUD CORE ACTIVO ($0.00 USD)")
        print("=" * 60)
        print(f"🌐 Webhook: {webhook_url}")
        print(f"👤 Dueño: {ALLOWED_CHAT_ID}")
        print("💻 Iniciando Local Windows Companion Daemon...")
        print("   • Envía telemetría de hardware cada 25s")
        print("   • Ejecuta pantallazos y bloqueo físico cuando se solicite")
        print("   • Si apagas este PC, Azure seguirá respondiendo en tu móvil 24/7")
        print("=" * 60)
        pc_companion.run_companion()
    else:
        print("⚠️ No se detectó webhook en Azure. Iniciando en modo Polling...")
        run_legacy_polling()


if __name__ == "__main__":
    main()
