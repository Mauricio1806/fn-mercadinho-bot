"""Configuração central: carrega .env + business.yaml."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do servidor, lidas de variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Banco de dados
    database_url: str = "postgresql+asyncpg://fn_user:changeme@localhost:5432/fn_mercadinho"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = "TODO"

    # Evolution API
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = "evo_key_change_me"
    whatsapp_instance: str = "fn-mercadinho"

    # JWT
    jwt_secret: str = "change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Admin inicial
    admin_email: str = "admin@fn-mercadinho.com"
    admin_password: str = "TroqueEstaSenh@123"

    # App
    env: str = "development"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000"

    # Caminho para o business.yaml
    business_config_path: str = "../config/business.yaml"

    # API key de serviço para integrações externas (n8n, automações)
    service_api_key: str = "service_key_change_me"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_test(self) -> bool:
        return self.env == "test"


class BusinessConfig:
    """Configuração do negócio lida do business.yaml."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._raw = config

    # ── Mercadinho ──────────────────────────────────────────────
    @property
    def nome(self) -> str:
        return self._raw.get("mercadinho", {}).get("nome", "Estabelecimento")

    @property
    def endereco(self) -> str:
        return self._raw.get("mercadinho", {}).get(
            "endereco", "Conjunto Chácara do Cabula, 74 Box 09, Salvador - BA"
        )

    # ── Horário ──────────────────────────────────────────────────
    @property
    def horario_abertura(self) -> str:
        return self._raw.get("horario", {}).get("abertura", "07:00")

    @property
    def horario_fechamento(self) -> str:
        return self._raw.get("horario", {}).get("fechamento", "21:00")

    @property
    def horario_dias(self) -> str:
        return self._raw.get("horario", {}).get("dias", "Segunda a Domingo")

    @property
    def msg_fora_horario(self) -> str:
        return self._raw.get("horario", {}).get(
            "msg_fora_horario", "Estamos fechados agora! Voltamos amanhã às 7h 😊"
        )

    # ── Horário domingo ──────────────────────────────────────────
    @property
    def horario_abertura_domingo(self) -> str | None:
        return self._raw.get("horario", {}).get("domingo_abertura")

    @property
    def horario_fechamento_domingo(self) -> str | None:
        return self._raw.get("horario", {}).get("domingo_fechamento")

    # ── Delivery ─────────────────────────────────────────────────
    @property
    def delivery_tipo(self) -> str:
        return self._raw.get("delivery", {}).get("tipo", "condominio")

    @property
    def delivery_blocos(self) -> list[str]:
        blocos = self._raw.get("delivery", {}).get("blocos", ["TODO"])
        return [b for b in blocos if b != "TODO"]

    @property
    def delivery_taxa_proxima(self) -> float:
        """Taxa para distância até raio_taxa_proxima metros."""
        return float(self._raw.get("delivery", {}).get("taxa_proxima", 3.0))

    @property
    def delivery_taxa_distante(self) -> float:
        """Taxa para distância acima de raio_taxa_proxima metros."""
        return float(self._raw.get("delivery", {}).get("taxa_distante", 5.0))

    @property
    def delivery_raio_taxa_proxima(self) -> int:
        """Raio em metros que define qual taxa aplicar."""
        return int(self._raw.get("delivery", {}).get("raio_taxa_proxima", 500))

    @property
    def delivery_taxa(self) -> float:
        """Compat: retorna taxa padrão (proxima)."""
        return self.delivery_taxa_proxima

    @property
    def delivery_pedido_minimo(self) -> float:
        return float(self._raw.get("delivery", {}).get("pedido_minimo", 15.0))

    @property
    def delivery_tempo_estimado(self) -> str:
        return self._raw.get("delivery", {}).get("tempo_estimado", "15-30 min")

    @property
    def delivery_horario_abertura(self) -> str:
        return self._raw.get("delivery", {}).get("horario_abertura", "08:00")

    @property
    def delivery_horario_fechamento(self) -> str:
        return self._raw.get("delivery", {}).get("horario_fechamento", "20:00")

    @property
    def delivery_dias_semana(self) -> str:
        return self._raw.get("delivery", {}).get("dias_semana", "Segunda a sexta")

    @property
    def msg_fora_horario_delivery(self) -> str:
        return self._raw.get("delivery", {}).get(
            "msg_fora_horario_delivery",
            "Delivery disponível de segunda a sexta, das 8h às 20h 😊",
        )

    # ── Pix ──────────────────────────────────────────────────────
    @property
    def pix_chave(self) -> str:
        return self._raw.get("pix", {}).get("chave", "TODO")

    @property
    def pix_tipo_chave(self) -> str:
        return self._raw.get("pix", {}).get("tipo_chave", "TODO")

    @property
    def pix_titular(self) -> str:
        return self._raw.get("pix", {}).get("titular", "TODO")

    @property
    def pix_banco(self) -> str:
        return self._raw.get("pix", {}).get("banco", "TODO")

    @property
    def pix_configured(self) -> bool:
        return self.pix_chave != "TODO"

    # ── Catálogo ─────────────────────────────────────────────────
    @property
    def catalogo(self) -> list[dict[str, Any]]:
        raw = self._raw.get("catalogo", [])
        return [c for c in raw if c.get("categoria") not in ("TODO - Adicionar mais", None)]

    def get_catalog_text(self) -> str:
        """Retorna catálogo para o system prompt — categorias + preços se disponíveis."""
        lines: list[str] = []
        for cat in self.catalogo:
            descricao = cat.get("descricao", "")
            header = f"\n{cat['categoria']}:"
            if descricao:
                header += f" {descricao}"
            lines.append(header)
            for p in cat.get("produtos", []):
                if p.get("nome") not in ("TODO", None):
                    lines.append(f"  - {p['nome']}: R$ {p.get('preco', 0):.2f}")
        return "\n".join(lines)

    # ── Personalidade ────────────────────────────────────────────
    @property
    def saudacao(self) -> str:
        return self._raw.get("personalidade", {}).get(
            "saudacao", "Olá! Bem-vindo 👋"
        )

    @property
    def despedida(self) -> str:
        return self._raw.get("personalidade", {}).get("despedida", "Obrigado! Até a próxima 😊")

    @property
    def quando_nao_entende(self) -> str:
        return self._raw.get("personalidade", {}).get(
            "quando_nao_entende", "Desculpa, não entendi 😅 Pode repetir?"
        )

    @property
    def quando_sem_estoque(self) -> str:
        return self._raw.get("personalidade", {}).get(
            "quando_sem_estoque", "Poxa, tá em falta 😕 Posso sugerir outra coisa?"
        )

    @property
    def quando_fora_area(self) -> str:
        return self._raw.get("personalidade", {}).get(
            "quando_fora_area", "Só entregamos no condomínio, mas pode buscar! 😊"
        )

    @property
    def girias_baianas(self) -> bool:
        return self._raw.get("personalidade", {}).get("girias_baianas", True)

    @property
    def tratamento(self) -> str:
        return self._raw.get("personalidade", {}).get("tratamento", "você")

    @property
    def tom(self) -> str:
        return self._raw.get("personalidade", {}).get("tom", "amigável e informal")

    # ── Notificações ─────────────────────────────────────────────
    @property
    def whatsapp_dono_1(self) -> str:
        return self._raw.get("notificacao", {}).get("whatsapp_dono_1", "TODO")

    @property
    def whatsapp_dono_2(self) -> str:
        return self._raw.get("notificacao", {}).get("whatsapp_dono_2", "TODO")

    @property
    def valor_alto(self) -> float:
        return float(self._raw.get("notificacao", {}).get("valor_alto", 100.0))

    @property
    def comissao_percentual(self) -> float:
        return float(self._raw.get("notificacao", {}).get("comissao_percentual", 5.0))


def load_business_config(path: str | None = None) -> BusinessConfig:
    """Carrega o arquivo business.yaml e retorna um BusinessConfig."""
    config_path = path or os.getenv("BUSINESS_CONFIG_PATH", "../config/business.yaml")

    resolved = Path(config_path)
    if not resolved.is_absolute():
        # Tenta relativo ao diretório do projeto
        resolved = Path(__file__).parent.parent.parent / config_path

    if not resolved.exists():
        # Fallback: defaults vazios (sistema funciona com placeholders)
        return BusinessConfig({})

    with resolved.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return BusinessConfig(data or {})


@lru_cache
def get_settings() -> Settings:
    """Retorna instância única (singleton) das configurações de servidor."""
    return Settings()


@lru_cache
def get_business_config() -> BusinessConfig:
    """Retorna instância única (singleton) do config do negócio."""
    settings = get_settings()
    return load_business_config(settings.business_config_path)
