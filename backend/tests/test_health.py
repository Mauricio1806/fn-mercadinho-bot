"""Testes do endpoint de health check e bootstrap da app."""

import pytest
from httpx import AsyncClient


async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "fn-mercadinho-api"


async def test_docs_disponivel(client: AsyncClient):
    resp = await client.get("/docs")
    assert resp.status_code == 200


async def test_404_desconhecido(client: AsyncClient):
    resp = await client.get("/rota-que-nao-existe")
    assert resp.status_code == 404
