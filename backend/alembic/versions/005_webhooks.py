"""005 — sistema de webhooks."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("webhook_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("secret_encrypted", sa.Text, nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("allowed_ips", postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column("max_per_minute", sa.Integer, nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_endpoints_tenant", "webhook_endpoints", ["tenant_id"])
    op.create_index("ix_webhook_endpoints_slug", "webhook_endpoints", ["tenant_id", "slug"])
    op.create_table("webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("webhook_endpoints.id"), nullable=True),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("request_headers", postgresql.JSONB, nullable=True),
        sa.Column("request_body", sa.Text, nullable=True),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("source_ip", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deliveries_tenant", "webhook_deliveries", ["tenant_id"])
    op.create_index("ix_deliveries_status", "webhook_deliveries", ["status"])
    op.create_table("webhook_idempotency",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_idempotency_tenant", "webhook_idempotency", ["tenant_id"])

def downgrade() -> None:
    op.drop_table("webhook_idempotency")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_endpoints")
