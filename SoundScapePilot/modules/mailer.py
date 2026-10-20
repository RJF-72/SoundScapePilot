import base64
import hashlib
import logging
import smtplib
import dns.resolver
import socket
import ssl
import uuid
import os
import re
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import List, Dict, Any, Optional

logger = logging.getLogger("soundscape.mailer")

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

    def _dkim_key(self) -> Optional[bytes]:
        """Load the DKIM RSA private key from env/config. Returns None
        (no error) when DKIM is simply not configured."""
        pem = os.getenv("SOUNDSCAPE_DKIM_PRIVATE_KEY", "")
        if "\\n" in pem:
            pem = pem.replace("\\n", "\n")
        key_file = os.getenv("SOUNDSCAPE_DKIM_PRIVATE_KEY_FILE", "")
        if not pem and key_file:
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    pem = f.read()
            except Exception as e:
                logger.warning("DKIM: could not read key file %s: %s", key_file, e)
                return None
        if not pem:
            return None
        return pem.encode("utf-8")

    def _dkim_sign(self, raw_message: str) -> Optional[str]:
        """Prepend a real DKIM-Signature header (rsa-sha256, relaxed
        header / simple body canonicalization, RFC 6376) to a serialized
        message. Returns the signed message, or None when DKIM is not
        configured or signing fails — the caller then sends the message
        WITHOUT any signature claim."""
        key_pem = self._dkim_key()
        if not key_pem:
            if not getattr(self, "_dkim_logged_unconfigured", False):
                logger.info("DKIM: no private key configured (set SOUNDSCAPE_DKIM_PRIVATE_KEY or "
                            "SOUNDSCAPE_DKIM_PRIVATE_KEY_FILE to enable); sending without signature")
                self._dkim_logged_unconfigured = True
            return None
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
        except Exception:
            if not getattr(self, "_dkim_logged_nolib", False):
                logger.warning("DKIM: 'cryptography' package not installed; sending without signature")
                self._dkim_logged_nolib = True
            return None
        try:
            private_key = serialization.load_pem_private_key(key_pem, password=None)
        except Exception as e:
            logger.warning("DKIM: failed to load private key: %s", e)
            return None

        domain = os.getenv("SOUNDSCAPE_DKIM_DOMAIN", DEFAULT_DOMAIN)
        selector = os.getenv("SOUNDSCAPE_DKIM_SELECTOR", "soundscape")

        raw = raw_message.replace("\r\n", "\n").replace("\n", "\r\n")
        header_blob, _, body = raw.partition("\r\n\r\n")

        # Simple body canonicalization: drop trailing empty lines, single CRLF at end.
        blines = body.split("\r\n")
        while blines and blines[-1] == "":
            blines.pop()
        body_canon = "\r\n".join(blines) + ("\r\n" if blines else "")
        bh = base64.b64encode(hashlib.sha256(body_canon.encode("utf-8")).digest()).decode("ascii")

        # Parse headers (unfold), keeping order.
        headers: List[tuple] = []
        cur_name: Optional[str] = None
        cur_val = ""
        for line in header_blob.split("\r\n"):
            if line[:1] in (" ", "\t") and cur_name is not None:
                cur_val += " " + line.strip()
                continue
            if cur_name is not None:
                headers.append((cur_name, cur_val))
            if ":" not in line:
                cur_name, cur_val = None, ""
                continue
            cur_name, _, v = line.partition(":")
            cur_name = cur_name.strip().lower()
            cur_val = v.strip()
        if cur_name is not None:
            headers.append((cur_name, cur_val))

        def relaxed(value: str) -> str:
            return re.sub(r"\s+", " ", value).strip()

        sign_names = ["from", "to", "subject", "date", "message-id", "mime-version", "content-type"]
        present = [n for n in sign_names if any(h[0] == n for h in headers)]
        if not present:
            return None

        sign_blob = b""
        for name in present:
            # RFC 6376: sign the LAST instance of each header name.
            val = next(v for n, v in reversed(headers) if n == name)
            sign_blob += f"{name}:{relaxed(val)}\r\n".encode("utf-8")

        # DKIM-Signature VALUE (tag list, b= empty). The header is hashed
        # as "dkim-signature:" + value with no trailing CRLF.
        dkim_value = (f"v=1; a=rsa-sha256; c=relaxed/simple; d={domain}; "
                      f"s={selector}; h={':'.join(present)}; bh={bh}; b=")
        sign_blob += ("dkim-signature:" + dkim_value).encode("utf-8")

        try:
            sig = private_key.sign(sign_blob, rsa_padding.PKCS1v15(), hashes.SHA256())
        except Exception as e:
            logger.warning("DKIM: signing failed: %s", e)
            return None
        b64sig = base64.b64encode(sig).decode("ascii")
        # Fold the b= value to ~73 chars per line.
        folded = [b64sig[i:i + 73] for i in range(0, len(b64sig), 73)]
        dkim_header = "DKIM-Signature: " + dkim_value + "\r\n\t" + "\r\n\t".join(folded) + "\r\n"
        return dkim_header + raw

    def _build_message(self, owner: Dict[str, str], recipient: str, subject: str,
                       body: str, module: str, tracking_id: str) -> MIMEMultipart:
        msg = MIMEMultipart('alternative')
        msg["From"] = f"{owner['name']} <{owner['email']}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=os.getenv("SOUNDSCAPE_DKIM_DOMAIN", DEFAULT_DOMAIN))
        msg["X-SoundScape-Tracking-ID"] = tracking_id
        msg["X-SoundScape-Module"] = module
        msg["Reply-To"] = owner["email"]
        msg.attach(MIMEText(body, 'plain'))
        # HTML part with tracking pixel
        html_body = body.replace('\n', '<br>').replace('\r', '')
        tracking_pixel = f"<img src='http://127.0.0.1:{os.environ.get('PORT', '8765')}/track/{tracking_id}.gif' width='1' height='1'/>"
        msg.attach(MIMEText(f"<html><body>{html_body}{tracking_pixel}</body></html>", 'html'))
        return msg

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

        # Real DKIM signature when a key is configured; otherwise the
        # message goes out WITHOUT any signature claim (never faked).
        signed = self._dkim_sign(msg.as_string())
        raw_message = signed if signed is not None else msg.as_string().replace("\n", "\r\n")

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
                        server.sendmail(from_addr, [recipient], raw_message)
                else:
                    if not self.smtp_host or not self.smtp_user or not self.smtp_pass:
                        raise Exception("SMTP credentials not configured. Set smtp_host, smtp_user, smtp_pass.")
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                        server.starttls(context=ssl.create_default_context())
                        server.login(self.smtp_user, self.smtp_pass)
                        server.sendmail(from_addr, [recipient], raw_message)

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
