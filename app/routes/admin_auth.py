from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..auth import authenticate_admin, create_admin_token, get_token_header_name


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    header_name: str = get_token_header_name()


router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login", response_model=AdminLoginResponse, status_code=status.HTTP_200_OK)
def admin_login(payload: AdminLoginRequest) -> AdminLoginResponse:
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required.",
        )
    authenticate_admin(username, payload.password)
    token, ttl = create_admin_token(username)
    return AdminLoginResponse(token=token, expires_in=ttl)
