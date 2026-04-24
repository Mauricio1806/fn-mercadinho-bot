"""Testes do validador de comprovantes PIX."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import BusinessConfig
from app.core.payments.receipt_validator import (
    ReceiptValidation,
    _build_analysis_prompt,
    _parse_claude_response,
    validate_pix_receipt,
)


def make_business() -> BusinessConfig:
    return BusinessConfig(
        {
            "pix": {
                "chave": "12.345.678/0001-99",
                "tipo_chave": "cnpj",
                "titular": "FN Mercadinho",
                "banco": "SumUp",
            },
            "notificacao": {"whatsapp_dono_1": "TODO", "whatsapp_dono_2": "TODO", "valor_alto": 100},
        }
    )


class TestBuildAnalysisPrompt:
    def test_inclui_valor_esperado(self):
        business = make_business()
        prompt = _build_analysis_prompt(30.00, business)
        assert "30.00" in prompt

    def test_inclui_chave_pix(self):
        business = make_business()
        prompt = _build_analysis_prompt(30.00, business)
        assert "12.345.678/0001-99" in prompt

    def test_inclui_titular(self):
        business = make_business()
        prompt = _build_analysis_prompt(30.00, business)
        assert "FN Mercadinho" in prompt

    def test_pede_json_valido(self):
        business = make_business()
        prompt = _build_analysis_prompt(30.00, business)
        assert "JSON" in prompt


class TestParseClaudeResponse:
    def test_json_puro(self):
        raw = '{"is_comprovante_pix": true, "valor_detectado": 30.0, "valor_correto": true, "chave_destino_encontrada": true, "motivo": "OK"}'
        result = _parse_claude_response(raw)
        assert result["is_comprovante_pix"] is True
        assert result["valor_detectado"] == 30.0

    def test_json_com_markdown(self):
        raw = '```json\n{"is_comprovante_pix": false, "valor_detectado": null, "valor_correto": false, "chave_destino_encontrada": false, "motivo": "Não é comprovante"}\n```'
        result = _parse_claude_response(raw)
        assert result["is_comprovante_pix"] is False

    def test_json_invalido_lanca_excecao(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_claude_response("isso não é json")


class TestValidatePixReceipt:
    @pytest.fixture
    def mock_claude(self):
        claude = AsyncMock()
        return claude

    @pytest.fixture
    def valid_response(self) -> str:
        return json.dumps({
            "is_comprovante_pix": True,
            "valor_detectado": 50.0,
            "valor_correto": True,
            "chave_destino_encontrada": True,
            "motivo": "Comprovante válido",
        })

    @pytest.fixture
    def invalid_response(self) -> str:
        return json.dumps({
            "is_comprovante_pix": True,
            "valor_detectado": 20.0,
            "valor_correto": False,
            "chave_destino_encontrada": False,
            "motivo": "Valor incorreto",
        })

    async def test_imagem_valida_aprovada(self, mock_claude, valid_response):
        mock_claude.chat_with_image = AsyncMock(return_value=(valid_response, 100))
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=("base64data", "image/jpeg")):
            result = await validate_pix_receipt("http://fake/image.jpg", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is True
        assert result.amount_detected == 50.0
        assert result.pix_key_match is True

    async def test_pdf_valido_aprovado(self, mock_claude, valid_response):
        mock_claude.chat_with_document = AsyncMock(return_value=(valid_response, 100))
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=("base64data", "application/pdf")):
            result = await validate_pix_receipt("http://fake/comprovante.pdf", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is True
        mock_claude.chat_with_document.assert_called_once()

    async def test_valor_errado_rejeitado(self, mock_claude, invalid_response):
        mock_claude.chat_with_image = AsyncMock(return_value=(invalid_response, 100))
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=("base64data", "image/png")):
            result = await validate_pix_receipt("http://fake/image.png", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is False
        assert result.amount_detected == 20.0

    async def test_download_falha_retorna_invalido(self, mock_claude):
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=None):
            result = await validate_pix_receipt("http://fake/image.jpg", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is False
        assert "comprovante" in result.reason.lower() or "acessar" in result.reason.lower()

    async def test_tipo_nao_suportado_retorna_invalido(self, mock_claude):
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=("data", "video/mp4")):
            result = await validate_pix_receipt("http://fake/video.mp4", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is False
        assert "Formato" in result.reason or "formato" in result.reason

    async def test_claude_retorna_json_invalido(self, mock_claude):
        mock_claude.chat_with_image = AsyncMock(return_value=("não é json", 100))
        business = make_business()

        with patch("app.core.payments.receipt_validator._download", return_value=("data", "image/jpeg")):
            result = await validate_pix_receipt("http://fake/img.jpg", 50.0, claude=mock_claude, business=business)

        assert result.is_valid is False
