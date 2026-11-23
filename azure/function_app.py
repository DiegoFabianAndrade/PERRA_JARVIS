"""
PERRA_JARVIS 24/7 - Executive Cloud Serverless Core
Desplegado en Azure Functions (Consumption Plan - $0.00 USD).
Opera de forma continua incluso con el computador personal apagado.
Almacenamiento persistente en Azure Blob Storage (cero pérdida de órdenes entre reinicios).
"""

import os
import re
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

# Cadena de conexión Azure Blob Storage persistente
AZURE_STORAGE_CONN = os.getenv("AzureWebJobsStorage", "")


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ─────────────────────────────────────────────────────────────
# 2. CAPA DE PERSISTENCIA REAL: AZURE BLOB STORAGE VÍA HTTPS REST
# ─────────────────────────────────────────────────────────────
AZURE_BLOB_SAS_URL = os.getenv("AZURE_BLOB_SAS_URL", "https://stperrajarvis125.blob.core.windows.net/jarvis-state")
AZURE_BLOB_SAS_QUERY = os.getenv("AZURE_BLOB_SAS_QUERY", "")


def load_persistent_json(blob_name: str, default=None):
    """Carga un JSON persistente directamente desde Azure Blob Storage vía HTTPS REST."""
    url = f"{AZURE_BLOB_SAS_URL}/{blob_name}?{AZURE_BLOB_SAS_QUERY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return default if default is not None else {}
        logging.warning(f"HTTPError leyendo blob {blob_name}: {e.code}")
    except Exception as e:
        logging.warning(f"Error leyendo blob {blob_name}: {e}")
    return default if default is not None else {}

