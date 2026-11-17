"""
Módulo de Ejecución Remota de Pruebas Unitarias (Remote Test Runner) para PERRA_JARVIS.
Ejecuta suites de tests en repositorios locales (Maven Java, Node.js, Python)
y diagnostica automáticamente los fallos con Gemini 3.5 Flash Lite.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from config import BASE_DIR, GEMINI_API_KEY
from modules import antigravity_bridge

DOWNLOADS_DIR = BASE_DIR.parent


def _diagnose_failure_with_ai(project_name: str, test_output: str) -> str:
    """Envía la traza de error a Gemini Flash Lite para diagnóstico técnico rápido."""
    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "⚠️ Traza de error registrada. Configura `GEMINI_API_KEY` para diagnóstico con IA."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = (
            f"El estudiante de ingeniería Diego ejecutó pruebas en el proyecto '{project_name}' y fallaron.\n"
            f"Analiza la siguiente salida de terminal y explica en 3 oraciones ejecutivas:\n"
            f"1. Qué prueba falló exactamente (nombre de clase/método o archivo).\n"
            f"2. Causa técnica raíz (ej: NullPointerException, assertion failed, timeout).\n"
            f"3. Sugerencia concreta para corregirlo.\n\n"
            f"Salida de pruebas:\n{test_output[-2500:]}"
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        return response.text if response.text else "No se pudo generar diagnóstico."
    except Exception as e:
        return f"Error en diagnóstico IA: {e}"


def run_project_tests(project_name: str) -> Dict[str, Any]:
    """Detecta el tipo de proyecto y ejecuta su suite de pruebas."""
    proj_path = DOWNLOADS_DIR / project_name
    if not proj_path.exists():
        # Buscar insensible a mayúsculas
        matched = [p for p in DOWNLOADS_DIR.iterdir() if p.is_dir() and p.name.lower() == project_name.lower()]
        if matched:
            proj_path = matched[0]
        else:
            return {
                "success": False,
                "project": project_name,
                "message": f"❌ No se encontró el proyecto `{project_name}` en {DOWNLOADS_DIR}."
            }

    cmd = None
    runner_type = "Desconocido"

    # 1. Maven Java (con wrapper mvnw.cmd o global)
    mvnw_cmd = proj_path / "mvnw.cmd"
    pom_xml = proj_path / "pom.xml"

    # Verificar si el pom o mvnw está en un subdirectorio
    if not pom_xml.exists():
        sub_poms = list(proj_path.glob("**/pom.xml"))
        if sub_poms:
            pom_xml = sub_poms[0]
            proj_path = pom_xml.parent
            mvnw_cmd = proj_path / "mvnw.cmd"

    if mvnw_cmd.exists():
        cmd = [str(mvnw_cmd), "test"]
        runner_type = "Maven (mvnw)"
    elif pom_xml.exists():
        cmd = ["mvn", "test"]
        runner_type = "Maven (CLI)"

    # 2. Node.js (package.json)
    elif (proj_path / "package.json").exists() or list(proj_path.glob("**/package.json")):
        pkg = proj_path / "package.json"
        if not pkg.exists():
            pkg = list(proj_path.glob("**/package.json"))[0]
            proj_path = pkg.parent
        cmd = ["npm", "test"]
        runner_type = "Node.js (npm test)"

    # 3. Python (pytest o unittest)
    elif list(proj_path.glob("test_*.py")) or list(proj_path.glob("**/test_*.py")):
        cmd = ["python", "-m", "unittest", "discover"]
        runner_type = "Python unittest"

    if not cmd:
        return {
            "success": False,
            "project": project_name,
            "message": f"⚠️ No se detectó un ejecutor de pruebas automático (pom.xml, package.json o test_*.py) en `{proj_path.name}`."
        }

    # Ejecutar pruebas con timeout de 60 segundos
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(proj_path),
            capture_output=True,
            text=True,
            timeout=70,
            shell=True
        )
        combined_output = (proc.stdout + "\n" + proc.stderr).strip()
        passed = (proc.returncode == 0)

        diagnosis = None
        if not passed:
            diagnosis = _diagnose_failure_with_ai(project_name, combined_output)

        return {
            "success": True,
            "passed": passed,
            "project": project_name,
            "runner": runner_type,
            "returncode": proc.returncode,
            "diagnosis": diagnosis,
            "output_tail": combined_output[-1200:] if combined_output else "Sin salida"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "passed": False,
            "project": project_name,
            "runner": runner_type,
            "message": "⏱️ Tiempo de espera agotado (>70s). Es posible que alguna prueba tenga un bucle infinito o espere entrada por teclado."
        }
    except Exception as e:
        return {
            "success": False,
            "project": project_name,
            "message": f"Error ejecutando pruebas: {e}"
        }


def format_test_report(res: Dict[str, Any]) -> str:
    """Formatea el reporte de ejecución de pruebas para Telegram."""
    if not res.get("success"):
        return res.get("message", "Error ejecutando pruebas.")

    proj = res["project"]
    runner = res["runner"]
    passed = res.get("passed", False)

    lines = [f"🧪 *REPORTE DE TESTS: {proj}*"]
    lines.append("─────────────────────────────")
    lines.append(f"⚙️ *Ejecutor:* `{runner}`")

    if passed:
        lines.append("🚦 *Resultado:* ✅ *TODAS LAS PRUEBAS EN VERDE (PASSED)*")
        lines.append("\n🎉 Tu suite de pruebas unitarias corrió limpiamente sin errores.")
    else:
        lines.append("🚦 *Resultado:* ❌ *PRUEBAS FALLIDAS (FAILED)*")
        if res.get("diagnosis"):
            lines.append("\n🤖 *Diagnóstico Inteligente con IA:*")
            lines.append(res["diagnosis"])
        lines.append("\n📄 *Últimas líneas de terminal:*")
        tail = res.get("output_tail", "")
        # Filtrar o escapar markdown básico
        clean_tail = tail.replace("*", "").replace("_", "")[-500:]
        lines.append(f"```\n{clean_tail}\n```")

    lines.append("─────────────────────────────")
    return "\n".join(lines)
