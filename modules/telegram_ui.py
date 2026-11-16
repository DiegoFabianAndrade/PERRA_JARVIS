"""
Interfaz de Telegram Premium para PERRA_JARVIS.
Implementa navegación intuitiva por categorías, menú táctil,
soporte para fotos/imágenes (Gemini Vision) y atajos rápidos.
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
from modules import weather_service
from modules.proactive_monitor import monitor


def is_authorized(update: Update) -> bool:
    """Verifica si el usuario es Diego."""
    user_id = update.effective_user.id if update.effective_user else None
    return user_id == ALLOWED_CHAT_ID


# =========================================================================
# TECLADOS TÁCTILES POR CATEGORÍA
# =========================================================================

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Menú Principal Maestro: Limpio y organizado por áreas de acción."""
    keyboard = [
        [
            InlineKeyboardButton("☀️ Briefing Ejecutivo Diario", callback_data="menu_briefing")
        ],
        [
            InlineKeyboardButton("💻 Control de PC", callback_data="nav_pc"),
            InlineKeyboardButton("📱 Mi Día & Productividad", callback_data="nav_myday")
        ],
        [
            InlineKeyboardButton("🧑‍💻 Proyectos & Antigravity", callback_data="nav_projects"),
            InlineKeyboardButton("📊 TRM & Finanzas", callback_data="nav_finances")
        ],
        [
            InlineKeyboardButton("💬 WhatsApp Desktop", callback_data="nav_wapp"),
            InlineKeyboardButton("📸 Captura Rápida", callback_data="act_screenshot")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pc_keyboard() -> InlineKeyboardMarkup:
    """Submenú de Control de PC."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Screenshot", callback_data="act_screenshot"),
            InlineKeyboardButton("💻 Telemetría HW", callback_data="act_stats")
        ],
        [
            InlineKeyboardButton("🔒 Bloquear PC", callback_data="act_lock"),
            InlineKeyboardButton("📁 Descargas", callback_data="act_downloads")
        ],
        [
            InlineKeyboardButton("🔊 Vol +", callback_data="act_vol_up"),
            InlineKeyboardButton("🔉 Vol -", callback_data="act_vol_down"),
            InlineKeyboardButton("🔇 Mute", callback_data="act_vol_mute"),
            InlineKeyboardButton("⏯️ Play/Pausa", callback_data="act_play")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_myday_keyboard() -> InlineKeyboardMarkup:
    """Submenú de Productividad y Día a Día."""
    keyboard = [
        [
            InlineKeyboardButton("📧 Bandeja Gmail", callback_data="act_gmail"),
            InlineKeyboardButton("📅 Agenda iPhone", callback_data="act_schedule")
        ],
        [
            InlineKeyboardButton("🌦️ Clima Bogotá", callback_data="act_weather"),
            InlineKeyboardButton("☀️ Briefing Completo", callback_data="menu_briefing")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_finances_keyboard() -> InlineKeyboardMarkup:
    """Submenú Financiero."""
    keyboard = [
        [
            InlineKeyboardButton("💵 TRM & Cripto", callback_data="act_trm"),
            InlineKeyboardButton("📈 Gráfica Dark Mode", callback_data="act_chart")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_projects_keyboard() -> InlineKeyboardMarkup:
    """Submenú de Desarrollo y Antigravity."""
    keyboard = [
        [
            InlineKeyboardButton("📂 Mis Repositorios", callback_data="act_projects"),
            InlineKeyboardButton("📋 Órdenes Pendientes", callback_data="act_orders")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# =========================================================================
# MANEJADORES DE COMANDOS Y NAVEGACIÓN
# =========================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start o /menu: Dashboard interactivo maestro."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido. Este asistente es privado para Diego.")
        return

    welcome_text = (
        f"🤖 *CENTRO DE COMANDO - {ASSISTANT_NAME}*\n"
        "─────────────────────────────\n"
        "Asistente personal ejecutivo conectado en tiempo real.\n\n"
        "✨ *Acceso Rápido:*\n"
        "• Selecciona una categoría táctil abajo.\n"
        "• Escríbeme o envíame una **nota de voz**.\n"
        "• O envíame una **foto** para analizarla con IA.\n"
        "─────────────────────────────"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador central de botones con feedback inmediato."""
    query = update.callback_query
    if not is_authorized(update):
        await query.answer("Acceso no autorizado.", show_alert=True)
        return

    data = query.data
    await query.answer()

    # --- NAVEGACIÓN ENTRE MENÚS ---
    if data == "nav_main":
        await query.edit_message_text(
            f"🤖 *CENTRO DE COMANDO - {ASSISTANT_NAME}*\n"
            "─────────────────────────────\n"
            "Selecciona el módulo que deseas gestionar:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_pc":
        await query.edit_message_text(
            "💻 *CENTRO DE CONTROL - PC WINDOWS*\n"
            "─────────────────────────────\n"
            "Gestiona hardware, capturas, aplicaciones y multimedia:",
            reply_markup=get_pc_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_myday":
        await query.edit_message_text(
            "📱 *MI DÍA & PRODUCTIVIDAD*\n"
            "─────────────────────────────\n"
            "Consulta tus correos, compromisos del calendario y clima:",
            reply_markup=get_myday_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_finances":
        await query.edit_message_text(
            "📊 *MERCADOS & FINANZAS*\n"
            "─────────────────────────────\n"
            "Superfinanciera de Colombia y cotizaciones cripto:",
            reply_markup=get_finances_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_projects":
        await query.edit_message_text(
            "🧑‍💻 *DESARROLLO & ANTIGRAVITY*\n"
            "─────────────────────────────\n"
            "Control remoto de tus proyectos de código y buzón del agente:",
            reply_markup=get_projects_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_wapp":
        msg = whatsapp_controller.get_whatsapp_status_report()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # --- ACCIONES DIRECTAS ---
    elif data == "menu_briefing":
        await query.message.reply_text("⏳ Preparando tu briefing ejecutivo...")
        briefing = monitor.get_executive_briefing()
        await query.message.reply_text(briefing, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_screenshot":
        await query.message.reply_text("📸 Tomando captura de pantalla...")
        shot_path = pc_controller.take_screenshot("telegram_shot.png")
        with open(shot_path, "rb") as f:
            await query.message.reply_photo(photo=f, caption="🖥️ Pantalla actual de tu PC.")

    elif data == "act_stats":
        stats = pc_controller.get_system_stats()
        msg = pc_controller.format_stats_message(stats)
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_lock":
        ok = pc_controller.lock_pc()
        txt = "🔒 Computador bloqueado exitosamente." if ok else "⚠️ No se pudo bloquear el PC."
        await query.message.reply_text(txt)

    elif data == "act_downloads":
        files = pc_controller.list_downloads(6)
        if not files:
            await query.message.reply_text("📁 La carpeta Descargas no tiene archivos recientes.")
        else:
            lines = ["📁 *Archivos recientes en Descargas:*"]
            for f in files:
                lines.append(f"• `{f['name']}` ({f['size_mb']} MB)")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "act_gmail":
        await query.message.reply_text("📬 Consultando Gmail...")
        msg = email_hub.format_emails_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_schedule":
        msg = calendar_hub.format_schedule_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_weather":
        msg = weather_service.format_weather_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_trm":
        msg = market_tracker.format_market_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_chart":
        await query.message.reply_text("📊 Generando gráfica histórica...")
        chart_path = market_tracker.generate_trm_chart("telegram_trm_chart.png", 20)
        if chart_path:
            with open(chart_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption="📈 Historial TRM USD/COP (20 días).")
        else:
            await query.message.reply_text("⚠️ No se pudo generar la gráfica en este momento.")

    elif data == "act_projects":
        projs = antigravity_bridge.list_local_projects()
        if not projs:
            await query.message.reply_text("📁 No se detectaron proyectos.")
        else:
            lines = ["🧑‍💻 *Proyectos en tu PC:*"]
            for p in projs:
                lines.append(f"• `{p}`")
            lines.append("\n💡 Escribe `/status <nombre>` para ver rama Git y commits.")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "act_orders":
        orders = antigravity_bridge.list_pending_orders()
        if not orders:
            await query.message.reply_text("📋 No hay órdenes de código pendientes.")
        else:
            lines = ["📋 *Órdenes pendientes en el buzón:*"]
            for o in orders:
                lines.append(f"• `[#{o['id']}]` {o['order']} ({o['timestamp']})")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "act_vol_up":
        await query.message.reply_text(pc_controller.media_control("up"))
    elif data == "act_vol_down":
        await query.message.reply_text(pc_controller.media_control("down"))
    elif data == "act_vol_mute":
        await query.message.reply_text(pc_controller.media_control("mute"))
    elif data == "act_play":
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

    reply_text = result.get("text", "Orden procesada.")
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


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de fotos enviadas por Diego desde su celular (Visión Multimodal)."""
    if not is_authorized(update):
        return

    photos = update.message.photo
    if not photos:
        return

    caption = update.message.caption
    await update.message.reply_text("👁️ Analizando imagen...")

    # Tomar la foto de mayor resolución
    best_photo = photos[-1]
    photo_file = await best_photo.get_file()
    photo_path = TEMP_DIR / f"input_{best_photo.file_unique_id}.jpg"
    await photo_file.download_to_drive(custom_path=photo_path)

    with open(photo_path, "rb") as f:
        bytes_data = f.read()

    ans = brain.process_photo(bytes_data, caption)
    await update.message.reply_text(ans, parse_mode=ParseMode.MARKDOWN)


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /briefing para reporte diario rápido."""
    if not is_authorized(update):
        return
    await update.message.reply_text("⏳ Preparando tu briefing ejecutivo...")
    msg = monitor.get_executive_briefing()
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def run_cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /run <cmd> para PowerShell remoto."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: `/run <comando>` (ej. `/run ipconfig`)", parse_mode=ParseMode.MARKDOWN)
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
        await update.message.reply_text("Uso: `/orden <instrucción>`\nEjemplo: `/orden Revisa el lab de ARSW y corre las pruebas`", parse_mode=ParseMode.MARKDOWN)
        return

    order_text = " ".join(context.args)
    order = antigravity_bridge.queue_remote_order(order_text)
    await update.message.reply_text(
        f"📝 *Orden registrada en el buzón:*\n\n"
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
    app.add_handler(CommandHandler(["briefing", "resumen"], briefing_command))
    app.add_handler(CommandHandler("run", run_cmd_command))
    app.add_handler(CommandHandler("wapp", wapp_command))
    app.add_handler(CommandHandler("orden", order_command))
    app.add_handler(CommandHandler("status", project_status_command))
    app.add_handler(CommandHandler(["correos", "gmail"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler(["agenda", "calendario"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler("clima", lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler("proyectos", lambda u, c: handle_text_message(u, c)))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
