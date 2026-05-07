"""fix conversation status to varchar

Revision ID: 002_fix_status
Revises: 001
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = '002_fix_status'
down_revision = '001_payment_confirmation'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE conversations ALTER COLUMN status TYPE VARCHAR(50) USING status::text")

def downgrade():
    pass
