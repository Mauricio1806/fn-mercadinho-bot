"""Valida comprovantes de PIX via Claude Vision / Document API.

Suporta:
- Imagem (PNG, JPG, WEBP) — enviada como imageMessage no WhatsApp
- PDF — enviado como documentMessage no WhatsApp

Quando db, order_id e customer_phone são fornecidos, executa verificação
anti-fraude completa via pix_fraud_guard (7 vetores de fraude).
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BusinessConfig, get_business_config
from app.core.ai.claude_client import ClaudeClient, get_claude_client
from app.models.pix_receipt_log import PixReceiptLog  # noqa: F401 — registra tabela no Base.metadata
from app.services.pix_fraud_guard import (
    FRAUD_RESPONSES,
    RECEIPT_EXTRACTION_PROMPT,
    FraudCheckResult,
    check_fraud,
)

logger = logging.getLogger(__name__)

_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
_PDF_TYPE = "application/pdf"


@dataclass
class ReceiptValidation:
    is_valid: bool
    amount_detected: float | None
    pix_key_match: bool
    reason: str
    fraud_result: Optional[FraudCheckResult] = field(default=None)


async def _download(url: str) -> tuple[str, str] | None:
    """Baixa arquivo da URL ou decodifica data URI. Retorna (base64_data, content_type)."""
    try:
        # Suporte a data URI: data:mimetype;base64,DADOS
        if url.startswith("data:"):
            header, data = url.split(",", 1)
            content_type = header.split(":")[1].split(";")[0]
            return data, content_type
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            data = base64.standard_b64encode(resp.content).decode("utf-8")
            return data, content_type
    except Exception as e:
        logger.error("Erro ao baixar comprovante de %s: %s", url[:80], e)
        return None


def _build_analysis_prompt(expected_amount: float, business: BusinessConfig) -> str:
    return f"""Analise este comprovante de pagamento PIX com atenção.

Dados esperados:
- Valor: R$ {expected_amount:.2f}
- Chave PIX destino: {business.pix_chave} ({business.pix_tipo_chave.upper()})
- Nome do destinatário: {business.pix_titular}
- Banco: {business.pix_banco}

Verifique:
1. É realmente um comprovante de transação PIX (não uma tela de agendamento, saldo ou outra coisa)?
2. O valor pago bate com R$ {expected_amount:.2f}?
3. O destinatário ou chave PIX corresponde ao mercadinho?

Responda SOMENTE com JSON válido (sem markdown, sem texto extra):
{{
  "is_comprovante_pix": true|false,
  "valor_detectado": <número decimal ou null>,
  "valor_correto": true|false,
  "chave_destino_encontrada": true|false,
  "motivo": "<explicação em 1 frase>"
}}

