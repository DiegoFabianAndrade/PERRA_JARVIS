"""
Módulo de Correo Electrónico (Email Hub) para PERRA_JARVIS.
Soporte simultáneo para:
- Gmail (Personal)
- Outlook / Office 365 (Escuela Colombiana de Ingeniería)
Utiliza IMAP SSL seguro nativo de Python para lectura y resúmenes.
"""

import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional

from config import (
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
    OUTLOOK_USER,
    OUTLOOK_PASSWORD
)


def _decode_mime_str(s: Any) -> str:
    """Decodifica encabezados de correo MIME a texto legible UTF-8."""
    if not s:
        return ""
    try:
        decoded_parts = decode_header(s)
        res = []
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                encoding = encoding or "utf-8"
                try:
                    res.append(content.decode(encoding, errors="replace"))
                except Exception:
                    res.append(content.decode("latin-1", errors="replace"))
            else:
                res.append(str(content))
        return "".join(res)
    except Exception:
        return str(s)


def fetch_account_emails(
    host: str,
    user: str,
    password: str,
    folder: str = "INBOX",
    limit: int = 5,
    unread_only: bool = True
) -> List[Dict[str, Any]]:
    """Conecta por IMAP SSL y extrae los últimos correos."""
    if not user or not password:
        return []

    emails = []
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, 993, timeout=10)
        mail.login(user, password)
        mail.select(folder, readonly=True)

        criterion = "UNSEEN" if unread_only else "ALL"
        status, data = mail.search(None, criterion)
        if status != "OK" or not data[0]:
            # Si no hay no leídos, buscar los más recientes
            if unread_only:
                status, data = mail.search(None, "ALL")

        if status == "OK" and data[0]:
            msg_ids = data[0].split()
            # Tomar los últimos 'limit'
            latest_ids = msg_ids[-limit:]
            latest_ids.reverse()

            for msg_id in latest_ids:
                res, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
                if res == "OK":
                    raw_email = msg_data[0][1]
                    parsed = email.message_from_bytes(raw_email)
                    subject = _decode_mime_str(parsed.get("Subject", "Sin Asunto"))
                    from_ = _decode_mime_str(parsed.get("From", "Desconocido"))
                    date_ = parsed.get("Date", "")

                    emails.append({
                        "id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                        "subject": subject,
                        "from": from_,
                        "date": date_[:16] if len(date_) > 16 else date_
                    })
    except Exception as e:
        print(f"Error consultando correos en {host}: {e}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    return emails


def get_all_recent_emails(limit: int = 4) -> Dict[str, Any]:
    """Consulta tanto Gmail como Outlook y consolida los resultados."""
    results = {
        "gmail": {
            "configured": bool(GMAIL_USER and GMAIL_APP_PASSWORD),
            "user": GMAIL_USER,
            "emails": []
        },
        "outlook": {
            "configured": bool(OUTLOOK_USER and OUTLOOK_PASSWORD),
            "user": OUTLOOK_USER,
            "emails": []
        }
    }

    if results["gmail"]["configured"]:
        results["gmail"]["emails"] = fetch_account_emails(
            "imap.gmail.com",
            GMAIL_USER,
            GMAIL_APP_PASSWORD,
            limit=limit
        )

    if results["outlook"]["configured"]:
        results["outlook"]["emails"] = fetch_account_emails(
            "outlook.office365.com",
            OUTLOOK_USER,
            OUTLOOK_PASSWORD,
            limit=limit
        )

    return results


def format_emails_summary() -> str:
    """Genera un reporte resumido de la bandeja de entrada para Telegram."""
    data = get_all_recent_emails(limit=4)
    lines = ["📬 *BANDEJA DE ENTRADA - CORREOS*"]
    lines.append("─────────────────────────────")

    has_configured = False

    # Sección Gmail
    gm = data["gmail"]
    if gm["configured"]:
        has_configured = True
        lines.append(f"🔴 *Gmail:* `{gm['user']}`")
        if gm["emails"]:
            for e in gm["emails"]:
                lines.append(f"• *{e['subject']}*\n  De: `{e['from']}` ({e['date']})")
        else:
            lines.append("  _Bandeja al día (sin correos nuevos)._")
        lines.append("")
    else:
        lines.append("🔴 *Gmail:* _No configurado en .env (requiere GMAIL_USER y GMAIL_APP_PASSWORD)_")

    # Sección Outlook
    out = data["outlook"]
    if out["configured"]:
        has_configured = True
        lines.append(f"🔵 *Outlook / Escuela:* `{out['user']}`")
        if out["emails"]:
            for e in out["emails"]:
                lines.append(f"• *{e['subject']}*\n  De: `{e['from']}` ({e['date']})")
        else:
            lines.append("  _Bandeja al día (sin correos nuevos)._")
    else:
        lines.append("🔵 *Outlook:* _No configurado en .env (requiere OUTLOOK_USER y OUTLOOK_PASSWORD)_")

    lines.append("─────────────────────────────")
    if not has_configured:
        lines.append("💡 *Tip de configuración:* Añade tus credenciales en `.env` para ver tus correos al instante.")

    return "\n".join(lines)
