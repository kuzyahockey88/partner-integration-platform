from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json
from ....core.database import get_db
from ....services.operation_service import OperationService
from ....schemas.operation import OperationCreateRequest, OperationResponse, OperationStatusResponse
from ....models.operation import ValidationError
from ....schemas.operation import ValidationErrorResponse
from typing import List
from sqlalchemy import select
from ....services.cache_service import cache_service
from ....api.v1.dependencies import get_current_active_user
from ....models.user import User

router = APIRouter()

@router.post("/operations", response_model=OperationResponse, status_code=201)
async def create_operation(
        request: OperationCreateRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):

    service = OperationService(db)

    try:
        operation = await service.create_operation(request, current_user.id)

        logger.info(f"Операция создана: {operation.operation_id} (партнер: {operation.partner_id}, пользователь: {current_user.username})")

        return OperationResponse(
            operation_id=operation.operation_id,
            status=operation.status,
            received_at=operation.received_at,
            partner_id=operation.partner_id
        )
    except ValueError as e:
        logger.warning(f"Ошибка при создании операции: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданна ошибка при создании операции: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.get("/operations/{operation_id}/status", response_model=OperationStatusResponse)
async def get_operation_status(
        operation_id: str,
        db: AsyncSession = Depends(get_db)
):
    cache_key = f"operation_status:{operation_id}"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        logger.info(f"Cache hit for operation {operation_id}")
        return json.loads(cached_data)

    logger.info(f"Cache miss for operation {operation_id}")

    service = OperationService(db)

    try:
        operation = await service.get_operation_by_id(operation_id)

        response = OperationStatusResponse(
            operation_id=operation.operation_id,
            status=operation.status,
            received_at=operation.received_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
            retry_count=operation.retry_count,
            last_error_message=operation.last_error_message,
        )

        await cache_service.set(cache_key, response.model_dump())
        return response
    except ValueError as e:
        logger.warning(f"Операция не найдена: {operation_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении статуса операции: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервиса")

@router.get("/operations/{operation_id}/errors", response_model=List[ValidationErrorResponse])
async def get_operation_errors(
        operation_id: str,
        db: AsyncSession = Depends(get_db)
):
    service = OperationService(db)
    try:
        operation = await service.get_operation_by_id(operation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Операция не найдена")

    stmt = select(ValidationError).where(
        ValidationError.operation_id == operation.id
    ).order_by(ValidationError.row_number)

    result = await db.execute(stmt)
    errors = result.scalars().all()

    return errors