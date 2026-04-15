"""Validador de área de delivery para o condomínio."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import BusinessConfig, get_business_config


@dataclass
class DeliveryValidationResult:
    is_valid: bool
    block: str | None = None
    apartment: str | None = None
    fee: float = 0.0
    error_message: str | None = None


def validate_delivery(
    block: str,
    apartment: str,
    business: BusinessConfig | None = None,
) -> DeliveryValidationResult:
    """
    Valida se o bloco e apartamento estão na área de entrega.

    Args:
        block: Bloco informado pelo cliente (ex: "A", "bloco b", "B2")
        apartment: Número do apartamento
        business: Config do negócio (usa singleton se não informado)

    Returns:
        DeliveryValidationResult com is_valid e fee
    """
    if business is None:
        business = get_business_config()

    # Normaliza o bloco (remove "bloco", "bl.", espaços e converte para maiúsculo)
    normalized_block = _normalize_block(block)

    if not normalized_block:
        return DeliveryValidationResult(
            is_valid=False,
            error_message="Bloco inválido. Por favor, informe apenas a letra do bloco (ex: A, B, C).",
        )

    if not apartment or not apartment.strip():
        return DeliveryValidationResult(
            is_valid=False,
            error_message="Número do apartamento não informado.",
        )

    allowed_blocks = [b.upper() for b in business.delivery_blocos]

    # Se não há blocos configurados, aceita qualquer um
    if not allowed_blocks:
        return DeliveryValidationResult(
            is_valid=True,
            block=normalized_block,
            apartment=apartment.strip(),
            fee=business.delivery_taxa,
        )

    if normalized_block not in allowed_blocks:
        blocos_str = ", ".join(allowed_blocks) if allowed_blocks else "todos"
        return DeliveryValidationResult(
            is_valid=False,
            error_message=(
                f"Desculpa, não entregamos no bloco {normalized_block} 😕 "
                f"Atendemos os blocos: {blocos_str}. "
                "Mas você pode retirar aqui no mercadinho!"
            ),
        )

    return DeliveryValidationResult(
        is_valid=True,
        block=normalized_block,
        apartment=apartment.strip(),
        fee=business.delivery_taxa,
    )


def _normalize_block(block: str) -> str:
    """Normaliza string de bloco para letra(s) maiúscula(s)."""
    if not block:
        return ""

    clean = (
        block.strip()
        .upper()
        .replace("BLOCO", "")
        .replace("BL.", "")
        .replace("BL", "")
        .strip()
    )

    # Extrai apenas letras/números do bloco
    result = "".join(c for c in clean if c.isalnum())
    return result


def extract_block_and_apartment(text: str) -> tuple[str | None, str | None]:
    """
    Tenta extrair bloco e apartamento de uma frase do cliente.
    Ex: "Bloco A, apto 201" → ("A", "201")
    Ex: "B 302" → ("B", "302")
    """
    import re

    text_upper = text.upper().strip()

    # Padrão: "Bloco X, Apt Y" ou "Bloco X Apto Y"
    pattern_full = re.search(
        r"(?:BLOCO\s*)?([A-Z][0-9]?)\s*[,\s]+(?:APT[O]?\.?\s*|AP\.?\s*|N[º°]?\s*)?(\d+)",
        text_upper,
    )
    if pattern_full:
        return pattern_full.group(1), pattern_full.group(2)

    # Padrão simples: letra seguida de número (ex: "A 201")
    pattern_simple = re.search(r"\b([A-Z])\s+(\d{2,4})\b", text_upper)
    if pattern_simple:
        return pattern_simple.group(1), pattern_simple.group(2)

    return None, None
