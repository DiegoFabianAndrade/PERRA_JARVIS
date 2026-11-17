"""
Módulo de Análisis de Documentos y PDFs para PERRA_JARVIS.
Procesa archivos PDF, diapositivas y código con Gemini 3.5 Flash Lite Multimodal:
- Resúmenes ejecutivos para parciales y talleres.
- Extracción de preguntas clave y conceptos esenciales.
- Diagnóstico de archivos de código y configuración.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import os

from config import GEMINI_API_KEY, ASSISTANT_NAME

SYSTEM_DOC_PROMPT = (
    f"Eres {ASSISTANT_NAME}, el copiloto de ingeniería y asistente ejecutivo de Diego Fabián Andrade. "
    "Tu tarea es analizar el documento adjunto y ofrecer una respuesta estructurada, ejecutiva y directa al punto. "
    "Si el usuario hace una pregunta concreta, respóndela con base en el documento. "
    "Si no hay pregunta, resume los 5 puntos clave indispensables y conceptos clave para estudio o aplicación práctica. "
    "Usa formato Markdown limpio con viñetas y negritas."
)


def analyze_document_file(file_path: Path, prompt_override: Optional[str] = None) -> str:
    """Procesa un archivo PDF o de texto usando Gemini 3.5 Flash Lite."""
    if not file_path.exists():
        return f"⚠️ Archivo no encontrado: {file_path.name}"

    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "⚠️ Configura `GEMINI_API_KEY` en tu `.env` para analizar documentos."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        ext = file_path.suffix.lower()

        # Determinar MIME type
        mime_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".py": "text/x-python",
            ".java": "text/x-java-source",
            ".json": "application/json",
            ".md": "text/markdown",
            ".csv": "text/csv",
        }
        mime_type = mime_map.get(ext, "application/pdf" if ext == ".pdf" else "text/plain")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        user_prompt = prompt_override.strip() if prompt_override and prompt_override.strip() else (
            "Analiza este documento: entrega un resumen ejecutivo de los 5 puntos clave y conceptos indispensables."
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_DOC_PROMPT,
            temperature=0.3
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=[file_part, user_prompt],
            config=config
        )

        if response.text:
            return (
                f"📑 *ANÁLISIS DOCUMENTAL: {file_path.name}*\n"
                f"─────────────────────────────\n"
                f"{response.text}\n"
                f"─────────────────────────────"
            )
        return "⚠️ Gemini no devolvió texto para este documento."
    except Exception as e:
        print(f"Error analizando documento: {e}")
        return f"⚠️ Error al procesar `{file_path.name}`: {e}"
