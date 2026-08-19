from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from ....core.database import get_db
from ....services.operation_service import OperationService
from ....schemas.operation import OperationCreateRequest, OperationResponse, OperationStatusResponse

router = APIRouter()

@router.post("/operations", response_model=OperationResponse, status_code=201)
async def create_operation(
        request: OperationCreateRequest,
        db: AsyncSession = Depends(get_db)
):

    service = OperationService(db)

    try:
        operation = await service.create_operation(request)

        logger.info(f"Операция создана: {operation.operation_id} (партнер: {operation.partner_id})")

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
    service = OperationService(db)

    try:
        operation = await service.get_operation_by_id(operation_id)

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
        logger.warning(f"Операция не найдена: {operation_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении статуса операции: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервиса")
