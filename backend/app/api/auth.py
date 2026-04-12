from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.base import get_db
from backend.app.models.user import User
from backend.app.services.research_repository import ResearchRepository

router = APIRouter(prefix="/auth", tags=["auth"])


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
    task_ids: list[str]


class ClaimAnonymousHistoryResponse(BaseModel):
    claimed: int


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
    request: ClaimAnonymousHistoryRequest,
    current_user: User = Depends(get_current_user),
) -> ClaimAnonymousHistoryResponse:
    repository = ResearchRepository()
    claimed = repository.assign_anonymous_tasks_to_user(
        request.task_ids,
        current_user.id,
    )
    return ClaimAnonymousHistoryResponse(claimed=claimed)
