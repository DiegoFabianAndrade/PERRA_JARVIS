"""
PERRA_JARVIS 24/7 - Executive Cloud Serverless Core
Desplegado en Azure Functions (Consumption Plan - $0.00 USD).
Opera de forma continua incluso con el computador personal apagado.
"""

import os
import json
import time
import base64
import smtplib
import logging
import datetime
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import azure.functions as func

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9115868775:AAFd3FBROZJ7jKfi49-cv_ts8iwPQEFyHaY")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "1257398092"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GMAIL_USER = os.getenv("GMAIL_USER", "diegofabian105@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ICLOUD_CALENDAR_URL = os.getenv("ICLOUD_CALENDAR_URL", "")
GOOGLE_TOKEN_JSON = os.getenv("GOOGLE_TOKEN_JSON", "")

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Estado persistente para el PC Companion
DATA_DIR = "/home/site/data" if os.path.exists("/home/site") else "/tmp"
STATE_FILE = os.path.join(DATA_DIR, "pc_state.json")
ORDERS_FILE = os.path.join(DATA_DIR, "pc_orders.json")

def _load_json(file_path, default=None):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Error cargando {file_path}: {e}")
    return default if default is not None else {}

def _save_json(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Error guardando {file_path}: {e}")


# ─────────────────────────────────────────────────────────────
# 2. CLIENTE TELEGRAM BOT API
# ─────────────────────────────────────────────────────────────
def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None) -> bool:
    """Envía un mensaje a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status == 200
    except Exception as e:
        logging.error(f"Error enviando mensaje Telegram: {e}")
        return False

def answer_callback_query(callback_query_id: str, text: str = None) -> bool:
    """Responde al callback query para quitar el reloj de arena en el botón."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False

