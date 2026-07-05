"""
EmailManager: Full Gmail integration.
- Reads unread emails via IMAP with clean summaries.
- Sends emails via SMTP with TLS.
- Supports two accounts (primary / secondary).
"""
import email
import imaplib
import json
import os
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config.json"
)


class EmailManager:

    # ─── Config helpers ───────────────────────────────────────────────────────

    @classmethod
    def _get_account(cls, label: str = "primary") -> dict:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        for acc in cfg["email_accounts"]:
            if acc["label"] == label:
                return acc
        return cfg["email_accounts"][0]

    @staticmethod
    def _decode_str(s) -> str:
        if s is None:
            return ""
        parts = decode_header(s)
        result = []
        for part, enc in parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)

    @staticmethod
    def _get_body(msg) -> str:
        """Extract plain-text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                cd = str(part.get("Content-Disposition", ""))
                if ct == "text/plain" and "attachment" not in cd:
                    try:
                        return part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )[:300]
                    except Exception:
                        return ""
        else:
            try:
                return msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", errors="replace"
                )[:300]
            except Exception:
                return ""
        return ""

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def read_unread(cls, n: int = 5, account_label: str = "primary") -> str:
        acc = cls._get_account(account_label)
        try:
            mail = imaplib.IMAP4_SSL(acc["imap_server"])
            mail.login(acc["address"], acc["app_password"].replace(" ", ""))
            mail.select("inbox")

            _, msg_ids = mail.search(None, "UNSEEN")
            ids = msg_ids[0].split()

            if not ids:
                mail.logout()
                return "No unread emails, boss."

            # Most recent first, limit to n
            ids = ids[-n:][::-1]
            summaries = []
            for uid in ids:
                _, data = mail.fetch(uid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                subject = cls._decode_str(msg.get("Subject", "(No Subject)"))
                sender  = cls._decode_str(msg.get("From", "Unknown"))
                preview = cls._get_body(msg).replace("\n", " ").strip()[:80]
                summaries.append(f"From {sender}: '{subject}'" + (f" — {preview}" if preview else ""))

            mail.logout()
            return f"You have {len(ids)} unread email(s). " + ". ".join(summaries)

        except Exception as e:
            return f"Email read failed: {e}"

    @classmethod
    def send_email(cls, to: str, subject: str, body: str, account_label: str = "primary") -> str:
        acc = cls._get_account(account_label)
        try:
            msg = MIMEMultipart()
            msg["From"]    = acc["address"]
            msg["To"]      = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(acc["smtp_server"], acc["smtp_port"], timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(acc["address"], acc["app_password"].replace(" ", ""))
                server.send_message(msg)

            return f"Email sent to {to} with subject '{subject}'."
        except Exception as e:
            return f"Email send failed: {e}"
