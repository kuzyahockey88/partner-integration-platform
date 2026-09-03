import uuid
from loguru import logger
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..models.operation import IntegrationOperation, OperationStatus, StatusHistory
from ..schemas.operation import OperationCreateRequest
from ..validators.payload_validator import PayloadValidator
from .cache_service import cache_service

class OperationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_operation(self, request: OperationCreateRequest, user_id: int) -> IntegrationOperation:
        if request.external_request_id:
            existing = await self._find_by_external_id(
                request.partner_id,
                request.external_request_id
            )
            if existing:
                return existing

        operation_id = str(uuid.uuid4())

        operation = IntegrationOperation(
            operation_id=operation_id,
            partner_id=request.partner_id,
            external_request_id=request.external_request_id,
            operation_type=request.operation_type,
            payload=request.payload,
            status=OperationStatus.RECEIVED,
            received_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=user_id,
        )

        self.db.add(operation)

        history = StatusHistory(
            operation=operation,
            from_status=None,
            to_status=OperationStatus.RECEIVED,
            reason="Операция создана",
            changed_at=datetime.utcnow()
        )
        self.db.add(history)

        try:
            await self.db.commit()
            await self.db.refresh(operation)
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Операция с таким external_request_id уже существует")

        await self._validate_operation(operation)

        return operation

    async def get_operation_by_id(self, operation_id: str) -> IntegrationOperation:
        stmt = select(IntegrationOperation).where(
            IntegrationOperation.operation_id == operation_id
        )
        result = await self.db.execute(stmt)
        operation = result.scalar_one_or_none()

        if not operation:
            raise ValueError(f"Операция {operation_id} не найдена")
        return operation

    async def _find_by_external_id(self, partner_id: int, external_id: str):
        stmt = select(IntegrationOperation).where(
IntegrationOperation.partner_id == partner_id,
            IntegrationOperation.external_request_id == external_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_operation(self, operation: IntegrationOperation) -> None:
        errors = PayloadValidator.validate(
            payload=operation.payload,
            operation_type=operation.operation_type,
            operation_id=operation.id
        )

        if errors:
            for error in errors:
                self.db.add(error)

            operation.status = OperationStatus.VALIDATION_FAILED
            operation.updated_at = datetime.utcnow()

            operation.error_details = {
                'errors': [
                    {
                        "row": e.row_number,
                        "field": e.field_name,
                        "code": e.error_code,
                        "message": e.error_message
                    }
                    for e in errors
                ],
                "total_errors": len(errors)
            }

            history = StatusHistory(
                operation=operation,
                from_status=OperationStatus.RECEIVED,
                to_status=OperationStatus.VALIDATION_FAILED,
                reason=f"Ошибка валидации: {len(errors)} шт.",
                changed_at=datetime.utcnow()
            )
            self.db.add(history)

            await self.db.commit()
            await self.db.refresh(operation)

            cache_key = f"operation_status:{operation.operation_id}"
            await cache_service.delete(cache_key)
            logger.info(f"Cache invalidated for operation {operation.operation_id}")