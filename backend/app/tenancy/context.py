"""TenantContext — objeto imutável que circula por toda a requisição."""
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID

from app.tenancy.defaults import (
    DefaultCatalogProvider,
    DefaultDeliveryCalculator,
    DefaultOrderHooks,
)


@dataclass(frozen=True)
class TenantContext:
    id: UUID
    slug: str
    name: str
    whatsapp_number: str
    ai_model: str
    config: dict

    # Implementações — defaults se tenant não tiver override
    catalog: DefaultCatalogProvider = field(compare=False)
    delivery: DefaultDeliveryCalculator = field(compare=False)
    hooks: DefaultOrderHooks = field(compare=False)

    @classmethod
    def from_orm(cls, tenant) -> "TenantContext":
        """Monta TenantContext a partir do model ORM Tenant."""
        config = tenant.config or {}
        return cls(
            id=tenant.id,
            slug=tenant.slug,
            name=tenant.name,
            whatsapp_number=tenant.whatsapp_number,
            ai_model=tenant.ai_model,
            config=config,
            catalog=DefaultCatalogProvider(db_factory=None),
            delivery=DefaultDeliveryCalculator(config=config),
            hooks=DefaultOrderHooks(),
        )

    # ── Atalhos para config comum ─────────────────────────────────────────────

    @property
    def pix_chave(self) -> str:
        return self.config.get("pix_chave", "")

    @property
    def pix_tipo_chave(self) -> str:
        return self.config.get("pix_tipo_chave", "cnpj")

    @property
    def pix_titular(self) -> str:
        return self.config.get("pix_titular", self.name)

    @property
    def pix_banco(self) -> str:
        return self.config.get("pix_banco", "")

    @property
    def comissao_percentual(self) -> float:
        return float(self.config.get("comissao_percentual", 5.0))

    @property
    def owner_phones(self) -> list[str]:
        return self.config.get("owners", [])

    @property
    def horario_abertura(self) -> str:
        return self.config.get("horario", {}).get("abertura", "07:00")

    @property
    def horario_fechamento(self) -> str:
        return self.config.get("horario", {}).get("fechamento", "21:00")
