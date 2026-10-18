"""Mailer stub module."""

DEFAULT_DOMAIN = "titan2026.com"
OWNER_EMAILS = ["ray@titan2026.com", "keith@titan2026.com", "joni@titan2026.com", "paige@titan2026.com"]


def send_email(to, subject, body, html=None):
    return {"status": "logged", "reason": "SMTP credentials not configured"}

