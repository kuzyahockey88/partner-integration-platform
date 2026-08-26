"""Create integration table

Revision ID: 17c385c3028f
Revises: 
Create Date: 2026-08-19 21:24:54.222667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '17c385c3028f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем таблицы с CASCADE через сырой SQL
    op.execute("DROP TABLE IF EXISTS validation_errors CASCADE")
    op.execute("DROP TABLE IF EXISTS status_history CASCADE")
    op.execute("DROP TABLE IF EXISTS integration_operations CASCADE")

    # Создаём таблицы (это сгенерировано Alembic)
    op.create_table(
        'integration_operations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_id', sa.String(length=64), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('external_request_id', sa.String(length=128), nullable=True),
        sa.Column('operation_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('RECEIVED', 'VALIDATION', 'VALIDATION_FAILED', 'PROCESSING', 'RETRYING', 'FAILED',
                                    'COMPLETED', name='operationstatus'), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_integration_operations_external_request_id', 'integration_operations', ['external_request_id'],
                    unique=False)
    op.create_index('ix_integration_operations_id', 'integration_operations', ['id'], unique=False)
    op.create_index('ix_integration_operations_operation_id', 'integration_operations', ['operation_id'], unique=True)
    op.create_index('ix_integration_operations_partner_id', 'integration_operations', ['partner_id'], unique=False)
    op.create_index('idx_operations_partner_status', 'integration_operations', ['partner_id', 'status'], unique=False)
    op.create_index('idx_operations_received_at', 'integration_operations', ['received_at'], unique=False)
    op.create_index('idx_operations_status_updated', 'integration_operations', ['status', 'updated_at'], unique=False)

    op.create_table(
        'status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_id', sa.Integer(), nullable=False),
        sa.Column('from_status',
                  sa.Enum('RECEIVED', 'VALIDATION', 'VALIDATION_FAILED', 'PROCESSING', 'RETRYING', 'FAILED',
                          'COMPLETED', name='operationstatus'), nullable=True),
        sa.Column('to_status',
                  sa.Enum('RECEIVED', 'VALIDATION', 'VALIDATION_FAILED', 'PROCESSING', 'RETRYING', 'FAILED',
                          'COMPLETED', name='operationstatus'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['integration_operations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_status_history_id', 'status_history', ['id'], unique=False)
    op.create_index('ix_status_history_operation_id', 'status_history', ['operation_id'], unique=False)
    op.create_index('idx_history_operation_changed', 'status_history', ['operation_id', 'changed_at'], unique=False)

    op.create_table(
        'validation_errors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=True),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['integration_operations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_errors_id', 'validation_errors', ['id'], unique=False)
    op.create_index('ix_validation_errors_operation_id', 'validation_errors', ['operation_id'], unique=False)
    op.create_index('idx_errors_operation_field', 'validation_errors', ['operation_id', 'field_name'], unique=False)


def downgrade() -> None:
    # Откат изменений
    op.execute("DROP TABLE IF EXISTS validation_errors CASCADE")
    op.execute("DROP TABLE IF EXISTS status_history CASCADE")
    op.execute("DROP TABLE IF EXISTS integration_operations CASCADE")
