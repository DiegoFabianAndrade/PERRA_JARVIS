"""
Módulo de Clima en Tiempo Real para PERRA_JARVIS.
Utiliza Open-Meteo API (100% gratuita, sin límites y sin API Key).
Configurado por defecto para Bogotá, Colombia.
"""

import requests
from typing import Dict, Any, Optional

# Coordenadas de Bogotá, Colombia
BOGOTA_LAT = 4.7110
BOGOTA_LON = -74.0721

WEATHER_CODES = {
    0: ("Despejado", "☀️"),
    1: ("Mayormente despejado", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Neblina", "🌫️"),
    48: ("Neblina con escarcha", "🌫️"),
    51: ("Llovizna ligera", "🌦️"),
    53: ("Llovizna moderada", "🌦️"),
    55: ("Llovizna densa", "🌧️"),
    61: ("Lluvia ligera", "🌧️"),
    63: ("Lluvia moderada", "🌧️"),
    65: ("Lluvia fuerte", "⛈️"),
    80: ("Chubascos ligeros", "🌦️"),
    81: ("Chubascos moderados", "🌧️"),
    82: ("Chubascos violentos", "⛈️"),
    95: ("Tormenta eléctrica", "⚡"),
}


def get_current_weather(lat: float = BOGOTA_LAT, lon: float = BOGOTA_LON) -> Dict[str, Any]:
    """Obtiene el clima actual y pronóstico para Bogotá."""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "timezone": "America/Bogota"
        }
        res = requests.get(url, params=params, timeout=6)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current_weather", {})
            code = curr.get("weathercode", 0)
            desc, emoji = WEATHER_CODES.get(code, ("Desconocido", "🌡️"))
            return {
                "temperature": curr.get("temperature", 0),
                "windspeed": curr.get("windspeed", 0),
                "condition": desc,
                "emoji": emoji,
                "is_day": bool(curr.get("is_day", 1))
            }
    except Exception as e:
        print(f"Error consultando clima: {e}")
    return {}


def format_weather_summary() -> str:
    """Formatea el reporte del clima para Telegram."""
    w = get_current_weather()
    if not w:
        return "🌦️ *Clima Bogotá:* No disponible temporalmente."

    return (
        f"{w['emoji']} *Clima Bogotá:* `{w['temperature']}°C` — {w['condition']}\n"
        f"💨 Viento: `{w['windspeed']} km/h`"
    )
