"""
Monitor Proactivo de PERRA_JARVIS.
Ejecuta vigilancia en segundo plano para notificar activamente a Diego:
- Alertas de batería baja (<20%) y batería llena (100%).
- Generación de Briefing Ejecutivo Diario consolidado.
"""

import time
import asyncio
import psutil
from typing import Optional, Callable, Dict, Any

from modules import weather_service
from modules import calendar_hub
from modules import email_hub
from modules import market_tracker
from modules import pc_controller
from modules import antigravity_bridge


class ProactiveMonitor:
    def __init__(self, bot_send_func: Optional[Callable] = None):
        self.bot_send_func = bot_send_func
        self.low_battery_alerted = False
        self.full_battery_alerted = False
        self.running = False

    def check_battery(self) -> Optional[str]:
        """Revisa la batería y genera alerta proactiva si es necesario."""
        battery = psutil.sensors_battery()
        if not battery:
            return None

        # Alerta de batería baja
        if not battery.power_plugged and battery.percent <= 20:
            if not self.low_battery_alerted:
                self.low_battery_alerted = True
                return (
                    f"⚠️ *ALERTA PROACTIVA JARVIS*\n\n"
                    f"🔋 Batería de tu portátil al `{battery.percent}%` y desconectado.\n"
                    f"Conéctalo a corriente pronto para no interrumpir tus tareas."
                )
        elif battery.power_plugged:
            self.low_battery_alerted = False  # Resetear cuando se conecta

        # Alerta de batería cargada al 100%
        if battery.power_plugged and battery.percent >= 99:
            if not self.full_battery_alerted:
                self.full_battery_alerted = True
                return (
                    f"⚡ *BATERÍA CARGADA*\n\n"
                    f"Tu portátil ya alcanzó el `100%` de carga. "
                    f"Puedes desconectarlo si deseas cuidar los ciclos de batería."
                )
        elif not battery.power_plugged:
            self.full_battery_alerted = False

        return None

    def get_executive_briefing(self) -> str:
        """Genera un reporte ejecutivo diario ultra completo y proactivo."""
        fecha_str = time.strftime("%A, %d de %B de %Y")
        
        # 1. Clima
        clima_str = weather_service.format_weather_summary()

        # 2. Batería y PC
        stats = pc_controller.get_system_stats()
        b = stats.get("battery")
        bat_str = f"🔋 {b['percent']}%" if b else "🔌 Escritorio"
        if b and b["plugged"]:
            bat_str += " (Cargando ⚡)"

        # 3. TRM
        trm_records = market_tracker.fetch_trm_history(2)
        trm_val = trm_records[0]["valor"] if trm_records else 0

        # 4. Correos
        gmail_list = email_hub.fetch_gmail_emails(limit=3, unread_only=True)
        if gmail_list:
            mail_summary = f"Tienes *{len(gmail_list)} correos sin leer*. Último: _{gmail_list[0]['subject']}_"
        else:
            mail_summary = "Bandeja de Gmail al día (0 correos sin leer)."

        # 5. Calendario
        cal_events = calendar_hub.fetch_icalendar_events(days_ahead=1)
        today_events = [e for e in cal_events if e.get("is_today")]
        if today_events:
            event_lines = [f"• `{e['start'].strftime('%I:%M %p')}` {e['summary']}" for e in today_events]
            cal_summary = f"*{len(today_events)} eventos para hoy:*\n" + "\n".join(event_lines)
        else:
            cal_summary = "Sin eventos agendados para hoy."

        # 6. Órdenes pendientes
        orders = antigravity_bridge.list_pending_orders()
        orders_str = f"📋 *Órdenes de código pendientes:* `{len(orders)}`" if orders else "📋 *Buzón de código:* Al día."

        briefing = (
            f"☀️ *BRIEFING EJECUTIVO - PERRA_JARVIS*\n"
            f"📅 `{fecha_str}`\n"
            "─────────────────────────────\n"
            f"{clima_str}\n\n"
            f"💵 *TRM Dólar:* `${trm_val:,.2f} COP`\n"
            f"💻 *Portátil:* {bat_str} | RAM: `{stats['ram_percent']}%`\n"
            "─────────────────────────────\n"
            f"📬 *Gmail:* {mail_summary}\n\n"
            f"📅 *Agenda:* {cal_summary}\n\n"
            f"{orders_str}\n"
            "─────────────────────────────\n"
            "✨ _Jarvis activo y a tu disposición._"
        )
        return briefing


monitor = ProactiveMonitor()
