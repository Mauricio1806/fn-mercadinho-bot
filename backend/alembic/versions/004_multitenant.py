"""004 — add multi-tenant: tabela tenants + tenant_id em todas as tabelas + campos ERP."""
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

FN_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # ── 1. Tabela tenants ────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("whatsapp_number", sa.String(20), nullable=False, unique=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "ai_model",
            sa.String(50),
            nullable=False,
            server_default="claude-haiku-4-5-20251001",
        ),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tenants_whatsapp_number", "tenants", ["whatsapp_number"])

    # ── 2. FN Mercadinho como tenant inicial ─────────────────────────────────
    op.execute(f"""
        INSERT INTO tenants (id, slug, name, whatsapp_number, config)
        VALUES (
            '{FN_TENANT}',
            'fn-mercadinho',
            'FN Mercadinho',
            '557199371599',
            '{{"pix_chave": "60747738000149",
               "pix_tipo_chave": "cnpj",
               "pix_titular": "FN Mercadinho",
               "pix_banco": "SumUp",
               "comissao_percentual": 5.0,
               "owners": ["+5571991356145", "+5571993266224"],
               "horario": {{"abertura": "07:00", "fechamento": "21:00",
                            "domingo_abertura": "08:00", "domingo_fechamento": "12:30"}},
               "delivery": {{"taxa_proxima": 3.0, "taxa_distante": 5.0,
                              "raio_proxima": 500, "pedido_minimo": 15.0}}}}'
        )
        ON CONFLICT DO NOTHING;
    """)

    # ── 3. tenant_id nas tabelas principais ──────────────────────────────────
    tables = ["customers", "conversations", "products", "orders", "product_categories"]
    for tbl in tables:
        op.add_column(
            tbl,
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id"),
                nullable=True,
            ),
        )
        op.execute(f"UPDATE {tbl} SET tenant_id = '{FN_TENANT}' WHERE tenant_id IS NULL")
        op.alter_column(tbl, "tenant_id", nullable=False)
        op.create_index(f"ix_{tbl}_tenant_id", tbl, ["tenant_id"])

    # ── 4. admin_users: role + tenant_id ─────────────────────────────────────
    op.add_column(
        "admin_users",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "admin_users",
        sa.Column("role", sa.String(20), nullable=False, server_default="tenant_admin"),
    )
    op.execute(
        f"UPDATE admin_users SET tenant_id = '{FN_TENANT}' WHERE tenant_id IS NULL"
    )

    # ── 5. products: campos para integração ERP ──────────────────────────────
    op.add_column("products", sa.Column("external_id", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("external_source", sa.String(50), nullable=True))
    op.add_column("products", sa.Column("stock_quantity", sa.Integer, nullable=True))
    op.add_column(
        "products",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_products_tenant_external_id",
        "products",
        ["tenant_id", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_products_tenant_external_id", "products")
    for col in ["external_id", "external_source", "stock_quantity", "last_synced_at"]:
        op.drop_column("products", col)

    op.drop_column("admin_users", "role")
    op.drop_column("admin_users", "tenant_id")

    tables = ["customers", "conversations", "products", "orders", "product_categories"]
    for tbl in tables:
        op.drop_index(f"ix_{tbl}_tenant_id", tbl)
        op.drop_column(tbl, "tenant_id")

    op.drop_index("ix_tenants_whatsapp_number", "tenants")
    op.drop_table("tenants")
