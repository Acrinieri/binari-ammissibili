from __future__ import annotations

import base64
import binascii
import hmac
import hashlib
import os
import time
from typing import Tuple

from fastapi import HTTPException, status

_TOKEN_HEADER = "X-Admin-Token"
_DEFAULT_TOKEN_TTL = 3600


def get_token_header_name() -> str:
    return _TOKEN_HEADER


def _get_secret_key() -> str:
    secret = os.environ.get("ADMIN_API_KEY")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured on the server.",
        )
    return secret


def _get_admin_credentials() -> Tuple[str, str]:
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin credentials not configured on the server.",
        )
    return username, password


def authenticate_admin(username: str, password: str) -> None:
    expected_username, expected_password = _get_admin_credentials()
    if not hmac.compare_digest(username, expected_username) or not hmac.compare_digest(
        password, expected_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )


def _get_token_ttl() -> int:
    try:
        raw_ttl = int(os.environ.get("ADMIN_TOKEN_TTL", str(_DEFAULT_TOKEN_TTL)))
    except ValueError:
        raw_ttl = _DEFAULT_TOKEN_TTL
    return max(60, raw_ttl)


def create_admin_token(username: str) -> Tuple[str, int]:
    secret = _get_secret_key()
    ttl = _get_token_ttl()
    expires_at = int(time.time()) + ttl
    payload = f"{username}:{expires_at}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token_bytes = f"{payload}:{signature}".encode()
    token = base64.urlsafe_b64encode(token_bytes).decode()
    return token, ttl


def verify_admin_token(token: str) -> str:
    secret = _get_secret_key()
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        username, expires_at_str, signature = decoded.rsplit(":", 2)
        expires_at = int(expires_at_str)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token."
        ) from None

    message = f"{username}:{expires_at}"
    expected_signature = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token."
        )
    if expires_at < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired admin token."
        )

    return username
