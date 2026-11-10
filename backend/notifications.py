import os
import smtplib
from email.message import EmailMessage


def send_email(subject, body):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    recipient = os.environ.get("ALERT_EMAIL")

    if not all([user, password, recipient]):
        print("Email configuration is incomplete.")
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

        print("Email sent successfully:", subject)
        return True

    except (smtplib.SMTPException, OSError, ValueError) as error:
        print("Email sending failed:", error)
        return False