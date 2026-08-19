from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class OperationStatus(str, Enum):
    RECEIVED = "received"
    VALIDATION = "validation"
    VALIDATION_FAILED = "validation_failed"
    PROCESSING = "processing"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"

class OperationCreateRequest(BaseModel):
    partner_id: int = Field(..., description="ID партнер")
    operation_type: str = Field(..., description="Тип операции: product_upload, price_update, stock_update")
    external_request_id: Optional[str] = Field(None,
    description="ID запрос от партнера (для идемпотентности)")
    payload: Dict[str, Any] = Field(..., description="Данные от партнера")

    @validator('operation_type')
    def validate_operation_type(cls, v):
        allowed = ['product_upload', 'price_update', 'stock_update']
        if v not in allowed:
            raise ValueError(f'Operation type must be one of {allowed}')
        return v

class OperationResponse(BaseModel):
    operation_id: str
    status: OperationStatus
    received_at: datetime
    partner_id: int

    class Config:
        from_attributes = True

class OperationStatusResponse(BaseModel):
    operation_id: str
    status: OperationStatus
    received_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    retry_count: int
    last_error_message: Optional[str]

    class Config:
        from_attributes = True
