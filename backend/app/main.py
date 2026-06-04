"""Ponto de entrada da aplicação FastAPI — multi-tenant."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.base import Base
from app.database.session import engine

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialização e teardown da aplicação."""
    logger.info("🚀 Atendê Platform iniciando...")

    if settings.env in ("development", "test"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tabelas criadas/verificadas.")

        # Seed de tenants em desenvolvimento
        if settings.env == "development":
            try:
                from app.database.session import AsyncSessionLocal
                from app.database.seed_tenants import seed_tenants
                async with AsyncSessionLocal() as session:
                    await seed_tenants(session)
            except Exception:
                logger.warning("Seed de tenants falhou — continuando sem seed.")

    logger.info("🏢 Plataforma multi-tenant pronta — ambiente: %s", settings.env)
    from app.core.recovery.scheduler import start_scheduler, stop_scheduler, activate_recovery_for_tenant
    from app.models.tenant import Tenant
    from app.database.session import AsyncSessionLocal
    from sqlalchemy import select as _select
    start_scheduler()
    # Re-ativa recovery para tenants que tinham ativo antes do restart
    async with AsyncSessionLocal() as _db:
        _r = await _db.execute(_select(Tenant).where(Tenant.is_active == True))
        for _t in _r.scalars().all():
            if (_t.config or {}).get('recovery', {}).get('enabled', False):
                activate_recovery_for_tenant(_t.id, _t.config)
    yield
    stop_scheduler()

    logger.info("👋 Atendê Platform encerrando...")
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Atendê Platform API",
        description="Backend multi-tenant para chatbots WhatsApp de comércio local",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Security headers
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Rotas
    from app.api.routes.webhook import router as webhook_router
    from app.api.routes.recovery import router as recovery_router
    from app.api.routes.orders import router as orders_router
    from app.api.routes.products import router as products_router
    from app.api.routes.customers import router as customers_router
    from app.api.routes.auth import router as auth_router
    from app.api.routes.dashboard import router as dashboard_router
    from app.api.routes.conversations import router as conversations_router
    from app.api.routes.service import router as service_router
    from app.api.routes.ws import router as ws_router
    from app.api.routes.tenants import router as tenants_router
    from app.api.routes.integrations import router as integrations_router

    app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
    app.include_router(products_router, prefix="/api/products", tags=["products"])
    app.include_router(customers_router, prefix="/api/customers", tags=["customers"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])
    app.include_router(service_router, prefix="/api/service", tags=["service"])
    app.include_router(ws_router, prefix="/ws", tags=["websocket"])
    app.include_router(tenants_router, prefix="/api/tenants", tags=["tenants"])
    app.include_router(recovery_router, prefix="/api/recovery", tags=["recovery"])
    app.include_router(integrations_router, prefix="/api/integrations", tags=["integrations"])

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "atende-platform", "version": "2.0.0"}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno. Tente novamente em instantes."},
        )

    return app


app = create_app()
