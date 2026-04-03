"""
Utility functions for MuseGenx1000
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(to_email, subject, body):
    """
    Send an email notification.
    Requires SMTP settings in config.py
    """
    if not config.SMTP_EMAIL or not config.SMTP_PASSWORD:
        print(f"[MOCK EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")
        return False, "SMTP settings not configured (Mock sent)"

    try:
        msg = MIMEMultipart()
        msg["From"] = config.SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.SMTP_EMAIL, to_email, text)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False, f"Failed to send email: {e}"
