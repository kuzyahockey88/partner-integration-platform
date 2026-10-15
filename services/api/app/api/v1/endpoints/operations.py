from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json

from ....core.database import get_db
from ....services.operation_service import OperationService
from ....services.llm_service import llm_service
from ....schemas.operation import (
    OperationCreateRequest,
    OperationResponse,
    OperationStatusResponse,
    ValidationErrorResponse,
    OperationListResponse,
    OperationStatus,
)
from ....models.operation import ValidationError
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from ....services.cache_service import cache_service
from ....api.v1.dependencies import get_current_active_user, check_operation_access
from ....models.user import User, UserRole

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
            partner_id=operation.partner_id,
            user_id=operation.user_id,
            operation_type=operation.operation_type,
            completed_at=operation.completed_at,
        )
    except ValueError as e:
        logger.warning(f"Ошибка при создании операции: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданна ошибка при создании операции: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/operations", response_model=OperationListResponse)
async def list_operations(
        partner_id: Optional[int] = Query(None, description="Фильтр по ID партнёра"),
        status: Optional[OperationStatus] = Query(None, description="Фильтр по статусу"),
        operation_type: Optional[str] = Query(None, description="Тип операции"),
        date_from: Optional[datetime] = Query(None, description="Дата начала (ISO 8601)"),
        date_to: Optional[datetime] = Query(None, description="Дата конца (ISO 8601)"),
        skip: int = Query(0, ge=0, description="Сколько операций пропустить"),
        limit: int = Query(20, ge=1, le=100, description="Максимум операций в ответе"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):

    service = OperationService(db)

    operations, total = await service.list_operations(
        partner_id=partner_id,
        status=status,
        operation_type=operation_type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )

    logger.info(
        f"📋 Список операций: найдено {total}, "
        f"показано {len(operations)} (skip={skip}, limit={limit})"
    )

    return OperationListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[
            OperationResponse(
                operation_id=op.operation_id,
                status=op.status,
                received_at=op.received_at,
                partner_id=op.partner_id,
                user_id=op.user_id,
                operation_type=op.operation_type,
                completed_at=op.completed_at,
            )
            for op in operations
        ],
    )


@router.post("/operations/{operation_id}/retry", response_model=OperationStatusResponse)
async def retry_operation(
    operation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):

    service = OperationService(db)

    try:
        operation = await service.retry_operation(
            operation_id=operation_id,
            user_id=current_user.id,
        )

        logger.info(
            f"Retry операции {operation_id} "
            f"(пользователь: {current_user.username})"
        )

        return OperationStatusResponse(
            operation_id=operation.operation_id,
            status=operation.status,
            received_at=operation.received_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
            retry_count=operation.retry_count,
            last_error_message=operation.last_error_message,
        )
    except ValueError as e:
        logger.warning(f"Ошибка retry: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при retry: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/operations/{operation_id}/status", response_model=OperationStatusResponse)
async def get_operation_status(
        operation_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):

    service = OperationService(db)

    try:
        operation = await service.get_operation_by_id(operation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Операция не найдена')

    check_operation_access(operation, current_user)

    cache_key = f"operation_status:{operation_id}"
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for operation {operation_id}")
        return json.loads(cached_data)

    logger.info(f"Cache miss for operation {operation_id}")

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

@router.get("/operations/{operation_id}/errors", response_model=List[ValidationErrorResponse])
async def get_operation_errors(
        operation_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    service = OperationService(db)

    try:
        operation = await service.get_operation_by_id(operation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Операция не найдена")

    check_operation_access(operation, current_user)

    stmt = select(ValidationError).where(
        ValidationError.operation_id == operation.id
    ).order_by(ValidationError.row_number)

    result = await db.execute(stmt)
    errors = result.scalars().all()

    enriched_errors = []
    for error in errors:
        explanation = await llm_service.explain_validation_error(
            error_code=error.error_code,
            field_name=error.field_name,
            row_number=error.row_number,
            error_message=error.error_message,
            operation_type=operation.operation_type,
        )

        enriched_errors.append(
            ValidationErrorResponse(
                id=error.id,
                row_number=error.row_number,
                field_name=error.field_name,
                error_code=error.error_code,
                error_message=error.error_message,
                created_at=error.created_at,
                llm_explanation=explanation,
            )
        )

    return enriched_errors