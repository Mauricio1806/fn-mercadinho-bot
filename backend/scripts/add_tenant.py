"""
Adiciona novo tenant ao banco.
Uso: python -m scripts.add_tenant --config app/tenants/tenant_02/config.yaml.template
"""
from __future__ import annotations
import argparse, asyncio, sys, uuid, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from sqlalchemy import select

async def add_tenant(config_path: str) -> None:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    if cfg.get("nome") == "AGUARDANDO_CLIENTE":
        print("Preencha os dados antes."); return
    async with AsyncSessionLocal() as db:
        if (await db.execute(select(Tenant).where(Tenant.slug == cfg["slug"]))).scalar_one_or_none():
            print(f"Slug '{cfg['slug']}' ja existe."); return
        t = Tenant(id=uuid.uuid4(), slug=cfg["slug"], name=cfg["nome"],
                   whatsapp_number=cfg["whatsapp_number"], is_active=True,
                   config={
                       "pix_chave": cfg["pix"]["chave"],
                       "pix_tipo_chave": cfg["pix"]["tipo_chave"],
                       "pix_titular": cfg["pix"]["titular"],
                       "pix_banco": cfg["pix"]["banco"],
                       "horario": cfg["horario"],
                       "delivery": cfg["delivery"],
                       "owners": cfg["owners"],
                       "comissao_percentual": cfg.get("comissao_percentual", 5.0),
                       "persona": cfg.get("persona", {}),
                       "branding": cfg.get("branding", {}),
                       "recovery": cfg.get("recovery", {"enabled": False}),
                       "integracao_estoque": cfg.get("integracao_estoque", {"ativo": False}),
                   })
        db.add(t); await db.commit(); await db.refresh(t)
        print(f"Tenant criado: {t.name} | ID: {t.id} | WhatsApp: {t.whatsapp_number}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    asyncio.run(add_tenant(p.parse_args().config))
