"""
Punto de entrada principal para PERRA_JARVIS.
Inicia el bot asíncrono de Telegram con long polling,
control local de Windows y monitor proactivo en segundo plano.
"""

import sys
import asyncio
import logging
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ASSISTANT_NAME, DEBUG
from modules.telegram_ui import register_handlers
from modules.proactive_monitor import monitor
from modules import reminder_service
from modules import antigravity_bridge

# Configuración de logs
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=log_level
)
logger = logging.getLogger(ASSISTANT_NAME)


async def proactive_background_task(app):
    """Tarea proactiva en segundo plano: Vigila recordatorios y batería."""
    await asyncio.sleep(5)
    logger.info("🛡️ Monitor proactivo en segundo plano iniciado.")
    battery_counter = 0

    while True:
        try:
            # 1. Revisar recordatorios que hayan cumplido su hora
            due_reminders = reminder_service.check_due_reminders()
            for r in due_reminders:
                logger.info(f"Disparando recordatorio: {r['text']}")
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

            # 2. Revisar si el agente completó órdenes remotas
            new_results = antigravity_bridge.check_undelivered_results()
            for res in new_results:
                logger.info(f"Entregando resultado de orden #{res['id']} a Telegram")
                await app.bot.send_message(
                    chat_id=ALLOWED_CHAT_ID,
                    text=res["result"],
                    parse_mode=ParseMode.MARKDOWN
                )

            # 2. Revisar batería cada 2 minutos (4 ciclos de 30s)
            battery_counter += 1
            if battery_counter >= 4:
                battery_counter = 0
                alert = monitor.check_battery()
                if alert:
                    logger.info(f"Enviando alerta de batería: {alert[:30]}...")
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


def main():
    if not TELEGRAM_BOT_TOKEN or "tu_token" in TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN no configurado en el archivo .env")
        print("\n[ERROR] Por favor define tu TELEGRAM_BOT_TOKEN en el archivo .env\n")
        sys.exit(1)

    print("=" * 60)
    print(f"🤖 INICIANDO {ASSISTANT_NAME} - ASISTENTE PERSONAL EJECUTIVO")
    print("=" * 60)
    print(f"👤 Dueño Autorizado (Telegram Chat ID): {ALLOWED_CHAT_ID}")
    print("💻 Plataforma: Windows (Control de hardware y sistema activo)")
    print("📬 Gmail: Conectado vía IMAP SSL seguro")
    print("📅 Calendario iPhone: Conectado a iCloud (Casa + Trabajo)")
    print("🌦️ Clima: Open-Meteo Bogotá en tiempo real")
    print("🛡️ Proactividad: Alertas automáticas de batería (<20% y 100%)")
    print("📡 Modo de Conexión: Telegram Long-Polling (Costo Cloud: $0.00)")
    print("=" * 60)
    print("⚡ Jarvis está en línea y escuchando órdenes desde tu móvil...\n")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init_callback).build()

    # Registrar rutas y manejadores
    register_handlers(app)

    # Iniciar polling
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
