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
        max_tokens: int = 1024,
        product_search_fn=None,
    ) -> tuple[str, int]:
        messages = [*history, {"role": "user", "content": user_message}]
        tools = [
            {
                "name": "buscar_produtos",
                "description": "Busca produtos no catalogo do mercadinho por termo. Use sempre que o cliente pedir um produto.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "termo": {"type": "string", "description": "Termo de busca, ex: salsicha, pao de forma, cerveja"}
                    },
                    "required": ["termo"]
                }
            }
        ] if product_search_fn else []

        total_tokens = 0
        max_iterations = 5
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                kwargs = dict(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                )
                if tools:
                    kwargs["tools"] = tools

                response = await self._client.messages.create(**kwargs, timeout=25.0)
                total_tokens += response.usage.input_tokens + response.usage.output_tokens
                logger.info(f"Claude stop_reason={response.stop_reason} tokens={total_tokens}")

                if response.stop_reason == "tool_use" and product_search_fn:
                    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
                    if tool_block and tool_block.name == "buscar_produtos":
                        termo = tool_block.input.get("termo", "")
                        logger.info(f"Buscando produtos: {termo}")
                        resultado = await product_search_fn(termo)
                        logger.info(f"Resultado: {(resultado or '')[:100]}")
                        messages = [
                            *messages,
                            {"role": "assistant", "content": response.content},
                            {"role": "user", "content": [
                                {"type": "tool_result", "tool_use_id": tool_block.id, "content": resultado or "Nenhum produto encontrado."}
                            ]}
                        ]
                        continue

                # Extrair texto da resposta
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text
                return text, total_tokens

            return "Deixa eu verificar e já te respondo!", total_tokens

        except anthropic.RateLimitError:
            logger.warning("Rate limit atingido.")
            return "Desculpa, estou sobrecarregado agora 😅 Tenta de novo em instantes!", 0
        except anthropic.APIConnectionError:
            logger.error("Sem conexão com Anthropic.")
            return "Tô com problema de conexão agora 😔 Tenta de novo!", 0
        except Exception as e:
            logger.exception(f"Erro no Claude: {e}")
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
