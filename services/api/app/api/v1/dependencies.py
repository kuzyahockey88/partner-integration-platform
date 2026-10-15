from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.core.database import get_db
from services.api.app.services.auth_service import AuthService
from ...models.user import User, UserRole
from ...models.operation import IntegrationOperation

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
)-> User:
    auth_service = AuthService(db)
    try:
        user = await auth_service.get_current_user(token)
        if not user:
            raise ValueError("User not found")
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
        current_user: User = Depends(get_current_user)
)-> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_manager(
        current_user: User = Depends(get_current_active_user)
)-> User:
    if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permission. Manager or Admin required."
        )
    return current_user

async def get_current_admin(
        current_user: User = Depends(get_current_active_user)
)-> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def check_operation_access(operation: IntegrationOperation, user: User) -> None:
    if user.role in (UserRole.MANAGER, UserRole.ADMIN):
        return

    if user.partner_id is None or operation.partent_id != user.partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Нет доступа к этой операции',
        )