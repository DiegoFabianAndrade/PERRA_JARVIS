"""
Módulo Antigravity Bridge para PERRA_JARVIS.
Conecta Telegram directamente con tu entorno de desarrollo, tus repositorios y este agente:
- Inspección remota de cualquier repositorio en tu PC.
- Envío de órdenes a este chat/agente especificando el repositorio objetivo.
- Registro en REMOTE_ORDERS.jsonl y resultados en REMOTE_RESULTS.jsonl.
- Ejecución remota de comandos Git, compilaciones y pruebas.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import ORDERS_FILE, BASE_DIR

RESULTS_FILE = BASE_DIR / "REMOTE_RESULTS.jsonl"
DASHBOARD_MD = BASE_DIR / "REMOTE_DASHBOARD.md"
PROJECTS_DIR = Path.home() / "Downloads"


def _update_dashboard_md(order_id: int, repo: str, order_text: str, status: str):
    """Actualiza el archivo markdown de visualización en vivo para el editor."""
    content = f"""# 📋 Panel de Órdenes Remotas de Telegram (En Vivo)

Este documento refleja en tiempo real las órdenes que envías a tu agente desde tu celular a través de **@PerraJarvis_bot**.

---

### ⏳ Última Orden Registrada:
- **ID:** `#{order_id}`
- **Fecha:** `{time.strftime("%Y-%m-%d %H:%M:%S")}`
- **Repositorio Objetivo:** `{repo}`
- **Instrucción Enviada:**
  > *"{order_text}"*
- **Estado:** `{status}`

---

*💡 Puedes tener este archivo abierto en una pestaña de tu editor para ver tus órdenes en cuanto las envíes desde el celular.*
"""
    try:
        with open(DASHBOARD_MD, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def list_local_projects() -> List[str]:
    """Lista las carpetas de proyectos y repositorios de desarrollo en tu PC."""
    projects = []
    if PROJECTS_DIR.exists():
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("."):
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
            f"📦 *REPOSITORIO: {project_name}*\n"
            f"─────────────────────────────\n"
            f"🌿 *Rama & Cambios:*\n```\n{status_out if status_out else 'Limpio (sin cambios pendientes)'}\n```\n"
            f"📜 *Últimos Commits:*\n```\n{log_out}\n```\n"
            f"─────────────────────────────"
        )
    except Exception as e:
        return f"⚠️ Error consultando Git en {project_name}: {e}"


def queue_remote_order(order_text: str, project_name: str = "PERRA_JARVIS") -> Dict[str, Any]:
    """Registra una orden remota enviada desde Telegram dirigida a un repositorio específico."""
    order_id = int(time.time())
    order_data = {
        "id": order_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repo": project_name.strip(),
        "order": order_text.strip(),
        "status": "PENDING"
    }

    with open(ORDERS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(order_data, ensure_ascii=False) + "\n")

    _update_dashboard_md(order_id, project_name, order_text, "⏳ PENDIENTE DE EJECUCIÓN")
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


def record_order_result(order_id: int, result_text: str, success: bool = True):
    """Registra el resultado de la ejecución de una orden para retroalimentar a Telegram."""
    result_data = {
        "id": order_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "success": success,
        "result": result_text
    }
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result_data, ensure_ascii=False) + "\n")

    # Marcar como DONE en ORDERS_FILE
    if ORDERS_FILE.exists():
        lines = []
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    try:
                        d = json.loads(l)
                        if d.get("id") == order_id:
                            d["status"] = "DONE"
                        lines.append(json.dumps(d, ensure_ascii=False) + "\n")
                    except Exception:
                        lines.append(l)
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)


DELIVERED_RESULTS_FILE = BASE_DIR / "temp" / "delivered_results.json"


def check_undelivered_results() -> List[Dict[str, Any]]:
    """Devuelve resultados de órdenes que aún no han sido entregados a Telegram."""
    if not RESULTS_FILE.exists():
        return []

    delivered_ids = set()
    if DELIVERED_RESULTS_FILE.exists():
        try:
            with open(DELIVERED_RESULTS_FILE, "r", encoding="utf-8") as f:
                delivered_ids = set(json.load(f))
        except Exception:
            pass

    undelivered = []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line)
                    if d.get("id") not in delivered_ids:
                        undelivered.append(d)
                        delivered_ids.add(d.get("id"))
                except Exception:
                    continue

    if undelivered:
        DELIVERED_RESULTS_FILE.parent.mkdir(exist_ok=True)
        with open(DELIVERED_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(delivered_ids), f)

    return undelivered


def run_project_command(project_name: str, command: str) -> str:
    """Ejecuta un comando en la carpeta de cualquier repositorio."""
    target_dir = PROJECTS_DIR / project_name
    if not target_dir.exists():
        return f"⚠️ El proyecto `{project_name}` no existe en Descargas."

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
            out = "Comando ejecutado sin salida en consola."
        if len(out) > 3000:
            out = out[:3000] + "\n... [Salida truncada]"
        return out
    except subprocess.TimeoutExpired:
        return "⏰ Tiempo de espera agotado (timeout 25s)."
    except Exception as e:
        return f"⚠️ Error ejecutando comando: {e}"
