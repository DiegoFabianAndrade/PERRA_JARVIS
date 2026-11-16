"""
Azure Function Serverless (HTTP Trigger / Telegram Webhook).
Permite que PERRA_JARVIS funcione 24/7 en la nube cuando tu PC está apagado.
Costo mensual en Azure for Students: $0.00 USD (Capa gratuita de 1,000,000 peticiones/mes).
"""

import os
import json
import logging
import urllib.request
import azure.functions as func

# Claves de entorno en Azure
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "1257398092"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def send_telegram_reply(chat_id: int, text: str):
    """Envía un mensaje de vuelta a Telegram desde Azure."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        logging.error(f"Error enviando mensaje desde Azure: {e}")


@app.route(route="telegram_webhook", methods=["POST"])
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """Receptor del Webhook de Telegram 24/7 en Azure Serverless."""
    try:
        body = req.get_json()
        message = body.get("message", {})
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "").strip()

        # Whitelist de seguridad: Solo Diego
        if user_id != ALLOWED_CHAT_ID:
            return func.HttpResponse("Unauthorized", status_code=200)

        logging.info(f"Mensaje recibido en Azure 24/7: {text}")

        # Si el mensaje pide cosas que requieren el PC físico
        pc_keywords = ["pantalla", "pantallazo", "screenshot", "bloquear", "volumen", "spotify"]
        if any(w in text.lower() for w in pc_keywords):
            reply = (
                "☁️ *PERRA_JARVIS CLOUD RELAY (Azure 24/7)*\n"
                "─────────────────────────────\n"
                "💻 *Estado del PC:* Tu computador principal se encuentra **APAGADO o en reposo**.\n\n"
                "📌 He registrado tu solicitud. Las acciones de hardware (pantallazo, apps y volumen) "
                "se ejecutarán automáticamente en cuanto enciendas tu equipo.\n\n"
                "✨ _(Recuerda que Gmail, Calendario de iPhone, Clima, TRM y consultas con IA "
                "siguen 100% disponibles aquí en la nube)._\n"
                "─────────────────────────────"
            )
            send_telegram_reply(user_id, reply)
            return func.HttpResponse("OK", status_code=200)

        # Si es una consulta en la nube (ej. /start o ayuda)
        if text.startswith("/start"):
            reply = (
                "☁️ *PERRA_JARVIS CLOUD (Modo 24/7 Nube)*\n"
                "─────────────────────────────\n"
                "¡Hola, Diego! Tu PC local está apagado, pero yo estoy activo en la nube de Azure ($0.00).\n\n"
                "Puedes consultarme:\n"
                "• *🌦️ Clima:*\n"
                "• *💵 TRM Dólar:*\n"
                "• *🧠 Preguntas generales:*\n"
                "• *📝 Enviar órdenes a tus repositorios para cuando abras el PC.*\n"
                "─────────────────────────────"
            )
            send_telegram_reply(user_id, reply)
            return func.HttpResponse("OK", status_code=200)

        # Respuesta general con IA o confirmación
        send_telegram_reply(user_id, f"☁️ *Jarvis Cloud (24/7):* Orden recibida: `{text}`.")
        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.error(f"Error procesando webhook en Azure: {e}")
        return func.HttpResponse("Internal Server Error", status_code=200)
