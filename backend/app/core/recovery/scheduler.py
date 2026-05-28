"""Scheduler APScheduler para jobs de recuperação de carrinho."""
from __future__ import annotations
import logging
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    return _scheduler


def start_scheduler() -> None:
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("Scheduler iniciado")


def stop_scheduler() -> None:
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("Scheduler encerrado")


def activate_recovery_for_tenant(tenant_id: UUID, tenant_config: dict) -> bool:
    sched = get_scheduler()
    job_id = f"recovery_{tenant_id}"

    if sched.get_job(job_id):
        logger.info("Recovery já ativo para tenant %s", tenant_id)
        return False

    async def _job():
        from app.database.session import AsyncSessionLocal
        from app.core.recovery.cart_recovery import run_recovery
        from app.core.whatsapp.client import get_whatsapp_client

        async with AsyncSessionLocal() as db:
            result = await run_recovery(
                db=db,
                tenant_id=tenant_id,
                whatsapp_client=get_whatsapp_client(),
                tenant_config=tenant_config,
            )
            if result.get("sent", 0) + result.get("reminded", 0) > 0:
                logger.info("Recovery tenant=%s: %s", tenant_id, result)

    sched.add_job(
        _job,
        trigger=IntervalTrigger(minutes=5),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("Recovery ATIVADO para tenant %s (a cada 5 min)", tenant_id)
    return True


def deactivate_recovery_for_tenant(tenant_id: UUID) -> bool:
    sched = get_scheduler()
    job_id = f"recovery_{tenant_id}"
    if sched.get_job(job_id):
        sched.remove_job(job_id)
        logger.info("Recovery DESATIVADO para tenant %s", tenant_id)
        return True
    return False


def list_active_recovery_tenants() -> list[str]:
    sched = get_scheduler()
    return [
        job.id.replace("recovery_", "")
        for job in sched.get_jobs()
        if job.id.startswith("recovery_")
    ]
