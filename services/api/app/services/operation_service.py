import uuid
from loguru import logger
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.exc import IntegrityError
from ..models.operation import IntegrationOperation, OperationStatus, StatusHistory, ValidationError
from ..schemas.operation import OperationCreateRequest
from ..validators.payload_validator import PayloadValidator
from .cache_service import cache_service
from typing import Optional, List, Tuple


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

        if operation.status == OperationStatus.RECEIVED:
            from ..worker.tasks import process_operation
            process_operation.delay(operation.operation_id)
            logger.info(f"Задача в Celery: {operation.operation_id}")
        else:
            logger.info(
                f"Операция {operation.operation_id} не отправлена в Celery"
                f"(статус: {operation.status.value})"
            )
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
        await self.db.execute(
            delete(ValidationError).where(ValidationError.operation_id == operation.id)
        )
        await self.db.flush()

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

    async def list_operations(
        self,
        partner_id: Optional[int] = None,
        status: Optional[OperationStatus] = None,
        operation_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[IntegrationOperation], int]:

        conditions = []

        if partner_id is not None:
            conditions.append(IntegrationOperation.partner_id == partner_id)

        if status is not None:
            conditions.append(IntegrationOperation.status == status)

        if operation_type is not None:
            conditions.append(IntegrationOperation.operation_type == operation_type)

        if date_from is not None:
            conditions.append(IntegrationOperation.received_at >= date_from)

        if date_to is not None:
            conditions.append(IntegrationOperation.received_at <= date_to)

        count_stmt = select(func.count()).select_from(IntegrationOperation)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = select(IntegrationOperation)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt
            .order_by(IntegrationOperation.received_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        operations = list(result.scalars().all())

        return operations, total

    async def retry_operation(
        self,
        operation_id: str,
        user_id: int,
    ) -> IntegrationOperation:

        operation = await self.get_operation_by_id(operation_id)

        allowed_statuses = {
            OperationStatus.FAILED,
            OperationStatus.VALIDATION_FAILED,
        }

        if operation.status not in allowed_statuses:
            raise ValueError(
                f"Нельзя перезапустить операцию в статусе "
                f"{operation.status.value}. "
                f"Разрешено только: {', '.join(s.value for s in allowed_statuses)}"
            )

        old_status = operation.status
        operation.status = OperationStatus.RECEIVED
        operation.retry_count = 0
        operation.last_error_message = None
        operation.updated_at = datetime.utcnow()
        operation.completed_at = None

        history = StatusHistory(
            operation=operation,
            from_status=old_status,
            to_status=OperationStatus.RECEIVED,
            reason=f"Ручной перезапуск пользователем #{user_id}",
            changed_at=datetime.utcnow(),
        )
        self.db.add(history)

        await self.db.commit()
        await self.db.refresh(operation)

        await self._validate_operation(operation)

        cache_key = f"operation_status:{operation.operation_id}"
        await cache_service.delete(cache_key)

        if operation.status == OperationStatus.RECEIVED:
            from ..worker.tasks import process_operation
            process_operation.delay(operation.operation_id)
            logger.info(
                f"Ручной retry операции {operation.operation_id} "
                f"(было: {old_status.value}, пользователь: {user_id})"
            )
        else:
            logger.info(
                f"Retry отменен: {operation.operation_id} "
                f"снова не прошла валидация "
                f"(статус: {operation.status.value})"
            )

        return operation