"""Migration 003 — sistema multi-tenant.

Cria tabela tenants e adiciona tenant_id em todas as entidades.
Altera admin_users com role e tenant_id.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revisão
revision = "003"
down_revision = "002_add_pix_receipt_logs"
branch_labels = None
depends_on = None

# UUID fixo do tenant FN Mercadinho (tenant histórico)
FN_MERCADINHO_UUID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # ── 1. Cria tabela tenants ────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("whatsapp_number", sa.String(30), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_whatsapp_number", "tenants", ["whatsapp_number"])

    # ── 2. Insere o tenant FN Mercadinho (UUID fixo) ──────────────────────
    fn_config = {
        "nome": "FN Mercadinho",
        "endereco": "Conjunto Chácara do Cabula, 74 Box 09, Salvador - BA",
        "pix_chave": "60747738000149",
        "pix_tipo_chave": "cnpj",
        "pix_titular": "NN Mercadinho",
        "pix_banco": "SumUp",
        "horario": {
            "abertura": "07:00",
            "fechamento": "21:00",
            "domingo_abertura": "08:00",
            "domingo_fechamento": "12:30",
            "dias": "Segunda a sábado",
            "msg_fora_horario": "Estamos fechados agora! 😊",
        },
        "delivery": {
            "taxa_proxima": 3.00,
            "taxa_distante": 5.00,
            "raio_proxima_metros": 500,
            "pedido_minimo": 15.00,
            "tempo_estimado": "15-30 min",
        },
        "owners": ["+5571991356145", "+5571993266224"],
        "comissao_percentual": 5.0,
        "persona": {
            "tom": "informal",
            "usa_emojis": True,
            "girias_regionais": "baianas",
            "saudacao": "Olá! Bem-vindo ao FN Mercadinho 👋",
            "despedida": "Obrigado! Até a próxima 😊",
        },
        "branding": {
            "cor_primaria": "#2E7D32",
            "cor_secundaria": "#FFA000",
            "logo_url": None,
        },
        "integracao_estoque": {"ativo": False, "sistema": None},
    }

    op.execute(
        sa.text(
            """
            INSERT INTO tenants (id, slug, name, is_active, config)
            VALUES (:id, :slug, :name, true, :config::jsonb)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=FN_MERCADINHO_UUID,
            slug="fn-mercadinho",
            name="FN Mercadinho",
            config=__import__("json").dumps(fn_config),
        )
    )

    # ── 3. Adiciona tenant_id em customers ───────────────────────────────
    op.add_column(
        "customers",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,  # nullable para a migration, depois tornamos NOT NULL
        ),
    )
    op.execute(
        sa.text("UPDATE customers SET tenant_id = :tid WHERE tenant_id IS NULL").bindparams(
            tid=FN_MERCADINHO_UUID
        )
    )
    op.alter_column("customers", "tenant_id", nullable=False)
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])

    # Remove unique constraint antiga de phone (agora é por tenant)
    # Tenta remover se existir (pode variar conforme o banco)
    try:
        op.drop_constraint("customers_phone_key", "customers", type_="unique")
    except Exception:
        pass  # Não existe em todos os ambientes

    # ── 4. Adiciona tenant_id em product_categories ──────────────────────
    op.add_column(
        "product_categories",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE product_categories SET tenant_id = :tid WHERE tenant_id IS NULL"
        ).bindparams(tid=FN_MERCADINHO_UUID)
    )
    op.alter_column("product_categories", "tenant_id", nullable=False)
    op.create_index("ix_product_categories_tenant_id", "product_categories", ["tenant_id"])

    # ── 5. Adiciona tenant_id + campos ERP em products ───────────────────
    op.add_column(
        "products",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(
        sa.text("UPDATE products SET tenant_id = :tid WHERE tenant_id IS NULL").bindparams(
            tid=FN_MERCADINHO_UUID
        )
    )
    op.alter_column("products", "tenant_id", nullable=False)
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    op.add_column("products", sa.Column("external_id", sa.String(200), nullable=True))
    op.add_column("products", sa.Column("external_source", sa.String(50), nullable=True))
    op.add_column(
        "products",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_products_external_id", "products", ["external_id"])

    # ── 6. Adiciona tenant_id em orders ──────────────────────────────────
    op.add_column(
        "orders",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(
        sa.text("UPDATE orders SET tenant_id = :tid WHERE tenant_id IS NULL").bindparams(
            tid=FN_MERCADINHO_UUID
        )
    )
    op.alter_column("orders", "tenant_id", nullable=False)
    op.create_index("ix_orders_tenant_id", "orders", ["tenant_id"])

    # ── 7. Adiciona tenant_id em conversations ───────────────────────────
    op.add_column(
        "conversations",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE conversations SET tenant_id = :tid WHERE tenant_id IS NULL"
        ).bindparams(tid=FN_MERCADINHO_UUID)
    )
    op.alter_column("conversations", "tenant_id", nullable=False)
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])

    # ── 8. Altera admin_users: adiciona role + tenant_id ─────────────────
    op.add_column(
        "admin_users",
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="tenant_admin",
        ),
    )
    op.add_column(
        "admin_users",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Admins existentes viram admins do FN Mercadinho
    op.execute(
        sa.text(
            "UPDATE admin_users SET tenant_id = :tid WHERE is_superuser = false"
        ).bindparams(tid=FN_MERCADINHO_UUID)
    )
    # Superadmins mantêm tenant_id NULL
    op.create_index("ix_admin_users_tenant_id", "admin_users", ["tenant_id"])


def downgrade() -> None:
    # Remove índices e colunas na ordem inversa
    op.drop_index("ix_admin_users_tenant_id", table_name="admin_users")
    op.drop_column("admin_users", "tenant_id")
    op.drop_column("admin_users", "role")

    op.drop_index("ix_conversations_tenant_id", table_name="conversations")
    op.drop_column("conversations", "tenant_id")

    op.drop_index("ix_orders_tenant_id", table_name="orders")
    op.drop_column("orders", "tenant_id")

    op.drop_index("ix_products_external_id", table_name="products")
    op.drop_column("products", "last_synced_at")
    op.drop_column("products", "external_source")
    op.drop_column("products", "external_id")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_column("products", "tenant_id")

    op.drop_index("ix_product_categories_tenant_id", table_name="product_categories")
    op.drop_column("product_categories", "tenant_id")

    op.drop_index("ix_customers_tenant_id", table_name="customers")
    op.drop_column("customers", "tenant_id")

    op.drop_index("ix_tenants_whatsapp_number", table_name="tenants")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
