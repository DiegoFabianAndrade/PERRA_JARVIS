"""
Módulo de Calendario (Calendar Hub) para PERRA_JARVIS.
Soporte para:
- Múltiples calendarios de iPhone (iCloud) mediante suscripción Webcal (.ics).
- Fusión inteligente de calendarios (ej. Casa, Trabajo, Universidad).
- Filtrado inteligente de eventos para hoy y próximos días.
- Formateo de agenda para Telegram.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import requests
from icalendar import Calendar

from config import ICLOUD_CALENDAR_URL


def fetch_icalendar_events(days_ahead: int = 4) -> List[Dict[str, Any]]:
    """Descarga y procesa eventos de uno o varios enlaces iCalendar (.ics / webcal)."""
    if not ICLOUD_CALENDAR_URL:
        return []

    # Soporte para múltiples calendarios separados por coma o salto de línea
    raw_urls = [u.strip() for u in ICLOUD_CALENDAR_URL.replace(";", ",").split(",") if u.strip()]
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
                        end_val = dtend.dt if dtend else start_val

                        # Normalizar a naive datetime
                        if isinstance(start_val, datetime):
                            start_naive = start_val.replace(tzinfo=None)
                        else:
                            start_naive = datetime.combine(start_val, datetime.min.time())

                        # Filtrar eventos desde hoy temprano hasta días adelante
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
            print(f"Error consultando calendario {url[:30]}...: {e}")

    # Ordenar cronológicamente
    all_events.sort(key=lambda x: x["start"])
    return all_events


def format_schedule_summary() -> str:
    """Genera el reporte de agenda diaria para Telegram."""
    if not ICLOUD_CALENDAR_URL:
        return (
            "📅 *AGENDA & CALENDARIO IPHONE*\n"
            "─────────────────────────────\n"
            "⚠️ _Calendario de iPhone no configurado aún._\n\n"
            "💡 Pega el enlace en tu `.env` en `ICLOUD_CALENDAR_URL=...`\n"
            "─────────────────────────────"
        )

    events = fetch_icalendar_events(days_ahead=4)
    lines = ["📅 *TU AGENDA (CALENDARIO IPHONE)*"]
    lines.append("─────────────────────────────")

    if not events:
        lines.append("🎉 _¡No tienes eventos pendientes para hoy ni los próximos días!_")
        lines.append("\n💡 _(Si tienes clases o tareas en el calendario de 'Trabajo', puedes compartir también ese enlace y los combinamos)._")
    else:
        today_events = [e for e in events if e["is_today"]]
        future_events = [e for e in events if not e["is_today"]]

        if today_events:
            lines.append("📍 *EVENTOS PARA HOY:*")
            for e in today_events:
                hora = e["start"].strftime("%I:%M %p")
                cal_tag = f" `[{e['calendar']}]`" if e.get("calendar") else ""
                loc = f"\n   📌 Lugar: {e['location']}" if e["location"] else ""
                lines.append(f"• ⏰ `{hora}`: *{e['summary']}*{cal_tag}{loc}")
            lines.append("")

        if future_events:
            lines.append("🔮 *PRÓXIMOS DÍAS:*")
            for e in future_events[:6]:
                dia_hora = e["start"].strftime("%a %d/%b - %I:%M %p")
                cal_tag = f" `[{e['calendar']}]`" if e.get("calendar") else ""
                loc = f" (📌 {e['location']})" if e["location"] else ""
                lines.append(f"• 🗓️ `{dia_hora}`: *{e['summary']}*{cal_tag}{loc}")

    lines.append("─────────────────────────────")
    return "\n".join(lines)