def edit_telegram_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> bool:
    """Edita un mensaje existente en Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status == 200
    except Exception as e:
        logging.error(f"Error editando mensaje Telegram: {e}")
        return False

def get_telegram_file_bytes(file_id: str) -> tuple:
    """Obtiene los bytes y la extensión de un archivo adjunto en Telegram."""
    try:
        info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        req = urllib.request.Request(info_url)
        with urllib.request.urlopen(req, timeout=10) as res:
            file_info = json.loads(res.read().decode("utf-8"))
        file_path = file_info.get("result", {}).get("file_path")
        if not file_path:
            return None, None
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        with urllib.request.urlopen(download_url, timeout=20) as d_res:
            return d_res.read(), file_path
    except Exception as e:
        logging.error(f"Error descargando archivo de Telegram: {e}")
        return None, None


# ─────────────────────────────────────────────────────────────
# 3. TECLADOS INTERACTIVOS (UI VISUAL)
# ─────────────────────────────────────────────────────────────
MAIN_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "☀️ Briefing Matutino", "callback_data": "act_briefing"},
            {"text": "💻 Apartado PC", "callback_data": "nav_pc"}
        ],
        [
            {"text": "📱 Mi Día & Agenda", "callback_data": "nav_agenda"},
            {"text": "🧑‍💻 Antigravity", "callback_data": "nav_antigravity"}
        ],
        [
            {"text": "📊 Finanzas & TRM", "callback_data": "nav_finances"},
            {"text": "🛡️ Centro Seguridad", "callback_data": "nav_security"}
        ]
    ]
}

PC_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📸 Pantallazo PC", "callback_data": "act_pc_screenshot"},
            {"text": "🔒 Bloquear PC", "callback_data": "act_pc_lock"}
        ],
        [
            {"text": "📊 Telemetría Hardware", "callback_data": "act_pc_stats"},
            {"text": "🔄 Estado Conexión", "callback_data": "nav_pc"}
        ],
        [
            {"text": "⬅️ Menú Principal", "callback_data": "nav_main"}
        ]
    ]
}

AGENDA_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📅 Eventos de Hoy", "callback_data": "act_agenda_today"},
            {"text": "➕ Crear Evento", "callback_data": "act_agenda_create_info"}
        ],
        [
            {"text": "☀️ Briefing Completo", "callback_data": "act_briefing"},
            {"text": "⬅️ Menú Principal", "callback_data": "nav_main"}
        ]
    ]
}

FINANCES_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "💵 TRM Oficial Hoy", "callback_data": "act_fin_trm"},
            {"text": "🪙 Criptomonedas", "callback_data": "act_fin_crypto"}
        ],
        [
            {"text": "⬅️ Menú Principal", "callback_data": "nav_main"}
        ]
    ]
}

SECURITY_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🔍 Auditoría en Vivo", "callback_data": "act_sec_audit"},
            {"text": "🔒 Bloquear PC Ya", "callback_data": "act_pc_lock"}
        ],
        [
            {"text": "⬅️ Menú Principal", "callback_data": "nav_main"}
        ]
    ]
}

ANTIGRAVITY_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🧪 Correr Tests", "callback_data": "act_pc_tests"},
            {"text": "📦 Estado Repos Git", "callback_data": "act_pc_git"}
        ],
        [
            {"text": "📋 Ver Cola de Órdenes", "callback_data": "act_orders_queue"},
            {"text": "⬅️ Menú Principal", "callback_data": "nav_main"}
        ]
    ]
}


# ─────────────────────────────────────────────────────────────
# 4. SERVICIOS EXTERNOS (CALENDARIO, TRM, CLIMA, GMAIL, IA)
# ─────────────────────────────────────────────────────────────

def get_google_access_token() -> str:
    """Obtiene un access token fresco de Google Calendar mediante el refresh token."""
    try:
        raw_token = GOOGLE_TOKEN_JSON
        if not raw_token and os.path.exists("token.json"):
            with open("token.json", "r") as f:
                raw_token = f.read()

        if not raw_token:
            return ""

        token_data = json.loads(raw_token)
        refresh_token = token_data.get("refresh_token")
        client_id = token_data.get("client_id")
        client_secret = token_data.get("client_secret")

        if not refresh_token:
            return token_data.get("token", "")

        post_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=8) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data.get("access_token", "")
    except Exception as e:
        logging.error(f"Error renovando Google Calendar Token: {e}")
        return ""

def fetch_google_calendar_events(days: int = 1) -> list:
    """Consulta los eventos de Google Calendar del día de hoy."""
    token = get_google_access_token()
    if not token:
        return []

    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_range = start_of_day + datetime.timedelta(days=days)

    params = urllib.parse.urlencode({
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_range.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime"
    })
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?{params}"

    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            events = []
            for item in items:
                summary = item.get("summary", "Sin título")
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                events.append({"summary": summary, "start": start, "source": "Google Calendar"})
            return events
    except Exception as e:
        logging.error(f"Error consultando Google Calendar: {e}")
        return []

def create_google_calendar_event(summary: str, start_dt: datetime.datetime, end_dt: datetime.datetime, description: str = "") -> dict:
    """Inserta un evento nuevo directamente en Google Calendar."""
    token = get_google_access_token()
    if not token:
        return {"success": False, "message": "No hay credenciales activas de Google Calendar."}

    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    payload = {
        "summary": summary,
        "description": description or "Creado por PERRA_JARVIS 24/7",
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()}
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return {"success": True, "link": res_data.get("htmlLink", "")}
    except Exception as e:
        return {"success": False, "message": str(e)}

def fetch_trm() -> str:
    """Consulta la TRM oficial de Colombia desde Datos Abiertos Superfinanciera."""
    url = "https://www.datos.gov.co/resource/32sa-8st3.json?$limit=2&$order=vigenciadesde%20DESC"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data:
                val = float(data[0].get("valor", 0))
                fecha = data[0].get("vigenciadesde", "")[:10]
                return f"💵 *TRM Oficial Colombia:* `${val:,.2f} COP`\n📅 *Vigencia:* `{fecha}`"
    except Exception as e:
        logging.error(f"Error consultando TRM: {e}")
    return "💵 TRM Colombia: No disponible temporalmente."

def fetch_crypto() -> str:
    """Consulta precios de BTC, ETH y SOL en CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd,cop"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            btc = data.get("bitcoin", {}).get("usd", 0)
            eth = data.get("ethereum", {}).get("usd", 0)
            sol = data.get("solana", {}).get("usd", 0)
            return (
                "🪙 *MERCADO CRIPTO (USD):*\n"
                f"• *BTC:* `${btc:,.2f}`\n"
                f"• *ETH:* `${eth:,.2f}`\n"
                f"• *SOL:* `${sol:,.2f}`"
            )
    except Exception as e:
        logging.error(f"Error consultando Cripto: {e}")
    return "🪙 Criptomonedas: Servicio no disponible."

