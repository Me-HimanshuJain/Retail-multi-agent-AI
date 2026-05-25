"""Authentication routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserInfo(BaseModel):
    username: str
    role: str
    is_active: bool


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> LoginResponse:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username, "role": user.role}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return LoginResponse(access_token=token, username=user.username, role=user.role)


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(**current_user.model_dump())


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)) -> LoginResponse:
    token = create_access_token({"sub": current_user.username, "role": current_user.role}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return LoginResponse(access_token=token, username=current_user.username, role=current_user.role)
