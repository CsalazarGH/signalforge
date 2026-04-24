from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .http import post_json


def send_slack(webhook_url: str, text: str) -> None:
    if not webhook_url:
        return
    post_json(webhook_url, {"text": text})


def send_email(email_config: dict, subject: str, body: str) -> None:
    if not email_config.get("enabled"):
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_config["from_email"]
    message["To"] = email_config["to_email"]
    message.set_content(body)

    with smtplib.SMTP(email_config["smtp_host"], email_config.get("smtp_port", 587), timeout=30) as server:
        server.starttls()
        server.login(email_config["username"], email_config["password"])
        server.send_message(message)
