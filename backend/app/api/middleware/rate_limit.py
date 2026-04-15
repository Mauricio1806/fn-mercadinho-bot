"""Rate limiting por número de WhatsApp usando Redis."""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_MESSAGES_PER_MINUTE = 30
WINDOW_SECONDS = 60


async def is_rate_limited(phone: str) -> bool:
    """
    Verifica se o número excedeu o limite de mensagens por minuto.
    Usa Redis com janela deslizante simples (contador com TTL).
    Falha aberta (não bloqueia) se Redis estiver indisponível.

    Returns:
        True se o número deve ser bloqueado.
    """
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        key = f"rate:{phone}"

        async with redis:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, WINDOW_SECONDS)

            if count > MAX_MESSAGES_PER_MINUTE:
                logger.warning(
                    "Rate limit atingido para %s: %d msgs/min", phone, count
                )
                return True

        return False

    except Exception as e:
        # Falha aberta — se Redis não estiver disponível, permite atendimento
        logger.debug("Redis indisponível para rate limiting: %s", e)
        return False


async def get_message_count(phone: str) -> int:
    """Retorna a contagem atual de mensagens do número (para diagnóstico)."""
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        async with redis:
            count = await redis.get(f"rate:{phone}")
            return int(count) if count else 0
    except Exception:
        return 0
