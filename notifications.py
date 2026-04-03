import os
import logging
from config import SLACK_WEBHOOK_URL, SMTP_HOST, SMTP_PORT, SMTP_FROM, SMTP_USER, SMTP_PASS

logger = logging.getLogger(__name__)
try:
    import requests
except Exception:
    requests = None
from email.message import EmailMessage
import smtplib

def send_slack_message(webhook_url: str, text: str):
    if not webhook_url or requests is None:
        logger.debug("Slack webhook not configured or requests missing")
        return False
    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=5)
        return resp.status_code == 200
    except Exception:
        logger.exception("Failed to send slack message")
        return False

# Alias for backward compatibility
send_slack = lambda text: send_slack_message(SLACK_WEBHOOK_URL, text)

def send_email(to_addr: str, subject: str, body: str):
    if not SMTP_HOST:
        logger.debug("SMTP not configured")
        return False
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            if SMTP_USER and SMTP_PASS:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email")
        return False

def notify_admins_new_subscription(sub_id: int, user_id: int, plan: str, proof_url: str, note: str = ""):
    text = f"New subscription request #{sub_id} from user {user_id} plan={plan}. Proof: {proof_url}. {note}"
    send_slack_message(SLACK_WEBHOOK_URL, text)
    # optionally send email to admin list if configured

def notify_user_subscription_approved(user_id: int, plan: str, credits: int):
    # Implement mapping from user_id to email or in-app message
    logger.info(f"Notify user {user_id} approved for {plan}, +{credits} GG")

def notify_user_subscription_rejected(user_id: int, reason: str):
    logger.info(f"Notify user {user_id} rejected: {reason}")
