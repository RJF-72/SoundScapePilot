import smtplib
import dns.resolver
import socket
import ssl
import uuid
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

# Default self-hosted domain for Redemption Road Music Group.
DEFAULT_DOMAIN = os.getenv("SOUNDSCAPE_MAIL_DOMAIN", "redemptionroadmg.com")

# Owner emails can be configured via environment variable
_owner_emails_env = os.getenv("SOUNDSCAPE_OWNER_EMAILS", "")
if _owner_emails_env:
    OWNERS = []
    for email in _owner_emails_env.split(","):
        email = email.strip().lower()
        if email:
            name = email.split("@")[0].capitalize()
            OWNERS.append({"name": name, "email": email})
else:
    OWNERS = [
        {"name": "Ray", "email": f"ray@{DEFAULT_DOMAIN}"},
        {"name": "Joni", "email": f"joni@{DEFAULT_DOMAIN}"},
        {"name": "Keith", "email": f"keith@{DEFAULT_DOMAIN}"},
        {"name": "Paige", "email": f"paige@{DEFAULT_DOMAIN}"},
    ]

# Self-hosted default for redemptionroadmg.com
SELF_HOSTED_DEFAULTS = {
    "host": os.getenv("SOUNDSCAPE_SMTP_HOST", "mail.redemptionroadmg.com"),
    "port": int(os.getenv("SOUNDSCAPE_SMTP_PORT", "587")),
    "user": os.getenv("SOUNDSCAPE_SMTP_USER", ""),
    "password": os.getenv("SOUNDSCAPE_SMTP_PASS", ""),
}


class Mailer:
    """
    Proprietary direct-to-MX / SMTP mailer.
    Rotates sender identities to maximize inbox placement.
    Supports self-hosted Postfix/Dovecot for redemptionroadmg.com.
    """

    def __init__(self, smtp_host: Optional[str] = None, smtp_port: int = 587,
                 smtp_user: Optional[str] = None, smtp_pass: Optional[str] = None,
                 use_direct_mx: bool = False, max_retries: int = 2):
        self.smtp_host = smtp_host or SELF_HOSTED_DEFAULTS["host"]
        self.smtp_port = smtp_port or SELF_HOSTED_DEFAULTS["port"]
        self.smtp_user = smtp_user or SELF_HOSTED_DEFAULTS["user"]
        self.smtp_pass = smtp_pass or SELF_HOSTED_DEFAULTS["password"]
        self.use_direct_mx = use_direct_mx
        self.max_retries = max_retries
        self._owner_index = 0

    def configure(self, host: str, port: int, user: str, password: str):
        self.smtp_host = host
        self.smtp_port = port
        self.smtp_user = user
        self.smtp_pass = password
        self.use_direct_mx = False

    def _next_owner(self) -> Dict[str, str]:
        owner = OWNERS[self._owner_index % len(OWNERS)]
        self._owner_index += 1
        return owner

    def _resolve_mx(self, domain: str) -> Optional[str]:
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            mx = sorted(answers, key=lambda r: r.preference)[0].exchange.to_text().rstrip('.')
            return mx
        except Exception:
            return None

    def _sign_dkim(self, msg: MIMEMultipart) -> MIMEMultipart:
        """Placeholder for proprietary DKIM signing. In production this uses rsa-sha256."""
        msg["X-SoundScape-DKIM"] = "signed"
        return msg

    def _build_message(self, owner: Dict[str, str], recipient: str, subject: str,
                       body: str, module: str, tracking_id: str) -> MIMEMultipart:
        msg = MIMEMultipart('alternative')
        msg["From"] = f"{owner['name']} <{owner['email']}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg["X-SoundScape-Tracking-ID"] = tracking_id
        msg["X-SoundScape-Module"] = module
        msg["Reply-To"] = owner["email"]
        msg.attach(MIMEText(body, 'plain'))
        # HTML part with tracking pixel
        html_body = body.replace('\n', '<br>').replace('\r', '')
        tracking_pixel = f"<img src='http://127.0.0.1:{os.environ.get('PORT', '8765')}/track/{tracking_id}.gif' width='1' height='1'/>"
        msg.attach(MIMEText(f"<html><body>{html_body}{tracking_pixel}</body></html>", 'html'))
        return self._sign_dkim(msg)

    def send_email(self, recipient: str, subject: str, body: str,
                   module: str = "general", sender_name: Optional[str] = None,
                   sender_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends an email with aggressive retry logic.
        Uses configured SMTP first; falls back to direct MX if enabled.
        """
        owner = self._next_owner() if not sender_email else {"name": sender_name or "SoundScape", "email": sender_email}
        from_addr = owner["email"]
        tracking_id = str(uuid.uuid4())[:12]
        msg = self._build_message(owner, recipient, subject, body, module, tracking_id)

        result = {
            "owner": owner["name"],
            "owner_email": from_addr,
            "recipient": recipient,
            "subject": subject,
            "tracking_id": tracking_id,
            "status": "failed",
            "error": None
        }

        for attempt in range(self.max_retries + 1):
            try:
                if self.use_direct_mx and not self.smtp_host:
                    domain = recipient.split('@')[1]
                    mx = self._resolve_mx(domain)
                    if not mx:
                        raise Exception("MX record not found")
                    with smtplib.SMTP(mx, 25, timeout=15) as server:
                        server.starttls(context=ssl.create_default_context())
                        server.sendmail(from_addr, [recipient], msg.as_string())
                else:
                    if not self.smtp_host or not self.smtp_user or not self.smtp_pass:
                        raise Exception("SMTP credentials not configured. Set smtp_host, smtp_user, smtp_pass.")
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                        server.starttls(context=ssl.create_default_context())
                        server.login(self.smtp_user, self.smtp_pass)
                        server.sendmail(from_addr, [recipient], msg.as_string())

                result["status"] = "sent"
                result["error"] = None
                return result
            except Exception as e:
                result["error"] = str(e)
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))

        return result

    def send_bulk(self, items: List[Dict[str, str]], module: str) -> List[Dict[str, Any]]:
        results = []
        for item in items:
            res = self.send_email(
                recipient=item["contact"],
                subject=item["subject"],
                body=item["body"],
                module=module
            )
            results.append(res)
        return results


def load_mailer_from_env() -> Mailer:
    return Mailer(
        smtp_host=os.getenv("SOUNDSCAPE_SMTP_HOST"),
        smtp_port=int(os.getenv("SOUNDSCAPE_SMTP_PORT", "587")),
        smtp_user=os.getenv("SOUNDSCAPE_SMTP_USER"),
        smtp_pass=os.getenv("SOUNDSCAPE_SMTP_PASS"),
        use_direct_mx=os.getenv("SOUNDSCAPE_DIRECT_MX", "false").lower() == "true"
    )
