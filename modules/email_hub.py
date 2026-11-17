"""
Módulo de Correo Electrónico (Gmail Hub) para PERRA_JARVIS.
Conecta de forma segura a Gmail vía IMAP SSL nativo.
"""

import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional

from config import GMAIL_USER, GMAIL_APP_PASSWORD


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


def fetch_gmail_emails(limit: int = 5, unread_only: bool = True) -> List[Dict[str, Any]]:
    """Conecta por IMAP SSL a Gmail y extrae los correos más recientes."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return []

    clean_password = GMAIL_APP_PASSWORD.replace(" ", "").strip()
    emails = []
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=10)
        mail.login(GMAIL_USER, clean_password)
        mail.select("INBOX", readonly=True)

        criterion = "UNSEEN" if unread_only else "ALL"
        status, data = mail.search(None, criterion)
        if status != "OK" or not data[0]:
            if unread_only:
                status, data = mail.search(None, "ALL")

        if status == "OK" and data[0]:
            msg_ids = data[0].split()
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
        print(f"Error consultando Gmail: {e}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    return emails


def format_emails_summary() -> str:
    """Genera un reporte resumido de la bandeja de entrada de Gmail para Telegram."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return (
            "📧 *BANDEJA DE ENTRADA - GMAIL*\n"
            "─────────────────────────────\n"
            "⚠️ _Gmail no está configurado aún._\n\n"
            "💡 *Configuración en 2 pasos:*\n"
            "1. Asegúrate de tener activada la **Verificación en 2 pasos** en tu cuenta de Google.\n"
            "2. En el buscador de tu Cuenta de Google busca **'Contraseñas de aplicaciones'**, genera una para Jarvis y colócala en `.env`:\n"
            "   `GMAIL_USER=tu_correo@gmail.com`\n"
            "   `GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx`\n"
            "─────────────────────────────"
        )

    emails = fetch_gmail_emails(limit=5)
    lines = [
        "📧 *BANDEJA DE ENTRADA - GMAIL*",
        f"👤 Cuenta: `{GMAIL_USER}`",
        "─────────────────────────────"
    ]

    if not emails:
        lines.append("🎉 _¡Bandeja al día! No tienes correos sin leer._")
    else:
        for i, e in enumerate(emails, 1):
            lines.append(f"{i}. *{e['subject']}*")
            lines.append(f"   De: `{e['from']}`")
            lines.append(f"   📅 `{e['date']}`\n")

    lines.append("─────────────────────────────")
    return "\n".join(lines)


def send_email(to_address: str, subject: str, body: str) -> Dict[str, Any]:
    """Envía un correo electrónico desde la cuenta oficial de Gmail."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return {"success": False, "error": "Credenciales de Gmail no configuradas."}

    clean_password = GMAIL_APP_PASSWORD.replace(" ", "").strip()
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Diego Andrade via PERRA_JARVIS <{GMAIL_USER}>"
        msg["To"] = to_address

        # Formato texto plano
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(GMAIL_USER, clean_password)
            server.sendmail(GMAIL_USER, [to_address], msg.as_string())

        return {"success": True, "to": to_address, "subject": subject}
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return {"success": False, "error": str(e)}

