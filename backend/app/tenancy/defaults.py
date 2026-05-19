"""Valores default para campos opcionais do config de tenant."""

from __future__ import annotations

# UUID fixo do tenant FN Mercadinho (tenant #1)
FN_MERCADINHO_UUID = "00000000-0000-0000-0000-000000000001"

# Config mínimo válido para um tenant recém-criado (placeholder)
TENANT_CONFIG_DEFAULTS: dict = {
    "nome": "Novo Tenant",
    "pix_chave": "TODO",
    "pix_tipo_chave": "cnpj",
    "pix_titular": "TODO",
    "pix_banco": "TODO",
    "horario": {
        "abertura": "08:00",
        "fechamento": "18:00",
        "dias": "Segunda a sexta",
        "msg_fora_horario": "Estamos fechados agora! Voltamos em breve 😊",
    },
    "delivery": {
        "taxa_proxima": 5.00,
        "taxa_distante": 8.00,
        "raio_proxima_metros": 500,
        "pedido_minimo": 0.00,
        "tempo_estimado": "30-45 min",
    },
    "owners": [],
    "comissao_percentual": 5.0,
    "persona": {
        "tom": "informal",
        "usa_emojis": True,
        "saudacao": "Olá! Bem-vindo! 👋",
        "despedida": "Obrigado! Até a próxima 😊",
    },
    "branding": {
        "cor_primaria": "#1976D2",
        "cor_secundaria": "#FFC107",
        "logo_url": None,
    },
    "integracao_estoque": {
        "ativo": False,
        "sistema": None,
    },
}
