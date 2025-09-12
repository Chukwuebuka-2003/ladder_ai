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
    """
    Return whether SMTP configuration variables are set for sending email.
    
    Checks the module-level SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, and SMTP_FROM values and returns True if all are truthy. If any are missing or falsy, logs a warning with the current server/port/email/from values and whether a password is present (the actual password value is not logged).
     
    Returns:
        bool: True if all required SMTP settings are configured, False otherwise.
    """
    config_ok = bool(SMTP_SERVER and SMTP_PORT and SMTP_EMAIL and SMTP_PASSWORD and SMTP_FROM)
    if not config_ok:
        logger.warning(
            f"SMTP config incomplete. "
            f"Server: {SMTP_SERVER}, Port: {SMTP_PORT}, Email: {SMTP_EMAIL}, From: {SMTP_FROM}, PasswordSet: {SMTP_PASSWORD is not None}"
        )
    return config_ok

def send_smtp_email(to: str, subject: str, html: str):
    """
    Send an HTML email via the configured Zoho SMTP server.
    
    Checks that SMTP settings are complete (via smtp_is_configured()); if not configured the function returns without sending. Constructs a MIME multipart message with the provided HTML body and attempts to send it over an SSL SMTP connection using module-level SMTP credentials. All exceptions during connect/auth/send are caught and logged; the function does not raise on failure.
    
    Parameters:
        to (str): Recipient email address (as a single address string).
        subject (str): Email subject line.
        html (str): HTML-formatted email body.
    """
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
    """
    Send a one-time passcode (OTP) email to a user.
    
    Composes a simple HTML email containing the provided verification `code` and its time-to-live (in minutes), then sends it to `user_email` using the module's SMTP sender (delegates to send_smtp_email).
    
    Parameters:
        user_email (str): Recipient email address.
        code (str): Verification code to include in the message (expected to be a 6-digit string).
        ttl_minutes (int): Time-to-live for the code, expressed in minutes.
    """
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
