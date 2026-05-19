"""
TenantContext — objeto rico que encapsula o tenant ORM e expõe
propriedades compatíveis com o BusinessConfig legado.

Substitui BusinessConfig em todo o código novo. O código legado
que ainda usa BusinessConfig continuará funcionando durante a migração.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from app.tenancy.config_schema import TenantConfig

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class TenantContext:
    """
    Contexto completo de um tenant.

    Construído a partir do ORM Tenant e expõe todas as propriedades
    necessárias para o ConversationEngine, prompt builder e notificações.
    """

    def __init__(self, tenant_id: uuid.UUID, slug: str, config: TenantConfig) -> None:
        self.tenant_id = tenant_id
        self.slug = slug
        self._config = config

    @classmethod
    def from_orm(cls, tenant: "Tenant") -> "TenantContext":
        """Constrói TenantContext a partir do model ORM."""
        raw_config = tenant.config or {}
        # Garante que 'nome' esteja no config usando o name do modelo como fallback
        if "nome" not in raw_config:
            raw_config = {"nome": tenant.name, **raw_config}
        config = TenantConfig(**raw_config)
        return cls(tenant_id=tenant.id, slug=tenant.slug, config=config)

    # ── Propriedades diretas do config ─────────────────────────────────────

    @property
    def nome(self) -> str:
        return self._config.nome

    @property
    def pix_chave(self) -> str:
        return self._config.pix_chave

    @property
    def pix_tipo_chave(self) -> str:
        return self._config.pix_tipo_chave

    @property
    def pix_titular(self) -> str:
        return self._config.pix_titular

    @property
    def pix_banco(self) -> str:
        return self._config.pix_banco

    @property
    def pix_configured(self) -> bool:
        return self._config.pix_configured

    @property
    def owner_phones(self) -> list[str]:
        return self._config.owner_phones

    @property
    def comissao_percentual(self) -> float:
        return self._config.comissao_percentual

    @property
    def valor_alto(self) -> float:
        return self._config.valor_alto_alerta

    # ── Horário ──────────────────────────────────────────────────────────

    @property
    def horario_abertura(self) -> str:
        return self._config.horario.abertura

    @property
    def horario_fechamento(self) -> str:
        return self._config.horario.fechamento

    @property
    def horario_dias(self) -> str:
        return self._config.horario.dias

    @property
    def horario_abertura_domingo(self) -> str | None:
        return self._config.horario.domingo_abertura

    @property
    def horario_fechamento_domingo(self) -> str | None:
        return self._config.horario.domingo_fechamento

    @property
    def msg_fora_horario(self) -> str:
        return self._config.horario.msg_fora_horario

    # ── Delivery ─────────────────────────────────────────────────────────

    @property
    def delivery_taxa_proxima(self) -> float:
        return self._config.delivery.taxa_proxima

    @property
    def delivery_taxa_distante(self) -> float:
        return self._config.delivery.taxa_distante

    @property
    def delivery_taxa(self) -> float:
        return self._config.delivery.taxa_proxima

    @property
    def delivery_raio_taxa_proxima(self) -> int:
        return self._config.delivery.raio_proxima_metros

    @property
    def delivery_pedido_minimo(self) -> float:
        return self._config.delivery.pedido_minimo

    @property
    def delivery_tempo_estimado(self) -> str:
        return self._config.delivery.tempo_estimado

    @property
    def delivery_horario_abertura(self) -> str:
        return self._config.delivery.horario_abertura

    @property
    def delivery_horario_fechamento(self) -> str:
        return self._config.delivery.horario_fechamento

    @property
    def delivery_dias_semana(self) -> str:
        return self._config.delivery.dias_semana

    @property
    def msg_fora_horario_delivery(self) -> str:
        return self._config.delivery.msg_fora_horario_delivery

    @property
    def delivery_blocos(self) -> list[str]:
        return self._config.delivery.blocos

    @property
    def delivery_tipo(self) -> str:
        return self._config.delivery.tipo

    # ── Personalidade / Persona ───────────────────────────────────────────

    @property
    def saudacao(self) -> str:
        return self._config.persona.saudacao

    @property
    def despedida(self) -> str:
        return self._config.persona.despedida

    @property
    def quando_nao_entende(self) -> str:
        return self._config.persona.quando_nao_entende

    @property
    def quando_sem_estoque(self) -> str:
        return self._config.persona.quando_sem_estoque

    @property
    def quando_fora_area(self) -> str:
        return self._config.persona.quando_fora_area

    @property
    def tom(self) -> str:
        return self._config.persona.tom

    @property
    def girias_baianas(self) -> bool:
        """Compat legado — verifica se gírias regionais são baianas."""
        return (self._config.persona.girias_regionais or "").lower() == "baianas"

    @property
    def tratamento(self) -> str:
        return self._config.persona.tratamento

    # ── Notificação compat legado ─────────────────────────────────────────

    @property
    def whatsapp_dono_1(self) -> str:
        phones = self._config.owner_phones
        return f"+{phones[0]}" if phones else "TODO"

    @property
    def whatsapp_dono_2(self) -> str:
        phones = self._config.owner_phones
        return f"+{phones[1]}" if len(phones) > 1 else "TODO"

    # ── Branding ─────────────────────────────────────────────────────────

    @property
    def cor_primaria(self) -> str:
        return self._config.branding.cor_primaria

    @property
    def cor_secundaria(self) -> str:
        return self._config.branding.cor_secundaria

    @property
    def logo_url(self) -> str | None:
        return self._config.branding.logo_url

    # ── Compat BusinessConfig (para código legado) ────────────────────────

    @property
    def _raw(self) -> dict[str, Any]:
        """Compat: retorna dict raw para código que acessa _raw diretamente."""
        return self._config.model_dump()

    def get_catalog_text(self) -> str:
        """
        Compat com BusinessConfig.get_catalog_text().
        No multi-tenant, o catálogo vem do banco (tabela products).
        Retorna string vazia — o prompt builder deve buscar do banco.
        """
        return ""

    def __repr__(self) -> str:
        return f"<TenantContext slug={self.slug} nome={self.nome}>"
