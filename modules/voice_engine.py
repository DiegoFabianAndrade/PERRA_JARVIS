"""
Módulo de Síntesis de Voz (Voice Engine) para PERRA_JARVIS.
Genera notas de voz ultrarrealistas en español neutro / colombiano
utilizando edge-tts a costo $0.00 USD.
"""

import re
import asyncio
from pathlib import Path
from typing import Optional
import edge_tts

from config import TEMP_DIR

DEFAULT_VOICE = "es-CO-GonzaloNeural"  # Voz colombiana ejecutiva masculina
ALT_VOICE = "es-CO-SalomeNeural"      # Voz colombiana femenina


def _clean_markdown_for_speech(text: str) -> str:
    """Remueve caracteres de formato Markdown para que la voz no los lea."""
    t = text
    # Remover enlaces [texto](url) -> texto
    t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)
    # Remover negritas, cursivas, código
    t = re.sub(r"[*_`~#>]", "", t)
    # Remover líneas separadoras
    t = re.sub(r"─+", "", t)
    # Remover saltos de línea repetidos y espacios
    t = re.sub(r"\n+", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


async def generate_voice_file(text: str, filename: str = "jarvis_reply.mp3", voice: str = DEFAULT_VOICE) -> Optional[Path]:
    """Genera un archivo de audio MP3 a partir de texto."""
    clean_text = _clean_markdown_for_speech(text)
    if not clean_text:
        return None

    # Limitar longitud para no generar audios excesivamente largos
    if len(clean_text) > 800:
        clean_text = clean_text[:800] + "... Fin del reporte."

    output_path = TEMP_DIR / filename
    try:
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(str(output_path))
        return output_path if output_path.exists() else None
    except Exception as e:
        print(f"Error generando síntesis de voz: {e}")
        return None


def generate_voice_file_sync(text: str, filename: str = "jarvis_reply.mp3", voice: str = DEFAULT_VOICE) -> Optional[Path]:
    """Versión síncrona para ser llamada desde cualquier hilo."""
    try:
        return asyncio.run(generate_voice_file(text, filename, voice))
    except Exception as e:
        print(f"Error en generate_voice_file_sync: {e}")
        return None
