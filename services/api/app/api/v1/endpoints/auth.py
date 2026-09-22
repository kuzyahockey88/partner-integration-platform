from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from fastapi.security import OAuth2PasswordRequestForm

from ....core.database import get_db
from ....services.auth_service import AuthService
from ....schemas.auth import UserCreateRequest, UserLoginRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
        request: UserCreateRequest,
        db: AsyncSession = Depends(get_db)
):

    auth_service = AuthService(db)

    try:
        user = await auth_service.create_user(request)
        logger.info(f"User registered: {user.username} ({user.email})")
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/auth/token", response_model=TokenResponse)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):

    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    logger.info(f"User logged in via OAuth2: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login", response_model=TokenResponse)
async def login(
        request: UserLoginRequest,
        db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}