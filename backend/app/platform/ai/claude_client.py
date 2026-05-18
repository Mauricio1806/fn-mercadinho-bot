"""Wrapper assíncrono do SDK Anthropic."""
from __future__ import annotations
import logging
import anthropic
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024


def build_tools(tenant_name: str = "do cliente") -> list:
    """Retorna a lista de tools com o nome do tenant injetado dinamicamente."""
    return [
        {
            "name": "buscar_produtos",
            "description": (
                f"Busca produtos disponíveis no catálogo {tenant_name} pelo nome ou termo. "
                "Use SEMPRE que o cliente mencionar qualquer produto que queira comprar. "
                "Exemplos: 'arroz', 'leite', 'frango', 'cerveja', 'detergente'. "
                "Faça uma busca separada para cada produto diferente mencionado."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome ou parte do nome do produto a buscar. Use termos simples: 'arroz', 'leite integral', 'frango congelado'."
                    }
                },
                "required": ["termo"]
            }
        }
    ]


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
        tenant_name: str = "do cliente",
    ) -> tuple[str, int]:
        messages = [*history, {"role": "user", "content": user_message}]
        total_tokens = 0

        try:
            # Loop de tool use — Haiku pode chamar buscar_produtos várias vezes
            while True:
                response = await self._client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=[{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }],
                    messages=messages,
                    tools=build_tools(tenant_name),
                    timeout=30.0,
                )
                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                # Se parou por tool_use, executa a busca e continua
                if response.stop_reason == "tool_use":
                    # Adiciona resposta do assistente com a tool call ao histórico
                    messages.append({"role": "assistant", "content": response.content})

                    # Processa cada tool call
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use" and block.name == "buscar_produtos":
                            termo = block.input.get("termo", "")
                            logger.info("Tool use: buscar_produtos('%s')", termo)

                            if product_search_fn:
                                resultado = await product_search_fn(termo)
                            else:
                                resultado = f"Busca não disponível para '{termo}'."

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": resultado,
                            })

                    # Adiciona resultados e continua o loop
                    messages.append({"role": "user", "content": tool_results})
                    continue

                # stop_reason == "end_turn" — extrai texto final e sai
                text = "".join(
                    b.text for b in response.content
                    if hasattr(b, "text") and b.type == "text"
                )
                return text, total_tokens

        except anthropic.RateLimitError:
            logger.warning("Rate limit Anthropic atingido")
            return "Desculpa, estou sobrecarregado agora 😅 Tenta de novo em instantes!", 0
        except anthropic.APIConnectionError:
            logger.warning("Falha de conexão com Anthropic")
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
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_media_type,
                                "data": image_data
                            }
                        },
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
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": document_data
                            }
                        },
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
