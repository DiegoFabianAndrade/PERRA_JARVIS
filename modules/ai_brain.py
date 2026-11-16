"""
Cerebro Inteligente (AI Brain) para PERRA_JARVIS.
Combina:
1. Modelos Gemini de última generación (gemini-3.5-flash y gemini-3.8-flash) con Function Calling y Visión.
2. Soporte nativo para notas de voz de Telegram y análisis de imágenes enviadas desde el móvil.
3. Resiliencia con conmutación por error entre modelos (Model Fallback).
4. Motor de intenciones semánticas local de respaldo.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from config import GEMINI_API_KEY, ASSISTANT_NAME, TEMP_DIR
from modules import pc_controller
from modules import market_tracker
from modules import antigravity_bridge
from modules import email_hub
from modules import calendar_hub
from modules import whatsapp_controller
from modules import weather_service
from modules.proactive_monitor import monitor

CANDIDATE_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]

SYSTEM_INSTRUCTION = (
    f"Eres {ASSISTANT_NAME}, el asistente personal ejecutivo de primer nivel de Diego Fabián Andrade. "
    "Tienes control operativo directo sobre su computador Windows (capturas, hardware, apps, volumen, archivos), "
    "gestión de finanzas (TRM USD/COP, criptomonedas), consulta de correos (Gmail), "
    "agenda del calendario de iPhone, control de WhatsApp, clima y puente remoto con su entorno de desarrollo Antigravity. "
    "Responde siempre de forma proactiva, leal, precisa y con estilo Jarvis de Iron Man. "
    "Cuando Diego te pida una acción, invoca las herramientas correspondientes de forma autónoma."
)

# Herramientas del sistema para Function Calling
def get_system_telemetry() -> str:
    """Obtiene métricas de CPU, RAM, batería y disco del PC."""
    stats = pc_controller.get_system_stats()
    return pc_controller.format_stats_message(stats)

def capture_pc_screen() -> str:
    """Toma una captura de pantalla del computador y devuelve confirmación."""
    path = pc_controller.take_screenshot("telegram_screen.png")
    return f"SCREENSHOT_TAKEN:{path}"

def lock_computer() -> str:
    """Bloquea inmediatamente la sesión de Windows por seguridad."""
    ok = pc_controller.lock_pc()
    return "PC bloqueado con éxito." if ok else "No se pudo bloquear el PC."

def open_app(app_name: str) -> str:
    """Abre un programa en Windows como Chrome, Spotify, VS Code, Calc, Notepad, etc."""
    return pc_controller.open_application(app_name)

def control_audio(action: str) -> str:
    """Controla el volumen o reproducción: subir, bajar, silenciar, play, pausa."""
    return pc_controller.media_control(action)

def get_market_data() -> str:
    """Consulta la TRM oficial de Colombia (USD/COP) y precios de criptomonedas."""
    return market_tracker.format_market_summary()

def check_recent_downloads() -> str:
    """Lista los archivos descargados recientemente en la carpeta Downloads."""
    files = pc_controller.list_downloads(5)
    if not files:
        return "No hay archivos recientes en la carpeta Descargas."
    res = ["📁 *Archivos recientes en Descargas:*"]
    for f in files:
        res.append(f"• `{f['name']}` ({f['size_mb']} MB)")
    return "\n".join(res)

def run_powershell_cmd(command: str) -> str:
    """Ejecuta un comando en la terminal PowerShell del computador de Diego."""
    return pc_controller.run_command(command)

def check_emails() -> str:
    """Consulta los correos recientes de Gmail."""
    return email_hub.format_emails_summary()

def check_calendar_schedule() -> str:
    """Consulta los eventos y compromisos del calendario de iPhone para hoy y próximos días."""
    return calendar_hub.format_schedule_summary()

def check_weather() -> str:
    """Consulta el clima actual y pronóstico para Bogotá."""
    return weather_service.format_weather_summary()

def get_daily_briefing() -> str:
    """Genera el briefing ejecutivo del día (clima, batería, agenda, correos, finanzas)."""
    return monitor.get_executive_briefing()

def list_dev_projects() -> str:
    """Lista los proyectos de código y repositorios en el computador de Diego."""
    projs = antigravity_bridge.list_local_projects()
    if not projs:
        return "No se encontraron proyectos en la carpeta Descargas."
    return "🧑‍💻 *Proyectos en tu PC:*\n" + "\n".join(f"• `{p}`" for p in projs)

def send_whatsapp(phone: str, message: str) -> str:
    """Abre o despacha un mensaje de WhatsApp a un contacto."""
    return whatsapp_controller.send_whatsapp_message(phone, message)

TOOLS_REGISTRY = {
    "get_system_telemetry": get_system_telemetry,
    "capture_pc_screen": capture_pc_screen,
    "lock_computer": lock_computer,
    "open_app": open_app,
    "control_audio": control_audio,
    "get_market_data": get_market_data,
    "check_recent_downloads": check_recent_downloads,
    "run_powershell_cmd": run_powershell_cmd,
    "check_emails": check_emails,
    "check_calendar_schedule": check_calendar_schedule,
    "check_weather": check_weather,
    "get_daily_briefing": get_daily_briefing,
    "list_dev_projects": list_dev_projects,
    "send_whatsapp": send_whatsapp,
}


class JarvisBrain:
    def __init__(self):
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        """Inicializa el cliente de Gemini si la API key está presente."""
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Error inicializando Gemini: {e}")
                self.client = None

    def process_text(self, text: str) -> Dict[str, Any]:
        """Procesa una orden de texto proveniente de Telegram."""
        text_clean = text.strip()

        if self.client:
            for model_name in CANDIDATE_MODELS:
                try:
                    from google.genai import types
                    tools_list = list(TOOLS_REGISTRY.values())

                    config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=tools_list,
                        temperature=0.4
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=text_clean,
                        config=config
                    )

                    if response.function_calls:
                        for fc in response.function_calls:
                            func_name = fc.name
                            args = fc.args or {}
                            if func_name in TOOLS_REGISTRY:
                                fn = TOOLS_REGISTRY[func_name]
                                fn_result = fn(**args)
                                
                                if isinstance(fn_result, str) and fn_result.startswith("SCREENSHOT_TAKEN:"):
                                    photo_path = fn_result.split(":", 1)[1]
                                    return {
                                        "text": "📸 Aquí tienes la captura en tiempo real de tu pantalla, Diego.",
                                        "photo": photo_path
                                    }
                                return {"text": fn_result}

                    if response.text:
                        return {"text": response.text}
                except Exception as e:
                    print(f"Aviso: Fallo con modelo {model_name}: {e}. Intentando alternativa...")
                    continue

        return self._local_intent_fallback(text_clean)

    def process_voice_file(self, voice_path: Path) -> Dict[str, Any]:
        """Procesa una nota de voz enviada por Diego desde Telegram."""
        if not self.client:
            return {
                "text": "🎙️ Recibí tu nota de voz, pero necesitas configurar tu `GEMINI_API_KEY` en `.env` "
                        "para que pueda transcribirla y entender tu voz gratis."
            }

        with open(voice_path, "rb") as f:
            audio_bytes = f.read()

        for model_name in CANDIDATE_MODELS:
            try:
                from google.genai import types
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
                instruction = "Transcribe y ejecuta la siguiente orden de Diego como Jarvis."
                tools_list = list(TOOLS_REGISTRY.values())

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools_list,
                    temperature=0.3
                )

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[audio_part, instruction],
                    config=config
                )

                if response.function_calls:
                    for fc in response.function_calls:
                        func_name = fc.name
                        args = fc.args or {}
                        if func_name in TOOLS_REGISTRY:
                            fn = TOOLS_REGISTRY[func_name]
                            fn_result = fn(**args)
                            if isinstance(fn_result, str) and fn_result.startswith("SCREENSHOT_TAKEN:"):
                                return {
                                    "text": "📸 Orden por voz ejecutada: Captura de pantalla tomada.",
                                    "photo": fn_result.split(":", 1)[1]
                                }
                            return {"text": f"🎙️ *Orden por voz procesada:*\n\n{fn_result}"}

                if response.text:
                    return {"text": f"🎙️ *Transcripción y respuesta:*\n{response.text}"}
            except Exception as e:
                print(f"Error procesando voz con {model_name}: {e}")
                continue

        return {"text": "⚠️ No se pudo procesar el audio en este momento. Intenta de nuevo o envía texto."}

    def process_photo(self, photo_bytes: bytes, caption: Optional[str] = None) -> str:
        """Analiza con Gemini Vision una foto enviada por Diego desde su celular."""
        if not self.client:
            return "📸 Recibí tu foto. Para que pueda analizarla visualmente con IA, añade tu `GEMINI_API_KEY` en `.env`."

        for model_name in CANDIDATE_MODELS:
            try:
                from google.genai import types
                img_part = types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")
                prompt = caption if caption else "Analiza esta imagen con detalle y dame la información o solución que necesita Diego."

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[img_part, prompt],
                )
                if response.text:
                    return f"👁️ *Análisis Visual Jarvis:*\n\n{response.text}"
            except Exception as e:
                print(f"Error procesando foto con {model_name}: {e}")
                continue

        return "⚠️ Error analizando imagen con los modelos de visión."

    def _local_intent_fallback(self, query: str) -> Dict[str, Any]:
        """Parser de intenciones locales sin necesidad de API externa."""
        q = query.lower()

        # Briefing Diario
        if any(w in q for w in ["briefing", "resumen diario", "buenos dias", "buenos días", "mi dia", "mi día"]):
            return {"text": monitor.get_executive_briefing()}

        # Clima
        if any(w in q for w in ["clima", "tiempo", "temperatura", "lluvia"]):
            return {"text": weather_service.format_weather_summary()}

        # Pantallazo
        if any(w in q for w in ["pantallazo", "captura", "screenshot", "screen", "pantalla"]):
            path = pc_controller.take_screenshot("screen.png")
            return {"text": "📸 Captura de pantalla tomada en este instante:", "photo": str(path)}

        # Estado del PC
        if any(w in q for w in ["estado", "status", "bateria", "batería", "ram", "cpu", "pc"]):
            stats = pc_controller.get_system_stats()
            return {"text": pc_controller.format_stats_message(stats)}

        # Correos (Gmail)
        if any(w in q for w in ["correo", "correos", "email", "emails", "gmail", "bandeja"]):
            return {"text": email_hub.format_emails_summary()}

        # Calendario / Agenda
        if any(w in q for w in ["calendario", "agenda", "eventos", "clases", "compromisos", "horario"]):
            return {"text": calendar_hub.format_schedule_summary()}

        # Proyectos / Antigravity Bridge
        if any(w in q for w in ["proyecto", "proyectos", "repos", "codigo", "código", "antigravity"]):
            return {"text": list_dev_projects()}

        # WhatsApp
        if "whatsapp" in q or "wapp" in q:
            return {"text": whatsapp_controller.get_whatsapp_status_report()}

        # Bloquear PC
        if any(w in q for w in ["bloquear", "bloquea", "lock"]):
            ok = pc_controller.lock_pc()
            msg = "🔒 Computador bloqueado exitosamente." if ok else "⚠️ No se pudo bloquear la estación."
            return {"text": msg}

        # Mercado / Dólar / TRM
        if any(w in q for w in ["dolar", "dólar", "trm", "precio", "mercado", "bitcoin", "crypto", "cripto"]):
            return {"text": market_tracker.format_market_summary()}

        # Gráfica TRM
        if any(w in q for w in ["grafica", "gráfica", "grafico", "chart", "tendencia"]):
            chart = market_tracker.generate_trm_chart("trm_chart.png", 20)
            if chart:
                return {
                    "text": "📈 Historial TRM USD/COP (Superfinanciera):",
                    "photo": str(chart)
                }
            return {"text": "⚠️ No se pudo generar la gráfica en este momento."}

        # Control Multimedia
        if "silenciar" in q or "mute" in q:
            return {"text": pc_controller.media_control("mute")}
        if "subir volumen" in q or "mas volumen" in q:
            return {"text": pc_controller.media_control("up")}
        if "bajar volumen" in q or "menos volumen" in q:
            return {"text": pc_controller.media_control("down")}
        if any(w in q for w in ["pausa", "play", "reproducir"]):
            return {"text": pc_controller.media_control("play")}

        # Abrir aplicaciones
        m_app = re.search(r"abrir?\s+([a-zA-Z0-9_\-\.]+)", q)
        if m_app:
            return {"text": pc_controller.open_application(m_app.group(1))}

        # Descargas recientes
        if "descargas" in q or "downloads" in q or "archivos" in q:
            return {"text": check_recent_downloads()}

        # Ayuda general
        return {
            "text": (
                f"🤖 *{ASSISTANT_NAME} activo y escuchando*\n\n"
                "Puedes darme órdenes por texto, botones o notas de voz:\n"
                "• *☀️ Briefing:* 'Dame mi briefing diario'\n"
                "• *🌦️ Clima:* '¿Cómo está el clima en Bogotá?'\n"
                "• *📧 Correos:* 'Revisa mis correos de Gmail'\n"
                "• *📅 Agenda:* '¿Qué tengo en el calendario de iPhone?'\n"
                "• *🧑‍💻 Proyectos:* 'Muéstrame mis repositorios'\n"
                "• *💬 WhatsApp:* '/wapp 3101234567 Hola amigo'\n"
                "• *📸 Pantalla:* 'Mándame un pantallazo'\n"
                "• *🔋 Hardware:* '¿Cómo está la batería y la RAM?'\n"
                "• *💵 Finanzas:* '¿A cómo está el dólar?'\n"
            )
        }


brain = JarvisBrain()
