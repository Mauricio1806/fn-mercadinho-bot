"""Rotas WebSocket — stream de mensagens em tempo real."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import get_settings
from app.platform.ws_manager import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.websocket("/conversations/{conversation_id}")
async def ws_conversation(
    conversation_id: str,
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    WebSocket para receber novas mensagens de uma conversa em tempo real.

    Conexão: ws://host/ws/conversations/{id}?token={access_token}

    Mensagens recebidas (JSON):
        {"type": "new_message", "data": {"direction": "outbound", "content": "...", ...}}
        {"type": "ping"}  ← heartbeat a cada 30s
    """
    # Valida token antes de aceitar conexão
    if not _validate_token(token):
        await websocket.close(code=4001, reason="Token inválido ou expirado")
        return

    await ws_manager.connect(conversation_id, websocket)
    logger.info("WS aberto: conv=%s", conversation_id)

    try:
        while True:
            # Aguarda mensagem do cliente (usado para ping/pong e keepalive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WS fechado: conv=%s", conversation_id)
    finally:
        ws_manager.disconnect(conversation_id, websocket)


def _validate_token(token: str) -> bool:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload.get("sub") is not None
    except JWTError:
        return False
