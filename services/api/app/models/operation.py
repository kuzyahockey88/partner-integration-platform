from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Enum,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from ..core.database import Base

class OperationStatus(str, enum.Enum):
    RECEIVED = "received"
    VALIDATION = "validation"
    VALIDATION_FAILED = "validation_failed"
    PROCESSING = "processing"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"

class IntegrationOperation(Base):
    __tablename__ = "integration_operations"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(String(64), unique=True, nullable=False, index=True)
    partner_id = Column(Integer, nullable=False, index=True)
    external_request_id = Column(String(128), nullable=True, index=True)
    operation_type = Column(String(50), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(Enum(OperationStatus), default=OperationStatus.RECEIVED)
    version = Column(Integer, default=1)

    received_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)

    payload = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)

    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error_message = Column(Text,nullable=True)

    status_history = relationship("StatusHistory", back_populates="operation",
    cascade="all, delete-orphan")
    validation_errors = relationship("ValidationError", back_populates="operation",
    cascade="all, delete-orphan")

    user = relationship("User", back_populates="operations")

    __table_args__ = (
        Index('idx_operations_partner_status', 'partner_id', 'status'),
        Index('idx_operations_status_updated', 'status', 'updated_at'),
        Index('idx_operations_received_at', 'received_at'),
    )

    def __repr__(self) -> str:
        return f"<IntegrationOperation {self.operation_id} [{self.status}]>"

class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("integration_operations.id"),
    nullable=False, index=True)

    from_status = Column(Enum(OperationStatus), nullable=True)
    to_status = Column(Enum(OperationStatus), nullable=False)
    reason = Column(Text, nullable=True)

    changed_at = Column(DateTime, nullable=False, default=func.now())

    operation = relationship("IntegrationOperation", back_populates="status_history")

    __table_args__ = (
        Index('idx_history_operation_changed', 'operation_id', 'changed_at'),
    )

    def __repr__(self) -> str:
        return f"<StatusHistory {self.id}: {self.from_status} -> {self.to_status}>"

class ValidationError(Base):
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("integration_operations.id"),
    nullable=False, index=True)

    row_number = Column(Integer, nullable=True)
    field_name = Column(String(100), nullable=True)
    error_code = Column(String(50), nullable=False)

    error_message = Column(Text, nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now())

    operation = relationship("IntegrationOperation", back_populates="validation_errors")

    __table_args__ = (
        Index('idx_errors_operation_field','operation_id', 'field_name'),
    )

    def __repr__(self) -> str:
        return f"<ValidationError {self.error_code}: {self.field_name}"

