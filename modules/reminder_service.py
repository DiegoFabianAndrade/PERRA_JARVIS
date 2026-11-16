"""
Módulo de Recordatorios y Alarmas para PERRA_JARVIS.
Permite programar alertas con notificaciones push sonoras a Telegram a la hora exacta:
- Parsing de expresiones en lenguaje natural ("en 15 minutos", "a las 7:30 pm", "mañana a las 9 am").
- Persistencia en JSON local.
- Vigilancia continua en segundo plano.
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from config import TEMP_DIR

REMINDERS_FILE = TEMP_DIR / "reminders.json"


def _load_reminders() -> List[Dict[str, Any]]:
    if not REMINDERS_FILE.exists():
        return []
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reminders(reminders: List[Dict[str, Any]]):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


def parse_target_time(time_str: str) -> Optional[datetime]:
    """Interpreta expresiones temporales en español."""
    now = datetime.now()
    s = time_str.lower().strip()

    # 1. "en X minutos" / "en X horas"
    m_min = re.search(r"en\s+(\d+)\s+min", s)
    if m_min:
        return now + timedelta(minutes=int(m_min.group(1)))

    m_hour = re.search(r"en\s+(\d+)\s+hora", s)
    if m_hour:
        return now + timedelta(hours=int(m_hour.group(1)))

    # 2. "a las HH:MM (am/pm)" o "a las HH"
    m_time = re.search(r"(?:a las|a la)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if m_time:
        hour = int(m_time.group(1))
        minute = int(m_time.group(2)) if m_time.group(2) else 0
        ampm = m_time.group(3)

        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        elif not ampm and hour < 7:  # Asumir tarde si es número pequeño sin am/pm
            hour += 12

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Si la hora ya pasó hoy o dice "mañana", pasar a mañana
        if "mañana" in s or target <= now:
            target += timedelta(days=1)
        return target

    return None


def add_reminder(text: str, time_expr: str) -> Dict[str, Any]:
    """Crea y registra un recordatorio con hora objetivo."""
    target_dt = parse_target_time(time_expr)
    if not target_dt:
        # Fallback por defecto: en 30 minutos si no se especificó hora exacta
        target_dt = datetime.now() + timedelta(minutes=30)

    reminders = _load_reminders()
    reminder_id = int(datetime.now().timestamp())
    item = {
        "id": reminder_id,
        "text": text.strip(),
        "time_str": time_expr.strip(),
        "due_iso": target_dt.isoformat(),
        "notified": False
    }
    reminders.append(item)
    _save_reminders(reminders)
    return {
        "id": reminder_id,
        "text": text,
        "due_formatted": target_dt.strftime("%I:%M %p (%d/%b)"),
        "minutes_left": int((target_dt - datetime.now()).total_seconds() / 60)
    }


def check_due_reminders() -> List[Dict[str, Any]]:
    """Devuelve los recordatorios cuya hora ya se cumplió y no han sido notificados."""
    reminders = _load_reminders()
    now = datetime.now()
    due = []
    modified = False

    for r in reminders:
        if not r.get("notified", False):
            try:
                due_dt = datetime.fromisoformat(r["due_iso"])
                if now >= due_dt:
                    r["notified"] = True
                    due.append(r)
                    modified = True
            except Exception:
                continue

    if modified:
        _save_reminders(reminders)

    return due


def format_active_reminders() -> str:
    """Muestra la lista de recordatorios activos pendientes."""
    reminders = _load_reminders()
    now = datetime.now()
    active = [r for r in reminders if not r.get("notified") and datetime.fromisoformat(r["due_iso"]) > now]

    if not active:
        return (
            "🔔 *RECORDATORIOS Y ALARMAS*\n"
            "─────────────────────────────\n"
            "🎉 _No tienes recordatorios pendientes._\n\n"
            "💡 *¿Cómo crear uno?*\n"
            "Solo dímelo por texto o nota de voz:\n"
            "• _'Recuérdame a las 8:30 pm revisar el correo'_\n"
            "• _'Recuérdame en 20 minutos apagar el horno'_\n"
            "─────────────────────────────"
        )

    lines = ["🔔 *TUS RECORDATORIOS ACTIVOS:*"]
    lines.append("─────────────────────────────")
    for r in active:
        due = datetime.fromisoformat(r["due_iso"])
        hora = due.strftime("%I:%M %p (%d/%b)")
        lines.append(f"• ⏰ `{hora}`: *{r['text']}*")
    lines.append("─────────────────────────────")
    return "\n".join(lines)
