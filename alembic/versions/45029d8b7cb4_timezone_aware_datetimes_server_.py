"""timezone aware datetimes + server defaults for operations

Revision ID: 45029d8b7cb4
Revises: 7e302985748f
Create Date: 2026-11-03 13:26:53.654371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '45029d8b7cb4'
down_revision: Union[str, Sequence[str], None] = '7e302985748f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ✅ 1. server_default для retry_count / max_retries
    op.alter_column(
        'integration_operations', 'retry_count',
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
    )
    op.alter_column(
        'integration_operations', 'max_retries',
        existing_type=sa.Integer(),
        server_default=sa.text("3"),
    )

    # ✅ 2. Обновить существующие NULL → дефолты
    # (server_default применяется только к новым INSERT)
    op.execute(
        "UPDATE integration_operations SET retry_count=0 WHERE retry_count IS NULL"
    )
    op.execute(
        "UPDATE integration_operations SET max_retries=3 WHERE max_retries IS NULL"
    )

    # ✅ 3. DateTime → timestamptz (автогенерация Alembic)
    op.alter_column('integration_operations', 'received_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('integration_operations', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('integration_operations', 'completed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('status_history', 'changed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('validation_errors', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""

    # ✅ 1. Откат timestamptz → timestamp
    op.alter_column('validation_errors', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('status_history', 'changed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('integration_operations', 'completed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('integration_operations', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('integration_operations', 'received_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)

    # ✅ 2. Откат server_default
    op.alter_column(
        'integration_operations', 'max_retries',
        existing_type=sa.Integer(),
        server_default=None,
    )
    op.alter_column(
        'integration_operations', 'retry_count',
        existing_type=sa.Integer(),
        server_default=None,
    )