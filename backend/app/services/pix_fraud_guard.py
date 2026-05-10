"""Módulo Anti-Fraude Pix — protege contra os principais vetores de fraude."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pix_receipt_log import PixReceiptLog

logger = logging.getLogger(__name__)

AMOUNT_TOLERANCE = 0.10
MAX_RECEIPT_AGE_MINUTES = 60

SCHEDULING_KEYWORDS = [
    "agendado", "agendamento", "será realizado", "data futura",
    "programado", "previsão", "scheduled",
]

PRESSURE_KEYWORDS = [
    "já paguei", "ja paguei", "já mandei", "ja mandei",
    "libera logo", "libera agora", "tá demorando",
    "paguei sim", "pode liberar", "tá pago", "ta pago",
    "juro que paguei", "manda o pedido", "cadê meu pedido",
    "vou reclamar", "vou cancelar", "demora",
]

RECEIPT_EXTRACTION_PROMPT = """Analise esta imagem/PDF de comprovante Pix.
Extraia EXATAMENTE estes campos em JSON puro (sem markdown):
{
  "status": "concluido|agendado|pendente|erro",
  "amount": 0.00,
  "recipient_name": "",
  "recipient_key": "",
  "payer_name": "",
  "txid": "",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "bank": "",
  "is_screenshot": true,
  "confidence": "high|medium|low",
  "raw_text": "texto completo visível no comprovante"
}
Regras:
- Se não conseguir ler um campo, coloque null
- "confidence" é sua confiança geral na leitura
- "status" DEVE refletir se o Pix foi CONCLUÍDO ou apenas AGENDADO
- Procure palavras como "agendado", "programado", "será realizado"
- "raw_text" é TODO texto visível, para auditoria
- Responda APENAS o JSON, nada mais"""

FRAUD_RESPONSES: dict[str, str] = {
    "COMPROVANTE_REUTILIZADO": (
        "⚠️ Esse comprovante já foi usado em outro pedido. "
        "Por favor, envie o comprovante do pagamento deste pedido."
    ),
    "VALOR_DIVERGENTE": (
        "⚠️ O valor do comprovante não bate com o total do pedido (R${expected:.2f}). "
        "Verifique e envie o comprovante correto, por favor."
    ),
    "PIX_AGENDADO": (
        "⚠️ Parece que esse Pix foi agendado, não efetivado. "
        "Precisamos do comprovante de pagamento concluído pra liberar o pedido."
    ),
    "CHAVE_PIX_ERRADA": (
        "⚠️ O comprovante mostra um pagamento pra outra chave Pix. "
        "Nossa chave é {pix_key}. Pode verificar?"
    ),
    "RECEBEDOR_ERRADO": (
        "⚠️ O nome do recebedor no comprovante não corresponde ao FN Mercadinho. "
        "Verifique se o Pix foi pra gente, por favor."
    ),
    "COMPROVANTE_ANTIGO": (
        "⚠️ Esse comprovante parece ser de um pagamento antigo. "
        "Envie o comprovante do pagamento que acabou de fazer."
    ),
    "STATUS_INVALIDO": (
        "⚠️ O comprovante não mostra pagamento concluído. "
        "Só liberamos o pedido com Pix efetivado."
    ),
    "COMPROVANTE_ILEGIVEL": (
        "⚠️ Não consegui ler o comprovante. "
        "Mande uma foto mais nítida ou o PDF do banco, por favor."
    ),
    "PRESSAO_DETECTADA": (
        "Entendo a urgência! Mas preciso validar o comprovante pra segurança de todos. "
        "Manda a foto/PDF que eu confiro rapidinho. 😊"
    ),
}


class FraudCheckResult:
    def __init__(self) -> None:
        self.passed = True
        self.flags: list[str] = []
        self.severity: str = "ok"  # ok | warning | blocked

    def fail(self, reason: str, severity: str = "blocked") -> None:
        self.passed = False
        self.flags.append(reason)
        if severity == "blocked" or self.severity != "blocked":
            self.severity = severity

    def warn(self, reason: str) -> None:
        self.flags.append(reason)
        if self.severity == "ok":
            self.severity = "warning"


def compute_receipt_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


async def check_fraud(
    db: AsyncSession,
    claude_extracted_data: dict,
    order_amount: float,
    order_id: str,
    customer_phone: str,
    image_bytes: Optional[bytes] = None,
    valid_pix_keys: Optional[list[str]] = None,
    valid_recipient_names: Optional[list[str]] = None,
) -> FraudCheckResult:
    """
    Valida comprovante Pix extraído pelo Claude contra os principais vetores de fraude.

    claude_extracted_data deve conter os campos do RECEIPT_EXTRACTION_PROMPT.
    valid_pix_keys e valid_recipient_names são carregados do BusinessConfig pelo caller.
    """
    result = FraudCheckResult()
    data = claude_extracted_data
    pix_keys = valid_pix_keys or []
    recipient_names = valid_recipient_names or []

    # CHECK 1: Confiança do Claude
    if data.get("confidence") == "low":
        result.fail("COMPROVANTE_ILEGIVEL: Claude não conseguiu extrair dados com confiança.")
        return result

    # CHECK 2: Status — agendamento (vetor #2)
    status = (data.get("status") or "").lower()
    if status not in ("concluido", "concluído"):
        result.fail(f"STATUS_INVALIDO: Pix com status '{status}', não concluído.")

    raw_text = (data.get("raw_text") or "").lower()
    for kw in SCHEDULING_KEYWORDS:
        if kw in raw_text or kw in status:
            result.fail("PIX_AGENDADO: Comprovante indica agendamento, não pagamento efetivo.")
            break

    # CHECK 3: Valor divergente (vetor #5)
    receipt_amount = data.get("amount")
    if receipt_amount is not None:
        diff = abs(float(receipt_amount) - order_amount)
        if diff > AMOUNT_TOLERANCE:
            result.fail(
                f"VALOR_DIVERGENTE: Comprovante R${receipt_amount:.2f}, "
                f"pedido R${order_amount:.2f} (dif R${diff:.2f})."
            )
    else:
        result.fail("VALOR_NAO_ENCONTRADO: Não foi possível extrair o valor do comprovante.")


    # CHECK 4: Recebedor — qualquer evidencia passa (nome, sumup, cnpj mascarado)
    recipient_key = (data.get("recipient_key") or "").strip().lower()
    recipient_name = (data.get("recipient_name") or "").strip().lower()
    raw_text_low = (data.get("raw_text") or "").lower()
    bank_low = (data.get("bank") or "").lower()
    import re as _re
    cnpj_digits = _re.sub(r"[^0-9]", "", recipient_key)
    CNPJ = "60747738000149"
    evidencia_nome = any(t in recipient_name or t in raw_text_low for t in ["fn merc", "fn mercadinho"])
    evidencia_sumup = any(t in bank_low or t in raw_text_low for t in ["sumup", "sum up"])
    evidencia_cnpj = len(cnpj_digits) >= 4 and cnpj_digits in CNPJ
    if not (evidencia_nome or evidencia_sumup or evidencia_cnpj):
        result.fail(
            f"RECEBEDOR_ERRADO: sem evidencia do FN Mercadinho. nome='{recipient_name}' banco='{bank_low}' chave='{recipient_key}'"
        )

            result.fail(
                f"COMPROVANTE_ANTIGO: Pagamento de {payment_dt.strftime('%d/%m %H:%M')}, "
                f"há {int(age_minutes)} minutos. Limite: {MAX_RECEIPT_AGE_MINUTES}min."
            )
        if payment_dt > now + timedelta(minutes=5):
            result.fail("DATA_FUTURA: Comprovante com data no futuro.")

    # CHECK 6: Comprovante duplicado/reutilizado (vetor #6)
    receipt_hash: Optional[str] = None
    if image_bytes:
        receipt_hash = compute_receipt_hash(image_bytes)
        existing = await db.execute(
            select(PixReceiptLog).where(PixReceiptLog.receipt_hash == receipt_hash)
        )
        existing_log = existing.scalar_one_or_none()
        if existing_log:
            result.fail(
                f"COMPROVANTE_REUTILIZADO: Este comprovante já foi usado "
                f"no pedido #{existing_log.order_id}."
            )

    # CHECK 7: Mesmo TXID reutilizado
    txid = data.get("txid")
    if txid:
        existing_txid = await db.execute(
            select(PixReceiptLog).where(PixReceiptLog.pix_txid == txid)
        )
        existing_txid_log = existing_txid.scalar_one_or_none()
        if existing_txid_log and existing_txid_log.order_id != order_id:
            result.fail(
                f"TXID_REUTILIZADO: Transação {txid} já vinculada "
                f"ao pedido #{existing_txid_log.order_id}."
            )

    # Registra log para auditoria (mesmo quando inválido)
    if image_bytes and receipt_hash is None:
        receipt_hash = compute_receipt_hash(image_bytes)

    if receipt_hash:
        log_entry = PixReceiptLog(
            receipt_hash=receipt_hash,
            order_id=order_id,
            customer_phone=customer_phone,
            amount=float(receipt_amount) if receipt_amount is not None else 0.0,
            pix_txid=txid,
            payer_name=data.get("payer_name"),
            recipient_key=data.get("recipient_key"),
            payment_date=payment_dt,
            flagged=not result.passed,
            flag_reason="; ".join(result.flags) if result.flags else None,
        )
        db.add(log_entry)
        await db.flush()

    if not result.passed:
        logger.warning(
            "FRAUDE DETECTADA pedido #%s tel %s: %s",
            order_id, customer_phone, "; ".join(result.flags),
        )

    return result


def detect_pressure(message: str) -> bool:
    """Detecta tentativa de pressão para liberar pedido sem comprovante."""
    msg = message.lower().strip()
    return any(kw in msg for kw in PRESSURE_KEYWORDS)


def _parse_datetime(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        if time_str:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
