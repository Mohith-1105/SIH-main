"""RFC 6238 Multi-Factor Authentication (TOTP) Module

Provides Time-Based One-Time Password generation and verification compatible with
Google Authenticator, Microsoft Authenticator, and hardware security tokens.

Each user holds their own random TOTP secret (users.totp_secret); nothing here is
derived from the server SECRET_KEY or the user's email.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

from jose import jwt, JWTError
from app.config import settings

# 30-second standard RFC 6238 interval
TOTP_INTERVAL = 30
MFA_ALGORITHM = "HS256"


def generate_totp_secret() -> str:
    """Generate a fresh random RFC 4648 base32 secret (16 chars) for a user."""
    return base64.b32encode(secrets.token_bytes(10)).decode("ascii").rstrip("=")


def _totp_code(secret_base32: str, counter: int) -> str:
    """RFC 6238 TOTP value for an explicit counter."""
    padded = secret_base32 + "=" * ((8 - len(secret_base32) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"


def generate_current_totp(secret_base32: str, interval: int = TOTP_INTERVAL) -> str:
    """Generate current 6-digit TOTP code according to RFC 6238."""
    return _totp_code(secret_base32, int(time.time() // interval))


def verify_totp(secret_base32: str, code: str, window: int = 1) -> bool:
    """Verify an input 6-digit MFA code against the user's stored secret.
    Allows a +/- 1 step (30s) clock drift window. No bypass code.
    """
    cleaned = (code or "").strip()
    if not cleaned or len(cleaned) != 6 or not cleaned.isdigit():
        return False
    try:
        counter = int(time.time() // TOTP_INTERVAL)
        for step in range(counter - window, counter + window + 1):
            if _totp_code(secret_base32, step) == cleaned:
                return True
    except Exception:
        return False
    return False


def create_temp_mfa_token(user_id: int, email: str) -> str:
    """Create a short-lived (5 minute) token to bridge between password auth and MFA completion."""
    expire = time.time() + 300  # 5 minutes
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "mfa_pending",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=MFA_ALGORITHM)


def decode_temp_mfa_token(token: str) -> dict:
    """Decode and validate a temporary MFA token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[MFA_ALGORITHM])
        if payload.get("type") != "mfa_pending":
            raise ValueError("Invalid token type")
        return payload
    except (JWTError, ValueError) as err:
        raise ValueError("MFA verification session expired or invalid") from err