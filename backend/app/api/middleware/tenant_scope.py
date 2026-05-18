"""Tenant scope — injeta tenant_id no contexto da requisição via JWT."""
from __future__ import annotations
from contextvars import ContextVar
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings

# ContextVar acessível em qualquer parte da requisição
current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)
current_role: ContextVar[str] = ContextVar("current_role", default="tenant_admin")

settings = get_settings()


class TenantScopeMiddleware(BaseHTTPMiddleware):
    """
    Extrai tenant_id e role do JWT e injeta no ContextVar.
    Rotas públicas (webhook, /health, /docs) são ignoradas.
    Superadmin não recebe filtro de tenant — vê tudo.
    """

    SKIP_PATHS = {"/webhook/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Reseta contexto a cada requisição
        current_tenant_id.set(None)
        current_role.set("tenant_admin")

        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if token:
            try:
                import jwt as _jwt
                payload = _jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=["HS256"],
                )
                role = payload.get("role", "tenant_admin")
                current_role.set(role)

                if role != "superadmin":
                    tid = payload.get("tenant_id")
                    if tid:
                        current_tenant_id.set(UUID(tid))
            except Exception:
                pass  # token inválido — deixa a rota tratar o 401

        return await call_next(request)


def get_current_tenant_id() -> UUID | None:
    return current_tenant_id.get()


def get_current_role() -> str:
    return current_role.get()
