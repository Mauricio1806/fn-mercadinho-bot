"""Wrapper assíncrono do SDK Anthropic com prompt caching."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL = "claude-haiku-4-5-20251001"  # 20x mais barato que Sonnet
MAX_TOKENS = 1024


class ClaudeClient:
    """
    Cliente para o Claude com suporte a:
    - Histórico de conversa (multi-turn)
    - Prompt caching no system prompt (reduz custo em ~90%)
    - Timeout e retry básicos
    """

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.anthropic_api_key
        self._client = anthropic.AsyncAnthropic(api_key=key)

    async def chat(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        user_message: str,
        max_tokens: int = MAX_TOKENS,
    ) -> tuple[str, int]:
        """
        Envia mensagem para Claude com histórico.

        Args:
            system_prompt: Prompt de sistema (com cache).
            history: Lista de dicts {"role": "user"/"assistant", "content": "..."}.
            user_message: Mensagem atual do usuário.
            max_tokens: Limite de tokens na resposta.

        Returns:
            Tuple (resposta: str, tokens_usados: int).
        """
        messages = [*history, {"role": "user", "content": user_message}]

        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        # Cache o system prompt — economiza tokens em conversas longas
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )

            text = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens

            logger.debug(
                "Claude respondeu: %d tokens (input=%d output=%d cache_hit=%s)",
                tokens,
                response.usage.input_tokens,
                response.usage.output_tokens,
                getattr(response.usage, "cache_read_input_tokens", 0),
            )

            return text, tokens

        except anthropic.RateLimitError:
            logger.warning("Rate limit atingido no Claude. Usando fallback.")
            return "Desculpa, estou sobrecarregado agora 😅 Tenta de novo em instantes!", 0

        except anthropic.APIConnectionError:
            logger.error("Sem conexão com a API Anthropic.")
            return "Tô com problema de conexão agora 😔 Tenta de novo!", 0

        except Exception as e:
            logger.exception("Erro inesperado no Claude: %s", e)
            return "Opa, tive um probleminha aqui 🙈 Pode repetir?", 0

    async def chat_with_document(
        self,
        system_prompt: str,
        document_data: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> tuple[str, int]:
        """Analisa um documento PDF com Claude (Document API)."""
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": document_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            text = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens
        except Exception as e:
            logger.exception("Erro ao analisar PDF com Claude: %s", e)
            return "", 0

    async def chat_with_image(
        self,
        system_prompt: str,
        image_data: str,
        image_media_type: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> tuple[str, int]:
        """Analisa uma imagem com Claude Vision."""
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            text = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens
        except Exception as e:
            logger.exception("Erro ao analisar imagem com Claude: %s", e)
            return "", 0


# Singleton
_claude: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    global _claude
    if _claude is None:
        _claude = ClaudeClient()
    return _claude
