# COMANDOS DE ATIVACAO — ATENDE
Todos os tenants nascem com features DESATIVADAS.

## Autenticacao
export API_URL="https://SEU-DOMINIO.up.railway.app"
TOKEN=$(curl -s -X POST $API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@atende.app","password":"Atende2026!Super"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

## 1. Recuperacao de Carrinho
# Ativar
curl -X POST $API_URL/api/recovery/$TENANT_ID/activate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes_threshold":15}'

# Desativar
curl -X POST $API_URL/api/recovery/$TENANT_ID/deactivate \
  -H "Authorization: Bearer $TOKEN"

## 2. Notificacoes de Status
curl -X PATCH $API_URL/api/tenants/$TENANT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"config":{"order_status_notifications":{"enabled":true}}}'

## 3. ERP Bling
curl -X PATCH $API_URL/api/tenants/$TENANT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"config":{"integracao_estoque":{"ativo":true,"sistema":"bling","client_id":"XXX","client_secret":"XXX"}}}'

## 4. ERP Tiny
curl -X PATCH $API_URL/api/tenants/$TENANT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"config":{"integracao_estoque":{"ativo":true,"sistema":"tiny","api_key":"XXX"}}}'

## 5. Importar catalogo CSV
curl -X POST $API_URL/api/integrations/$TENANT_ID/csv \
  -H "Authorization: Bearer $TOKEN" -F "file=@catalogo.csv"

## 6. Webhook inbound (ERP chama a gente)
curl -X POST $API_URL/api/webhooks/$TENANT_ID/endpoints \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Bling","direction":"inbound","slug":"bling","events":["product.price_changed"]}'
# SALVE o secret da resposta - aparece so UMA VEZ

## 7. Webhook outbound (a gente chama n8n/Zapier)
curl -X POST $API_URL/api/webhooks/$TENANT_ID/endpoints \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"n8n","direction":"outbound","url":"https://n8n.cliente.com/webhook","events":["order.payment_confirmed"]}'

## 8. Onboarding rapido — cria tenant
curl -X POST $API_URL/api/tenants/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"slug":"slug-do-cliente","name":"Nome","whatsapp_number":"5571999998888","config":{"pix_chave":"chave","pix_tipo_chave":"email","pix_titular":"Nome","pix_banco":"Banco","horario":{"abertura":"08:00","fechamento":"18:00"},"delivery":{"taxa_proxima":3.00,"taxa_distante":5.00,"pedido_minimo":0},"owners":["+5571988887777"],"comissao_percentual":5.0,"persona":{"tom":"informal","usa_emojis":true}}}'

Atende v1.0 — todas as features sao opt-in
