"""
Módulo de Control de Git y Repositorios (Git & GitHub Agent) para PERRA_JARVIS.
Permite inspeccionar ramas, ver commits recientes, revisar archivos modificados
y realizar commits/push desde Telegram.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from config import BASE_DIR

DOWNLOADS_DIR = BASE_DIR.parent


def _run_git_cmd(repo_path: Path, args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=20,
        shell=True
    )


def get_repo_overview(repo_name: str) -> str:
    """Devuelve un reporte ejecutivo del estado de Git del repositorio."""
    repo_path = DOWNLOADS_DIR / repo_name
    if not repo_path.exists() or not (repo_path / ".git").exists():
        # Búsqueda insensible a mayúsculas
        matched = [p for p in DOWNLOADS_DIR.iterdir() if p.is_dir() and (p / ".git").exists() and p.name.lower() == repo_name.lower()]
        if matched:
            repo_path = matched[0]
        else:
            return f"⚠️ `{repo_name}` no parece ser un repositorio Git válido."

    # 1. Rama actual
    res_b = _run_git_cmd(repo_path, ["branch", "--show-current"])
    current_branch = res_b.stdout.strip() or "main"

    # 2. Último commit
    res_log = _run_git_cmd(repo_path, ["log", "-1", "--format=%h - %s (%cr)"])
    last_commit = res_log.stdout.strip() or "Sin commits"

    # 3. Estado de archivos modificados
    res_stat = _run_git_cmd(repo_path, ["status", "--short"])
    status_lines = [l for l in res_stat.stdout.splitlines() if l.strip()]

    lines = [f"🐙 *ESTADO GIT: {repo_path.name}*"]
    lines.append("─────────────────────────────")
    lines.append(f"🌿 *Rama activa:* `{current_branch}`")
    lines.append(f"📌 *Último commit:* `{last_commit}`")

    if not status_lines:
        lines.append("\n✅ *Árbol de trabajo limpio:* No hay cambios pendientes.")
    else:
        lines.append(f"\n📝 *Archivos pendientes ({len(status_lines)}):*")
        for l in status_lines[:8]:
            lines.append(f"• `{l}`")
        if len(status_lines) > 8:
            lines.append(f"... y {len(status_lines) - 8} más.")

    lines.append("─────────────────────────────")
    return "\n".join(lines)


def get_recent_commits(repo_name: str, limit: int = 5) -> str:
    """Muestra el historial de los últimos commits de un repositorio."""
    repo_path = DOWNLOADS_DIR / repo_name
    if not repo_path.exists() or not (repo_path / ".git").exists():
        matched = [p for p in DOWNLOADS_DIR.iterdir() if p.is_dir() and (p / ".git").exists() and p.name.lower() == repo_name.lower()]
        if matched:
            repo_path = matched[0]
        else:
            return f"⚠️ `{repo_name}` no es un repositorio Git válido."

    res = _run_git_cmd(repo_path, ["log", f"-{limit}", "--format=%h | %s (%cr)"])
    if res.returncode != 0 or not res.stdout.strip():
        return f"No se encontraron commits en `{repo_name}`."

    lines = [f"📜 *COMMITS RECIENTES: {repo_path.name}*"]
    lines.append("─────────────────────────────")
    for l in res.stdout.strip().splitlines():
        lines.append(f"• `{l}`")
    lines.append("─────────────────────────────")
    return "\n".join(lines)


def commit_and_push_changes(repo_name: str, commit_message: str) -> str:
    """Ejecuta git add, commit y push seguro en el repositorio."""
    repo_path = DOWNLOADS_DIR / repo_name
    if not repo_path.exists() or not (repo_path / ".git").exists():
        matched = [p for p in DOWNLOADS_DIR.iterdir() if p.is_dir() and (p / ".git").exists() and p.name.lower() == repo_name.lower()]
        if matched:
            repo_path = matched[0]
        else:
            return f"⚠️ `{repo_name}` no es un repositorio Git válido."

    # Status previo
    stat = _run_git_cmd(repo_path, ["status", "--short"])
    if not stat.stdout.strip():
        return f"ℹ️ En `{repo_path.name}` no hay cambios para hacer commit."

    # Add
    _run_git_cmd(repo_path, ["add", "."])
    # Commit
    res_c = _run_git_cmd(repo_path, ["commit", "-m", commit_message])
    if res_c.returncode != 0:
        return f"❌ Falló el commit: {res_c.stderr or res_c.stdout}"

    # Push
    res_p = _run_git_cmd(repo_path, ["push"])
    push_msg = "✅ Cambios subidos a GitHub con éxito." if res_p.returncode == 0 else f"⚠️ Commit local creado, pero push advirtió: {res_p.stderr[:200]}"

    return (
        f"🚀 *GIT COMMIT & PUSH: {repo_path.name}*\n"
        f"─────────────────────────────\n"
        f"💬 *Mensaje:* _{commit_message}_\n"
        f"🚦 *Estado:* {push_msg}\n"
        f"─────────────────────────────"
    )
