"""integration_credentials table (encrypted vault)

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Enum("bling", "tiny", "webhook", "mercadopago", "other", name="integrationprovider"), nullable=False),
        sa.Column("credential_type", sa.Enum("api_key", "oauth2", "hmac_secret", "basic_auth", name="credentialtype"), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh", sa.Text(), nullable=True),
        sa.Column("secret_hint", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_config", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_integration_credentials_tenant", "integration_credentials", ["tenant_id"])
    op.create_unique_constraint(
        "uq_credential_tenant_provider",
        "integration_credentials",
        ["tenant_id", "provider"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_credential_tenant_provider", "integration_credentials", type_="unique")
    op.drop_index("ix_integration_credentials_tenant", "integration_credentials")
    op.drop_table("integration_credentials")
    op.execute("DROP TYPE IF EXISTS integrationprovider")
    op.execute("DROP TYPE IF EXISTS credentialtype")
