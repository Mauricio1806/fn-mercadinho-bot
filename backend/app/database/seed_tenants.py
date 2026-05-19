"""
Seed de tenants para desenvolvimento e testes.

Cria:
- FN Mercadinho (tenant real, UUID fixo)
- Padaria Teste (fictício)
- Farmácia Teste (fictício)
- superadmin@atende.app / Atende2026!Super
- atende096@gmail.com (admin FN Mercadinho)
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.admin_user import AdminRole, AdminUser
from app.models.tenant import Tenant
from app.tenancy.defaults import FN_MERCADINHO_UUID

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

FN_UUID = uuid.UUID(FN_MERCADINHO_UUID)
PADARIA_UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")
FARMACIA_UUID = uuid.UUID("00000000-0000-0000-0000-000000000003")


_FN_CONFIG = {
    "nome": "FN Mercadinho",
    "endereco": "Conjunto Chácara do Cabula, 74 Box 09, Salvador - BA",
    "pix_chave": "60747738000149",
    "pix_tipo_chave": "cnpj",
    "pix_titular": "NN Mercadinho",
    "pix_banco": "SumUp",
    "horario": {
        "abertura": "07:00",
        "fechamento": "21:00",
        "domingo_abertura": "08:00",
        "domingo_fechamento": "12:30",
        "dias": "Segunda a sábado",
        "msg_fora_horario": "Estamos fechados agora! 😊",
    },
    "delivery": {
        "taxa_proxima": 3.00,
        "taxa_distante": 5.00,
        "raio_proxima_metros": 500,
        "pedido_minimo": 15.00,
        "tempo_estimado": "15-30 min",
        "horario_abertura": "08:00",
        "horario_fechamento": "20:00",
        "dias_semana": "Segunda a sexta",
        "msg_fora_horario_delivery": "Delivery disponível de segunda a sexta, das 8h às 20h 😊",
        "blocos": ["A", "B", "C"],
        "tipo": "distancia",
    },
    "owners": ["+5571991356145", "+5571993266224"],
    "comissao_percentual": 5.0,
    "valor_alto_alerta": 100.0,
    "persona": {
        "tom": "informal",
        "usa_emojis": True,
        "girias_regionais": "baianas",
        "saudacao": "Olá! Bem-vindo ao FN Mercadinho 👋",
        "despedida": "Obrigado! Até a próxima 😊",
        "quando_nao_entende": "Desculpa, não entendi 😅 Pode repetir?",
        "quando_sem_estoque": "Poxa, tá em falta 😕 Posso sugerir outra coisa?",
        "quando_fora_area": "Entregamos em até 500m do mercadinho. Pode vir buscar! 😊",
        "tratamento": "você",
    },
    "branding": {"cor_primaria": "#2E7D32", "cor_secundaria": "#FFA000", "logo_url": None},
    "integracao_estoque": {"ativo": False, "sistema": None},
}

_PADARIA_CONFIG = {
    "nome": "Padaria Teste",
    "pix_chave": "padaria@teste.com",
    "pix_tipo_chave": "email",
    "pix_titular": "Padaria Teste LTDA",
    "pix_banco": "Nubank",
    "horario": {"abertura": "06:00", "fechamento": "20:00", "dias": "Segunda a sábado",
                "msg_fora_horario": "Estamos fechados! Voltamos amanhã cedo ☕"},
    "delivery": {"taxa_proxima": 4.00, "taxa_distante": 7.00, "raio_proxima_metros": 800,
                 "pedido_minimo": 20.00, "tempo_estimado": "20-40 min",
                 "dias_semana": "Segunda a sexta"},
    "owners": ["+5511999999001"],
    "comissao_percentual": 5.0,
    "persona": {"tom": "formal", "usa_emojis": True,
                "saudacao": "Olá! Bem-vindo à Padaria Teste 🍞",
                "despedida": "Obrigado! Volte sempre 😊"},
    "branding": {"cor_primaria": "#795548", "cor_secundaria": "#FF9800", "logo_url": None},
    "integracao_estoque": {"ativo": False, "sistema": None},
}

_FARMACIA_CONFIG = {
    "nome": "Farmácia Teste",
    "pix_chave": "00000000000",
    "pix_tipo_chave": "cpf",
    "pix_titular": "João da Farmácia",
    "pix_banco": "Bradesco",
    "horario": {"abertura": "08:00", "fechamento": "22:00", "dias": "Segunda a domingo",
                "msg_fora_horario": "Estamos fechados! Voltamos às 8h 💊"},
    "delivery": {"taxa_proxima": 5.00, "taxa_distante": 8.00, "raio_proxima_metros": 1000,
                 "pedido_minimo": 30.00, "tempo_estimado": "30-60 min",
                 "dias_semana": "Segunda a sexta"},
    "owners": ["+5521999999002"],
    "comissao_percentual": 5.0,
    "persona": {"tom": "formal", "usa_emojis": False,
                "saudacao": "Olá! Como posso ajudar?",
                "despedida": "Obrigado! Cuide-se bem."},
    "branding": {"cor_primaria": "#1565C0", "cor_secundaria": "#43A047", "logo_url": None},
    "integracao_estoque": {"ativo": False, "sistema": None},
}


async def seed_tenants(session: AsyncSession) -> None:
    """Cria tenants e usuários admin para desenvolvimento."""
    from sqlalchemy import select

    # ── Tenants ───────────────────────────────────────────────────────────
    tenants_data = [
        {"id": FN_UUID, "slug": "fn-mercadinho", "name": "FN Mercadinho",
         "whatsapp_number": "557199371599", "config": _FN_CONFIG},
        {"id": PADARIA_UUID, "slug": "padaria-teste", "name": "Padaria Teste",
         "whatsapp_number": "5511999999001", "config": _PADARIA_CONFIG},
        {"id": FARMACIA_UUID, "slug": "farmacia-teste", "name": "Farmácia Teste",
         "whatsapp_number": "5521999999002", "config": _FARMACIA_CONFIG},
    ]

    for t_data in tenants_data:
        existing = await session.execute(
            select(Tenant).where(Tenant.id == t_data["id"])
        )
        if existing.scalar_one_or_none():
            logger.info("Tenant já existe: %s", t_data["slug"])
            continue

        tenant = Tenant(**t_data)
        session.add(tenant)
        logger.info("Tenant criado: %s", t_data["slug"])

    await session.flush()

    # ── AdminUsers ────────────────────────────────────────────────────────
    admins_data = [
        {
            "email": "superadmin@atende.app",
            "password": "Atende2026!Super",
            "full_name": "Super Admin",
            "role": AdminRole.SUPERADMIN,
            "tenant_id": None,
        },
        {
            "email": "atende096@gmail.com",
            "password": "AtendeFN2026!",  # Senha genérica — alterar em produção
            "full_name": "Admin FN Mercadinho",
            "role": AdminRole.TENANT_ADMIN,
            "tenant_id": FN_UUID,
        },
        {
            "email": "admin@padaria-teste.com",
            "password": "Padaria2026!",
            "full_name": "Admin Padaria",
            "role": AdminRole.TENANT_ADMIN,
            "tenant_id": PADARIA_UUID,
        },
    ]

    for a_data in admins_data:
        existing = await session.execute(
            select(AdminUser).where(AdminUser.email == a_data["email"])
        )
        if existing.scalar_one_or_none():
            logger.info("Admin já existe: %s", a_data["email"])
            continue

        admin = AdminUser(
            email=a_data["email"],
            hashed_password=pwd_context.hash(a_data["password"]),
            full_name=a_data["full_name"],
            role=a_data["role"],
            tenant_id=a_data["tenant_id"],
            is_active=True,
        )
        session.add(admin)
        logger.info("Admin criado: %s", a_data["email"])

    await session.commit()
    logger.info("✅ Seed de tenants concluído.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as session:
        await seed_tenants(session)


if __name__ == "__main__":
    asyncio.run(main())
