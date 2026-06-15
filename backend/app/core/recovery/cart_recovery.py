"""
Cart recovery — ciclo de cadência de recuperação de vendas.

Lê recoverable_sales pendentes e envia mensagens WhatsApp conforme a cadência
configurada em tenant.config["recovery_cadence"]. Pensado para ser chamado
por um APScheduler embutido no lifespan do FastAPI.

Estrutura de recovery_cadence no config do tenant (JSONB):
{
  "pix_pendente": {
    "touches": [
      {"after_minutes": 15, "template": "clarify_pix_pendente_1"},
      {"after_minutes": 120, "template": "clarify_pix_pendente_2"}
    ],
    "stop_at_expiry": true
  },
  "abandono": {
    "touches": [
      {"after_minutes": 20,   "template": "clarify_abandono_1"},
      {"after_minutes": 1440, "template": "clarify_abandono_2_cupom"},
      {"after_minutes": 4320, "template": "clarify_abandono_3_lastcall"}
    ]
  }
}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from string import Template
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.recoverable_sale import RecoverableSale, RecoverySaleStatus
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Templates de mensagem por nome — substitua pelas mensagens reais do produto
_TEMPLATES: dict[str, str] = {
    "clarify_pix_pendente_1": (
        "Oi ${name}! 👋 Seu Clarify está quase chegando!\n\n"
        "Complete o pagamento via Pix e receba em casa:\n${checkout_url}\n\n"
        "O código Pix expira em breve — não perca!"
    ),
    "clarify_pix_pendente_2": (
        "⏰ Lembrete, ${name}!\n\n"
        "Seu pagamento do Clarify ainda está pendente.\n"
        "Complete aqui: ${checkout_url}"
    ),
    "clarify_abandono_1": (
        "Oi ${name}! 🧠 Você deixou o Clarify no carrinho.\n\n"
        "Que tal completar sua compra e começar a sentir a diferença?\n"
        "${checkout_url}"
    ),
    "clarify_abandono_2_cupom": (
        "🎁 Presente especial para você, ${name}!\n\n"
        "Use o cupom *${coupon}* e garanta seu Clarify com desconto exclusivo:\n"
        "${checkout_url}"
    ),
    "clarify_abandono_3_lastcall": (
        "🚨 Última chance, ${name}!\n\n"
        "O estoque do Clarify está acabando. Garanta o seu agora:\n"
        "${checkout_url}"
    ),
}

_SAFE_TEMPLATE = "Olá! Você tem uma compra pendente. Acesse: ${checkout_url}"


def _render_template(template_name: str, sale: RecoverableSale) -> str:
    """Renderiza o template de mensagem com os dados da venda."""
    tmpl_str = _TEMPLATES.get(template_name, _SAFE_TEMPLATE)
    return Template(tmpl_str).safe_substitute(
        name=sale.customer_name or "cliente",
        checkout_url=sale.checkout_url or "",
        coupon=sale.coupon or "",
        amount=f"{float(sale.amount):.2f}",
    )


def _get_cadence(tenant_config: dict[str, Any], funnel_stage: str) -> dict[str, Any]:
    """Extrai a cadência configurada para o funnel_stage ou usa padrão."""
    cadence = (tenant_config.get("recovery_cadence") or {}).get(funnel_stage) or {}
    return cadence


def _next_touch(
    sale: RecoverableSale,
    cadence: dict[str, Any],
    now: datetime,
) -> dict[str, Any] | None:
    """
    Determina o próximo toque a enviar.

    Lógica:
    - O índice do próximo toque é `sale.attempts`
    - O toque só dispara se elapsed_minutes >= touch["after_minutes"]
    - stop_at_expiry: se agora > expires_at, não dispara (caller deve marcar expired)
    """
    touches: list[dict[str, Any]] = cadence.get("touches") or []
    if not touches:
        return None

    attempt_idx = sale.attempts
    if attempt_idx >= len(touches):
        return None  # cadência esgotada

    touch = touches[attempt_idx]
    after_minutes: int = int(touch.get("after_minutes") or 0)

    # Calcula tempo decorrido desde o evento
    ref = sale.abandoned_at
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    elapsed = (now - ref).total_seconds() / 60.0

    if elapsed < after_minutes:
        return None  # ainda não é hora

    return touch


async def _process_sale(
    sale: RecoverableSale,
    cadence: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Processa um único recoverable_sale — verifica expiração, envia toque."""
    now = datetime.now(tz=timezone.utc)
    stage = sale.funnel_stage.value if sale.funnel_stage else ""

    # Verifica expiração (stop_at_expiry)
    if cadence.get("stop_at_expiry") and sale.expires_at:
        exp = sale.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp and sale.status == RecoverySaleStatus.PENDING:
            sale.status = RecoverySaleStatus.EXPIRED
            await db.commit()
            logger.info("RecoverableSale %s marcada EXPIRED (pix expirou)", sale.id)
            return

    touch = _next_touch(sale, cadence, now)
    if touch is None:
        return

    template_name: str = touch.get("template") or ""
    message = _render_template(template_name, sale)

    from app.core.whatsapp.client import get_whatsapp_client
    client = get_whatsapp_client()
    sent = await client.send_text(sale.customer_phone, message)

    if sent:
        sale.attempts += 1
        sale.last_contacted_at = now
        sale.status = RecoverySaleStatus.CONTACTED
        await db.commit()
        logger.info(
            "Toque %d enviado | sale=%s phone=%s template=%s",
            sale.attempts, sale.id, sale.customer_phone[:6] + "****", template_name,
        )
    else:
        logger.warning("Falha ao enviar toque para sale=%s", sale.id)


async def run_recovery_cycle() -> None:
    """
    Ciclo principal — chamado pelo APScheduler a cada N minutos.

    Para cada tenant ativo com recovery_cadence configurada:
    1. Busca recoverable_sales com status pending/contacted
    2. Para cada venda, verifica expiração e tenta enviar próximo toque
    """
    async with AsyncSessionLocal() as db:
        # Carrega todos os tenants ativos
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.is_active == True)  # noqa: E712
        )
        tenants = tenants_result.scalars().all()

        for tenant in tenants:
            config = tenant.config or {}
            if not config.get("recovery_cadence"):
                continue

            # Busca vendas ativas (pending ou contacted, ainda recuperáveis)
            sales_result = await db.execute(
                select(RecoverableSale).where(
                    RecoverableSale.tenant_id == str(tenant.id),
                    RecoverableSale.status.in_(
                        [RecoverySaleStatus.PENDING, RecoverySaleStatus.CONTACTED]
                    ),
                )
            )
            sales = sales_result.scalars().all()

            if not sales:
                continue

            logger.debug(
                "Recovery cycle | tenant=%s vendas_ativas=%d", tenant.slug, len(sales)
            )

            for sale in sales:
                stage = sale.funnel_stage.value if sale.funnel_stage else ""
                cadence = _get_cadence(config, stage)
                try:
                    await _process_sale(sale, cadence, db)
                except Exception:
                    logger.exception(
                        "Erro ao processar sale=%s tenant=%s", sale.id, tenant.slug
                    )
