"""Adiciona tabela de log anti-fraude Pix.

Revision ID: 002_add_pix_receipt_logs
Revises: 001_payment_confirmation
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_add_pix_receipt_logs"
down_revision = "001_payment_confirmation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pix_receipt_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("receipt_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("pix_txid", sa.String(100), nullable=True),
        sa.Column("payer_name", sa.String(200), nullable=True),
        sa.Column("recipient_key", sa.String(100), nullable=True),
        sa.Column("payment_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flag_reason", sa.String(500), nullable=True),
    )
    op.create_index("ix_pix_receipt_logs_receipt_hash", "pix_receipt_logs", ["receipt_hash"])


def downgrade() -> None:
    op.drop_index("ix_pix_receipt_logs_receipt_hash", table_name="pix_receipt_logs")
    op.drop_table("pix_receipt_logs")
