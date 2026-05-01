"""Adiciona campos de confirmação de pagamento e comissão.

Revision ID: 001_payment_confirmation
Revises:
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_payment_confirmation"
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Novos campos na tabela orders
    op.add_column("orders", sa.Column("pix_confirmed", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("orders", sa.Column("commission_amount", sa.Numeric(10, 2), nullable=True))

    # Novo valor no enum order_status
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'payment_confirmed'")

    # Novo valor no enum conversationstate
    op.execute("ALTER TYPE conversationstate ADD VALUE IF NOT EXISTS 'payment_receipt'")


def downgrade() -> None:
    op.drop_column("orders", "commission_amount")
    op.drop_column("orders", "pix_confirmed")
    # Nota: PostgreSQL não permite remover valores de enum sem recriar o tipo
