"""
Configuración centralizada de PERRA_JARVIS.
Carga variables de entorno desde .env y expone parámetros seguros.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Telegram & Seguridad
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_raw_chat_id = os.getenv("ALLOWED_CHAT_ID", "1257398092").strip()
try:
    ALLOWED_CHAT_ID = int(_raw_chat_id)
except ValueError:
    ALLOWED_CHAT_ID = 1257398092

# IA
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "PERRA_JARVIS").strip()
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Correo (Solo Gmail)
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()

# Calendario iPhone (iCloud) y Google Calendar
ICLOUD_CALENDAR_URL = os.getenv("ICLOUD_CALENDAR_URL", "").strip()
GOOGLE_CALENDAR_URL = os.getenv("GOOGLE_CALENDAR_URL", "").strip()
ICLOUD_USER = os.getenv("ICLOUD_USER", "").strip()
ICLOUD_APP_PASSWORD = os.getenv("ICLOUD_APP_PASSWORD", "").strip()

# Directorios de trabajo
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

ORDERS_FILE = BASE_DIR / "REMOTE_ORDERS.jsonl"
