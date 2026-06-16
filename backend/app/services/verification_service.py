"""Email verification: issue and check short-lived 6-digit codes.

A single active code is stored per user (hashed) directly on the ``app_users``
row. Codes expire quickly and allow a limited number of attempts to blunt
brute-force guessing of the small 6-digit space.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15
MAX_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    """SHA-256 hex digest of a verification code (codes are short-lived)."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    """Return a zero-padded random numeric code, e.g. ``'046913'``."""
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


class VerificationService:
    """Generate, send, and verify email-verification codes."""

    @staticmethod
    def issue_code(db: Session, user: User) -> bool:
        """Generate a fresh code, persist its hash, and email it to the user.

        Returns True if the email was sent. The code is stored regardless so a
        transient send failure can be retried via resend.
        """
        code = _generate_code()
        user.verification_code_hash = _hash_code(code)
        user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=CODE_TTL_MINUTES
        )
        user.verification_attempts = 0
        db.commit()

        sent = get_email_service().send_verification_email(
            recipient_email=user.email,
            user_name=user.first_name,
            code=code,
            expires_minutes=CODE_TTL_MINUTES,
        )
        if not sent:
            logger.error("[verify] Failed to send verification email to user %s", user.id)
        return sent

    @staticmethod
    def verify_code(db: Session, user: User, code: str) -> tuple[bool, str]:
        """Check a submitted code. Returns ``(ok, message)``.

        On success the user is marked verified and the code is cleared. On
        failure the attempt counter increments and the code is invalidated once
        the attempt limit is reached.
        """
        if user.is_verified:
            return True, "Email already verified."

        if not user.verification_code_hash or not user.verification_code_expires_at:
            return False, "No verification code pending. Request a new one."

        expires_at = user.verification_code_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return False, "Verification code expired. Request a new one."

        if user.verification_attempts >= MAX_ATTEMPTS:
            return False, "Too many attempts. Request a new code."

        submitted = (code or "").strip()
        if hmac.compare_digest(user.verification_code_hash, _hash_code(submitted)):
            user.is_verified = True
            user.verification_code_hash = None
            user.verification_code_expires_at = None
            user.verification_attempts = 0
            db.commit()
            return True, "Email verified successfully."

        user.verification_attempts += 1
        db.commit()
        remaining = MAX_ATTEMPTS - user.verification_attempts
        if remaining <= 0:
            return False, "Incorrect code. Too many attempts — request a new code."
        return False, f"Incorrect code. {remaining} attempt(s) remaining."

    @staticmethod
    def issue_reset_code(db: Session, user: User) -> bool:
        """Generate a password-reset code, persist its hash, and email it."""
        code = _generate_code()
        user.reset_code_hash = _hash_code(code)
        user.reset_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=CODE_TTL_MINUTES
        )
        user.reset_attempts = 0
        db.commit()

        sent = get_email_service().send_password_reset_email(
            recipient_email=user.email,
            user_name=user.first_name,
            code=code,
            expires_minutes=CODE_TTL_MINUTES,
        )
        if not sent:
            logger.error("[reset] Failed to send password reset email to user %s", user.id)
        return sent

    @staticmethod
    def reset_password(db: Session, user: User, code: str, new_password_hash: str) -> tuple[bool, str]:
        """Validate a reset code and, on success, set the new password hash."""
        if not user.reset_code_hash or not user.reset_code_expires_at:
            return False, "No reset code pending. Request a new one."

        expires_at = user.reset_code_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return False, "Reset code expired. Request a new one."

        if user.reset_attempts >= MAX_ATTEMPTS:
            return False, "Too many attempts. Request a new code."

        submitted = (code or "").strip()
        if hmac.compare_digest(user.reset_code_hash, _hash_code(submitted)):
            user.hashed_password = new_password_hash
            user.reset_code_hash = None
            user.reset_code_expires_at = None
            user.reset_attempts = 0
            db.commit()
            return True, "Password reset successfully."

        user.reset_attempts += 1
        db.commit()
        remaining = MAX_ATTEMPTS - user.reset_attempts
        if remaining <= 0:
            return False, "Incorrect code. Too many attempts — request a new code."
        return False, f"Incorrect code. {remaining} attempt(s) remaining."
