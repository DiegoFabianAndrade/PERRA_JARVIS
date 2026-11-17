"""
Módulo de Calendario (Calendar Hub) para PERRA_JARVIS.
Soporte para:
- Google Calendar API Oficial (Lectura y Escritura en tiempo real con OAuth2 token.json).
- Calendarios de iPhone (iCloud) mediante suscripción Webcal (.ics).
- Fusión inteligente de eventos (Google Calendar + iCloud Casa/Trabajo).
- Inserción directa de eventos desde órdenes de texto o notas de voz.
- Sincronización con recordatorios y alarmas push en Telegram.
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from icalendar import Calendar

from config import ICLOUD_CALENDAR_URL, GOOGLE_CALENDAR_URL, GMAIL_USER, GMAIL_APP_PASSWORD, BASE_DIR
from modules import reminder_service

TOKEN_FILE = BASE_DIR / "token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_google_calendar_service():
    """Obtiene o refresca el servicio oficial de Google Calendar API."""
    if not TOKEN_FILE.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"Error inicializando Google Calendar API: {e}")
        return None


def fetch_google_calendar_events(days_ahead: int = 4) -> List[Dict[str, Any]]:
    """Consulta eventos usando la API oficial de Google Calendar."""
    service = get_google_calendar_service()
    if not service:
        return []

    try:
        now = datetime.now()
        start_of_today = datetime.combine(now.date(), datetime.min.time())
        now_utc = datetime.now(timezone.utc).isoformat()
        max_date_utc = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now_utc,
            timeMax=max_date_utc,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        items = events_result.get("items", [])
        events = []

        for item in items:
            summary = item.get("summary", "Sin título")
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            location = item.get("location")

            start_str = start_raw.get("dateTime") or start_raw.get("date")
            if not start_str:
                continue

            # Parsear dateTime o date
            if "T" in start_str:
                # Quitar información de zona horaria compleja para comparar
                dt_clean = start_str.split("+")[0].split("Z")[0]
                start_dt = datetime.fromisoformat(dt_clean)
            else:
                d = date.fromisoformat(start_str)
                start_dt = datetime.combine(d, datetime.min.time())

            events.append({
                "summary": summary,
                "start": start_dt,
                "location": location,
                "calendar": "Google Calendar",
                "html_link": item.get("htmlLink"),
                "is_today": start_dt.date() == now.date()
            })

        return events
    except Exception as e:
        print(f"Error consultando eventos de Google Calendar API: {e}")
        return []


def fetch_icalendar_events(days_ahead: int = 4) -> List[Dict[str, Any]]:
    """Descarga y procesa eventos de iCloud y enlaces Webcal (.ics)."""
    urls_combined = []
    if ICLOUD_CALENDAR_URL:
        urls_combined.append(ICLOUD_CALENDAR_URL)
    if GOOGLE_CALENDAR_URL:
        urls_combined.append(GOOGLE_CALENDAR_URL)

    if not urls_combined:
        return []

    raw_urls = []
    for raw in urls_combined:
        for u in raw.replace(";", ",").split(","):
            if u.strip():
                raw_urls.append(u.strip())
    if not raw_urls:
        return []

    all_events = []
    now = datetime.now()
    max_date = now + timedelta(days=days_ahead)

    for raw_url in raw_urls:
        url = raw_url
        if url.startswith("webcal://"):
            url = "https://" + url[9:]

        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                cal = Calendar.from_ical(resp.content)
                cal_name = str(cal.get("X-WR-CALNAME", "iPhone"))

                for component in cal.walk():
                    if component.name == "VEVENT":
                        summary = str(component.get("summary", "Sin título"))
                        dtstart = component.get("dtstart")
                        dtend = component.get("dtend")
                        location = str(component.get("location", ""))

                        if not dtstart:
                            continue

                        start_val = dtstart.dt
                        if isinstance(start_val, datetime):
                            start_naive = start_val.replace(tzinfo=None)
                        else:
                            start_naive = datetime.combine(start_val, datetime.min.time())

                        start_of_today = datetime.combine(now.date(), datetime.min.time())
                        if start_of_today <= start_naive <= max_date:
                            all_events.append({
                                "summary": summary,
                                "start": start_naive,
                                "location": location if location and location != "None" else None,
                                "calendar": cal_name,
                                "is_today": start_naive.date() == now.date()
                            })
        except Exception as e:
            print(f"Error consultando calendario Webcal: {e}")

    return all_events


def fetch_all_calendar_events(days_ahead: int = 4) -> List[Dict[str, Any]]:
    """Combina eventos de Google Calendar API y iCloud."""
    google_events = fetch_google_calendar_events(days_ahead=days_ahead)
    ical_events = fetch_icalendar_events(days_ahead=days_ahead)

    # Evitar duplicados por título y hora
    seen = set()
    combined = []

    for e in google_events + ical_events:
        key = (e["summary"].strip().lower(), e["start"].strftime("%Y-%m-%d %H:%M"))
        if key not in seen:
            seen.add(key)
            combined.append(e)

    combined.sort(key=lambda x: x["start"])
    return combined


def format_schedule_summary() -> str:
    """Genera el reporte de agenda consolidada para Telegram."""
    events = fetch_all_calendar_events(days_ahead=4)
    has_google = TOKEN_FILE.exists()
    has_icloud = bool(ICLOUD_CALENDAR_URL)

    if not has_google and not has_icloud and not GOOGLE_CALENDAR_URL:
        return (
            "📅 *AGENDA & CALENDARIO*\n"
            "─────────────────────────────\n"
            "⚠️ _Calendario no vinculado aún._\n\n"
            "💡 Puedes vincular tu Google Calendar o tus calendarios de iCloud.\n"
            "─────────────────────────────"
        )

    lines = ["📅 *TU AGENDA (GOOGLE & IPHONE)*"]
    lines.append("─────────────────────────────")

    if not events:
        lines.append("🎉 _¡No tienes eventos pendientes para hoy ni los próximos días!_")
        lines.append("\n💡 Puedes pedirme: *'Agéndame reunión mañana a las 3 pm'*")
    else:
        today_events = [e for e in events if e["is_today"]]
        future_events = [e for e in events if not e["is_today"]]

        if today_events:
            lines.append("📍 *EVENTOS PARA HOY:*")
            for e in today_events:
                hora = e["start"].strftime("%I:%M %p")
                cal_tag = f" `[{e['calendar']}]`" if e.get("calendar") else ""
                loc = f"\n   📌 Lugar: {e['location']}" if e.get("location") else ""
                lines.append(f"• ⏰ `{hora}`: *{e['summary']}*{cal_tag}{loc}")
            lines.append("")

        if future_events:
            lines.append("🔮 *PRÓXIMOS DÍAS:*")
            for e in future_events[:6]:
                dia_hora = e["start"].strftime("%a %d/%b - %I:%M %p")
                cal_tag = f" `[{e['calendar']}]`" if e.get("calendar") else ""
                loc = f" (📌 {e['location']})" if e.get("location") else ""
                lines.append(f"• 🗓️ `{dia_hora}`: *{e['summary']}*{cal_tag}{loc}")

    lines.append("─────────────────────────────")
    return "\n".join(lines)


def create_calendar_event(
    title: str,
    time_expression: str,
    duration_minutes: int = 60,
    description: str = "Evento agendado por PERRA_JARVIS"
) -> Dict[str, Any]:
    """
    Crea un evento DIRECTAMENTE en Google Calendar mediante la API oficial
    y programa la alarma push en Telegram.
    """
    start_dt = reminder_service.parse_target_time(time_expression)
    if not start_dt:
        start_dt = datetime.now() + timedelta(hours=1)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    # 1. Intentar inserción directa vía Google Calendar API oficial
    service = get_google_calendar_service()
    api_created = False
    html_link = None

    if service:
        try:
            event_body = {
                "summary": title.strip(),
                "description": description.strip(),
                "start": {
                    "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "America/Bogota",
                },
                "end": {
                    "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "America/Bogota",
                },
                "reminders": {
                    "useDefault": True
                }
            }
            res = service.events().insert(calendarId="primary", body=event_body).execute()
            html_link = res.get("htmlLink")
            api_created = True
            print(f"Evento creado exitosamente en Google Calendar API: {res.get('id')}")
        except Exception as e:
            print(f"Error insertando evento vía Google Calendar API: {e}")

    # 2. Registrar alarma con sonido en Telegram
    reminder_service.add_reminder(f"📅 {title}", time_expression)

    return {
        "success": True,
        "api_created": api_created,
        "html_link": html_link,
        "title": title,
        "date_formatted": start_dt.strftime("%a %d/%b a las %I:%M %p"),
        "minutes_left": int((start_dt - datetime.now()).total_seconds() / 60)
    }


def update_calendar_url(url: str, is_google: bool = True) -> bool:
    """Guarda una URL de calendario en el archivo .env y actualiza en caliente."""
    import os
    import config
    global GOOGLE_CALENDAR_URL, ICLOUD_CALENDAR_URL
    env_path = BASE_DIR / ".env"
    key = "GOOGLE_CALENDAR_URL" if is_google else "ICLOUD_CALENDAR_URL"
    clean_url = url.strip()

    if is_google:
        GOOGLE_CALENDAR_URL = clean_url
        config.GOOGLE_CALENDAR_URL = clean_url
        os.environ["GOOGLE_CALENDAR_URL"] = clean_url
    else:
        ICLOUD_CALENDAR_URL = clean_url
        config.ICLOUD_CALENDAR_URL = clean_url
        os.environ["ICLOUD_CALENDAR_URL"] = clean_url

    if not env_path.exists():
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"{key}={clean_url}\n")
        return True

    lines = []
    found = False
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(f"{key}="):
                lines.append(f"{key}={clean_url}\n")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"\n# Calendario agregado automáticamente\n{key}={clean_url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True