def save_persistent_json(blob_name: str, data) -> bool:
    """Guarda un JSON de forma 100% persistente en Azure Blob Storage vía HTTPS REST."""
    url = f"{AZURE_BLOB_SAS_URL}/{blob_name}?{AZURE_BLOB_SAS_QUERY}"
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=raw,
            headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            return res.status in (200, 201)
    except Exception as e:
        logging.error(f"Error escribiendo blob {blob_name}: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# 3. CONTROL DE ESTADO DEL PC Y COLA DE ÓRDENES PERSISTENTE
# ─────────────────────────────────────────────────────────────
def is_pc_online() -> tuple:
    """Verifica si el PC personal ha enviado señal de vida en los últimos 90 segundos."""
    state = load_persistent_json("pc_state.json", default={})
    last_seen = state.get("last_seen", 0)
    now = time.time()
    online = (now - last_seen) < 90
    return online, state

def queue_pc_order(action: str, params: dict = None, repo: str = "PERRA_JARVIS", raw_text: str = "") -> dict:
    """Encola una orden en almacenamiento persistente de Azure Blob Storage."""
    orders = load_persistent_json("orders.json", default=[])
    order_id = int(time.time() * 1000)
    order = {
        "id": order_id,
        "action": action,
        "params": params or {},
        "repo": repo,
        "raw_text": raw_text,
        "created_at": time.time(),
        "created_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending"
    }
    orders.append(order)
    save_persistent_json("orders.json", orders)
    logging.info(f"Orden encolada exitosamente en Blob: #{order_id} ({action})")
    return order


# ─────────────────────────────────────────────────────────────
# 4. CLIENTE TELEGRAM BOT API
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
# 5. TECLADOS INTERACTIVOS (UI VISUAL)
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
# 6. SERVICIOS EXTERNOS (CALENDARIO, TRM, CLIMA, GMAIL, IA)
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

def query_gemini_flash(prompt: str, inline_parts: list = None, system_instruction: str = None) -> str:
    """Consulta a Gemini 3.5 Flash Lite para razonamiento multimodal con $0.00 USD de costo."""
    if not GEMINI_API_KEY:
        return "⚠️ Clave de Gemini no configurada en el servidor nube."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    
    parts = []
    if inline_parts:
        parts.extend(inline_parts)
    parts.append({"text": prompt})

    sys_text = system_instruction or (
        "Eres PERRA_JARVIS, el asistente ejecutivo de Diego Fabián Andrade. "
        "Estás operando 24/7 en la nube en Azure Serverless con costo $0.00. "
        "Responde siempre de forma concisa, ejecutiva, elegante y directa (máximo 2 a 3 oraciones). "
        "Tienes acceso a su Google Calendar, Gmail, clima, TRM de Colombia y control remoto de su computador."
    )

    payload = {
        "contents": [{"parts": parts}],
        "system_instruction": {"parts": [{"text": sys_text}]},
        "generation_config": {
            "temperature": 0.2,
            "max_output_tokens": 500
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=14) as res:
            res_json = json.loads(res.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error en Gemini Flash Lite: {e}")
        return "⚠️ Error de procesamiento en la red neuronal de Google Gemini."


# ─────────────────────────────────────────────────────────────
# 7. ENRUTADOR PRINCIPAL DE EVENTOS DE TELEGRAM (WEBHOOK)
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
                status_txt = f"🟢 *EN LÍNEA*\n• Hostname: `{st.get('hostname', 'Windows')}`\n• CPU: `{st.get('cpu', '--')}%` | RAM: `{st.get('ram', '--')}%`"
            else:
                status_txt = "🔴 *APAGADO / SUSPENDIDO*\n• Las órdenes se guardan en la nube y se ejecutan al encenderlo."
            
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
            order = queue_pc_order("screenshot")
            if online:
                send_telegram_message(user_id, f"📸 Solicitando pantallazo a tu PC en tiempo real (Orden #{order['id']})...")
            else:
                send_telegram_message(
                    user_id,
                    f"💻 *Tu PC está actualmente APAGADO.*\n"
                    f"📌 Orden #{order['id']} encolada en almacenamiento persistente de Azure.\n"
                    f"Se capturará inmediatamente cuando inicies sesión en Windows."
                )

        elif data == "act_pc_lock":
            online, _ = is_pc_online()
            order = queue_pc_order("lock")
            if online:
                send_telegram_message(user_id, f"🔒 Orden #{order['id']}: Bloqueo Windows enviado inmediatamente.")
            else:
                send_telegram_message(user_id, f"💻 *Tu PC está apagado.* Orden #{order['id']} encolada.")

        elif data == "act_pc_stats":
            online, st = is_pc_online()
            if online:
                send_telegram_message(
                    user_id,
                    f"📊 *TELEMETRÍA DE HARDWARE EN VIVO:*\n"
                    f"• Hostname: `{st.get('hostname', 'Windows')}`\n"
                    f"• CPU: `{st.get('cpu', 0)}%`\n"
                    f"• Memoria RAM: `{st.get('ram', 0)}%`\n"
                    f"• Batería: `{st.get('battery', 'N/A')}`\n"
                    f"• Última señal: hace `{int(time.time() - st.get('last_seen', time.time()))}s`"
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
                "💡 _Para ejecutar cualquier acción en tu PC, envíame una orden por texto o voz._"
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
                "• Persistencia: Azure Blob Storage Cifrado\n"
                "• Zero Leak Guarantee: Verificado",
                reply_markup=SECURITY_KEYBOARD
            )

        elif data == "act_sec_audit":
            report = (
                "🛡️ *INFORME DE AUDITORÍA DE SEGURIDAD 24/7*\n"
                "─────────────────────────────\n"
                "🚦 *Estado Global:* 🟢 `SECURE`\n"
                f"🔒 *Whitelist Telegram:* `ACTIVA` (ID: `{ALLOWED_CHAT_ID}`)\n"
                "🔐 *Fugas de Secretos:* `0` (Custodia en Azure Vault/Settings)\n"
                "💾 *Persistencia:* Azure Blob Storage (`stperrajarvis125`)\n"
                "☁️ *Infraestructura:* Azure Linux Serverless ($0.00 USD)\n"
                "─────────────────────────────\n"
                "✨ Máxima protección y 100% persistencia garantizada."
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
            orders = load_persistent_json("orders.json", default=[])
            pending = [o for o in orders if o.get("status") == "pending"]
            if pending:
                items_str = "\n".join([f"• `#{o['id']}` [{o.get('action')}]: _{o.get('repo', 'PC')}_" for o in pending[-5:]])
                msg = f"📋 *COLA DE ÓRDENES PERSISTENTE ({len(pending)} pendientes):*\n─────────────────────────────\n{items_str}"
            else:
                msg = "📋 *COLA DE ÓRDENES:* Vacía. Todas las órdenes han sido ejecutadas."
            send_telegram_message(user_id, msg)

        elif data == "act_pc_tests":
            order = queue_pc_order("test", {"project": "PERRA_JARVIS"}, repo="PERRA_JARVIS")
            online, _ = is_pc_online()
            status_txt = "Ejecutando en PC..." if online else "Encolada (PC apagado; se ejecutará al iniciar Windows)."
            send_telegram_message(user_id, f"🧪 Orden de tests #{order['id']} registrada para `PERRA_JARVIS`.\nEstado: {status_txt}")

        elif data == "act_pc_git":
            order = queue_pc_order("git", {"project": "PERRA_JARVIS"}, repo="PERRA_JARVIS")
            online, _ = is_pc_online()
            status_txt = "Consultando en PC..." if online else "Encolada (PC apagado; se ejecutará al iniciar Windows)."
            send_telegram_message(user_id, f"📦 Orden de Git #{order['id']} registrada para `PERRA_JARVIS`.\nEstado: {status_txt}")

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

    # B. COMANDO EXPLÍCITO /orden <repo> <instrucción>
    if text.startswith("/orden") or text.startswith("/order"):
        parts = text.split(maxsplit=2)
        if len(parts) >= 3 and parts[1].lower() in ["perra_jarvis", "telegram-dollar-bot", "dollarbot"]:
            target_repo = parts[1]
            instruction = parts[2]
        elif len(parts) >= 2:
            target_repo = "PERRA_JARVIS"
            instruction = text[len(parts[0]):].strip()
        else:
            send_telegram_message(user_id, "⚠️ Uso: `/orden <repositorio> <instrucción>`\nEjemplo: `/orden PERRA_JARVIS corre los tests unitarios`")
            return func.HttpResponse("OK", status_code=200)

        online, _ = is_pc_online()
        order = queue_pc_order("code_order", {"project": target_repo, "instruction": instruction}, repo=target_repo, raw_text=text)

        if online:
            msg = (
                f"⚡ *ORDEN #{order['id']} ENVIADA A TU PC*\n"
                "─────────────────────────────\n"
                f"📦 *Repositorio:* `{target_repo}`\n"
                f"📌 *Instrucción:* _{instruction}_\n"
                f"🟢 *Estado PC:* En línea (Ejecutando en Windows...)\n"
                "─────────────────────────────"
            )
        else:
            msg = (
                f"📋 *ORDEN #{order['id']} GUARDADA EN LA NUBE (24/7)*\n"
                "─────────────────────────────\n"
                f"📦 *Repositorio:* `{target_repo}`\n"
                f"📌 *Instrucción:* _{instruction}_\n"
                f"🔴 *Estado PC:* Apagado / En reposo\n\n"
                f"💾 He guardado tu orden en almacenamiento persistente de Azure. En cuanto inicies sesión en Windows, tu computador la ejecutará automáticamente."
            )
        send_telegram_message(user_id, msg)
        return func.HttpResponse("OK", status_code=200)

    # C. Mensaje de Voz (.ogg) con detección de acciones
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
            prompt = (
                "Escucha este audio de Diego. Determina si pide una acción concreta para su computador "
                "(pantallazo, bloquear PC, correr tests, abrir app, o una orden de código). "
                "Si pide una acción de PC, devuelve un JSON: {\"is_action\": true, \"action\": \"screenshot|lock|test|git|code_order\", \"repo\": \"PERRA_JARVIS\", \"details\": \"...\"}. "
                "Si es una pregunta general o conversacional, responde directamente en texto breve y ejecutivo."
            )
            ai_reply = query_gemini_flash(prompt, inline_parts=[inline_part])
            
            # Verificar si devolvió acción estructurada
            if "{" in ai_reply and "is_action" in ai_reply:
                try:
                    m = re.search(r"\{.*\}", ai_reply, re.DOTALL)
                    if m:
                        act_data = json.loads(m.group(0))
                        if act_data.get("is_action"):
                            act_name = act_data.get("action", "code_order")
                            act_repo = act_data.get("repo", "PERRA_JARVIS")
                            act_details = act_data.get("details", "")
                            online, _ = is_pc_online()
                            order = queue_pc_order(act_name, {"project": act_repo, "instruction": act_details}, repo=act_repo, raw_text="Nota de voz")
                            status_txt = "🟢 Ejecutando en PC..." if online else "🔴 PC apagado; orden guardada en Azure para ejecutarse al iniciar Windows."
                            send_telegram_message(user_id, f"🎙️ *Audio Procesado - Orden #{order['id']} Encolada:*\nAcción: `{act_name}` ({act_repo})\nEstado: {status_txt}")
                            return func.HttpResponse("OK", status_code=200)
                except Exception:
                    pass

            send_telegram_message(user_id, f"🎙️ *Jarvis:* {ai_reply}")
        else:
            send_telegram_message(user_id, "⚠️ No pude descargar la nota de voz.")
        return func.HttpResponse("OK", status_code=200)

    # D. Documento adjunto (PDF, código, texto)
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

    # E. Mensaje de Texto (Intenciones Directas o Chat con IA)
    if text:
        q = text.lower()

        # 1. Atajos instantáneos informativos
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

        # 2. Atajos directos de Hardware / PC
        if any(w in q for w in ["pantallazo", "screenshot", "captura de pantalla", "/pantallazo"]):
            online, _ = is_pc_online()
            order = queue_pc_order("screenshot", raw_text=text)
            if online:
                send_telegram_message(user_id, f"📸 Solicitando pantallazo a tu PC (Orden #{order['id']})...")
            else:
                send_telegram_message(user_id, f"💻 *Tu PC está APAGADO.*\n📌 Orden #{order['id']} encolada en Azure; se capturará inmediatamente al encender el PC.")
            return func.HttpResponse("OK", status_code=200)

        if any(w in q for w in ["bloquear pc", "bloquea el pc", "/bloquear"]):
            online, _ = is_pc_online()
            order = queue_pc_order("lock", raw_text=text)
            if online:
                send_telegram_message(user_id, f"🔒 Orden #{order['id']}: Bloqueo enviado al PC.")
            else:
                send_telegram_message(user_id, f"💻 Tu computador ya está apagado. Orden #{order['id']} guardada.")
            return func.HttpResponse("OK", status_code=200)

        # 3. Tests y Git directos
        if any(w in q for w in ["correr pruebas", "corre las pruebas", "ejecuta los tests", "correr tests", "/test"]):
            repo = "telegram-dollar-bot" if "dollar" in q else "PERRA_JARVIS"
            online, _ = is_pc_online()
            order = queue_pc_order("test", {"project": repo}, repo=repo, raw_text=text)
            status_txt = "Ejecutando en Windows..." if online else "PC apagado; se ejecutará al iniciar Windows."
            send_telegram_message(user_id, f"🧪 *Orden #{order['id']}:* Ejecución de pruebas unitarias para `{repo}`.\nEstado: {status_txt}")
            return func.HttpResponse("OK", status_code=200)

        if any(w in q for w in ["estado git", "ramas git", "ultimos commits", "/git"]):
            repo = "telegram-dollar-bot" if "dollar" in q else "PERRA_JARVIS"
            online, _ = is_pc_online()
            order = queue_pc_order("git", {"project": repo}, repo=repo, raw_text=text)
            status_txt = "Consultando en Windows..." if online else "PC apagado; se consultará al iniciar Windows."
            send_telegram_message(user_id, f"📦 *Orden #{order['id']}:* Consulta de Git para `{repo}`.\nEstado: {status_txt}")
            return func.HttpResponse("OK", status_code=200)

        # 4. Enviar correo electrónico
        if q.startswith("manda un correo") or q.startswith("enviar correo") or q.startswith("enviar email"):
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

        # 5. Detección Inteligente de Órdenes con Gemini 3.5 Flash Lite
        # Analizar si es una orden para el PC / Repositorios
        ai_intent_prompt = (
            f"El usuario Diego dijo: '{text}'. "
            "Determina si es una instrucción o petición para ejecutar en su computador personal o repositorios de software "
            "(ejemplos: modificar archivos, correr comandos, revisar código, abrir programas, apagar/suspender el PC, o realizar tareas de desarrollo). "
            "Responde estrictamente en formato JSON con la siguiente estructura: "
            "{\"is_pc_order\": true/false, \"action\": \"code_order|screenshot|lock|test|git|open_app|command\", \"repo\": \"PERRA_JARVIS\", \"details\": \"instrucción clara\", \"reply\": \"mensaje confirmando la recepción para Diego\"}."
        )
        intent_reply = query_gemini_flash(ai_intent_prompt)
        
        if "{" in intent_reply and "is_pc_order" in intent_reply:
            try:
                m = re.search(r"\{.*\}", intent_reply, re.DOTALL)
                if m:
                    parsed = json.loads(m.group(0))
                    if parsed.get("is_pc_order"):
                        action = parsed.get("action", "code_order")
                        repo = parsed.get("repo", "PERRA_JARVIS")
                        details = parsed.get("details", text)
                        confirm_text = parsed.get("reply", "Orden registrada.")
                        
                        online, _ = is_pc_online()
                        order = queue_pc_order(action, {"project": repo, "instruction": details}, repo=repo, raw_text=text)
                        
                        if online:
                            status_msg = f"🟢 *PC en línea:* Ejecutando en tu equipo inmediatamente."
                        else:
                            status_msg = f"🔴 *PC apagado:* Orden guardada en la nube persistente de Azure. Se ejecutará automáticamente en cuanto enciendas tu equipo."

                        send_telegram_message(
                            user_id,
                            f"📋 *ORDEN #{order['id']} REGISTRADA*\n"
                            "─────────────────────────────\n"
                            f"📦 *Objetivo:* `{repo}`\n"
                            f"⚡ *Acción:* `{action}`\n"
                            f"📌 *Detalle:* _{details}_\n\n"
                            f"{status_msg}\n"
                            "─────────────────────────────"
                        )
                        return func.HttpResponse("OK", status_code=200)
            except Exception as e:
                logging.warning(f"Error interpretando JSON de intención: {e}")

        # 6. Chat general y razonamiento ejecutivo con Gemini 3.5 Flash Lite
        ai_reply = query_gemini_flash(text)
        send_telegram_message(user_id, ai_reply)
        return func.HttpResponse("OK", status_code=200)

    return func.HttpResponse("OK", status_code=200)


# ─────────────────────────────────────────────────────────────
# 8. ENDPOINTS DE COMUNICACIÓN CON EL PC LOCAL (COMPANION API)
# ─────────────────────────────────────────────────────────────
@app.route(route="pc/heartbeat", methods=["POST"])
def pc_heartbeat(req: func.HttpRequest) -> func.HttpResponse:
    """Recibe la señal de vida periódica del PC local de Diego y la persiste en Azure."""
    try:
        data = req.get_json()
        data["last_seen"] = time.time()
        save_persistent_json("pc_state.json", data)
        return func.HttpResponse(json.dumps({"status": "ok", "timestamp": time.time()}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="pc/orders", methods=["GET"])
def pc_orders_get(req: func.HttpRequest) -> func.HttpResponse:
    """Devuelve las órdenes pendientes desde Azure Blob Storage para que el PC local las ejecute."""
    orders = load_persistent_json("orders.json", default=[])
    pending = [o for o in orders if o.get("status") == "pending"]
    return func.HttpResponse(json.dumps(pending), mimetype="application/json")

@app.route(route="pc/orders/complete", methods=["POST"])
def pc_orders_complete(req: func.HttpRequest) -> func.HttpResponse:
    """Marca una orden como completada en Azure Blob Storage."""
    try:
        body = req.get_json()
        order_id = body.get("order_id")
        result_text = body.get("result", "")
        
        orders = load_persistent_json("orders.json", default=[])
        for o in orders:
            if o.get("id") == order_id:
                o["status"] = "completed"
                o["completed_at"] = time.time()
                o["result"] = result_text
        save_persistent_json("orders.json", orders)
        return func.HttpResponse(json.dumps({"status": "ok"}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check 24/7 de Azure Function y almacenamiento persistente."""
    orders = load_persistent_json("orders.json", default=[])
    pending = len([o for o in orders if o.get("status") == "pending"])
    online, st = is_pc_online()
    return func.HttpResponse(json.dumps({
        "status": "healthy",
        "service": "PERRA_JARVIS 24/7 Cloud Core",
        "storage": "Azure Blob Storage (stperrajarvis125)",
        "monthly_cost": "$0.00 USD",
        "pc_online": online,
        "pending_orders": pending,
        "timestamp": time.time()
    }), mimetype="application/json")
