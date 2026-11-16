"""
Cerebro Inteligente (AI Brain) para PERRA_JARVIS.
Combina:
1. Gemini 2.5 Flash / 1.5 Flash (Free Tier) vía google-genai con Function Calling.
2. Soporte nativo para notas de voz de Telegram (audio multimodal).
3. Motor de intenciones semánticas local de respaldo (Fallback sin API key).
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from config import GEMINI_API_KEY, ASSISTANT_NAME, TEMP_DIR
from modules import pc_controller
from modules import market_tracker

SYSTEM_INSTRUCTION = (
    f"Eres {ASSISTANT_NAME}, el asistente personal inteligente, autónomo y ejecutor de Diego Fabián Andrade. "
    "Tienes control operativo directo sobre su computador Windows personal (ejecución de comandos, capturas de pantalla, "
    "monitoreo de batería/hardware, apertura de apps, control de volumen/música y archivos). "
    "También gestionas sus consultas de mercado (TRM USD/COP, criptomonedas). "
    "Responde siempre de forma ágil, segura, con personalidad leal, ejecutiva y estilo Jarvis. "
    "Cuando el usuario te pida una acción en su PC o mercado, invoca las herramientas correspondientes. "
    "Si te hace una pregunta general de programación, estudio o productividad, responde con máxima calidad y precisión."
)

# Herramientas expuestas para el Function Calling de Gemini
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

TOOLS_REGISTRY = {
    "get_system_telemetry": get_system_telemetry,
    "capture_pc_screen": capture_pc_screen,
    "lock_computer": lock_computer,
    "open_app": open_app,
    "control_audio": control_audio,
    "get_market_data": get_market_data,
    "check_recent_downloads": check_recent_downloads,
    "run_powershell_cmd": run_powershell_cmd,
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
        """
        Procesa una orden de texto proveniente de Telegram.
        Retorna un diccionario con:
        - 'text': texto de respuesta
        - 'photo': ruta de foto a enviar si aplica (e.g. screenshot, gráfica)
        - 'document': ruta de documento a enviar si aplica
        """
        text_clean = text.strip()

        # Si tenemos Gemini configurado, usamos el cerebro con IA y Tools
        if self.client:
            try:
                from google.genai import types
                
                # Definición de funciones como herramientas
                tools_list = [
                    get_system_telemetry,
                    capture_pc_screen,
                    lock_computer,
                    open_app,
                    control_audio,
                    get_market_data,
                    check_recent_downloads,
                    run_powershell_cmd
                ]

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools_list,
                    temperature=0.4
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=text_clean,
                    config=config
                )

                # Verificar si Gemini llamó a una función
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

                return {"text": response.text}
            except Exception as e:
                print(f"Error en llamada a Gemini: {e}")
                # En caso de error o límite de cuota, caemos en el parser local

        # Fallback local: Reglas semánticas inteligentes
        return self._local_intent_fallback(text_clean)

    def process_voice_file(self, voice_path: Path) -> Dict[str, Any]:
        """Procesa una nota de voz enviada por Diego desde Telegram."""
        if not self.client:
            return {
                "text": "🎙️ Recibí tu nota de voz, pero necesitas configurar tu `GEMINI_API_KEY` en `.env` "
                        "para que pueda transcribirla y entender tu voz gratis."
            }

        try:
            from google.genai import types
            with open(voice_path, "rb") as f:
                audio_bytes = f.read()

            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
            instruction = "Transcribe y ejecuta la siguiente orden de Diego como Jarvis."

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[
                    get_system_telemetry,
                    capture_pc_screen,
                    lock_computer,
                    open_app,
                    control_audio,
                    get_market_data,
                    check_recent_downloads,
                    run_powershell_cmd
                ],
                temperature=0.3
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
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

            return {"text": f"🎙️ *Transcripción y respuesta:*\n{response.text}"}
        except Exception as e:
            return {"text": f"⚠️ Error al procesar audio con Gemini: {str(e)}"}

    def _local_intent_fallback(self, query: str) -> Dict[str, Any]:
        """Parser de intenciones locales sin necesidad de API externa."""
        q = query.lower()

        # Pantallazo / Screenshot
        if any(w in q for w in ["pantallazo", "captura", "screenshot", "screen", "pantalla", "mira mi pc"]):
            path = pc_controller.take_screenshot("screen.png")
            return {
                "text": "📸 Captura de pantalla tomada en este instante:",
                "photo": str(path)
            }

        # Estado del PC / Batería / Telemetría
        if any(w in q for w in ["estado", "status", "bateria", "batería", "ram", "cpu", "pc"]):
            stats = pc_controller.get_system_stats()
            return {"text": pc_controller.format_stats_message(stats)}

        # Bloquear PC
        if any(w in q for w in ["bloquear", "bloquea", "lock"]):
            ok = pc_controller.lock_pc()
            msg = "🔒 Computador bloqueado exitosamente." if ok else "⚠️ No se pudo bloquear la estación."
            return {"text": msg}

        # Mercado / Dólar / TRM / Cripto
        if any(w in q for w in ["dolar", "dólar", "trm", "precio", "mercado", "bitcoin", "crypto", "cripto"]):
            return {"text": market_tracker.format_market_summary()}

        # Gráfica TRM
        if any(w in q for w in ["grafica", "gráfica", "grafico", "chart", "tendencia"]):
            chart = market_tracker.generate_trm_chart("trm_chart.png", 20)
            if chart:
                return {
                    "text": "📈 Aquí tienes la gráfica histórica de la TRM USD/COP (Superfinanciera):",
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
        if any(w in q for w in ["pausa", "play", "reproducir", "reanudar"]):
            return {"text": pc_controller.media_control("play")}

        # Abrir aplicaciones
        m_app = re.search(r"abrir?\s+([a-zA-Z0-9_\-\.]+)", q)
        if m_app:
            target_app = m_app.group(1)
            return {"text": pc_controller.open_application(target_app)}

        # Descargas recientes
        if "descargas" in q or "downloads" in q or "archivos" in q:
            return {"text": check_recent_downloads()}

        # Ayuda general
        return {
            "text": (
                f"🤖 *{ASSISTANT_NAME} activo y escuchando*\n\n"
                "Puedes darme órdenes por texto, botones o notas de voz:\n"
                "• *📸 Pantalla:* 'Mándame un pantallazo'\n"
                "• *🔋 Hardware:* '¿Cómo está la batería y la RAM?'\n"
                "• *🔒 Seguridad:* 'Bloquea el PC'\n"
                "• *💵 Finanzas:* '¿A cómo está el dólar?' o 'Muestra la gráfica'\n"
                "• *🚀 Apps:* 'Abre Spotify', 'Abre Chrome', 'Abre VS Code'\n"
                "• *🔊 Audio:* 'Sube el volumen', 'Silenciar', 'Pausa'\n\n"
                "💡 *Tip:* Para activar el razonamiento libre con IA ilimitada ($0.00), "
                "añade tu `GEMINI_API_KEY` gratuita en tu archivo `.env`."
            )
        }


# Instancia única del cerebro
brain = JarvisBrain()
