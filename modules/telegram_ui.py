"""
Interfaz de Telegram para PERRA_JARVIS.
Implementa:
- Menú táctil con botones interactivos (Inline Keyboards).
- Filtro estricto de seguridad (Whitelist Chat ID de Diego).
- Procesamiento de texto libre, comandos y notas de voz.
- Envío dinámico de capturas de pantalla y gráficos.
"""

import os
from pathlib import Path
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import ALLOWED_CHAT_ID, ASSISTANT_NAME, TEMP_DIR
from modules.ai_brain import brain
from modules import pc_controller
from modules import market_tracker


def is_authorized(update: Update) -> bool:
    """Verifica si el usuario es el dueño autorizado (Diego)."""
    user_id = update.effective_user.id if update.effective_user else None
    return user_id == ALLOWED_CHAT_ID


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Construye el teclado táctil principal de Jarvis."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Pantallazo PC", callback_data="btn_screenshot"),
            InlineKeyboardButton("💻 Telemetría", callback_data="btn_stats")
        ],
        [
            InlineKeyboardButton("💵 TRM & Cripto", callback_data="btn_trm"),
            InlineKeyboardButton("📈 Gráfica TRM", callback_data="btn_chart")
        ],
        [
            InlineKeyboardButton("📁 Descargas", callback_data="btn_downloads"),
            InlineKeyboardButton("🔒 Bloquear PC", callback_data="btn_lock")
        ],
        [
            InlineKeyboardButton("🔊 Vol +", callback_data="btn_vol_up"),
            InlineKeyboardButton("🔉 Vol -", callback_data="btn_vol_down"),
            InlineKeyboardButton("🔇 Mute", callback_data="btn_vol_mute"),
            InlineKeyboardButton("⏯️ Play/Pausa", callback_data="btn_play")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /start o /menu."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido. Este asistente es personal y privado.")
        return

    welcome_text = (
        f"🤖 *¡Hola, Diego! Soy {ASSISTANT_NAME}*\n"
        "─────────────────────────────\n"
        "Estoy conectado directamente a tu computador Windows y listo para tus órdenes.\n\n"
        "✨ *¿Qué puedes hacer?*\n"
        "• Toca cualquiera de los **botones táctiles** abajo.\n"
        "• Escríbeme cualquier orden en **lenguaje natural**.\n"
        "• O envíame una **nota de voz** desde la calle.\n"
        "─────────────────────────────"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de los clics en los botones táctiles."""
    query = update.callback_query
    if not is_authorized(update):
        await query.answer("Acceso no autorizado.", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "btn_screenshot":
        await query.message.reply_text("📸 Tomando captura de pantalla...")
        shot_path = pc_controller.take_screenshot("telegram_shot.png")
        with open(shot_path, "rb") as f:
            await query.message.reply_photo(photo=f, caption="🖥️ Pantalla actual de tu PC.")

    elif data == "btn_stats":
        stats = pc_controller.get_system_stats()
        msg = pc_controller.format_stats_message(stats)
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_trm":
        msg = market_tracker.format_market_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_chart":
        await query.message.reply_text("📊 Generando gráfica histórica...")
        chart_path = market_tracker.generate_trm_chart("telegram_trm_chart.png", 20)
        if chart_path:
            with open(chart_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption="📈 Historial TRM USD/COP (20 días).")
        else:
            await query.message.reply_text("⚠️ No se pudo generar la gráfica en este momento.")

    elif data == "btn_downloads":
        files = pc_controller.list_downloads(6)
        if not files:
            await query.message.reply_text("📁 La carpeta Descargas no tiene archivos recientes.")
        else:
            lines = ["📁 *Archivos recientes en Descargas:*"]
            for f in files:
                lines.append(f"• `{f['name']}` ({f['size_mb']} MB)")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_lock":
        ok = pc_controller.lock_pc()
        txt = "🔒 Computador bloqueado exitosamente." if ok else "⚠️ No se pudo bloquear el PC."
        await query.message.reply_text(txt)

    elif data == "btn_vol_up":
        res = pc_controller.media_control("up")
        await query.message.reply_text(res)

    elif data == "btn_vol_down":
        res = pc_controller.media_control("down")
        await query.message.reply_text(res)

    elif data == "btn_vol_mute":
        res = pc_controller.media_control("mute")
        await query.message.reply_text(res)

    elif data == "btn_play":
        res = pc_controller.media_control("play")
        await query.message.reply_text(res)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto en lenguaje natural."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido.")
        return

    user_text = update.message.text
    # Procesar con el cerebro
    result = brain.process_text(user_text)

    # Si la respuesta incluye una foto (captura o gráfica)
    if "photo" in result and result["photo"]:
        photo_path = Path(result["photo"])
        caption = result.get("text", "")
        if photo_path.exists():
            with open(photo_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=caption)
                return

    # Si es solo texto
    reply_text = result.get("text", "Orden recibida.")
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de notas de voz enviadas por Diego."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido.")
        return

    voice = update.message.voice
    if not voice:
        return

    await update.message.reply_text("🎙️ Escuchando tu nota de voz...")
    voice_file = await voice.get_file()
    voice_path = TEMP_DIR / f"voice_{voice.file_unique_id}.ogg"
    await voice_file.download_to_drive(custom_path=voice_path)

    result = brain.process_voice_file(voice_path)

    if "photo" in result and result["photo"]:
        photo_path = Path(result["photo"])
        if photo_path.exists():
            with open(photo_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=result.get("text", ""))
                return

    await update.message.reply_text(result.get("text", "Nota de voz procesada."), parse_mode=ParseMode.MARKDOWN)


async def run_cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /run <comando> para ejecutar PowerShell remoto."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: `/run <comando>` (ej. `/run dir` o `/run ipconfig`)", parse_mode=ParseMode.MARKDOWN)
        return

    cmd = " ".join(context.args)
    await update.message.reply_text(f"⏳ Ejecutando en tu PC: `{cmd}`...", parse_mode=ParseMode.MARKDOWN)
    output = pc_controller.run_command(cmd)
    await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)


def register_handlers(app):
    """Registra todos los comandos y manejadores en la aplicación de Telegram."""
    app.add_handler(CommandHandler(["start", "menu"], start_command))
    app.add_handler(CommandHandler("run", run_cmd_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
