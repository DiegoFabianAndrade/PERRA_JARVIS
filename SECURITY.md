# 🛡️ Security Policy & Threat Model — PERRA_JARVIS

## 1. Zero-Trust Architecture Overview

**PERRA_JARVIS** implementa un modelo de ciberdefensa de grado ejecutivo bajo el principio de **Privilegio Mínimo** y **Zero-Trust**:

1. **Control de Acceso Estricto (Telegram Whitelist):**
   - El bot valida criptográficamente cada interacción contra `ALLOWED_CHAT_ID`.
   - Cualquier petición originada por un usuario no autorizado es rechazada y registrada en `temp/security_access.log` para análisis forense.
   - No se expone información de la máquina ni del sistema a usuarios no identificados.

2. **Política de Cero Fuga de Secretos (Zero Secret Leak):**
   - Credenciales sensibles (`.env`, `token.json`, `credentials.json`, contraseñas de app) están permanentemente ignoradas en `.gitignore`.
   - Flujo de integración continua (`.github/workflows/security.yml`) que escanea activamente el repositorio en cada push para bloquear commits accidentales con tokens.

3. **Defensa contra Directory Traversal (CWE-22):**
   - Todos los selectores de repositorios (`test_runner`, `git_agent`) sanitizan las entradas mediante `security_guard.sanitize_project_name()`.
   - Se valida la frontera de subdirectorio con `security_guard.is_safe_subpath()` para impedir que comandos o lecturas escapen de los límites autorizados.

4. **Mitigación de Inyección de Comandos (CWE-78):**
   - El lanzador de aplicaciones (`modules/pc_controller.py`) aplica expresiones regulares que purgan meta-caracteres de shell (`&`, `;`, `|`, `` ` ``, `$`).

5. **Aislamiento de Sesión Windows:**
   - La captura de pantalla en segundo plano utiliza `user32.OpenInputDesktop` para interactuar de forma segura únicamente con el escritorio de usuario interactivo sin comprometer sesiones de otros usuarios.

---

## 2. Auditoría en Tiempo Real desde Telegram

El dueño autorizado puede ejecutar en cualquier momento:
- Comando: `/seguridad` o `/auditoria`
- O el botón interactivo: `[ 🛡️ Centro de Seguridad ] > [ 🔍 Correr Auditoría ]`

El sistema ejecuta una prueba de integridad local y reporta:
- Estado del Whitelist.
- Integridad de los archivos ignorados por Git.
- Contador de intentos no autorizados bloqueados.
- Estado de los módulos de protección perimetral.

---

## 3. Reporte de Vulnerabilidades

Si detectas cualquier fallo de seguridad, por favor abre un Issue privado o contacta al desarrollador:
- **Desarrollador:** Diego Fabián Andrade
- **Institución:** Escuela Colombiana de Ingeniería Julio Garavito
