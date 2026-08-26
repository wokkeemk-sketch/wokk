"""Email delivery for the daily digest, via SMTP (e.g. Gmail with an app password).

Credentials are read from environment variables only - never hardcode them or
commit them to config.yaml. See .env.example.

  SMTP_HOST      default: smtp.gmail.com
  SMTP_PORT      default: 587
  SMTP_USERNAME  the sending account's address (required)
  SMTP_PASSWORD  an app password, not your account login password (required)
  DIGEST_TO      recipient address (default: SMTP_USERNAME, i.e. email yourself)
"""

import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str) -> None:
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "SMTP_USERNAME and SMTP_PASSWORD must be set to send the digest email - see .env.example"
        )
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    recipient = os.environ.get("DIGEST_TO", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
