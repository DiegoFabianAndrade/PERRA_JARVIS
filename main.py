"""
Punto de entrada principal para PERRA_JARVIS.
Inicia el bot asíncrono de Telegram con long polling y control local de Windows.
"""

import sys
import logging
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ASSISTANT_NAME, DEBUG
from modules.telegram_ui import register_handlers

# Configuración de logs
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=log_level
)
logger = logging.getLogger(ASSISTANT_NAME)


def main():
    if not TELEGRAM_BOT_TOKEN or "tu_token" in TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN no configurado en el archivo .env")
        print("\n[ERROR] Por favor define tu TELEGRAM_BOT_TOKEN en el archivo .env\n")
        sys.exit(1)

    print("=" * 60)
    print(f"🤖 INICIANDO {ASSISTANT_NAME} - ASISTENTE PERSONAL INTELIGENTE")
    print("=" * 60)
    print(f"👤 Dueño Autorizado (Telegram Chat ID): {ALLOWED_CHAT_ID}")
    print("💻 Plataforma: Windows (Control de hardware y sistema activo)")
    print("🧠 Cerebro: Híbrido (Gemini 2.5 Flash + Parser Semántico)")
    print("📡 Modo de Conexión: Telegram Long-Polling (Costo Cloud: $0.00)")
    print("=" * 60)
    print("⚡ Jarvis está en línea y escuchando órdenes desde tu móvil...\n")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar rutas y manejadores
    register_handlers(app)

    # Iniciar polling
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
