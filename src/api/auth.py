"""JWT authentication helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRATION_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class User(BaseModel):
    username: str
    role: str
    is_active: bool = True


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


USERS_DB: Dict[str, UserInDB] = {
    "admin": UserInDB(username="admin", role="admin", hashed_password="sha256:" + hashlib.sha256(b"admin123").hexdigest()),
    "operator": UserInDB(username="operator", role="operator", hashed_password="sha256:" + hashlib.sha256(b"operator123").hexdigest()),
    "viewer": UserInDB(username="viewer", role="viewer", hashed_password="sha256:" + hashlib.sha256(b"viewer123").hexdigest()),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    return "sha256:" + hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_user(username: str) -> Optional[UserInDB]:
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub") or payload.get("username")
    role = payload.get("role", "viewer")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(username=user.username, role=role, is_active=user.is_active)


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user


admin_required = RoleChecker(["admin"])
operator_required = RoleChecker(["admin", "operator"])
any_authenticated = RoleChecker(["admin", "operator", "viewer"])
