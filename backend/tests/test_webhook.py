"""Testes do webhook da Evolution API."""

import pytest
from httpx import AsyncClient


class TestWebhook:
    async def test_webhook_aceita_payload_valido(self, client: AsyncClient):
        """Evento sem mensagem de usuário retorna 'ignored'."""
        resp = await client.post(
            "/webhook/",
            json={"event": "qr.updated", "data": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    async def test_webhook_rejeita_json_invalido(self, client: AsyncClient):
        resp = await client.post(
            "/webhook/",
            content=b"nao-e-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    async def test_webhook_aceita_sem_assinatura_em_dev(self, client: AsyncClient):
        """Em ambiente de desenvolvimento, webhook sem assinatura deve funcionar."""
        resp = await client.post(
            "/webhook/",
            json={"event": "connection.update", "data": {"state": "open"}},
        )
        assert resp.status_code == 200
