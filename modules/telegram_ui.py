"""
Interfaz de Telegram Premium para PERRA_JARVIS.
Estructura jerárquica ultra organizada por apartados y sub-apartados:
- Apartado PC (Hardware, Pantalla, Seguridad, Audio, Apps)
- Apartado Antigravity & Repositorios (Órdenes remotas interactivas con selector de repo)
- Apartado Mi Día & Productividad (Gmail, Calendario iPhone, Clima)
- Apartado Finanzas (TRM, Criptos, Gráficas)
- Apartado WhatsApp Desktop
"""

from pathlib import Path
from typing import Dict, Any, Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.constants import ParseMode, ChatAction
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
from modules import reminder_service
from modules import remote_test_runner as test_runner
from modules import git_agent
from modules import document_analyzer
from modules.proactive_monitor import monitor

# Memoria temporal de selección de repositorio por usuario
USER_SELECTED_REPO: Dict[int, str] = {}


def is_authorized(update: Update) -> bool:
    """Verifica si el usuario es Diego."""
    user_id = update.effective_user.id if update.effective_user else None
    return user_id == ALLOWED_CHAT_ID


# =========================================================================
# TECLADOS TÁCTILES ORGANIZADOS POR APARTADOS
# =========================================================================

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Menú Maestro: Apartados principales limpios y ejecutivos."""
    keyboard = [
        [
            InlineKeyboardButton("☀️ Briefing Ejecutivo Diario", callback_data="act_briefing")
        ],
        [
            InlineKeyboardButton("💻 Apartado PC", callback_data="nav_pc"),
            InlineKeyboardButton("📱 Mi Día & Productividad", callback_data="nav_myday")
        ],
        [
            InlineKeyboardButton("🧑‍💻 Antigravity & Repos", callback_data="nav_projects"),
            InlineKeyboardButton("📊 Finanzas & TRM", callback_data="nav_finances")
        ],
        [
            InlineKeyboardButton("💬 WhatsApp Desktop", callback_data="nav_wapp"),
            InlineKeyboardButton("📸 Captura Rápida", callback_data="act_pc_screenshot")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pc_keyboard() -> InlineKeyboardMarkup:
    """Apartado PC con sus sub-apartados organizados."""
    keyboard = [
        # Sub-apartado 1: Hardware y Pantalla
        [
            InlineKeyboardButton("🔋 Telemetría HW", callback_data="act_pc_stats"),
            InlineKeyboardButton("📸 Captura Pantalla", callback_data="act_pc_screenshot")
        ],
        # Sub-apartado 2: Seguridad y Archivos
        [
            InlineKeyboardButton("🔒 Bloquear PC", callback_data="act_pc_lock"),
            InlineKeyboardButton("📁 Ver Descargas", callback_data="act_pc_downloads")
        ],
        # Sub-apartado 3: Control Multimedia
        [
            InlineKeyboardButton("🔊 Vol +", callback_data="act_pc_vol_up"),
            InlineKeyboardButton("🔉 Vol -", callback_data="act_pc_vol_down"),
            InlineKeyboardButton("🔇 Mute", callback_data="act_pc_vol_mute"),
            InlineKeyboardButton("⏯️ Play/Pausa", callback_data="act_pc_play")
        ],
        # Sub-apartado 4: Lanzador de Aplicaciones
        [
            InlineKeyboardButton("🎵 Spotify", callback_data="act_pc_app_spotify"),
            InlineKeyboardButton("🌐 Chrome", callback_data="act_pc_app_chrome"),
            InlineKeyboardButton("💻 VS Code", callback_data="act_pc_app_vscode")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_myday_keyboard() -> InlineKeyboardMarkup:
    """Apartado Mi Día & Productividad."""
    keyboard = [
        [
            InlineKeyboardButton("📧 Bandeja Gmail", callback_data="act_myday_gmail"),
            InlineKeyboardButton("📅 Agenda (Google & iPhone)", callback_data="act_myday_schedule")
        ],
        [
            InlineKeyboardButton("🔔 Mis Recordatorios", callback_data="act_myday_reminders"),
            InlineKeyboardButton("🌦️ Clima Bogotá", callback_data="act_myday_weather")
        ],
        [
            InlineKeyboardButton("☀️ Briefing Completo", callback_data="act_briefing")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_finances_keyboard() -> InlineKeyboardMarkup:
    """Apartado Finanzas & Mercados."""
    keyboard = [
        [
            InlineKeyboardButton("💵 TRM Oficial USD/COP", callback_data="act_fin_trm"),
            InlineKeyboardButton("💎 Criptomonedas", callback_data="act_fin_crypto")
        ],
        [
            InlineKeyboardButton("📈 Gráfica Histórica Dark Mode", callback_data="act_fin_chart")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_projects_keyboard() -> InlineKeyboardMarkup:
    """Apartado Antigravity & Repositorios."""
    keyboard = [
        [
            InlineKeyboardButton("🎯 Enviar Orden al Agente", callback_data="nav_select_repo"),
            InlineKeyboardButton("🧪 Correr Pruebas", callback_data="act_proj_test")
        ],
        [
            InlineKeyboardButton("📂 Lista de Repositorios", callback_data="act_proj_list"),
            InlineKeyboardButton("🐙 Estado Git & Commits", callback_data="act_proj_status")
        ],
        [
            InlineKeyboardButton("📋 Órdenes y Resultados", callback_data="act_proj_orders")
        ],
        [
            InlineKeyboardButton("« Volver al Menú Principal", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_repo_selector_keyboard() -> InlineKeyboardMarkup:
    """Submenú interactivo para elegir a qué repositorio va dirigida la orden."""
    projs = antigravity_bridge.list_local_projects()
    # Tomar los proyectos principales
    keyboard = []
    # Priorizar proyectos conocidos
    priority = ["PERRA_JARVIS", "ARSW_LOAD-BALANCING_AZURE_II_ANDRADE_MELO", "PROYECTO-PTIA-STYLEAI-DIEGO-ANDRADE", "telegram-dollar-bot"]
    available_priority = [p for p in priority if p in projs]
    other_projs = [p for p in projs if p not in available_priority][:4]
    display_repos = available_priority + other_projs

    for i in range(0, len(display_repos), 2):
        row = []
        for r in display_repos[i:i+2]:
            short_name = r[:18]
            row.append(InlineKeyboardButton(f"📦 {short_name}", callback_data=f"selrepo_{r}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("« Volver a Proyectos", callback_data="nav_projects")])
    return InlineKeyboardMarkup(keyboard)


# =========================================================================
# MANEJADORES DE RUTAS Y NAVEGACIÓN
# =========================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start o /menu: Dashboard principal organizado."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido. Este asistente es privado para Diego.")
        return

    welcome_text = (
        f"🤖 *CENTRO DE COMANDO - {ASSISTANT_NAME}*\n"
        "─────────────────────────────\n"
        "Asistente personal ejecutivo conectado a tu ecosistema.\n\n"
        "📂 *Selecciona un apartado para operar:*\n"
        "• *💻 Apartado PC:* Control de Windows, hardware, pantalla y apps.\n"
        "• *📱 Mi Día:* Gmail, Calendarios iPhone (Casa + Trabajo) y Clima.\n"
        "• *🧑‍💻 Antigravity:* Envía órdenes a este chat para el repo que elijas.\n"
        "• *📊 Finanzas:* TRM oficial Colombia, criptos y gráficas.\n"
        "• *💬 WhatsApp:* Despacho de mensajes remotos.\n"
        "─────────────────────────────"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador central de botones y navegación entre apartados."""
    query = update.callback_query
    if not is_authorized(update):
        await query.answer("Acceso no autorizado.", show_alert=True)
        return

    data = query.data
    await query.answer()

    # 1. Navegación Principal
    if data == "nav_main":
        await query.edit_message_text(
            f"🤖 *CENTRO DE COMANDO - {ASSISTANT_NAME}*\n"
            "─────────────────────────────\n"
            "Selecciona el apartado que deseas gestionar:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_pc":
        await query.edit_message_text(
            "💻 *APARTADO: CONTROL TOTAL DE TU PC WINDOWS*\n"
            "─────────────────────────────\n"
            "Sub-apartados disponibles:\n"
            "• *Hardware:* Telemetría y estado de batería.\n"
            "• *Pantalla & Archivos:* Captura de pantalla y descargas.\n"
            "• *Seguridad:* Bloqueo inmediato de sesión.\n"
            "• *Multimedia & Apps:* Volumen, Spotify, Chrome, Code.",
            reply_markup=get_pc_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_myday":
        await query.edit_message_text(
            "📱 *APARTADO: MI DÍA & PRODUCTIVIDAD*\n"
            "─────────────────────────────\n"
            "Sub-apartados disponibles:\n"
            "• *Gmail:* Bandeja de entrada oficial (`diegofabian105@gmail.com`).\n"
            "• *Calendario iPhone:* Eventos de Casa y Trabajo combinados.\n"
            "• *Clima:* Pronóstico en tiempo real de Bogotá.\n"
            "• *Briefing:* Resumen completo de la jornada.",
            reply_markup=get_myday_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_finances":
        await query.edit_message_text(
            "📊 *APARTADO: FINANZAS & MERCADOS*\n"
            "─────────────────────────────\n"
            "Sub-apartados disponibles:\n"
            "• *TRM USD/COP:* Superfinanciera de Colombia.\n"
            "• *Criptos:* Bitcoin, Ethereum y Solana 24h.\n"
            "• *Gráfica:* Histórico 20 días en formato PNG.",
            reply_markup=get_finances_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_projects":
        await query.edit_message_text(
            "🧑‍💻 *APARTADO: ANTIGRAVITY & REPOSITORIOS*\n"
            "─────────────────────────────\n"
            "Conexión directa con este chat y tus repositorios:\n"
            "• *🎯 Enviar Orden:* Elige un repositorio y dale una tarea al agente.\n"
            "• *📂 Repos:* Explora los proyectos en tu computador.\n"
            "• *🌿 Git:* Consulta la rama y cambios pendientes.\n"
            "• *📋 Órdenes:* Historial de tareas pendientes.",
            reply_markup=get_projects_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_select_repo":
        await query.edit_message_text(
            "🎯 *ELIGE EL REPOSITORIO DESTINO PARA TU ORDEN:*\n"
            "─────────────────────────────\n"
            "Toca el repositorio al cual quieres enviar la instrucción:",
            reply_markup=get_repo_selector_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("selrepo_"):
        repo_name = data[8:]
        user_id = query.from_user.id
        USER_SELECTED_REPO[user_id] = repo_name
        await query.message.reply_text(
            f"🎯 *Repositorio Seleccionado:* `{repo_name}`\n"
            "─────────────────────────────\n"
            "Ahora escribe tu orden directamente en el chat, o usa:\n"
            f"`/orden {repo_name} <tu instrucción>`\n\n"
            "Ejemplo: `Revisa si hay errores en el código y corre los tests`\n"
            "─────────────────────────────",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "nav_wapp":
        msg = whatsapp_controller.get_whatsapp_status_report()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # 2. Acciones del Apartado PC
    elif data == "act_pc_screenshot":
        await query.message.reply_text("📸 Tomando captura de pantalla...")
        shot_path = pc_controller.take_screenshot("telegram_shot.png")
        with open(shot_path, "rb") as f:
            await query.message.reply_photo(photo=f, caption="🖥️ Pantalla actual de tu PC.")

    elif data == "act_pc_stats":
        stats = pc_controller.get_system_stats()
        msg = pc_controller.format_stats_message(stats)
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_pc_lock":
        ok = pc_controller.lock_pc()
        txt = "🔒 Computador bloqueado exitosamente." if ok else "⚠️ No se pudo bloquear el PC."
        await query.message.reply_text(txt)

    elif data == "act_pc_downloads":
        files = pc_controller.list_downloads(6)
        if not files:
            await query.message.reply_text("📁 La carpeta Descargas no tiene archivos recientes.")
        else:
            lines = ["📁 *Archivos recientes en Descargas:*"]
            for f in files:
                lines.append(f"• `{f['name']}` ({f['size_mb']} MB)")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "act_pc_vol_up":
        await query.message.reply_text(pc_controller.media_control("up"))
    elif data == "act_pc_vol_down":
        await query.message.reply_text(pc_controller.media_control("down"))
    elif data == "act_pc_vol_mute":
        await query.message.reply_text(pc_controller.media_control("mute"))
    elif data == "act_pc_play":
        await query.message.reply_text(pc_controller.media_control("play"))
    elif data == "act_pc_app_spotify":
        await query.message.reply_text(pc_controller.open_application("spotify"))
    elif data == "act_pc_app_chrome":
        await query.message.reply_text(pc_controller.open_application("chrome"))
    elif data == "act_pc_app_vscode":
        await query.message.reply_text(pc_controller.open_application("code"))

    # 3. Acciones de Mi Día
    elif data == "act_myday_gmail":
        await query.message.reply_text("📬 Consultando Gmail...")
        msg = email_hub.format_emails_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_myday_schedule":
        msg = calendar_hub.format_schedule_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_myday_reminders":
        msg = reminder_service.format_active_reminders()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_myday_weather":
        msg = weather_service.format_weather_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_briefing":
        await query.message.reply_text("⏳ Preparando tu briefing ejecutivo...")
        briefing = monitor.get_executive_briefing()
        await query.message.reply_text(briefing, parse_mode=ParseMode.MARKDOWN)

    # 4. Acciones de Finanzas
    elif data == "act_fin_trm":
        msg = market_tracker.format_market_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_fin_crypto":
        msg = market_tracker.format_market_summary()
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_fin_chart":
        await query.message.reply_text("📊 Generando gráfica histórica...")
        chart_path = market_tracker.generate_trm_chart("telegram_trm_chart.png", 20)
        if chart_path:
            with open(chart_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption="📈 Historial TRM USD/COP (20 días).")
        else:
            await query.message.reply_text("⚠️ No se pudo generar la gráfica.")

    # 5. Acciones de Proyectos
    elif data == "act_proj_list":
        projs = antigravity_bridge.list_local_projects()
        lines = ["📂 *Tus Repositorios en el PC:*"]
        for p in projs:
            lines.append(f"• `{p}`")
        lines.append("\n💡 Toca 'Enviar Orden' para dar una tarea sobre cualquiera de ellos.")
        await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    elif data == "act_proj_status":
        user_id = query.from_user.id
        target = USER_SELECTED_REPO.get(user_id, "PERRA_JARVIS")
        res = git_agent.get_repo_overview(target)
        await query.message.reply_text(res, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_proj_test":
        user_id = query.from_user.id
        target = USER_SELECTED_REPO.get(user_id, "Lab_P1_BluePrints_Java21_API_Andrade_Melo")
        await query.message.reply_text(f"⏳ Ejecutando pruebas unitarias en `{target}`...")
        res = test_runner.run_project_tests(target)
        report = test_runner.format_test_report(res)
        await query.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

    elif data == "act_proj_orders":
        orders = antigravity_bridge.list_pending_orders()
        if not orders:
            await query.message.reply_text("📋 No hay órdenes pendientes en el buzón. Todo al día.")
        else:
            lines = ["📋 *Órdenes pendientes en el buzón del agente:*"]
            for o in orders:
                lines.append(f"• `[#{o['id']}]` *Repo:* `{o['repo']}`\n  Tarea: _{o['order']}_\n  📅 {o['timestamp']}")
            await query.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# =========================================================================
# MANEJADORES DE MENSAJES Y COMANDOS
# =========================================================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto en lenguaje natural."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso restringido.")
        return

    user_text = update.message.text
    user_id = update.effective_user.id
    q_lower = user_text.lower().strip()

    # Detección de solicitud de menú en cualquier variación de lenguaje natural
    menu_triggers = [
        "menu", "menú", "/menu", "/start", "opciones", "panel", "dashboard",
        "muestrame el menu", "muéstrame el menú", "muestra el menu", "muestra el menú",
        "ver menu", "ver menú", "dame el menu", "dame el menú", "abrir menu", "abrir menú",
        "menu de opciones", "menú de opciones", "pon el menu", "pon el menú"
    ]
    if q_lower in menu_triggers or any(t in q_lower for t in ["muestrame el menu", "muéstrame el menú", "ver menú", "ver menu", "menu de opciones", "menú de opciones"]):
        await start_command(update, context)
        return

    # Detección inteligente de enlaces de calendario (.ics / Google / iCloud)
    if any(k in q_lower for k in ["calendar.google.com", "caldav.icloud.com", ".ics"]) and any(q_lower.startswith(p) for p in ["http://", "https://", "webcal://"]):
        is_google = "google" in q_lower
        calendar_hub.update_calendar_url(user_text, is_google=is_google)
        cal_type = "Google Calendar" if is_google else "iCloud Calendar"
        await update.message.reply_text(
            f"📅 *¡{cal_type.upper()} VINCULADO CON ÉXITO!*\n"
            "─────────────────────────────\n"
            f"✅ Enlace registrado y guardado en tu configuración.\n"
            f"Ahora PERRA_JARVIS leerá tus eventos en tiempo real en `/agenda` y en tu briefing matutino.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Si el usuario seleccionó un repositorio recientemente y su mensaje parece una orden de código
    if user_id in USER_SELECTED_REPO:
        selected_repo = USER_SELECTED_REPO.pop(user_id)
        # Registrar como orden remota para el agente
        order = antigravity_bridge.queue_remote_order(user_text, selected_repo)
        await update.message.reply_text(
            f"🎯 *ORDEN ENVIADA A ESTE CHAT / AGENTE*\n"
            "─────────────────────────────\n"
            f"📦 *Repositorio:* `{selected_repo}`\n"
            f"📝 *Instrucción:* _{order['order']}_\n"
            f"🆔 *ID:* `#{order['id']}`\n"
            f"🚦 *Estado:* `PENDIENTE EN COLA`\n\n"
            f"El agente en tu PC la tomará directamente en el workspace.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Visual feedback inmediato (Escribiendo...)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    result = brain.process_text(user_text)

    if result.get("action") == "SHOW_MENU":
        await start_command(update, context)
        return

    if "photo" in result and result["photo"]:
        photo_path = Path(result["photo"])
        caption = result.get("text", "")
        if photo_path.exists():
            with open(photo_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption=caption)
                return

    reply_text = result.get("text", "Orden procesada.")
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)

    if "voice" in result and result["voice"]:
        v_path = Path(result["voice"])
        if v_path.exists():
            with open(v_path, "rb") as vf:
                await update.message.reply_voice(voice=vf)


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

    reply_text = result.get("text", "Nota de voz procesada.")
    markup = get_main_keyboard() if any(m in reply_text.lower() for m in ["menú", "menu", "opciones"]) else None
    await update.message.reply_text(reply_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

    if "voice" in result and result["voice"]:
        v_path = Path(result["voice"])
        if v_path.exists():
            with open(v_path, "rb") as vf:
                await update.message.reply_voice(voice=vf)


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de fotos enviadas por Diego desde su celular (Visión Multimodal)."""
    if not is_authorized(update):
        return

    photos = update.message.photo
    if not photos:
        return

    caption = update.message.caption
    await update.message.reply_text("👁️ Analizando imagen...")

    best_photo = photos[-1]
    photo_file = await best_photo.get_file()
    photo_path = TEMP_DIR / f"input_{best_photo.file_unique_id}.jpg"
    await photo_file.download_to_drive(custom_path=photo_path)

    with open(photo_path, "rb") as f:
        bytes_data = f.read()

    ans = brain.process_photo(bytes_data, caption)
    await update.message.reply_text(ans, parse_mode=ParseMode.MARKDOWN)


async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /orden [repo] <instrucción>
    Ejemplo: /orden PERRA_JARVIS agrega tal función
    o: /orden ARSW revisa los balanceadores de carga
    """
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: `/orden <repositorio> <instrucción>`\n"
            "O usa el botón táctil **🎯 Enviar Orden al Agente**.\n\n"
            "Ejemplo:\n`/orden ARSW_LOAD-BALANCING_AZURE_II_ANDRADE_MELO Corre las pruebas del lab`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Si el primer argumento es un repo conocido
    possible_repo = context.args[0]
    local_repos = antigravity_bridge.list_local_projects()

    if possible_repo in local_repos:
        repo_name = possible_repo
        order_text = " ".join(context.args[1:])
    else:
        # Si no especifica repo, usar PERRA_JARVIS
        repo_name = "PERRA_JARVIS"
        order_text = " ".join(context.args)

    if not order_text:
        await update.message.reply_text(f"Indica qué instrucción deseas ejecutar en `{repo_name}`.")
        return

    order = antigravity_bridge.queue_remote_order(order_text, repo_name)
    await update.message.reply_text(
        f"🎯 *ORDEN ENVIADA A ESTE CHAT / AGENTE:*\n"
        "─────────────────────────────\n"
        f"📦 *Repositorio:* `{order['repo']}`\n"
        f"📝 *Instrucción:* _{order['order']}_\n"
        f"🆔 *ID:* `#{order['id']}`\n"
        f"🚦 *Estado:* `PENDIENTE EN COLA`\n\n"
        f"La tomaré y ejecutaré directamente aquí en tu máquina.",
        parse_mode=ParseMode.MARKDOWN
    )


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /briefing para reporte diario rápido."""
    if not is_authorized(update):
        return
    await update.message.reply_text("⏳ Preparando tu briefing ejecutivo...")
    msg = monitor.get_executive_briefing()
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


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


async def project_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status <proyecto> para ver el estado Git de un proyecto."""
    if not is_authorized(update):
        return

    p_name = context.args[0] if context.args else "PERRA_JARVIS"
    res = git_agent.get_repo_overview(p_name)
    await update.message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


async def test_runner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /test <proyecto> para ejecutar pruebas unitarias."""
    if not is_authorized(update):
        return

    p_name = context.args[0] if context.args else "Lab_P1_BluePrints_Java21_API_Andrade_Melo"
    await update.message.reply_text(f"⏳ Ejecutando pruebas unitarias en `{p_name}`...")
    res = test_runner.run_project_tests(p_name)
    report = test_runner.format_test_report(res)
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)


async def handle_document_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de documentos, PDFs y archivos enviados por Diego."""
    if not is_authorized(update):
        return

    doc = update.message.document
    if not doc:
        return

    caption = update.message.caption or ""
    await update.message.reply_text(f"📑 Analizando `{doc.file_name}` con Gemini...")

    file_obj = await doc.get_file()
    dest_path = TEMP_DIR / doc.file_name
    await file_obj.download_to_drive(custom_path=dest_path)

    analysis = document_analyzer.analyze_document_file(dest_path, prompt_override=caption)
    await update.message.reply_text(analysis, parse_mode=ParseMode.MARKDOWN)


def register_handlers(app):
    """Registra todos los comandos y manejadores."""
    app.add_handler(CommandHandler(["start", "menu"], start_command))
    app.add_handler(CommandHandler(["briefing", "resumen"], briefing_command))
    app.add_handler(CommandHandler("orden", order_command))
    app.add_handler(CommandHandler(["status", "git"], project_status_command))
    app.add_handler(CommandHandler(["test", "tests"], test_runner_command))
    app.add_handler(CommandHandler("wapp", wapp_command))
    app.add_handler(CommandHandler(["correos", "gmail"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler(["agenda", "calendario"], lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler("clima", lambda u, c: handle_text_message(u, c)))
    app.add_handler(CommandHandler("proyectos", lambda u, c: handle_text_message(u, c)))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
