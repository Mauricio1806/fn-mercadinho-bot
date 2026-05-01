"""Adiciona campos de confirmação de pagamento e comissão.
Revision ID: 001_payment_confirmation
Revises: 000_initial_schema
Create Date: 2026-04-19
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = "001_payment_confirmation"
down_revision = "000_initial_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('orders')]
    if 'pix_confirmed' not in cols:
        op.add_column("orders", sa.Column("pix_confirmed", sa.Boolean(), nullable=False, server_default="false"))
    if 'commission_amount' not in cols:
        op.add_column("orders", sa.Column("commission_amount", sa.Numeric(10, 2), nullable=True))
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN NULL; ELSE ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'payment_confirmed'; END IF; END $$;")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'conversationstate') THEN NULL; ELSE ALTER TYPE conversationstate ADD VALUE IF NOT EXISTS 'payment_receipt'; END IF; END $$;")

def downgrade() -> None:
    pass
