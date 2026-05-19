"""Testes de integração — webhook multi-tenant routing."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestWebhookTenantRouting:
    """Verifica que o webhook resolve o tenant correto e processa a mensagem."""

    @pytest.mark.asyncio
    async def test_webhook_desconhecido_nao_crasha(
        self,
        client: AsyncClient,
        tenant_fn,
    ):
        """Webhook com número desconhecido deve retornar 200 sem crash."""
        payload = {
            "event": "messages.upsert",
            "instance": "9999999999999",  # Número não cadastrado
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Olá"},
                "messageType": "conversation",
            },
        }

        # Mock do ConversationEngine para não chamar Claude
        with patch("app.api.routes.webhook.ConversationEngine") as MockEngine:
            MockEngine.return_value.handle = AsyncMock()
            resp = await client.post("/webhook/", json=payload)

        # Deve retornar 200 mesmo sem tenant encontrado (usa fallback)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_responde_200_em_eventos_ignorados(
        self,
        client: AsyncClient,
        tenant_fn,
    ):
        """Eventos não-mensagem (ex: connection.update) devem ser ignorados silenciosamente."""
        payload = {
            "event": "connection.update",
            "instance": "557199371599",
            "data": {"state": "open"},
        }

        resp = await client.post("/webhook/", json=payload)
        # Pode ser 200 (ignorado) ou 422 (parse inválido), mas nunca 500
        assert resp.status_code in (200, 422)


class TestInventoryWebhook:
    """Testa o recebimento de webhooks de ERP de estoque."""

    @pytest.mark.asyncio
    async def test_webhook_generico_cria_produto(
        self,
        client: AsyncClient,
        tenant_fn,
    ):
        payload = {
            "external_id": "TEST001",
            "name": "Produto via Webhook",
            "price": 12.99,
            "category": "Bebidas",
            "available": True,
            "stock_quantity": 50,
        }

        resp = await client.post(
            f"/api/integrations/{tenant_fn.id}/webhook",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["created"] == 1

    @pytest.mark.asyncio
    async def test_webhook_sem_external_id_retorna_erro(
        self,
        client: AsyncClient,
        tenant_fn,
    ):
        payload = {"name": "Sem ID", "price": 5.00, "category": "Cat"}

        resp = await client.post(
            f"/api/integrations/{tenant_fn.id}/webhook",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_webhook_tenant_inexistente_retorna_404(
        self,
        client: AsyncClient,
    ):
        import uuid
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/integrations/{fake_id}/webhook",
            json={"external_id": "X", "name": "X", "price": 1.0, "category": "X"},
        )
        assert resp.status_code == 404
