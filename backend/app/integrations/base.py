"""
ABC base para integrações de sincronização de estoque/catálogo.

Cada sistema (Bling, Tiny, CSV, webhook genérico) implementa esta interface.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProductData:
    """Dados normalizados de produto vindos de qualquer fonte externa."""

    name: str
    price: float
    category_name: str
    external_id: str
    external_source: str
    is_available: bool = True
    stock_quantity: int | None = None
    description: str | None = None


@dataclass
class SyncResult:
    """Resultado de uma operação de sincronização."""

    success: bool
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    synced_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_processed(self) -> int:
        return self.created + self.updated + self.skipped

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.success = False

    def __repr__(self) -> str:
        return (
            f"<SyncResult success={self.success} created={self.created} "
            f"updated={self.updated} errors={len(self.errors)}>"
        )


class InventorySync(ABC):
    """
    Interface base para integração com sistemas de estoque.

    Cada implementação deve suportar:
    - sync_all: sincronização completa do catálogo
    - sync_product: sincronização de um produto específico
    - handle_webhook: processamento de evento em tempo real
    - validate_credentials: verificação de credenciais antes de ativar
    """

    source_name: str = "unknown"

    @abstractmethod
    async def sync_all(self, tenant_id: uuid.UUID) -> SyncResult:
        """
        Sincroniza todo o catálogo do sistema externo para o banco local.
        Faz upsert baseado em external_id.
        """
        ...

    @abstractmethod
    async def sync_product(self, tenant_id: uuid.UUID, external_id: str) -> ProductData | None:
        """
        Sincroniza um único produto pelo ID externo.
        Retorna ProductData atualizado ou None se não encontrado.
        """
        ...

    @abstractmethod
    async def handle_webhook(
        self, tenant_id: uuid.UUID, payload: dict[str, Any]
    ) -> SyncResult:
        """
        Processa evento de webhook recebido do sistema externo.
        Atualiza preço/estoque em tempo real.
        """
        ...

    @abstractmethod
    async def validate_credentials(self, config: dict[str, Any]) -> bool:
        """
        Verifica se as credenciais fornecidas são válidas.
        Deve fazer uma chamada real para a API do sistema.
        """
        ...
