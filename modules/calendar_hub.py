"""
Módulo de Calendario (Calendar Hub) para PERRA_JARVIS.
Soporte para:
- Calendario de iPhone (iCloud) mediante suscripción Webcal (.ics) o CalDAV.
- Filtrado inteligente de eventos para hoy y próximos días.
- Formateo de agenda para Telegram.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import requests
from icalendar import Calendar

from config import ICLOUD_CALENDAR_URL


def fetch_icalendar_events(days_ahead: int = 3) -> List[Dict[str, Any]]:
    """Descarga y procesa eventos de calendario desde un enlace iCalendar (.ics / webcal)."""
    if not ICLOUD_CALENDAR_URL:
        return []

    url = ICLOUD_CALENDAR_URL.strip()
    # Convertir webcal:// a https://
    if url.startswith("webcal://"):
        url = "https://" + url[9:]

    events = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            cal = Calendar.from_ical(resp.content)
            now = datetime.now()
            max_date = now + timedelta(days=days_ahead)

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get("summary", "Sin título"))
                    dtstart = component.get("dtstart")
                    dtend = component.get("dtend")
                    location = str(component.get("location", ""))

                    if not dtstart:
                        continue

                    start_val = dtstart.dt
                    end_val = dtend.dt if dtend else start_val

                    # Manejar tanto datetime como date puro
                    if isinstance(start_val, datetime):
                        # Normalizar a naive si tiene tzinfo
                        start_naive = start_val.replace(tzinfo=None)
                    else:
                        start_naive = datetime.combine(start_val, datetime.min.time())

                    # Filtrar dentro del rango de interés
                    if (now - timedelta(hours=4)) <= start_naive <= max_date:
                        events.append({
                            "summary": summary,
                            "start": start_naive,
                            "location": location if location and location != "None" else None,
                            "is_today": start_naive.date() == now.date()
                        })

            events.sort(key=lambda x: x["start"])
    except Exception as e:
        print(f"Error consultando calendario: {e}")

    return events


def format_schedule_summary() -> str:
    """Genera el reporte de agenda diaria para Telegram."""
    if not ICLOUD_CALENDAR_URL:
        return (
            "📅 *AGENDA & CALENDARIO IPHONE*\n"
            "─────────────────────────────\n"
            "⚠️ _Calendario de iPhone no configurado aún._\n\n"
            "💡 *¿Cómo conectarlo en 1 minuto?*\n"
            "1. En tu iPhone ve a la app **Calendarios**.\n"
            "2. Toca la `(i)` junto a tu calendario y activa **'Calendario público'**.\n"
            "3. Copia el enlace y pégalo en tu `.env` en `ICLOUD_CALENDAR_URL=...`\n"
            "─────────────────────────────"
        )

    events = fetch_icalendar_events(days_ahead=3)
    lines = ["📅 *TU AGENDA (CALENDARIO IPHONE)*"]
    lines.append("─────────────────────────────")

    if not events:
        lines.append("🎉 _No tienes eventos pendientes para hoy ni los próximos días._")
    else:
        today_events = [e for e in events if e["is_today"]]
        future_events = [e for e in events if not e["is_today"]]

        if today_events:
            lines.append("📍 *EVENTOS PARA HOY:*")
            for e in today_events:
                hora = e["start"].strftime("%I:%M %p")
                loc = f" (📌 {e['location']})" if e["location"] else ""
                lines.append(f"• ⏰ `{hora}`: *{e['summary']}*{loc}")
            lines.append("")

        if future_events:
            lines.append("🔮 *PRÓXIMOS DÍAS:*")
            for e in future_events[:4]:
                dia_hora = e["start"].strftime("%a %d/%b - %I:%M %p")
                loc = f" (📌 {e['location']})" if e["location"] else ""
                lines.append(f"• 🗓️ `{dia_hora}`: *{e['summary']}*{loc}")

    lines.append("─────────────────────────────")
    return "\n".join(lines)
