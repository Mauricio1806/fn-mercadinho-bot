"""Ponto de entrada da aplicação FastAPI."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware.tenant_scope import TenantScopeMiddleware
from fastapi.responses import JSONResponse

from app.config import get_business_config, get_settings
from app.models.base import Base
from app.database.session import engine

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialização e teardown da aplicação."""
    logger.info("🚀 FN Mercadinho iniciando...")

    # Cria tabelas (em produção usar alembic migrate)
    if settings.env in ("development", "test"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tabelas criadas/verificadas.")

    # Valida config do negócio
    business = get_business_config()
    logger.info("📋 Config carregada: %s", business.nome)

    yield

    logger.info("👋 FN Mercadinho encerrando...")
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FN Mercadinho API",
        description="Backend do chatbot WhatsApp para o FN Mercadinho",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://fn-mercadinho-boss.lovable.app","https://fn-mercadinho-boss.lovable.app/","http://localhost:5173","http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # Tenant scope — injeta tenant_id do JWT no ContextVar
    app.add_middleware(TenantScopeMiddleware)

    # Security headers middleware
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
    from app.api.routes.orders import router as orders_router
    from app.api.routes.products import router as products_router
    from app.api.routes.customers import router as customers_router
    from app.api.routes.auth import router as auth_router
    from app.api.routes.dashboard import router as dashboard_router
    from app.api.routes.conversations import router as conversations_router
    from app.api.routes.service import router as service_router
    from app.api.routes.ws import router as ws_router

    app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
    app.include_router(products_router, prefix="/api/products", tags=["products"])
    app.include_router(customers_router, prefix="/api/customers", tags=["customers"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])
    app.include_router(service_router, prefix="/api/service", tags=["service"])
    app.include_router(ws_router, prefix="/ws", tags=["websocket"])

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Endpoint de health check para o load balancer."""
        return {"status": "ok", "service": "fn-mercadinho-api"}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno. Tente novamente em instantes."},
        )

    return app


app = create_app()

@app.on_event("startup")
async def start_cleanup_job():
    import asyncio
    async def cleanup_inactive_conversations():
        while True:
            await asyncio.sleep(300)  # Roda a cada 5 minutos
            try:
                from app.database.session import AsyncSessionLocal
                from sqlalchemy import text
                from datetime import datetime, timezone, timedelta
                async with AsyncSessionLocal() as db:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                    result = await db.execute(text("""
                        UPDATE conversations 
                        SET status = 'closed'
                        WHERE status IN ('ACTIVE', 'active') 
                        AND state NOT IN ('GREETING', 'MAIN_MENU')
                        AND updated_at < :cutoff
                        RETURNING id
                    """), {"cutoff": cutoff})
                    closed = result.rowcount
                    await db.commit()
                    if closed:
                        import logging
                        logging.getLogger(__name__).info(f"Fechadas {closed} conversas inativas")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro no cleanup: {e}")
    asyncio.create_task(cleanup_inactive_conversations())
