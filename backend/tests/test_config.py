"""Testes do config loader (business.yaml)."""

import pytest

from app.config import BusinessConfig, load_business_config


def make_config(overrides: dict | None = None) -> BusinessConfig:
    base = {
        "mercadinho": {"nome": "FN Mercadinho"},
        "horario": {
            "abertura": "07:00",
            "fechamento": "21:00",
            "dias": "Segunda a Domingo",
            "msg_fora_horario": "Fechado!",
        },
        "delivery": {
            "tipo": "condominio",
            "nome_condominio": "Residencial Teste",
            "blocos": ["A", "B", "C"],
            "taxa": 0,
            "pedido_minimo": 15.0,
            "tempo_estimado": "15-30 min",
        },
        "pix": {
            "tipo_chave": "cpf",
            "chave": "123.456.789-00",
            "titular": "Fulano Silva",
            "banco": "Nubank",
        },
        "catalogo": [
            {
                "categoria": "Bebidas",
                "produtos": [
                    {"nome": "Coca-Cola 2L", "preco": 10.00},
                    {"nome": "Água 500ml", "preco": 3.00},
                ],
            }
        ],
        "personalidade": {
            "saudacao": "Olá! 👋",
            "despedida": "Até logo!",
            "quando_nao_entende": "Hm?",
            "quando_sem_estoque": "Sem estoque.",
            "quando_fora_area": "Fora da área.",
            "girias_baianas": True,
            "tom": "amigável",
        },
        "notificacao": {
            "whatsapp_dono_1": "+5571999999999",
            "whatsapp_dono_2": "+5571888888888",
            "valor_alto": 100.0,
        },
    }
    if overrides:
        base.update(overrides)
    return BusinessConfig(base)


class TestBusinessConfig:
    def test_nome_mercadinho(self):
        config = make_config()
        assert config.nome == "FN Mercadinho"

    def test_horario(self):
        config = make_config()
        assert config.horario_abertura == "07:00"
        assert config.horario_fechamento == "21:00"
        assert config.horario_dias == "Segunda a Domingo"

    def test_delivery_blocos(self):
        config = make_config()
        assert config.delivery_blocos == ["A", "B", "C"]

    def test_delivery_blocos_exclui_todo(self):
        config = make_config({"delivery": {"blocos": ["TODO"], "tipo": "condominio"}})
        assert config.delivery_blocos == []

    def test_pix_configured(self):
        config = make_config()
        assert config.pix_configured is True

    def test_pix_nao_configured_quando_todo(self):
        config = BusinessConfig({"pix": {"chave": "TODO"}})
        assert config.pix_configured is False

    def test_catalogo_texto(self):
        config = make_config()
        texto = config.get_catalog_text()
        assert "Bebidas" in texto
        assert "Coca-Cola 2L" in texto
        assert "R$ 10.00" in texto

    def test_catalogo_exclui_todo(self):
        config = BusinessConfig(
            {
                "catalogo": [
                    {
                        "categoria": "TODO - Adicionar mais",
                        "produtos": [{"nome": "TODO", "preco": 0}],
                    }
                ]
            }
        )
        assert config.catalogo == []

    def test_valores_default_sem_yaml(self):
        config = BusinessConfig({})
        assert config.nome == "FN Mercadinho"
        assert config.horario_abertura == "07:00"
        assert config.saudacao == "Olá! Bem-vindo ao FN Mercadinho 👋"

    def test_pix_titular(self):
        config = make_config()
        assert config.pix_titular == "Fulano Silva"

    def test_whatsapp_donos(self):
        config = make_config()
        assert config.whatsapp_dono_1 == "+5571999999999"
        assert config.whatsapp_dono_2 == "+5571888888888"

    def test_valor_alto_default(self):
        config = BusinessConfig({})
        assert config.valor_alto == 100.0


class TestLoadBusinessConfig:
    def test_carrega_arquivo_inexistente_retorna_defaults(self, tmp_path):
        config = load_business_config(str(tmp_path / "nao_existe.yaml"))
        assert config.nome == "FN Mercadinho"

    def test_carrega_arquivo_valido(self, tmp_path):
        yaml_file = tmp_path / "business.yaml"
        yaml_file.write_text(
            "mercadinho:\n  nome: Padaria do João\n", encoding="utf-8"
        )
        config = load_business_config(str(yaml_file))
        assert config.nome == "Padaria do João"
