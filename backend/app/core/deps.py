import re
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import decode_token
from backend.app.db.base import get_db
from backend.app.models.user import User

bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)
_GUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(credentials.credentials)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer_scheme)
    ],
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None

    try:
        user_id = decode_token(credentials.credentials)
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()


def resolve_guest_id(request: Request) -> str | None:
    raw_guest_id = request.headers.get("X-Guest-Id", "").strip()
    if not raw_guest_id:
        return None
    if not _GUEST_ID_RE.fullmatch(raw_guest_id):
        return None
    return raw_guest_id
