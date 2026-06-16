"""Email service for sending reminders via Gmail SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via Gmail SMTP."""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.email_from = (settings.EMAIL_FROM or "").strip()
        # Gmail shows app passwords as four space-separated groups; users often
        # paste them verbatim. Spaces are display-only and break SMTP auth, so
        # strip all whitespace defensively.
        self.email_password = "".join((settings.EMAIL_PASSWORD or "").split())

    def is_configured(self) -> bool:
        """True if both sender address and password are present."""
        return bool(self.email_from and self.email_password)

    def verify_credentials(self, timeout: int = 20) -> tuple[bool, str]:
        """Attempt an SMTP login (no email sent) to confirm credentials work.

        Returns ``(ok, detail)`` where ``detail`` is a human-readable message
        suitable for logging at startup.
        """
        if not self.is_configured():
            return False, "Email credentials not configured (EMAIL_FROM / EMAIL_PASSWORD)."

        try:
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=timeout) as server:
                    server.login(self.email_from, self.email_password)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout) as server:
                    server.starttls()
                    server.login(self.email_from, self.email_password)
            return True, f"SMTP credentials authenticated for {self.email_from}."
        except smtplib.SMTPAuthenticationError as exc:
            return (
                False,
                f"SMTP authentication rejected (code {exc.smtp_code}). "
                "Use a valid 16-character Gmail App Password (with 2-Step "
                "Verification enabled); spaces are stripped automatically.",
            )
        except Exception as exc:  # noqa: BLE001 — report any connection failure
            return False, f"SMTP connection error: {type(exc).__name__}: {exc}"

    def send_reminder_email(
        self,
        recipient_email: str,
        user_name: str,
        check_in_link: str = "http://localhost:3000/diary",
    ) -> bool:
        """Send check-in reminder email."""

        subject = "Time for your daily mood check-in 💙 | MindTrackAi"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4f46e5;">Hello {user_name}! 👋</h2>
                    
                    <p>It's time for your <strong>daily mental health check-in</strong>.</p>
                    
                    <p>Take just <strong>2 minutes</strong> to log how you're feeling today. 
                    This helps us understand your patterns and provide better insights.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{check_in_link}" 
                           style="display: inline-block; padding: 12px 30px; background-color: #4f46e5; 
                                  color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            📝 Open Check-in
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        Why it matters: Regular check-ins help us build a complete picture of your 
                        mental health journey and provide personalized recommendations.
                    </p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    
                    <p style="color: #999; font-size: 12px;">
                        You're receiving this email because you enabled check-in reminders in your settings.
                        To manage your preferences, visit Settings → Reminders.
                    </p>
                    
                    <p style="color: #999; font-size: 12px;">
                        Best regards,<br>
                        <strong>MindTrackAi Team 💚</strong>
                    </p>
                </div>
            </body>
        </html>
        """

        plain_text = f"""
        Hello {user_name},

        It's time for your daily mental health check-in.

        Take just 2 minutes to log how you're feeling today. 
        This helps us understand your patterns and provide better insights.

        Open check-in: {check_in_link}

        Why it matters: Regular check-ins help us build a complete picture of your 
        mental health journey and provide personalized recommendations.

        Best regards,
        MindTrackAi Team
        """

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )

    def _send_code_email(
        self,
        *,
        recipient_email: str,
        user_name: str,
        code: str,
        subject: str,
        intro: str,
        note: str,
        plain_label: str,
    ) -> bool:
        """Send a one-time code email (verification or password reset).

        ``intro`` is the sentence above the code, ``note`` the expiry/ignore
        sentence below it, and ``plain_label`` names the code in plain text.
        """
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4f46e5;">Hi {user_name}! 👋</h2>
                    <p>{intro}</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="display: inline-block; padding: 14px 28px; background-color: #eef2ff;
                                     color: #4f46e5; font-size: 32px; font-weight: bold; letter-spacing: 8px;
                                     border-radius: 8px;">
                            {code}
                        </span>
                    </div>
                    <p style="color: #666; font-size: 14px;">{note}</p>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 12px;">
                        Best regards,<br><strong>MindTrackAi Team 💚</strong>
                    </p>
                </div>
            </body>
        </html>
        """

        plain_text = (
            f"Hi {user_name},\n\n"
            f"Your MindTrackAi {plain_label} is: {code}\n\n"
            f"{note}\n\n"
            f"MindTrackAi Team"
        )

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )

    def send_verification_email(
        self,
        recipient_email: str,
        user_name: str,
        code: str,
        expires_minutes: int = 15,
    ) -> bool:
        """Send a 6-digit email-verification code."""
        return self._send_code_email(
            recipient_email=recipient_email,
            user_name=user_name,
            code=code,
            subject="Verify your email 🔐 | MindTrackAi",
            intro="Use this code to verify your email address:",
            note=(
                f"This code expires in {expires_minutes} minutes. If you didn't "
                "create a MindTrackAi account, you can safely ignore this email."
            ),
            plain_label="email verification code",
        )

    def send_password_reset_email(
        self,
        recipient_email: str,
        user_name: str,
        code: str,
        expires_minutes: int = 15,
    ) -> bool:
        """Send a 6-digit password-reset code."""
        return self._send_code_email(
            recipient_email=recipient_email,
            user_name=user_name,
            code=code,
            subject="Reset your password 🔑 | MindTrackAi",
            intro="We received a request to reset your password. Use this code to continue:",
            note=(
                f"This code expires in {expires_minutes} minutes. If you didn't "
                "request a password reset, you can safely ignore this email — "
                "your password stays the same."
            ),
            plain_label="password reset code",
        )

    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        html_content: str,
        plain_text: str,
    ) -> bool:
        """Internal method to send email via SMTP."""

        if not self.email_from or not self.email_password:
            logger.error("Email credentials not configured in .env")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = recipient_email

            # Attach plain text and HTML
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send via SMTP — port 465 uses implicit SSL, others use STARTTLS
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.email_from, self.email_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.email_from, self.email_password)
                    server.send_message(msg)

            logger.info(f"✓ Reminder email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to send email to {recipient_email}: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
