"""
Interfaz de Telegram para PERRA_JARVIS.
Implementa:
- Menú táctil con botones interactivos expandidos.
- Whitelist de seguridad para Diego (Chat ID: 1257398092).
- Soporte para Correo (Gmail/Outlook), Calendario iPhone, WhatsApp y Proyectos.
"""

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
from modules import antigravity_bridge
from modules import email_hub
from modules import calendar_hub
from modules import whatsapp_controller


def is_authorized(update: Update) -> bool:
    """Verifica si el usuario es el dueño autorizado (Diego)."""
    user_id = update.effective_user.id if update.effective_user else None
    return user_id == ALLOWED_CHAT_ID


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Construye el teclado táctil maestro de Jarvis."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Pantallazo PC", callback_data="btn_screenshot"),
            InlineKeyboardButton("💻 Telemetría PC", callback_data="btn_stats")
        ],
        [
            InlineKeyboardButton("📧 Correos Gmail", callback_data="btn_emails"),
            InlineKeyboardButton("📅 Agenda iPhone", callback_data="btn_schedule")
        ],
        [
            InlineKeyboardButton("🧑‍💻 Mis Proyectos IDE", callback_data="btn_projects"),
            InlineKeyboardButton("💬 WhatsApp Desktop", callback_data="btn_wapp")
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
        await update.message.reply_text("⛔ Acceso restringido. Este asistente es privado para Diego.")
        return

    welcome_text = (
        f"🤖 *¡Hola, Diego! Soy {ASSISTANT_NAME}*\n"
        "─────────────────────────────\n"
        "Tu asistente personal ejecutor con control total de tu PC, correos, agenda y proyectos.\n\n"
        "✨ *Acciones directas disponibles:*\n"
        "• Toca cualquiera de los **botones táctiles** abajo.\n"
        "• Mándame una **nota de voz** o escríbeme cualquier orden.\n"
        "• Escribe `/orden <texto>` para enviarme instrucciones remotas al código.\n"
        "• Escribe `/wapp <número> <mensaje>` para enviar un WhatsApp desde el PC.\n"
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

    elif data == "btn_emails":
        await query.message.reply_text("📬 Consultando bandejas de entrada...")
        msg = email_hub.format_emails_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_schedule":
        msg = calendar_hub.format_schedule_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_projects":
        projs = antigravity_bridge.list_local_projects()
        if not projs:
            await query.message.reply_text("📁 No se detectaron proyectos en la carpeta Descargas.")
        else:
            lines = ["🧑‍💻 *Proyectos de desarrollo en tu PC:*"]
            for p in projs:
                lines.append(f"• `/proyecto_{p[:20]}` -> `{p}`")
            lines.append("\n💡 Escribe `/status <nombre>` para ver rama Git y commits.")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_wapp":
        msg = whatsapp_controller.get_whatsapp_status_report()
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
        await query.message.reply_text(pc_controller.media_control("up"))

    elif data == "btn_vol_down":
        await query.message.reply_text(pc_controller.media_control("down"))

    elif data == "btn_vol_mute":
        await query.message.reply_text(pc_controller.media_control("mute"))

    elif data == "btn_play":
        await query.message.reply_text(pc_controller.media_control("play"))


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto en lenguaje natural."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido.")
        return

    user_text = update.message.text
    result = brain.process_text(user_text)

    if "photo" in result and result["photo"]:
        photo_path = Path(result["photo"])
        caption = result.get("text", "")
        if photo_path.exists():
            with open(photo_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=caption)
                return

    reply_text = result.get("text", "Orden recibida.")
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de notas de voz de Diego."""
    if not is_authorized(update):
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
    """Comando /run <cmd> para PowerShell remoto."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: `/run <comando>` (ej. `/run ipconfig` o `/run dir`)", parse_mode=ParseMode.MARKDOWN)
        return

    cmd = " ".join(context.args)
    await update.message.reply_text(f"⏳ Ejecutando: `{cmd}`...", parse_mode=ParseMode.MARKDOWN)
    output = pc_controller.run_command(cmd)
    await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)


async def wapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /wapp <numero> <mensaje> para despachar WhatsApp."""
    if not is_authorized(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: `/wapp <número> <mensaje>`\nEjemplo: `/wapp 3101234567 Hola, ya voy en camino`", parse_mode=ParseMode.MARKDOWN)
        return

    phone = context.args[0]
    msg = " ".join(context.args[1:])
    result = whatsapp_controller.send_whatsapp_message(phone, msg)
    await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)


async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /orden <texto> para registrar tareas en el buzón del agente."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: `/orden <instrucción para tu proyecto>`\nEjemplo: `/orden Revisa el lab de ARSW y corre las pruebas`", parse_mode=ParseMode.MARKDOWN)
        return

    order_text = " ".join(context.args)
    order = antigravity_bridge.queue_remote_order(order_text)
    await update.message.reply_text(
        f"📝 *Orden registrada en el buzón del agente:*\n\n"
        f"• *ID:* `{order['id']}`\n"
        f"• *Orden:* _{order['order']}_\n"
        f"• *Estado:* `PENDIENTE`\n\n"
        f"Tu entorno de desarrollo la tomará automáticamente.",
        parse_mode=ParseMode.MARKDOWN
    )


async def project_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status <proyecto> para ver el estado Git de un proyecto."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: `/status <nombre_del_proyecto>`", parse_mode=ParseMode.MARKDOWN)
        return

    p_name = context.args[0]
    res = antigravity_bridge.get_project_status(p_name)
    await update.message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


def register_handlers(app):
    """Registra todos los comandos y manejadores."""
    app.add_handler(CommandHandler(["start", "menu"], start_command))
    app.add_handler(CommandHandler("run", run_cmd_command))
    app.add_handler(CommandHandler("wapp", wapp_command))
    app.add_handler(CommandHandler("orden", order_command))
    app.add_handler(CommandHandler("status", project_status_command))
    app.add_handler(CommandHandler(["correos", "email"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler(["agenda", "calendario"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler("proyectos", lambda u, c: handle_text_message(u, c)))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
