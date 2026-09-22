import asyncio
import sys
from datetime import datetime

from celery import Task
from loguru import logger
from sqlalchemy import select

from .celery_app import celery_app
from ..core.database import AsyncSessionLocal, engine
from ..models.operation import (
    IntegrationOperation,
    OperationStatus,
    StatusHistory,
)
from ..services.cache_service import cache_service
from ..models.user import User

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class OperationTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

@celery_app.task(
    bind=True,
    base=OperationTask,
    name="worker.process_operation",
)
def process_operation(self, operation_id: str):
    logger.info(f"[Task #{self.request.id}] Начало обработки: {operation_id}")
    retry_num = self.request.retries

    try:
        result = asyncio.run(
            _run_operation(operation_id, retry_num)
        )
        logger.info(f"[Task #{self.request.id}] Готово: {result}")
        return result
    except Exception as exc:
        logger.error(
            f"[Task #{self.request.id}] Ошибка {operation_id} "
            f"(попытка {retry_num + 1}): {exc}"
        )
        raise self.retry(exc=exc)


async def _run_operation(operation_id: str, retry_num: int) -> dict:
    try:
        result = await _process_operation_async(operation_id)
        return result
    except Exception as exc:
        await _handle_failure(operation_id, str(exc), retry_num)
        raise
    finally:
        await engine.dispose()

async def _process_operation_async(operation_id: str) -> dict:
    async with AsyncSessionLocal() as session:
        stmt = select(IntegrationOperation).where(
            IntegrationOperation.operation_id == operation_id
        )
        result = await session.execute(stmt)
        operation = result.scalar_one_or_none()

        if not operation:
            raise ValueError(f"Операция {operation_id} не найдена")

        if operation.status not in [
            OperationStatus.RECEIVED,
            OperationStatus.RETRYING,
        ]:
            logger.warning(
                f" Операция {operation_id} в статусе {operation.status.value}, пропускаем"
            )
            return {
                "operation_id": operation_id,
                "status": operation.status.value,
                "skipped": True,
            }

        old_status = operation.status
        operation.status = OperationStatus.PROCESSING
        operation.updated_at = datetime.utcnow()

        session.add(StatusHistory(
            operation=operation,
            from_status=old_status,
            to_status=OperationStatus.PROCESSING,
            reason="Начало обработки",
            changed_at=datetime.utcnow(),
        ))

        await session.commit()
        await session.refresh(operation)

        logger.info(
            f" Обработка {operation_id}"
            f"(партнер={operation.partner_id}, тип={operation.operation_type})"
        )

        payload = operation.payload or {}
        if payload.get("simulate_error"):
            raise Exception("Симуляция временной ошибки для теста retry")

        await asyncio.sleep(0.5)

        operation.status = OperationStatus.COMPLETED
        operation.completed_at = datetime.utcnow()
        operation.updated_at = datetime.utcnow()
        operation.last_error_message = None

        session.add(StatusHistory(
            operation=operation,
            from_status=OperationStatus.PROCESSING,
            to_status=OperationStatus.COMPLETED,
            reason="Обработка завершена успешно",
            changed_at=datetime.utcnow()
        ))

        await session.commit()

        await _invalidate_cache(operation.operation_id)

        return {
            "operation_id": operation_id,
            "status": "completed",
            "skipped": False,
        }
async def _handle_failure(
        operation_id: str,
        error_message: str,
        retry_count: int,
)  -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(IntegrationOperation).where(
            IntegrationOperation.operation_id == operation_id
        )
        result = await session.execute(stmt)
        operation = result.scalar_one_or_none()

        if not operation:
            logger.warning(f"Операция {operation_id} не найдена при обработке ошибки")
            return

        max_retries = operation.max_retries or 3

        if retry_count < max_retries:
            new_status = OperationStatus.RETRYING
            reason = (
                f"Временная ошибка, попытка {retry_count + 1}/{max_retries}: "
                f"{error_message[:200]}"
            )
        else:
            new_status = OperationStatus.FAILED
            reason = (
                f"Финальная ошибка после {max_retries} попыток: "
                f"{error_message[:200]}"
            )

        old_status = operation.status
        operation.status = new_status
        operation.retry_count = retry_count + 1
        operation.last_error_message = error_message[:500]
        operation.updated_at = datetime.utcnow()

        session.add(StatusHistory(
            operation=operation,
            from_status=old_status,
            to_status=new_status,
            reason=reason,
            changed_at=datetime.utcnow(),
        ))

        await session.commit()

        await _invalidate_cache(operation.operation_id)

        logger.info(
            f"Операция {operation_id} -> {new_status.value}"
            f"(попытка {retry_count + 1}/{max_retries}"
        )

async def _invalidate_cache(operation_id: str)-> None:
    try:
        if cache_service.redis_client is None:
            await cache_service.connect()

        cache_key = f"operation_status:{operation_id}"
        await cache_service.delete(cache_key)
        logger.debug(f"кеш инвалидирован для {operation_id}")
    except Exception as e:
        logger.warning(f"Не удалось инвалидировать кеш: {e}")