"""Migration 004 — tabela recoverable_sales para cart recovery multi-tenant."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recoverable_sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("customer_phone", sa.String(30), nullable=False),
        sa.Column("product_name", sa.String(300), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("checkout_url", sa.String(2048), nullable=True),
        sa.Column("pix_code", sa.String(1000), nullable=True),
        sa.Column("coupon", sa.String(100), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attribution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "contacted", "recovered", "expired", "lost",
                name="recoverysalestatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "funnel_stage",
            sa.Enum("pix_pendente", "abandono", name="recoveryfunnelstage"),
            nullable=False,
        ),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id", "external_id", name="uq_recoverable_sale_tenant_external"
        ),
    )
    op.create_index("ix_recoverable_sales_tenant_id", "recoverable_sales", ["tenant_id"])
    op.create_index("ix_recoverable_sales_external_id", "recoverable_sales", ["external_id"])
    op.create_index("ix_recoverable_sales_status", "recoverable_sales", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recoverable_sales_status", table_name="recoverable_sales")
    op.drop_index("ix_recoverable_sales_external_id", table_name="recoverable_sales")
    op.drop_index("ix_recoverable_sales_tenant_id", table_name="recoverable_sales")
    op.drop_table("recoverable_sales")
    op.execute("DROP TYPE IF EXISTS recoverysalestatus")
    op.execute("DROP TYPE IF EXISTS recoveryfunnelstage")