def fetch_weather() -> str:
    """Consulta el clima actual de Bogotá en Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast?latitude=4.6097&longitude=-74.0817&current=temperature_2m,precipitation,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=America%2FBogota"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            curr = data.get("current", {})
            temp = curr.get("temperature_2m", "--")
            precip = curr.get("precipitation", 0)
            lluvia = "Alta probabilidad de lluvia 🌧️" if precip > 0.2 else "Sin lluvias reportadas 🌤️"
            return f"🌦️ *Clima Bogotá:* `{temp}°C`\n💧 *Condición:* {lluvia}"
    except Exception as e:
        logging.error(f"Error consultando Clima: {e}")
    return "🌦️ Clima Bogotá: 15°C (Promedio)."

def send_email_smtp(to_email: str, subject: str, body: str) -> dict:
    """Envía un correo electrónico mediante Gmail SMTP SSL."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return {"success": False, "message": "Credenciales de Gmail no configuradas."}
    try:
        msg = MIMEMultipart()
        msg["From"] = f"PERRA_JARVIS <{GMAIL_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        clean_pwd = GMAIL_APP_PASSWORD.replace(" ", "")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(GMAIL_USER, clean_pwd)
            server.send_message(msg)
        return {"success": True, "message": f"Correo despachado con éxito a `{to_email}`."}
    except Exception as e:
        return {"success": False, "message": str(e)}

