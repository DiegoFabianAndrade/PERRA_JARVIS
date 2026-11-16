"""
Módulo Antigravity Bridge para PERRA_JARVIS.
Conecta Telegram directamente con tu entorno de desarrollo y tus proyectos:
- Inspección remota de repositorios y proyectos en tu máquina.
- Buzón de órdenes remotas (REMOTE_ORDERS.jsonl).
- Ejecución remota de compilaciones, pruebas y comandos Git.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import ORDERS_FILE, BASE_DIR

PROJECTS_DIR = Path.home() / "Downloads"


def list_local_projects() -> List[str]:
    """Lista las carpetas de proyectos y repositorios de desarrollo en tu PC."""
    projects = []
    if PROJECTS_DIR.exists():
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                # Detectar si es un repo git o proyecto de código
                is_git = (d / ".git").exists()
                is_code = any((d / f).exists() for f in ["pom.xml", "package.json", "requirements.txt", "main.py"])
                if is_git or is_code:
                    projects.append(d.name)
    return sorted(projects)


def get_project_status(project_name: str) -> str:
    """Obtiene el estado de Git y últimos commits de un proyecto."""
    target_dir = PROJECTS_DIR / project_name
    if not target_dir.exists():
        return f"⚠️ Proyecto `{project_name}` no encontrado en Descargas."

    git_dir = target_dir / ".git"
    if not git_dir.exists():
        return f"📁 `{project_name}` no es un repositorio Git, pero contiene archivos de código."

    try:
        res = subprocess.run(
            ["git", "-C", str(target_dir), "status", "--short", "-b"],
            capture_output=True,
            text=True,
            timeout=8
        )
        status_out = res.stdout.strip()

        log_res = subprocess.run(
            ["git", "-C", str(target_dir), "log", "-n", "3", "--oneline"],
            capture_output=True,
            text=True,
            timeout=8
        )
        log_out = log_res.stdout.strip()

        return (
            f"📦 *PROYECTO: {project_name}*\n"
            f"─────────────────────────────\n"
            f"🌿 *Rama & Cambios:*\n```\n{status_out if status_out else 'Limpio (sin cambios pendientes)'}\n```\n"
            f"📜 *Últimos Commits:*\n```\n{log_out}\n```\n"
            f"─────────────────────────────"
        )
    except Exception as e:
        return f"⚠️ Error consultando Git en {project_name}: {e}"


def queue_remote_order(order_text: str, project_name: str = "PERRA_JARVIS") -> Dict[str, Any]:
    """Registra una orden remota enviada desde el móvil en el buzón."""
    order_id = int(time.time())
    order_data = {
        "id": order_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "project": project_name,
        "order": order_text,
        "status": "PENDING"
    }

    with open(ORDERS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(order_data, ensure_ascii=False) + "\n")

    return order_data


def list_pending_orders() -> List[Dict[str, Any]]:
    """Lee todas las órdenes pendientes en el buzón."""
    if not ORDERS_FILE.exists():
        return []

    pending = []
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get("status") == "PENDING":
                        pending.append(data)
                except Exception:
                    continue
    return pending


def run_project_command(project_name: str, command: str) -> str:
    """Ejecuta un comando de desarrollo dentro de la carpeta del proyecto."""
    target_dir = PROJECTS_DIR / project_name
    if not target_dir.exists():
        return f"⚠️ El proyecto `{project_name}` no existe."

    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            timeout=25
        )
        out = res.stdout if res.stdout else res.stderr
        if not out:
            out = "Comando completado sin salida en consola."
        if len(out) > 3000:
            out = out[:3000] + "\n... [Salida truncada]"
        return out
    except subprocess.TimeoutExpired:
        return "⏰ Tiempo de espera agotado (timeout 25s)."
    except Exception as e:
        return f"⚠️ Error ejecutando comando: {e}"
