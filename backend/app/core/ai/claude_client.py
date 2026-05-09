"""Wrapper assíncrono do SDK Anthropic."""
from __future__ import annotations
import logging
import anthropic
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024


class ClaudeClient:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.anthropic_api_key
        self._client = anthropic.AsyncAnthropic(api_key=key)

    async def chat(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        user_message: str,
        max_tokens: int = MAX_TOKENS,
        product_search_fn=None,
    ) -> tuple[str, int]:
        messages = [*history, {"role": "user", "content": user_message}]
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=messages,
                timeout=25.0,
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            return text, tokens
        except anthropic.RateLimitError:
            return "Desculpa, estou sobrecarregado agora 😅 Tenta de novo em instantes!", 0
        except anthropic.APIConnectionError:
            return "Tô com problema de conexão agora 😔 Tenta de novo!", 0
        except Exception as e:
            logger.exception(f"Erro no Claude: {e}")
            return "Opa, tive um probleminha aqui 🙈 Pode repetir?", 0

    async def chat_with_image(
        self,
        system_prompt: str,
        image_data: str,
        image_media_type: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> tuple[str, int]:
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": image_media_type, "data": image_data}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                timeout=30.0,
            )
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens
        except Exception as e:
            logger.exception(f"Erro chat_with_image: {e}")
            return "", 0

    async def chat_with_document(
        self,
        system_prompt: str,
        document_data: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> tuple[str, int]:
        try:
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": document_data}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                timeout=30.0,
            )
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens
        except Exception as e:
            logger.exception(f"Erro chat_with_document: {e}")
            return "", 0


def get_claude_client() -> ClaudeClient:
    return ClaudeClient()
