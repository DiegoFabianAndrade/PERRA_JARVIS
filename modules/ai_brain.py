"""
Cerebro Inteligente de Alta Velocidad (Turbo AI Brain) para PERRA_JARVIS.
Optimizaciones de rendimiento:
1. Fast-Path Router local: Acciones operativas directas (pantalla, batería, bloqueo, menú, finanzas) en <0.1s.
2. Modelo ultra veloz: gemini-3.5-flash-lite como modelo primario (latencia <1s).
3. Soporte para notas de voz y fotos de celular ultrarrápidas.
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

# gemini-3.5-flash-lite responde en ~0.9s (vs 7.8s de modelos pesados)
FAST_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]

SYSTEM_INSTRUCTION = (
    f"Eres {ASSISTANT_NAME}, el asistente ejecutivo personal de Diego Fabián Andrade. "
    "Responde siempre de forma ultra concisa, directa y ejecutiva (máximo 2 a 3 oraciones). "
    "Tienes control de su PC, finanzas, correos, calendario y proyectos. "
    "Invoca herramientas solo cuando sea estrictamente necesario."
)

# Herramientas de Function Calling
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
        return "No hay archivos recientes en Descargas."
    return "📁 *Descargas recientes:*\n" + "\n".join(f"• `{f['name']}` ({f['size_mb']} MB)" for f in files)

def check_emails() -> str:
    """Consulta los correos recientes de Gmail."""
    return email_hub.format_emails_summary()

def check_calendar_schedule() -> str:
    """Consulta los eventos del calendario de iPhone para hoy."""
    return calendar_hub.format_schedule_summary()

def check_weather() -> str:
    """Consulta el clima en Bogotá."""
    return weather_service.format_weather_summary()

def get_daily_briefing() -> str:
    """Genera el briefing diario consolidado."""
    return monitor.get_executive_briefing()

def list_dev_projects() -> str:
    """Lista los proyectos de código en el computador."""
    projs = antigravity_bridge.list_local_projects()
    return "🧑‍💻 *Repositorios en PC:*\n" + "\n".join(f"• `{p}`" for p in projs)

TOOLS_REGISTRY = {
    "get_system_telemetry": get_system_telemetry,
    "capture_pc_screen": capture_pc_screen,
    "lock_computer": lock_computer,
    "open_app": open_app,
    "control_audio": control_audio,
    "get_market_data": get_market_data,
    "check_recent_downloads": check_recent_downloads,
    "check_emails": check_emails,
    "check_calendar_schedule": check_calendar_schedule,
    "check_weather": check_weather,
    "get_daily_briefing": get_daily_briefing,
    "list_dev_projects": list_dev_projects,
}


class JarvisBrain:
    def __init__(self):
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        """Inicializa el cliente de Gemini."""
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Error inicializando Gemini: {e}")
                self.client = None

    def fast_intent_router(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Fast-Path: Resuelve comandos operativos comunes en < 0.05 segundos
        sin necesidad de esperar el tiempo de ida y vuelta a la API de la nube.
        """
        q = query.lower().strip()

        # 1. Menú
        if q in ["menu", "menú", "opciones", "panel", "dashboard"] or \
           any(p in q for p in ["mostrar menu", "ver menu", "muestrame el menu", "muéstrame el menú", "dame el menu", "dame el menú"]):
            return {"action": "SHOW_MENU"}

        # 2. Captura de pantalla (Instantánea)
        if any(w in q for w in ["pantallazo", "captura", "screenshot", "screen"]) or ("pantalla" in q and any(w in q for w in ["mira", "toma", "foto", "ver"])):
            path = pc_controller.take_screenshot("screen.png")
            return {
                "text": "📸 Captura de pantalla tomada:",
                "photo": str(path)
            }

        # 3. Estado de batería y hardware
        if (("bateria" in q or "batería" in q) and len(q) < 40) or q in ["estado", "status", "estado pc", "como esta el pc", "¿cómo está el pc?"]:
            stats = pc_controller.get_system_stats()
            return {"text": pc_controller.format_stats_message(stats)}

        # 4. Bloquear PC
        if any(w in q for w in ["bloquear", "bloquea", "lock"]):
            ok = pc_controller.lock_pc()
            return {"text": "🔒 PC bloqueado con éxito." if ok else "⚠️ No se pudo bloquear el PC."}

        # 5. Briefing Ejecutivo
        if any(w in q for w in ["briefing", "resumen diario", "mi dia", "mi día"]):
            return {"text": monitor.get_executive_briefing()}

        # 6. Clima Bogotá
        if q in ["clima", "tiempo", "temperatura", "¿va a llover?", "va a llover"] or any(w in q for w in ["clima bogota", "clima bogotá", "tiempo hoy"]):
            return {"text": weather_service.format_weather_summary()}

        # 7. TRM Dólar
        if q in ["dolar", "dólar", "trm", "precio dolar", "precio dólar", "¿a cómo está el dólar?", "¿a como esta el dolar?"]:
            return {"text": market_tracker.format_market_summary()}

        # 8. Gráfica TRM
        if any(w in q for w in ["grafica", "gráfica", "grafico"]):
            chart = market_tracker.generate_trm_chart("trm_chart.png", 20)
            if chart:
                return {"text": "📈 Historial TRM USD/COP:", "photo": str(chart)}

        # 9. Correos Gmail
        if q in ["correos", "correo", "gmail", "bandeja", "revisar correos"]:
            return {"text": email_hub.format_emails_summary()}

        # 10. Calendario iPhone
        if q in ["calendario", "agenda", "eventos", "mis eventos", "clases"]:
            return {"text": calendar_hub.format_schedule_summary()}

        # 11. Control de Audio
        if "silenciar" in q or "mute" in q:
            return {"text": pc_controller.media_control("mute")}
        if "subir volumen" in q:
            return {"text": pc_controller.media_control("up")}
        if "bajar volumen" in q:
            return {"text": pc_controller.media_control("down")}
        if any(w in q for w in ["pausa", "play", "reproducir"]):
            return {"text": pc_controller.media_control("play")}

        # 12. Abrir apps comunes
        m_app = re.match(r"^abrir?\s+([a-zA-Z0-9_\-\.]+)$", q)
        if m_app:
            return {"text": pc_controller.open_application(m_app.group(1))}

        # No es comando simple, requiere razonamiento de LLM
        return None

    def process_text(self, text: str) -> Dict[str, Any]:
        """Procesa texto con Fast-Path prioritario + Gemini Flash Lite ultrarrápido."""
        text_clean = text.strip()

        # 1. Ejecutar Fast-Path (Respuesta en <0.05 segundos)
        fast_result = self.fast_intent_router(text_clean)
        if fast_result is not None:
            return fast_result

        # 2. Si no es acción directa, pasar a Gemini Flash Lite (<1 segundo)
        if self.client:
            for model_name in FAST_MODELS:
                try:
                    from google.genai import types
                    tools_list = list(TOOLS_REGISTRY.values())

                    config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=tools_list,
                        temperature=0.3
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
                                    return {
                                        "text": "📸 Captura de pantalla tomada:",
                                        "photo": fn_result.split(":", 1)[1]
                                    }
                                return {"text": fn_result}

                    if response.text:
                        return {"text": response.text}
                except Exception as e:
                    print(f"Aviso con {model_name}: {e}. Intentando alternativa...")
                    continue

        return {
            "text": "🤖 Orden recibida. Si necesitas el menú, escribe *menú* o selecciona una opción."
        }

    def process_voice_file(self, voice_path: Path) -> Dict[str, Any]:
        """Procesa notas de voz a máxima velocidad con Gemini Flash Lite."""
        if not self.client:
            return {
                "text": "🎙️ Nota de voz recibida, pero configura tu `GEMINI_API_KEY` para transcripción."
            }

        with open(voice_path, "rb") as f:
            audio_bytes = f.read()

        for model_name in FAST_MODELS:
            try:
                from google.genai import types
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
                instruction = "Transcribe y ejecuta la siguiente orden de Diego brevemente como Jarvis."
                tools_list = list(TOOLS_REGISTRY.values())

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools_list,
                    temperature=0.2
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
                                    "text": "📸 Captura tomada por comando de voz:",
                                    "photo": fn_result.split(":", 1)[1]
                                }
                            return {"text": f"🎙️ *Orden ejecutada:*\n\n{fn_result}"}

                if response.text:
                    return {"text": f"🎙️ *Jarvis:*\n{response.text}"}
            except Exception as e:
                print(f"Error procesando voz con {model_name}: {e}")
                continue

        return {"text": "⚠️ No se pudo procesar el audio en este instante."}

    def process_photo(self, photo_bytes: bytes, caption: Optional[str] = None) -> str:
        """Analiza imágenes con Gemini Flash Lite en tiempo récord."""
        if not self.client:
            return "📸 Recibí tu foto. Configura `GEMINI_API_KEY` para análisis visual."

        for model_name in FAST_MODELS:
            try:
                from google.genai import types
                img_part = types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")
                prompt = caption if caption else "Analiza esta imagen y responde de forma concisa y ejecutiva."

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[img_part, prompt],
                )
                if response.text:
                    return f"👁️ *Análisis Visual:*\n\n{response.text}"
            except Exception as e:
                continue

        return "⚠️ Error analizando imagen."


brain = JarvisBrain()
