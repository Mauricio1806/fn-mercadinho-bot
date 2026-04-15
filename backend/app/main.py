"""Ponto de entrada da aplicação FastAPI."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

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

    app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
    app.include_router(products_router, prefix="/api/products", tags=["products"])
    app.include_router(customers_router, prefix="/api/customers", tags=["customers"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])

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
