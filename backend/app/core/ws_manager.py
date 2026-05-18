"""Gerenciador de conexões WebSocket em memória."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Mantém um registro de conexões WebSocket ativas por conversa.
    Thread-safe para deploy single-worker (uvicorn --workers 1).
    Para multi-worker, substituir pelo Redis pub/sub.
    """

    def __init__(self) -> None:
        # conversation_id → set de WebSockets conectados
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, conversation_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[conversation_id].add(ws)
        logger.debug("WS conectado: conv=%s total=%d", conversation_id, len(self._connections[conversation_id]))

    def disconnect(self, conversation_id: str, ws: WebSocket) -> None:
        self._connections[conversation_id].discard(ws)
        if not self._connections[conversation_id]:
            del self._connections[conversation_id]
        logger.debug("WS desconectado: conv=%s", conversation_id)

    async def broadcast(self, conversation_id: str, payload: dict) -> None:
        """Envia payload JSON para todos os clientes conectados nessa conversa."""
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(conversation_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(conversation_id, ws)

    async def broadcast_conversation_update(
        self,
        conversation_id: str,
        message_content: str,
        direction: str,
        is_ai_generated: bool,
        tokens_used: int | None = None,
    ) -> None:
        """Atalho para transmitir uma nova mensagem no formato padrão do frontend."""
        await self.broadcast(
            conversation_id,
            {
                "type": "new_message",
                "data": {
                    "direction": direction,
                    "content": message_content,
                    "is_ai_generated": is_ai_generated,
                    "tokens_used": tokens_used,
                },
            },
        )


# Singleton global
ws_manager = WebSocketManager()
