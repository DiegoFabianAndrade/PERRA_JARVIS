"""
Script de autenticación de un solo paso para Google Calendar API.
Abre tu navegador para autorizar a PERRA_JARVIS y genera token.json de forma permanente.
"""

import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_credentials():
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"Aviso leyendo token existente: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f"No se encontró {CREDENTIALS_FILE}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES
            )
            # Imprimir URL explícita para el usuario
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
            print(f"\n=======================================================", flush=True)
            print(f"POR FAVOR ABRE ESTE ENLACE EN TU NAVEGADOR:\n{auth_url}", flush=True)
            print(f"=======================================================\n", flush=True)

            # Inicia servidor local para capturar el callback de OAuth2
            creds = flow.run_local_server(port=0, prompt="consent", open_browser=True)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        print(f"✅ token.json generado con éxito en {TOKEN_FILE}")

    return creds


if __name__ == "__main__":
    print("Iniciando autenticación de Google Calendar...")
    creds = get_calendar_credentials()
    print("¡Listo! Conexión con Google Calendar establecida.")
