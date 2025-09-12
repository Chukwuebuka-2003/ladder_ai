import logging
import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Ensure any process using this code logs to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

load_dotenv()
logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv('ZOHO_SMTP_SERVER', 'smtp.zoho.eu')
SMTP_PORT = int(os.getenv('ZOHO_SMTP_PORT', '465'))  # 465 for SSL, 587 for TLS
SMTP_EMAIL = os.getenv('ZOHO_EMAIL')
SMTP_PASSWORD = os.getenv('ZOHO_APP_PASSWORD')
SMTP_FROM = os.getenv('ZOHO_FROM', SMTP_EMAIL)

logger.info(f"SMTP config: server={SMTP_SERVER}, port={SMTP_PORT}, email={SMTP_EMAIL}, from={SMTP_FROM}")

def smtp_is_configured():
    config_ok = bool(SMTP_SERVER and SMTP_PORT and SMTP_EMAIL and SMTP_PASSWORD and SMTP_FROM)
    if not config_ok:
        logger.warning(
            f"SMTP config incomplete. "
            f"Server: {SMTP_SERVER}, Port: {SMTP_PORT}, Email: {SMTP_EMAIL}, From: {SMTP_FROM}, PasswordSet: {SMTP_PASSWORD is not None}"
        )
    return config_ok

def send_smtp_email(to: str, subject: str, html: str):
    logger.info(f"Preparing to send SMTP email to: {to} | subject: {subject}")
    if not smtp_is_configured():
        logger.warning("SMTP settings are not fully configured. Skipping email sending.")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_FROM
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(html, "html"))
    try:
        logger.info(f"Connecting to SMTP server at {SMTP_SERVER}:{SMTP_PORT} as {SMTP_EMAIL}")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Mail sent successfully to {to} via Zoho SMTP.")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")

def send_otp_email(user_email: str, code: str, ttl_minutes: int):
    logger.info(f"Sending OTP email to {user_email} | code: {code}")
    html_body = f"""
    <html>
        <body>
            <h3>Your Verification Code</h3>
            <p>Use the 6-digit code below to complete verification.</p>
            <div style="font-size: 24px; font-weight: bold; letter-spacing: 4px; margin: 12px 0;">{code}</div>
            <p>This code will expire in {ttl_minutes} minutes.</p>
            <p>If you did not request this, you can ignore this message.</p>
        </body>
    </html>
    """
    send_smtp_email(
        to=user_email,
        subject="OTP Verification",
        html=html_body,
    )
