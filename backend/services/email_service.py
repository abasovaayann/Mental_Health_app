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
        self.email_from = settings.EMAIL_FROM
        self.email_password = settings.EMAIL_PASSWORD

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
