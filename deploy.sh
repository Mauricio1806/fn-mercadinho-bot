#!/bin/bash
# Script de deploy para VPS — rode como: bash deploy.sh
set -e

echo "=== FN Mercadinho — Deploy ==="

# ── 1. Verifica .env ──────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "ERRO: arquivo .env não encontrado. Copie .env.example e preencha."
  exit 1
fi

source .env

# Variáveis obrigatórias
REQUIRED=(DB_PASSWORD REDIS_PASSWORD ANTHROPIC_API_KEY JWT_SECRET SERVICE_API_KEY
           EVOLUTION_API_KEY ADMIN_EMAIL ADMIN_PASSWORD NEXT_PUBLIC_API_URL ALLOWED_ORIGINS)

for var in "${REQUIRED[@]}"; do
  if [ -z "${!var}" ] || [[ "${!var}" == *"change_me"* ]] || [[ "${!var}" == "TODO"* ]]; then
    echo "ERRO: variável $var não definida ou ainda com valor padrão."
    exit 1
  fi
done

echo "✅ Variáveis de ambiente OK"

# ── 2. SSL (primeira vez) ─────────────────────────────────────────────────────
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "📜 Obtendo certificado SSL para $DOMAIN..."
  docker run --rm \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -v /var/www/certbot:/var/www/certbot \
    certbot/certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    -d "$DOMAIN" -d "www.$DOMAIN" \
    --email "$ADMIN_EMAIL" --agree-tos --no-eff-email
fi

# ── 3. Build e sobe serviços ──────────────────────────────────────────────────
echo "🐳 Building e subindo containers..."
docker compose -f docker-compose.prod.yml pull postgres redis nginx
docker compose -f docker-compose.prod.yml build --no-cache backend frontend
docker compose -f docker-compose.prod.yml up -d

# ── 4. Migrations ─────────────────────────────────────────────────────────────
echo "🗄️  Rodando migrations..."
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head

# ── 5. Seed do catálogo ───────────────────────────────────────────────────────
echo "🌱 Populando catálogo..."
docker compose -f docker-compose.prod.yml exec backend \
  python -m app.database.seed

# ── 6. Cria admin se não existir ──────────────────────────────────────────────
echo "👤 Criando admin..."
docker compose -f docker-compose.prod.yml exec backend \
  python -c "
import asyncio, os
os.environ.setdefault('ENV', 'production')
from app.database.seed import create_admin
asyncio.run(create_admin())
" 2>/dev/null || true

# ── 7. Health check ───────────────────────────────────────────────────────────
echo "🏥 Verificando health..."
sleep 5
HEALTH=$(curl -sf "https://$DOMAIN/api/health" 2>/dev/null || echo "falhou")
if [[ "$HEALTH" == *"ok"* ]]; then
  echo "✅ API respondendo!"
else
  echo "⚠️  API não respondeu — verifique: docker compose -f docker-compose.prod.yml logs backend"
fi

echo ""
echo "=== Deploy concluído ==="
echo "Painel: https://$DOMAIN"
echo "API docs (dev): http://localhost:8000/docs"
echo ""
echo "Próximos passos:"
echo "  1. Parear WhatsApp: acesse a Evolution API e escaneie o QR code"
echo "  2. Configurar webhook na Evolution API: https://$DOMAIN/webhook/whatsapp"
echo "  3. Importar n8n_stock_sync.json no n8n"
