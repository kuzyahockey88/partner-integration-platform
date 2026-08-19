import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..models.operation import IntegrationOperation, OperationStatus, StatusHistory
from ..schemas.operation import OperationCreateRequest

class OperationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_operation(self, request: OperationCreateRequest) -> IntegrationOperation:
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