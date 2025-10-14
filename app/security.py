from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .auth import get_token_header_name, verify_admin_token

_admin_token_header = APIKeyHeader(
    name=get_token_header_name(), auto_error=False
)


def require_admin_token(token: str | None = Security(_admin_token_header)) -> str:
    """Ensure the incoming request carries a valid admin session token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin token.",
        )
    verify_admin_token(token)
    return token
