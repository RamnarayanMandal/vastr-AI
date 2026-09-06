from __future__ import annotations

import base64
import logging
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)

RESET_SUBJECT = "Reset your VastrAI password"


def _password_reset_html(otp: str) -> str:
    return f"""<!doctype html>
<html lang="en">
    <body style="margin:0;background:#f5f2eb;color:#17151f;font-family:Arial,sans-serif;">
        <div style="max-width:560px;margin:32px auto;padding:0 20px;">
            <div style="background:#0d0b1a;padding:28px 32px;border-radius:14px 14px 0 0;">
                <div style="color:#c9a96a;font-size:24px;font-weight:700;">VastrAI</div>
                <div style="color:#f8f5ee;margin-top:8px;font-size:13px;">See it. Try it. Wear it.</div>
            </div>
            <div style="background:#ffffff;padding:32px;border-radius:0 0 14px 14px;">
                <h1 style="margin:0 0 16px;font-size:25px;">Reset your password</h1>
                <p style="line-height:1.6;">We received a request to reset your VastrAI password. Enter this one-time password in the VastrAI app.</p>
                <p style="margin:28px 0;text-align:center;font-size:36px;letter-spacing:10px;font-weight:800;color:#0d0b1a;">{otp}</p>
                <p style="color:#686474;font-size:13px;line-height:1.6;">This OTP expires in 10 minutes and can only be used once. If you did not request this, you can safely ignore this email.</p>
            </div>
        </div>
    </body>
</html>"""


def _password_reset_text(otp: str) -> str:
    return f"Reset your VastrAI password\n\nYour VastrAI one-time password is: {otp}\n\nIt expires in 10 minutes and can only be used once. If you did not request this, you can safely ignore this email."


class EmailService:
    """Gmail API sender using server-side OAuth refresh credentials."""

    def send_password_reset_email(self, recipient: str, otp: str) -> None:
        if settings.email_provider != "gmail":
            logger.warning("Gmail email service is not enabled")
            return
        if not all((settings.google_client_id, settings.google_client_secret, settings.google_refresh_token)):
            logger.warning("Gmail email service is not configured")
            return

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = Credentials(
            token=None,
            refresh_token=settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        credentials.refresh(Request())

        message = EmailMessage()
        message["To"] = recipient
        message["From"] = settings.google_sender_email or settings.email_from
        message["Subject"] = RESET_SUBJECT
        message.set_content(_password_reset_text(otp))
        message.add_alternative(_password_reset_html(otp), subtype="html")
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

        build("gmail", "v1", credentials=credentials, cache_discovery=False).users().messages().send(
            userId="me", body={"raw": encoded}
        ).execute()
        logger.info("Password reset email sent recipient=%s", recipient)


email_service = EmailService()