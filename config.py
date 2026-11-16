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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_raw_chat_id = os.getenv("ALLOWED_CHAT_ID", "1257398092").strip()
try:
    ALLOWED_CHAT_ID = int(_raw_chat_id)
except ValueError:
    ALLOWED_CHAT_ID = 1257398092

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "PERRA_JARVIS").strip()
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Directorios de trabajo
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
