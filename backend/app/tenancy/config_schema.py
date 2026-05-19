"""
Esquema Pydantic para validar o campo config JSONB de cada tenant.

O campo config é armazenado como JSONB no PostgreSQL e deve obedecer
exatamente esta estrutura. Campos opcionais têm defaults seguros.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class HorarioConfig(BaseModel):
    """Horário de funcionamento do negócio."""

    abertura: str = "07:00"
    fechamento: str = "21:00"
    domingo_abertura: str | None = None
    domingo_fechamento: str | None = None
    dias: str = "Segunda a sábado"
    msg_fora_horario: str = "Estamos fechados agora! Voltamos em breve 😊"


class DeliveryConfig(BaseModel):
    """Configuração de delivery do tenant."""

    taxa_proxima: float = 3.00
    taxa_distante: float = 5.00
    raio_proxima_metros: int = 500
    pedido_minimo: float = 0.00
    tempo_estimado: str = "15-30 min"
    horario_abertura: str = "08:00"
    horario_fechamento: str = "20:00"
    dias_semana: str = "Segunda a sexta"
    msg_fora_horario_delivery: str = "Delivery disponível de segunda a sexta 😊"
    blocos: list[str] = Field(default_factory=list)
    tipo: str = "distancia"  # distancia | condominio | fixo


class PersonaConfig(BaseModel):
    """Personalidade e tom do bot para este tenant."""

    tom: str = "informal"
    usa_emojis: bool = True
    girias_regionais: str | None = None  # ex: "baianas", "cariocas"
    saudacao: str = "Olá! Bem-vindo! 👋"
    despedida: str = "Obrigado! Até a próxima 😊"
    quando_nao_entende: str = "Desculpa, não entendi 😅 Pode repetir?"
    quando_sem_estoque: str = "Poxa, tá em falta 😕 Posso sugerir outra coisa?"
    quando_fora_area: str = "Não atendemos nessa área, mas pode vir buscar! 😊"
    tratamento: str = "você"


class BrandingConfig(BaseModel):
    """Identidade visual do tenant no dashboard."""

    cor_primaria: str = "#2E7D32"
    cor_secundaria: str = "#FFA000"
    logo_url: str | None = None


class IntegracaoEstoqueConfig(BaseModel):
    """Configuração de integração com sistema de estoque externo."""

    ativo: bool = False
    sistema: str | None = None        # bling | tiny | webhook | csv
    api_key: str | None = None
    webhook_url: str | None = None
    sync_intervalo_minutos: int = 60
    client_id: str | None = None      # para OAuth2 (Bling)
    client_secret: str | None = None  # para OAuth2 (Bling)

    @model_validator(mode="after")
    def validate_sistema_when_active(self) -> "IntegracaoEstoqueConfig":
        if self.ativo and not self.sistema:
            raise ValueError(
                "integracao_estoque.sistema é obrigatório quando ativo=true. "
                "Valores aceitos: bling, tiny, webhook, csv"
            )
        return self


class TenantConfig(BaseModel):
    """
    Schema completo do campo config JSONB de um tenant.

    Usado em todo lugar que lê configuração do tenant.
    Valores opcionais têm defaults seguros para que um tenant
    com config mínimo funcione sem erros.
    """

    # Identificação do negócio
    nome: str
    endereco: str | None = None
    instagram: str | None = None
    telefone: str | None = None

    # Dados Pix — obrigatórios para receber pagamentos
    pix_chave: str = "TODO"
    pix_tipo_chave: str = "cnpj"   # cpf | cnpj | email | telefone | aleatoria
    pix_titular: str = "TODO"
    pix_banco: str = "TODO"

    # Horário de funcionamento
    horario: HorarioConfig = Field(default_factory=HorarioConfig)

    # Delivery
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)

    # Números dos donos para notificações (com DDI, ex: "+5571991356145")
    owners: list[str] = Field(default_factory=list)

    # Comissão da plataforma sobre vendas confirmadas
    comissao_percentual: float = 5.0

    # Personalidade do bot
    persona: PersonaConfig = Field(default_factory=PersonaConfig)

    # Identidade visual no dashboard
    branding: BrandingConfig = Field(default_factory=BrandingConfig)

    # Integração com sistema de estoque
    integracao_estoque: IntegracaoEstoqueConfig = Field(
        default_factory=IntegracaoEstoqueConfig
    )

    # Valor de pedido "alto" para alerta especial
    valor_alto_alerta: float = 100.0

    @field_validator("pix_tipo_chave")
    @classmethod
    def valid_pix_tipo(cls, v: str) -> str:
        allowed = {"cpf", "cnpj", "email", "telefone", "aleatoria"}
        if v not in allowed:
            raise ValueError(f"pix_tipo_chave deve ser um de: {allowed}")
        return v

    @property
    def pix_configured(self) -> bool:
        return self.pix_chave not in ("TODO", "", None)

    @property
    def owner_phones(self) -> list[str]:
        """Lista de telefones dos donos sem '+'."""
        return [p.lstrip("+") for p in self.owners]

    model_config = {"extra": "ignore"}
