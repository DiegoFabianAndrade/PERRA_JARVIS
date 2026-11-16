"""
Módulo Financiero y de Mercados para PERRA_JARVIS.
Hereda y expande las capacidades del DollarBot:
- Consulta de TRM oficial de Colombia (Superfinanciera / datos.gov.co).
- Cotización en tiempo real de criptomonedas (BTC, ETH, SOL).
- Generación de gráficas de tendencia (Dark Mode) con matplotlib.
"""

import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Backend sin interfaz gráfica
import matplotlib.pyplot as plt

from config import TEMP_DIR

SOCRATA_TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"


def fetch_trm_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Obtiene el historial de TRM desde datos.gov.co."""
    try:
        params = {
            "$limit": limit,
            "$order": "vigenciadesde DESC"
        }
        res = requests.get(SOCRATA_TRM_URL, params=params, timeout=10)
        if res.status_code == 200:
            records = []
            for item in res.json():
                try:
                    valor = float(item.get("valor", 0))
                    fecha_raw = item.get("vigenciadesde", "")
                    fecha = fecha_raw[:10] if fecha_raw else "N/A"
                    records.append({"valor": valor, "fecha": fecha})
                except (ValueError, TypeError):
                    continue
            return records
    except Exception as e:
        print(f"Error consultando TRM: {e}")
    return []


def get_crypto_prices() -> Dict[str, Any]:
    """Obtiene precios de las principales criptomonedas en USD y COP."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,solana",
            "vs_currencies": "usd,cop",
            "include_24hr_change": "true"
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error consultando Criptos: {e}")
    return {}


def format_market_summary() -> str:
    """Genera un reporte resumido de TRM y Criptos para Telegram."""
    trm_records = fetch_trm_history(5)
    
    if trm_records:
        trm_actual = trm_records[0]["valor"]
        fecha_actual = trm_records[0]["fecha"]
        cambio_str = ""
        if len(trm_records) > 1:
            prev = trm_records[1]["valor"]
            diff = trm_actual - prev
            pct = (diff / prev) * 100
            icono = "📈" if diff >= 0 else "📉"
            signo = "+" if diff >= 0 else ""
            cambio_str = f"{icono} Variación: `{signo}${diff:,.2f} COP ({signo}{pct:.2f}%)`\n"

        trm_text = (
            f"🏛️ *TRM Oficial (Superfinanciera):*\n"
            f"💵 *1 USD = ${trm_actual:,.2f} COP*\n"
            f"📅 Fecha: `{fecha_actual}`\n"
            f"{cambio_str}"
        )
    else:
        trm_text = "⚠️ No se pudo obtener la TRM en este instante.\n"

    cryptos = get_crypto_prices()
    crypto_lines = []
    if cryptos:
        for symbol, key in [("₿ Bitcoin", "bitcoin"), ("Ξ Ethereum", "ethereum"), ("◎ Solana", "solana")]:
            data = cryptos.get(key)
            if data:
                usd = data.get("usd", 0)
                chg = data.get("usd_24h_change", 0)
                emoji = "🟢" if chg >= 0 else "🔴"
                crypto_lines.append(f"{symbol}: `${usd:,.2f} USD` ({emoji} {chg:+.2f}%)")

    crypto_text = ""
    if crypto_lines:
        crypto_text = "\n💎 *Criptomonedas (24h):*\n" + "\n".join(crypto_lines)

    msg = (
        "📊 *REPORTE FINANCIERO - PERRA_JARVIS*\n"
        "─────────────────────────────\n"
        f"{trm_text}"
        f"{crypto_text}\n"
        "─────────────────────────────"
    )
    return msg


def generate_trm_chart(filename: str = "trm_chart.png", days: int = 20) -> Optional[Path]:
    """Genera una gráfica moderna en Dark Mode con el historial de la TRM."""
    records = fetch_trm_history(days)
    if not records or len(records) < 3:
        return None

    records_chrono = list(reversed(records))
    fechas = [r["fecha"][5:] for r in records_chrono]  # MM-DD
    valores = [r["valor"] for r in records_chrono]

    # Estilo oscuro tipo terminal / Jarvis
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    fig.patch.set_facecolor("#121417")
    ax.set_facecolor("#181B20")

    # Gráfico de línea con gradiente de sombra
    ax.plot(fechas, valores, color="#00E5FF", linewidth=2.5, marker="o", markersize=4, label="TRM (COP)")
    ax.fill_between(fechas, valores, min(valores) * 0.998, color="#00E5FF", alpha=0.15)

    ax.set_title("Historial TRM USD/COP (Superfinanciera)", color="#FFFFFF", fontsize=13, weight="bold", pad=12)
    ax.set_ylabel("Pesos Colombianos (COP)", color="#A0AAB5", fontsize=10)
    ax.tick_params(axis="x", rotation=45, colors="#A0AAB5", labelsize=8)
    ax.tick_params(axis="y", colors="#A0AAB5", labelsize=9)
    ax.grid(True, linestyle="--", alpha=0.25, color="#506070")

    # Anotar último valor
    last_val = valores[-1]
    ax.annotate(
        f"${last_val:,.2f}",
        xy=(len(valores) - 1, last_val),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        color="#00FFAA",
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#202A30", ec="#00FFAA", lw=1)
    )

    plt.tight_layout()
    output_path = TEMP_DIR / filename
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return output_path
