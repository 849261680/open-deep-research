import os
import secrets
from asyncio import to_thread
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user
from backend.app.core.deps import resolve_guest_id
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.base import get_db
from backend.app.models.user import User
from backend.app.services.research_repository import ResearchRepository

router = APIRouter(prefix="/auth", tags=["auth"])
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_OAUTH_STATE_COOKIE = "google_oauth_state"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class ClaimAnonymousHistoryRequest(BaseModel):
    task_ids: list[str] = Field(default_factory=list)
    guest_id: str | None = None


class ClaimAnonymousHistoryResponse(BaseModel):
    claimed: int


class GoogleOAuthSettings(BaseModel):
    """保存构建 Google OAuth 授权请求所需的配置。"""

    client_id: str
    client_secret: str
    redirect_uri: str


class GoogleOAuthError(RuntimeError):
    """表示 Google OAuth 交换或用户资料读取失败。"""


def load_google_oauth_settings() -> GoogleOAuthSettings | None:
    """从环境变量读取 Google OAuth 配置，缺失时返回 None。"""
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        return None
    return GoogleOAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )


def build_google_authorization_url(settings: GoogleOAuthSettings, state: str) -> str:
    """生成 Google OAuth 授权页 URL。"""
    query = urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": settings.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTHORIZATION_URL}?{query}"


def frontend_oauth_redirect(params: dict[str, str] | None = None, fragment: dict[str, str] | None = None) -> str:
    """构建 OAuth 完成后跳回前端的 URL。"""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3003").rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    hash_fragment = f"#{urlencode(fragment)}" if fragment else ""
    return f"{frontend_url}/{query}{hash_fragment}"


def google_oauth_state_is_valid(request: Request, state: str | None) -> bool:
    """校验回调 state 是否匹配登录入口写入的 cookie。"""
    if not state:
        return False
    expected_state = request.cookies.get(GOOGLE_OAUTH_STATE_COOKIE)
    return bool(expected_state and secrets.compare_digest(expected_state, state))


def fetch_google_user_email_sync(settings: GoogleOAuthSettings, code: str) -> str:
    """通过 Google OAuth code 换取用户邮箱。"""
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.redirect_uri,
        },
        timeout=10,
    )
    if not token_response.ok:
        raise GoogleOAuthError("google_token_exchange_failed")

    access_token = token_response.json().get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthError("google_access_token_missing")

    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if not userinfo_response.ok:
        raise GoogleOAuthError("google_userinfo_failed")

    email = userinfo_response.json().get("email")
    if not isinstance(email, str) or not email:
        raise GoogleOAuthError("google_email_missing")
    return email


async def fetch_google_user_email(settings: GoogleOAuthSettings, code: str) -> str:
    """在线程中执行 Google OAuth 网络请求，避免阻塞事件循环。"""
    return await to_thread(fetch_google_user_email_sync, settings, code)


async def find_or_create_google_user(email: str, db: AsyncSession) -> User:
    """按邮箱复用用户，不存在则创建一个随机不可知密码的用户。"""
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()
    if user:
        return user

    random_password = secrets.token_urlsafe(32)
    user = User(email=normalized_email, hashed_password=hash_password(random_password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    user = User(email=request.email, hashed_password=hash_password(request.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """跳转到 Google 授权页并写入一次性 state cookie。"""
    settings = load_google_oauth_settings()
    if settings is None:
        raise HTTPException(status_code=503, detail="Google 登录未配置")

    state = secrets.token_urlsafe(32)
    response = RedirectResponse(build_google_authorization_url(settings, state))
    response.set_cookie(
        GOOGLE_OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """处理 Google OAuth 回调，成功后把现有 JWT 返回给前端。"""
    response = RedirectResponse(frontend_oauth_redirect({"oauth_error": "cancelled"}))
    if error:
        response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
        return response

    settings = load_google_oauth_settings()
    if settings is None or not code:
        response = RedirectResponse(frontend_oauth_redirect({"oauth_error": "config_missing"}))
        response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
        return response

    if not google_oauth_state_is_valid(request, state):
        response = RedirectResponse(frontend_oauth_redirect({"oauth_error": "invalid_state"}))
        response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
        return response

    try:
        email = await fetch_google_user_email(settings, code)
    except GoogleOAuthError:
        response = RedirectResponse(frontend_oauth_redirect({"oauth_error": "google_exchange_failed"}))
        response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
        return response

    user = await find_or_create_google_user(email, db)
    response = RedirectResponse(
        frontend_oauth_redirect(fragment={"auth_token": create_access_token(user.id)})
    )
    response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
    return response


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/claim-history", response_model=ClaimAnonymousHistoryResponse)
async def claim_anonymous_history(
    payload: ClaimAnonymousHistoryRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> ClaimAnonymousHistoryResponse:
    repository = ResearchRepository()
    guest_id = payload.guest_id or resolve_guest_id(http_request)
    claimed = repository.assign_anonymous_tasks_to_user(
        payload.task_ids,
        current_user.id,
        guest_id=guest_id,
    )
    return ClaimAnonymousHistoryResponse(claimed=claimed)