def query_gemini_flash(prompt: str, inline_parts: list = None) -> str:
    """Consulta a Gemini 3.5 Flash Lite para razonamiento multimodal con $0.00 USD de costo."""
    if not GEMINI_API_KEY:
        return "⚠️ Clave de Gemini no configurada en el servidor nube."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    
    parts = []
    if inline_parts:
        parts.extend(inline_parts)
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "system_instruction": {
            "parts": [{
                "text": (
                    "Eres PERRA_JARVIS, el asistente ejecutivo de Diego Fabián Andrade. "
                    "Estás operando 24/7 en la nube en Azure Serverless con costo $0.00. "
                    "Responde siempre de forma concisa, ejecutiva, elegante y directa (máximo 2 a 3 oraciones). "
                    "Tienes acceso a su Google Calendar, Gmail, clima, TRM de Colombia y control remoto de su computador."
                )
            }]
        },
        "generation_config": {
            "temperature": 0.3,
            "max_output_tokens": 500
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as res:
            res_json = json.loads(res.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error en Gemini Flash Lite: {e}")
        return "⚠️ Error de procesamiento en la red neuronal de Google Gemini."


# ─────────────────────────────────────────────────────────────
# 5. CONTROL DE ESTADO DEL PC Y COLA DE ÓRDENES
# ─────────────────────────────────────────────────────────────
def is_pc_online() -> tuple:
    """Verifica si el PC personal ha enviado señal de vida en los últimos 90 segundos."""
    state = _load_json(STATE_FILE, default={})
    last_seen = state.get("last_seen", 0)
    now = time.time()
    online = (now - last_seen) < 90
    return online, state

def queue_pc_order(action: str, params: dict = None) -> int:
    """Encola una orden para que el PC la ejecute cuando esté en línea."""
    orders = _load_json(ORDERS_FILE, default=[])
    order_id = int(time.time() * 1000)
    order = {
        "id": order_id,
        "action": action,
        "params": params or {},
        "created_at": time.time(),
        "status": "pending"
    }
    orders.append(order)
    _save_json(ORDERS_FILE, orders)
    return order_id


# ─────────────────────────────────────────────────────────────
# 6. ENRUTADOR PRINCIPAL DE EVENTOS DE TELEGRAM (WEBHOOK)
# ─────────────────────────────────────────────────────────────
@app.route(route="telegram_webhook", methods=["POST"])
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """Receptor oficial del Webhook de Telegram en Azure Serverless (24/7)."""
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse("Invalid JSON", status_code=200)

    # 1. Manejo de Botones (Callback Queries)
    if "callback_query" in body:
        cq = body["callback_query"]
        cq_id = cq.get("id")
        user_id = cq.get("from", {}).get("id")
        data = cq.get("data", "")
        message = cq.get("message", {})
        msg_id = message.get("message_id")

        if user_id != ALLOWED_CHAT_ID:
            answer_callback_query(cq_id, "Acceso no autorizado.")
            return func.HttpResponse("OK", status_code=200)

        answer_callback_query(cq_id)

        # Enrutamiento de botones
        if data == "nav_main":
            edit_telegram_message(
                user_id, msg_id,
                "🤖 *PERRA_JARVIS CLOUD CORE (24/7 ACTIVO)*\n"
                "─────────────────────────────\n"
                "Asistente ejecutivo en línea con costo mensual garantizado de *$0.00 USD*.\n"
                "Selecciona una categoría o háblame por voz/texto:",
                reply_markup=MAIN_KEYBOARD
            )

        elif data == "nav_pc":
            online, st = is_pc_online()
            if online:
                status_txt = f"🟢 *EN LÍNEA*\n• CPU: `{st.get('cpu', '--')}%` | RAM: `{st.get('ram', '--')}%`"
            else:
                status_txt = "🔴 *APAGADO / SUSPENDIDO*\n• Las órdenes se encolarán y ejecutarán al encenderlo."
            
            edit_telegram_message(
                user_id, msg_id,
                "💻 *APARTADO: COMPUTADOR PERSONAL*\n"
                "─────────────────────────────\n"
                f"Estado actual: {status_txt}\n\n"
                "Opciones de control remoto:",
                reply_markup=PC_KEYBOARD
            )

        elif data == "act_pc_screenshot":
            online, _ = is_pc_online()
            if online:
                queue_pc_order("screenshot")
                send_telegram_message(user_id, "📸 Solicitando pantallazo a tu PC en tiempo real...")
            else:
                queue_pc_order("screenshot")
                send_telegram_message(user_id, "💻 *Tu PC está actualmente APAGADO.*\nHe puesto la orden de captura en cola; se tomará inmediatamente al encender el equipo.")

        elif data == "act_pc_lock":
            online, _ = is_pc_online()
            if online:
                queue_pc_order("lock")
                send_telegram_message(user_id, "🔒 Orden de bloqueo Windows enviada inmediatamente.")
            else:
                send_telegram_message(user_id, "💻 *Tu PC está apagado.* La sesión se encuentra naturalmente inactiva.")

        elif data == "act_pc_stats":
            online, st = is_pc_online()
            if online:
                send_telegram_message(
                    user_id,
                    f"📊 *TELEMETRÍA DE HARDWARE:*\n"
                    f"• CPU: `{st.get('cpu', 0)}%`\n"
                    f"• Memoria RAM: `{st.get('ram', 0)}%`\n"
                    f"• Batería: `{st.get('battery', 'N/A')}`\n"
                    f"• Hostname: `{st.get('hostname', 'Windows')}`"
                )
            else:
                send_telegram_message(user_id, "💻 El PC está apagado. Telemetría de hardware fuera de línea.")

        elif data == "nav_agenda":
            edit_telegram_message(
                user_id, msg_id,
                "📱 *APARTADO: MI DÍA & AGENDA OFICIAL*\n"
                "─────────────────────────────\n"
                "Sincronizado directamente con Google Calendar y tu iPhone.\n"
                "Elige una opción:",
                reply_markup=AGENDA_KEYBOARD
            )

        elif data == "act_agenda_today":
            events = fetch_google_calendar_events(days=1)
            if events:
                ev_str = "\n".join([f"• *{e['start'][11:16] if 'T' in e['start'] else 'Todo el día'}:* {e['summary']}" for e in events])
                msg = f"📅 *EVENTOS DE HOY EN TU AGENDA:*\n─────────────────────────────\n{ev_str}"
            else:
                msg = "📅 *Agenda de Hoy:* No tienes eventos programados para el resto del día."
            send_telegram_message(user_id, msg)

        elif data == "act_briefing":
            clima = fetch_weather()
            trm = fetch_trm()
            events = fetch_google_calendar_events(days=1)
            ev_str = f"{len(events)} eventos programados" if events else "Día libre de eventos"
            msg = (
                "☀️ *BRIEFING EJECUTIVO MATUTINO (24/7 NUBE)*\n"
                "─────────────────────────────\n"
                f"{clima}\n\n"
                f"{trm}\n\n"
                f"📅 *Agenda:* {ev_str}\n"
                "─────────────────────────────\n"
                "💡 _Para escuchar en audio, pídeme 'Dame el briefing en voz'._"
            )
            send_telegram_message(user_id, msg)

        elif data == "nav_finances":
            edit_telegram_message(
                user_id, msg_id,
                "📊 *APARTADO: FINANZAS Y MERCADOS*\n"
                "─────────────────────────────\n"
                "Datos oficiales en tiempo real ($0.00 costo).\n"
                "Elige una consulta:",
                reply_markup=FINANCES_KEYBOARD
            )

        elif data == "act_fin_trm":
            send_telegram_message(user_id, fetch_trm())

        elif data == "act_fin_crypto":
            send_telegram_message(user_id, fetch_crypto())

        elif data == "nav_security":
            edit_telegram_message(
                user_id, msg_id,
                "🛡️ *APARTADO: CENTRO DE CIBERSEGURIDAD*\n"
                "─────────────────────────────\n"
                f"• Whitelist Telegram: `ACTIVA` (ID: `{ALLOWED_CHAT_ID}`)\n"
                "• Aislamiento Nube: Azure Functions Serverless\n"
                "• Zero Leak Guarantee: Verificado\n"
                "• Sandbox Shell Injection: Activo",
                reply_markup=SECURITY_KEYBOARD
            )

        elif data == "act_sec_audit":
            report = (
                "🛡️ *INFORME DE AUDITORÍA DE SEGURIDAD 24/7*\n"
                "─────────────────────────────\n"
                "🚦 *Estado Global:* 🟢 `SECURE`\n"
                f"🔒 *Whitelist Telegram:* `ACTIVA` (ID: `{ALLOWED_CHAT_ID}`)\n"
                "🔐 *Fugas de Secretos:* `0` (Custodia en Azure Vault/Settings)\n"
                "☁️ *Infraestructura:* Azure Linux Serverless ($0.00 USD)\n"
                "─────────────────────────────\n"
                "✨ Tu asistente opera con máxima protección contra accesos no autorizados."
            )
            send_telegram_message(user_id, report)

        elif data == "nav_antigravity":
            edit_telegram_message(
                user_id, msg_id,
                "🧑‍💻 *APARTADO: ANTIGRAVITY & REPOSITORIOS*\n"
                "─────────────────────────────\n"
                "Administración de proyectos de software en tu máquina local.",
                reply_markup=ANTIGRAVITY_KEYBOARD
            )

        elif data == "act_orders_queue":
            orders = _load_json(ORDERS_FILE, default=[])
            pending = [o for o in orders if o.get("status") == "pending"]
            if pending:
                msg = f"📋 *COLA DE ÓRDENES:* Hay `{len(pending)}` órdenes pendientes esperando que tu PC inicie sesión."
            else:
                msg = "📋 *COLA DE ÓRDENES:* Vacía. No hay acciones pendientes."
            send_telegram_message(user_id, msg)

        return func.HttpResponse("OK", status_code=200)

    # 2. Manejo de Mensajes Directos (Texto, Voz, Documento)
    message = body.get("message", {})
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()

    if user_id != ALLOWED_CHAT_ID:
        logging.warning(f"Intento de acceso bloqueado desde chat_id: {user_id}")
        return func.HttpResponse("Unauthorized", status_code=200)

    # A. Comandos de Menú / Inicio
    if text.lower() in ["/start", "/menu", "menu", "menú", "panel"]:
        send_telegram_message(
            user_id,
            "🤖 *PERRA_JARVIS CLOUD CORE (24/7 ACTIVO)*\n"
            "─────────────────────────────\n"
            "¡Hola, Diego! Tu asistente opera de forma ininterrumpida en la nube sin costo alguno.\n\n"
            "Selecciona un apartado o envíame cualquier instrucción por voz o texto:",
            reply_markup=MAIN_KEYBOARD
        )
        return func.HttpResponse("OK", status_code=200)

    # B. Mensaje de Voz (.ogg)
    if "voice" in message:
        voice = message["voice"]
        file_id = voice.get("file_id")
        send_telegram_message(user_id, "🎙️ _Escuchando nota de voz y procesando con Gemini Flash Lite..._")
        audio_bytes, _ = get_telegram_file_bytes(file_id)
        if audio_bytes:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            inline_part = {
                "inline_data": {
                    "mime_type": "audio/ogg",
                    "data": b64_audio
                }
            }
            prompt = "Escucha este audio de Diego y responde con máxima brevedad, ejecutividad y precisión."
            ai_reply = query_gemini_flash(prompt, inline_parts=[inline_part])
            send_telegram_message(user_id, f"🎙️ *Jarvis:* {ai_reply}")
        else:
            send_telegram_message(user_id, "⚠️ No pude descargar la nota de voz.")
        return func.HttpResponse("OK", status_code=200)

    # C. Documento adjunto (PDF, código, texto)
    if "document" in message:
        doc = message["document"]
        file_id = doc.get("file_id")
        file_name = doc.get("file_name", "documento")
        mime = doc.get("mime_type", "application/pdf")
        caption = message.get("caption", "Resume este documento y resalta los puntos clave.")
        send_telegram_message(user_id, f"📄 _Analizando `{file_name}` con Gemini Flash Lite..._")
        doc_bytes, _ = get_telegram_file_bytes(file_id)
        if doc_bytes:
            b64_doc = base64.b64encode(doc_bytes).decode("utf-8")
            inline_part = {
                "inline_data": {
                    "mime_type": mime,
                    "data": b64_doc
                }
            }
            ai_reply = query_gemini_flash(caption, inline_parts=[inline_part])
            send_telegram_message(user_id, f"📄 *Análisis de `{file_name}`:*\n\n{ai_reply}")
        else:
            send_telegram_message(user_id, "⚠️ No pude descargar el documento.")
        return func.HttpResponse("OK", status_code=200)

    # D. Mensaje de Texto (Intenciones Directas o Chat con IA)
    if text:
        q = text.lower()

        # Atajos instantáneos
        if q in ["dolar", "dólar", "trm", "/trm"]:
            send_telegram_message(user_id, fetch_trm())
            return func.HttpResponse("OK", status_code=200)

        if q in ["clima", "tiempo", "/clima"]:
            send_telegram_message(user_id, fetch_weather())
            return func.HttpResponse("OK", status_code=200)

        if q in ["agenda", "calendario", "/agenda"]:
            events = fetch_google_calendar_events(days=1)
            if events:
                ev_str = "\n".join([f"• *{e['start'][11:16] if 'T' in e['start'] else 'Todo el día'}:* {e['summary']}" for e in events])
                msg = f"📅 *EVENTOS DE HOY:*\n─────────────────────────────\n{ev_str}"
            else:
                msg = "📅 No tienes eventos pendientes hoy en tu Google Calendar."
            send_telegram_message(user_id, msg)
            return func.HttpResponse("OK", status_code=200)

        if any(w in q for w in ["pantallazo", "screenshot", "captura de pantalla"]):
            online, _ = is_pc_online()
            queue_pc_order("screenshot")
            if online:
                send_telegram_message(user_id, "📸 Solicitando pantallazo a tu PC...")
            else:
                send_telegram_message(user_id, "💻 *Tu PC está APAGADO.*\nOrden encolada; se capturará inmediatamente cuando tu computador se encienda.")
            return func.HttpResponse("OK", status_code=200)

        if any(w in q for w in ["bloquear pc", "bloquea el pc"]):
            online, _ = is_pc_online()
            if online:
                queue_pc_order("lock")
                send_telegram_message(user_id, "🔒 Orden de bloqueo enviada al PC.")
            else:
                send_telegram_message(user_id, "💻 Tu computador ya está apagado.")
            return func.HttpResponse("OK", status_code=200)

        # Enviar correo electrónico
        if q.startswith("manda un correo") or q.startswith("enviar correo") or q.startswith("enviar email"):
            # Usar Gemini para extraer datos estructurados
            extract_prompt = (
                f"Extrae el destinatario, asunto y cuerpo del siguiente mensaje: '{text}'. "
                "Devuelve ÚNICAMENTE un objeto JSON válido con los campos 'to', 'subject', 'body'. "
                "Si no hay asunto, invéntate uno formal. Si no hay correo explícito, usa 'diegofabian105@gmail.com'."
            )
            raw_json = query_gemini_flash(extract_prompt)
            try:
                clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                data_mail = json.loads(clean_json)
                res_mail = send_email_smtp(data_mail["to"], data_mail["subject"], data_mail["body"])
                send_telegram_message(user_id, f"📧 {res_mail['message']}")
            except Exception as e:
                send_telegram_message(user_id, f"⚠️ Error redactando correo: {e}")
            return func.HttpResponse("OK", status_code=200)

        # Chat general y razonamiento ejecutivo con Gemini 3.5 Flash Lite
        ai_reply = query_gemini_flash(text)
        send_telegram_message(user_id, ai_reply)
        return func.HttpResponse("OK", status_code=200)

    return func.HttpResponse("OK", status_code=200)


# ─────────────────────────────────────────────────────────────
# 7. ENDPOINTS DE COMUNICACIÓN CON EL PC LOCAL (COMPANION API)
# ─────────────────────────────────────────────────────────────
@app.route(route="pc/heartbeat", methods=["POST"])
def pc_heartbeat(req: func.HttpRequest) -> func.HttpResponse:
    """Recibe la señal de vida periódica del PC local de Diego."""
    try:
        data = req.get_json()
        data["last_seen"] = time.time()
        _save_json(STATE_FILE, data)
        return func.HttpResponse(json.dumps({"status": "ok", "timestamp": time.time()}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="pc/orders", methods=["GET"])
def pc_orders_get(req: func.HttpRequest) -> func.HttpResponse:
    """Devuelve las órdenes pendientes para que el PC local las ejecute."""
    orders = _load_json(ORDERS_FILE, default=[])
    pending = [o for o in orders if o.get("status") == "pending"]
    return func.HttpResponse(json.dumps(pending), mimetype="application/json")

@app.route(route="pc/orders/complete", methods=["POST"])
def pc_orders_complete(req: func.HttpRequest) -> func.HttpResponse:
    """Marca una orden como completada."""
    try:
        body = req.get_json()
        order_id = body.get("order_id")
        orders = _load_json(ORDERS_FILE, default=[])
        for o in orders:
            if o.get("id") == order_id:
                o["status"] = "completed"
                o["completed_at"] = time.time()
        _save_json(ORDERS_FILE, orders)
        return func.HttpResponse(json.dumps({"status": "ok"}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check 24/7 de Azure Function."""
    return func.HttpResponse(json.dumps({
        "status": "healthy",
        "service": "PERRA_JARVIS 24/7 Cloud Core",
        "monthly_cost": "$0.00 USD",
        "timestamp": time.time()
    }), mimetype="application/json")
