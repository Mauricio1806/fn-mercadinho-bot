# GUIA DE WEBHOOKS — ATENDE

## Tipos
INBOUND: sistema externo chama a gente (ex: Bling avisa mudanca de preco)
OUTBOUND: a gente chama sistema externo (ex: pedido pago avisa n8n)

## Criar webhook
# Inbound
curl -X POST $API_URL/api/webhooks/$TENANT_ID/endpoints \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Bling","direction":"inbound","slug":"bling","events":["product.price_changed"]}'

# Outbound
curl -X POST $API_URL/api/webhooks/$TENANT_ID/endpoints \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"n8n","direction":"outbound","url":"https://n8n.cliente.com/webhook","events":["order.payment_confirmed"]}'

URL inbound: https://SEU-DOMINIO/api/webhooks/inbound/{tenant_id}/{slug}

## Seguranca
- HMAC-SHA256 por endpoint (secret gerado na criacao)
- Timestamp window de 5 minutos (anti-replay)
- Hash do payload por 24h (anti-duplicata)
- Retry outbound: 1s, 5s, 30s, 5min, 1h
- Log completo em webhook_deliveries

## Eventos disponiveis
order.created, order.payment_confirmed, order.delivered, order.cancelled
product.stock_low, product.price_changed, product.created, customer.created

## Log de auditoria
curl $API_URL/api/webhooks/$TENANT_ID/deliveries -H "Authorization: Bearer $TOKEN"

## PRODUCAO — variavel obrigatoria no Railway
WEBHOOK_MASTER_KEY = (gerar com: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
