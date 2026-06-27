"""Rotas de gestão de usuários admin — só platform owner acessa."""

import secrets
import string
import uuid as _uuid
from datetime import datetime, timezone

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_superadmin
from app.database.session import get_db
from app.models.admin_user import AdminUser, AdminRole
from app.models.tenant import Tenant

router = APIRouter()


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str
    tenant_id: str  # UUID do tenant que vai administrar


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    reset_password: bool | None = None  # se True, gera senha nova e força troca


class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str | None
    tenant_name: str | None
    is_active: bool
    must_change_password: bool
    password_changed_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AdminUserCreateResponse(BaseModel):
    user: AdminUserResponse
    temp_password: str  # mostrar UMA VEZ pro platform owner copiar e mandar pro cliente


def _gen_temp_password() -> str:
    """Senha temporária forte: 12 chars, letras + dígitos."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def _to_response(user: AdminUser, tenant_name: str | None) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        tenant_name=tenant_name,
        is_active=user.is_active,
        must_change_password=bool(user.must_change_password),
        password_changed_at=user.password_changed_at.isoformat() if user.password_changed_at else None,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/", response_model=list[AdminUserResponse])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> list[AdminUserResponse]:
    """Lista todos os admins. Apenas platform owner acessa."""
    result = await db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
    users = result.scalars().all()

    # Pega nomes dos tenants
    tenant_ids = {u.tenant_id for u in users if u.tenant_id}
    tenant_names: dict = {}
    if tenant_ids:
        t_result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        for t in t_result.scalars().all():
            tenant_names[str(t.id)] = t.name

    return [_to_response(u, tenant_names.get(str(u.tenant_id))) for u in users]


@router.post("/", response_model=AdminUserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> AdminUserCreateResponse:
    """Cria um tenant_admin pra um tenant existente. Retorna senha temporária UMA VEZ."""
    # Valida que o tenant existe
    try:
        tenant_uuid = _uuid.UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="tenant_id inválido.")

    t_result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
    tenant = t_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    # Email único
    existing = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email já cadastrado.")

    # Gera senha temporária
    temp_password = _gen_temp_password()
    hashed = _bcrypt.hashpw(temp_password.encode(), _bcrypt.gensalt()).decode()

    user = AdminUser(
        email=body.email,
        hashed_password=hashed,
        full_name=body.full_name,
        is_active=True,
        role=AdminRole.TENANT_ADMIN,
        tenant_id=tenant_uuid,
        must_change_password=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return AdminUserCreateResponse(
        user=_to_response(user, tenant.name),
        temp_password=temp_password,
    )


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    user_id: str,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> AdminUserResponse:
    """Atualiza um admin: ativar/desativar, renomear, resetar senha."""
    try:
        u_uuid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido.")

    result = await db.execute(select(AdminUser).where(AdminUser.id == u_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    temp_pw = None
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.reset_password:
        temp_pw = _gen_temp_password()
        user.hashed_password = _bcrypt.hashpw(temp_pw.encode(), _bcrypt.gensalt()).decode()
        user.must_change_password = True
        user.password_changed_at = None

    await db.commit()
    await db.refresh(user)

    tenant_name = None
    if user.tenant_id:
        t_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        t = t_result.scalar_one_or_none()
        tenant_name = t.name if t else None

    resp = _to_response(user, tenant_name)
    if temp_pw:
        # Retorna como header pro frontend pegar
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content=resp.model_dump(),
            headers={"X-Temp-Password": temp_pw},
        )
    return resp
