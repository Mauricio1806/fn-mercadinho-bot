"""Adiciona tabela de log anti-fraude Pix

Revision ID: 002_add_pix_receipt_logs
Revises: 001_payment_confirmation
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_pix_receipt_logs'
down_revision = '001_payment_confirmation'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
