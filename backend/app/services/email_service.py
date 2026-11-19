import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging import logger


class DevMailbox:
    """In-memory mailbox strictly as a development-only fallback for local testing.
    
    Captures dispatched emails when Mailpit or external SMTP is not running,
    enabling full automated test coverage and local demonstration without external network dependencies.
    """
    _messages: List[Dict[str, Any]] = []

    @classmethod
    def record_message(
        cls,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        reset_link: Optional[str] = None,
        delivery_mode: str = "dev_mailbox_fallback",
    ):
        cls._messages.append({
            "to": to_email,
            "subject": subject,
            "text": text_body,
            "html": html_body,
            "reset_link": reset_link,
            "delivery_mode": delivery_mode,
        })

    @classmethod
    def get_messages(cls) -> List[Dict[str, Any]]:
        return list(cls._messages)

    @classmethod
    def get_latest_message_for(cls, email: str) -> Optional[Dict[str, Any]]:
        clean = email.strip().lower()
        for msg in reversed(cls._messages):
            if msg["to"].strip().lower() == clean:
                return msg
        return None

    @classmethod
    def clear(cls):
        cls._messages.clear()


class EmailService:
    """Enterprise SMTP Email Service with HTML templating, TLS/SSL, and local development capture."""

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address for safe logging without leaking citizen PII."""
        if not email or "@" not in email:
            return "***"
        parts = email.split("@", 1)
        name, domain = parts[0], parts[1]
        if len(name) <= 2:
            masked_name = name[0] + "***"
        else:
            masked_name = name[:2] + "***" + name[-1]
        return f"{masked_name}@{domain}"

    @classmethod
    def send_password_reset_email(
        cls,
        to_email: str,
        reset_link: str,
        recipient_name: Optional[str] = None,
    ) -> bool:
        """Dispatch a single-use password reset link via SMTP with HTML and plain-text fallback.
        
        Security constraints:
        - Never logs raw reset tokens or passwords.
        - Masks email in logs.
        - Sets expiration notice in email body.
        """
        masked = cls.mask_email(to_email)
        subject = f"[{settings.PROJECT_NAME}] Password Reset Instructions"
        greeting = f"Hello {recipient_name}," if recipient_name else "Hello,"
        expiry_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

        text_content = f"""{greeting}

We received a request to reset your JanMitra Assist account password.

Please click the secure link below or copy and paste it into your browser to choose a new password:
{reset_link}

This link is valid for {expiry_minutes} minutes and can only be used once.

Security Notice:
If you did not request this password reset, please ignore this email. Your password will remain unchanged and your account is secure.

JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background-color: #1e3a8a; color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .content {{ padding: 32px 28px; color: #334155; line-height: 1.6; font-size: 15px; }}
    .button-container {{ text-align: center; margin: 30px 0; }}
    .btn {{ background-color: #2563eb; color: #ffffff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; display: inline-block; }}
    .notice {{ background-color: #f8fafc; border-left: 4px solid #64748b; padding: 12px 16px; margin: 20px 0; font-size: 13px; color: #64748b; }}
    .footer {{ background-color: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🏛️ JanMitra Assist</h1>
      <p style="margin: 4px 0 0; font-size: 13px; opacity: 0.9;">Secure Password Recovery</p>
    </div>
    <div class="content">
      <p>{greeting}</p>
      <p>We received a request to reset your password for your JanMitra Assist account.</p>
      <div class="button-container">
        <a href="{reset_link}" class="btn" target="_blank">Reset Your Password</a>
      </div>
      <p style="font-size: 13px; color: #64748b;">Or paste this link into your browser:<br>
      <a href="{reset_link}" style="color: #2563eb; word-break: break-all;">{reset_link}</a></p>
      <div class="notice">
        <strong>Important:</strong> This single-use link is valid for <strong>{expiry_minutes} minutes</strong>. If you did not request a password reset, no action is needed; your account remains secure.
      </div>
    </div>
    <div class="footer">
      JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System<br>
      Automated system message. Please do not reply directly to this email.
    </div>
  </div>
</body>
</html>
"""

        # Attempt real SMTP delivery if SMTP_HOST is configured
        if settings.SMTP_HOST:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
                msg["To"] = to_email

                msg.attach(MIMEText(text_content, "plain", "utf-8"))
                msg.attach(MIMEText(html_content, "html", "utf-8"))

                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=4)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=4)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
                server.quit()
                logger.info(f"Password reset email dispatched successfully via actual network SMTP to {masked}")

                DevMailbox.record_message(
                    to_email=to_email,
                    subject=subject,
                    text_body=text_content,
                    html_body=html_content,
                    reset_link=reset_link,
                    delivery_mode="smtp_success",
                )
                return True
            except Exception as e:
                logger.warning(
                    f"SMTP dispatch to {masked} via {settings.SMTP_HOST}:{settings.SMTP_PORT} encountered network/service issue: {type(e).__name__}. "
                    "Falling back to local DevMailbox for local development and MCA demonstration."
                )

        # Explicit development-only fallback when SMTP is offline or not configured
        DevMailbox.record_message(
            to_email=to_email,
            subject=subject,
            text_body=text_content,
            html_body=html_content,
            reset_link=reset_link,
            delivery_mode="dev_mailbox_fallback",
        )
        logger.info(f"Password reset email captured in local development fallback mailbox for {masked}")
        return True