Seja rigoroso — validações incorretas causam prejuízo ao mercadinho."""


def _parse_claude_response(response_text: str) -> dict:
    """Extrai JSON da resposta do Claude, tolerando markdown."""
    clean = response_text.strip()
    clean = re.sub(r"^```(?:json)?", "", clean).rstrip("`").strip()
    return json.loads(clean)


async def validate_pix_receipt(
    image_url: str,
    expected_amount: float,
    claude: ClaudeClient | None = None,
    business: BusinessConfig | None = None,
    db: AsyncSession | None = None,
    order_id: str | None = None,
    customer_phone: str | None = None,
) -> ReceiptValidation:
    """
    Valida comprovante PIX enviado pelo cliente via WhatsApp.

    Passa db + order_id + customer_phone para ativar anti-fraude completo.
    Sem esses parâmetros usa o caminho legado (compatível com testes antigos).
    """
    if claude is None:
        claude = get_claude_client()
    if business is None:
        business = get_business_config()

    downloaded = await _download(image_url)
    if downloaded is None:
        return ReceiptValidation(
            is_valid=False,
            amount_detected=None,
            pix_key_match=False,
            reason="Não consegui acessar o comprovante. Tente enviar de novo.",
        )

    file_data, content_type = downloaded
    use_fraud_check = db is not None and order_id is not None and customer_phone is not None
    prompt = RECEIPT_EXTRACTION_PROMPT if use_fraud_check else _build_analysis_prompt(expected_amount, business)
    system = "Você analisa comprovantes PIX. Responda apenas com JSON válido."

    try:
        if content_type in _IMAGE_TYPES or content_type.startswith("image/"):
            response_text, _ = await claude.chat_with_image(
                system_prompt=system,
                image_data=file_data,
                image_media_type=content_type,
                prompt=prompt,
            )
        elif content_type in (_PDF_TYPE, "application/octet-stream"):
            response_text, _ = await claude.chat_with_document(
                system_prompt=system,
                document_data=file_data,
                prompt=prompt,
            )
        else:
            logger.warning("Tipo de arquivo não suportado para comprovante: %s", content_type)
            return ReceiptValidation(
                is_valid=False,
                amount_detected=None,
                pix_key_match=False,
                reason=f"Formato não reconhecido ({content_type}). Envie uma foto ou PDF do comprovante.",
            )

        data = _parse_claude_response(response_text)

        if use_fraud_check:
            return await _validate_with_fraud_check(
                data=data,
                file_data=file_data,
                expected_amount=expected_amount,
                order_id=order_id,  # type: ignore[arg-type]
                customer_phone=customer_phone,  # type: ignore[arg-type]
                db=db,  # type: ignore[arg-type]
                business=business,
            )

        # Caminho legado sem fraud check
        is_valid = data.get("is_comprovante_pix", False) and data.get("valor_correto", False)
        return ReceiptValidation(
            is_valid=is_valid,
            amount_detected=data.get("valor_detectado"),
            pix_key_match=data.get("chave_destino_encontrada", False),
            reason=data.get("motivo", ""),
        )

    except json.JSONDecodeError:
        logger.error("Claude retornou JSON inválido: %r", response_text[:200])
        return ReceiptValidation(
            is_valid=False,
            amount_detected=None,
            pix_key_match=False,
            reason="Erro ao processar o comprovante. Tente enviar novamente.",
        )
    except Exception:
        logger.exception("Erro inesperado ao validar comprovante")
        return ReceiptValidation(
            is_valid=False,
            amount_detected=None,
            pix_key_match=False,
            reason="Erro interno. Tente enviar o comprovante novamente.",
        )


async def _validate_with_fraud_check(
    data: dict,
    file_data: str,
    expected_amount: float,
    order_id: str,
    customer_phone: str,
    db: AsyncSession,
    business: BusinessConfig,
) -> ReceiptValidation:
    """Executa a verificação anti-fraude completa com os 7 checks."""
    try:
        image_bytes: Optional[bytes] = base64.b64decode(file_data)
    except Exception:
        image_bytes = None

    valid_pix_keys = [business.pix_chave] if business.pix_configured else []
    valid_recipient_names = list({business.pix_titular.lower(), "fn mercadinho"})

    fraud_result = await check_fraud(
        db=db,
        claude_extracted_data=data,
        order_amount=expected_amount,
        order_id=order_id,
        customer_phone=customer_phone,
        image_bytes=image_bytes,
        valid_pix_keys=valid_pix_keys,
        valid_recipient_names=valid_recipient_names,
    )

    amount = data.get("amount")
    recipient_key = (data.get("recipient_key") or "").strip()
    pix_key_match = recipient_key in valid_pix_keys if valid_pix_keys else True

    if fraud_result.passed:
        return ReceiptValidation(
            is_valid=True,
            amount_detected=amount,
            pix_key_match=pix_key_match,
            reason="Comprovante válido.",
            fraud_result=fraud_result,
        )

    first_flag_code = fraud_result.flags[0].split(":")[0] if fraud_result.flags else ""
    template = FRAUD_RESPONSES.get(first_flag_code, fraud_result.flags[0] if fraud_result.flags else "Comprovante inválido.")
    try:
        reason = template.format(expected=expected_amount, pix_key=business.pix_chave)
    except (KeyError, IndexError):
        reason = template

    return ReceiptValidation(
        is_valid=False,
        amount_detected=amount,
        pix_key_match=pix_key_match,
        reason=reason,
        fraud_result=fraud_result,
    )
