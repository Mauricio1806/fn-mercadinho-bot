"""
Model de credencial de integração — 1 credencial por tenant+provider.

O plaintext NUNCA fica no banco. Apenas ciphertext (Fernet).
A relação é via tenant_id + provider (bling, tiny, webhook, mercadopago, etc).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class IntegrationProvider(str, enum.Enum):
    BLING = "bling"
    TINY = "tiny"
    WEBHOOK = "webhook"
    MERCADOPAGO = "mercadopago"
    OTHER = "other"


class CredentialType(str, enum.Enum):
    API_KEY = "api_key"              # secret único (Tiny v2)
    OAUTH2 = "oauth2"                 # access + refresh (Bling v3)
    HMAC_SECRET = "hmac_secret"       # webhook signing
    BASIC_AUTH = "basic_auth"         # usuário/senha


class IntegrationCredential(UUIDMixin, TimestampMixin, Base):
    """
    Credencial criptografada por tenant+provider.
    Índice único garante 1 credencial ativa por (tenant, provider).
    """

    __tablename__ = "integration_credentials"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_credential_tenant_provider"),
    )

    tenant_id: Mapped[str] = mapped_column(
        UUIDType(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider), nullable=False
    )
    credential_type: Mapped[CredentialType] = mapped_column(
        Enum(CredentialType), nullable=False, default=CredentialType.API_KEY
    )

    # Ciphertext puro (Fernet). NUNCA logar, nunca serializar direto na resposta.
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)

    # Só pra OAuth: refresh token separado
    encrypted_refresh: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Últimos 4 chars do secret original — pra exibição no painel sem decifrar
    secret_hint: Mapped[str] = mapped_column(String(20), nullable=False, default="")

    # Versão da master key usada (pra rotação de key sem downtime)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Metadados úteis
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Configuração extra do provedor (client_id do Bling, URL do webhook, etc)
    # Non-secret data only — NUNCA colocar tokens aqui.
    provider_config: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<IntegrationCredential tenant={self.tenant_id} "
            f"provider={self.provider.value} hint={self.secret_hint}>"
        )
