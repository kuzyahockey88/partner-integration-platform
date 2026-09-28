from typing import Optional
from loguru import logger
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import hashlib

from ..core.config import settings
from .cache_service import cache_service

class LLMService:
    def __init__(self):
        self._client: Optional[GigaChat] = None

    def _get_client(self) -> GigaChat:
        if self._client is None:
            self._client = GigaChat(
                credentials=settings.gigachat_credentials,
                scope=settings.gigachat_scope,
                model=settings.gigachat_model,
                verify_ssl_certs=False,
            )
        return self._client

    async def explain_validation_error(
        self,
        error_code: str,
        field_name: Optional[str],
        row_number: Optional[int],
        error_message: str,
        operation_type: str,
    ) -> str:
        """
        Генерирует понятное объяснение ошибок валидации через LLM.
        """
        cache_key_raw = f"{error_code}:{field_name or 'none'}:{operation_type}"
        cache_hash = hashlib.md5(cache_key_raw.encode()).hexdigest()[:16]
        cache_key = f"llm_error:{cache_hash}"

        cached = await cache_service.get(cache_key)
        if cached:
            logger.info(f"LLM кеш HIT: {error_code} / {field_name}")
            return cached

        logger.info(f"LLM кеш MISS: {error_code} / {field_name}")

        prompt = f"""Ты - помощник техподдержки маркетплейса Мегамаркет.
Партнер отправил данные, но они не прошли валидацию.
**Детали ошибки:**
- Код ошибки: {error_code}
- Поле: {field_name or "не указано"}
- Строка: {row_number or "не указана"}
- Сообщение: {error_message}
- Тип операции: {operation_type}

**Твоя задача:**
Объясни простыми словами:
1. Что именно не так с данными партнёра
2. Как партнёру исправить эту ошибку (пошагово)
3. Готовый текст сообщения для партнёра (1-2 предложения, вежливо)

Отвечай кратко, без лишних слов. Формат ответа строго такой:

**Что не так:**
[объяснение в 1 предложении]

**Как исправить:**
1. [шаг 1]
2. [шаг 2]

**Сообщение для партнёра:**
[готовый текст на 1-2 предложения]
"""

        try:
            client = self._get_client()

            chat = Chat(
                messages=[
                    Messages(role=MessagesRole.USER, content=prompt)
                ],
                temperature=0.3,
            )

            response = client.chat(chat)
            explanation = response.choices[0].message.content

            logger.info(
                f"GigaChat ответил: {error_code} / {field_name}"
            )

            await cache_service.set(cache_key, explanation, ttl=86400)

            return explanation

        except Exception as e:
            logger.error(f"Ошибка LLM: {e}")
            return self._fallback_explanation(
                error_code, field_name, row_number, error_message
            )

    def _fallback_explanation(
        self,
        error_code: str,
        field_name: Optional[str],
        row_number: Optional[int],
        error_message: str,
    ) -> str:
        return f"""**Что не так:**
Ошибка в поле '{field_name or "не указано"}' (строка {row_number or "не указана"}): {error_message}

**Как исправить:**
1. Проверьте данные в указанном поле
2. Исправьте согласно требованиям API
3. Загрузите файл заново

**Сообщение для партнёра:**
Пожалуйста, проверьте поле '{field_name}' в строке {row_number}: {error_message}"""



llm_service = LLMService()