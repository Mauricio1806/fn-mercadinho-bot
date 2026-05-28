"""004 — tabela recovery_attempts para carrinho abandonado."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("cart_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recovery_tenant", "recovery_attempts", ["tenant_id"])
    op.create_index("ix_recovery_conversation", "recovery_attempts", ["conversation_id"])
    op.create_index("ix_recovery_status", "recovery_attempts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recovery_status", "recovery_attempts")
    op.drop_index("ix_recovery_conversation", "recovery_attempts")
    op.drop_index("ix_recovery_tenant", "recovery_attempts")
    op.drop_table("recovery_attempts")
