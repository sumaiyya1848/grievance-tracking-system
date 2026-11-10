import os
import smtplib
from email.message import EmailMessage


def send_email(subject, body):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    recipient = os.environ.get("ALERT_EMAIL")

    if not (user and password and recipient):
        print("Email is not set up, skipping:", subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = user
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
        return True
    except Exception as error:
        print("Email failed:", error)
        return False