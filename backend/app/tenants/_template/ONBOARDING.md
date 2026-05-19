# ══════════════════════════════════════════════════════════════
# ONBOARDING GUIDE — Atendê Plataforma SaaS
# Checklist completo para adicionar um novo cliente
# Tempo estimado: 1h30 a 2h por tenant
# ══════════════════════════════════════════════════════════════

# CHECKLIST DE ONBOARDING — NOVO CLIENTE

## 📋 1. DADOS A COLETAR DO CLIENTE

Antes de iniciar qualquer configuração, colete **todos** estes dados. Use o
formulário abaixo como roteiro de conversa/reunião com o cliente.

---

### 1.1 Identificação do Negócio

| Campo              | Exemplo                          | Obrigatório |
|--------------------|----------------------------------|-------------|
| Nome do negócio    | FN Mercadinho                    | ✅ Sim      |
| Endereço completo  | Rua X, 123, Bairro Y, Salvador-BA| Recomendado |
| Instagram          | @fnmercadinhooficial             | Opcional    |
| WhatsApp comercial | 71 99135-6145                    | Opcional    |

---

### 1.2 Número WhatsApp do Bot

> **CRÍTICO**: Este é o número que o bot vai usar para atender os clientes.
> Pode ser um chip novo ou um número já existente (precisa ser migrado para WhatsApp Business API).

| Campo                  | Formato             | Notas                                |
|------------------------|---------------------|--------------------------------------|
| Número WhatsApp do bot | +55 71 9XXXX-XXXX   | Com DDI (+55), com DDD               |
| Tipo de conta          | Business API / Baileys | Baileys = número real no celular  |

**Perguntas a fazer:**
- O cliente tem um chip/número dedicado para o bot?
- O número atual está ativo e com créditos?
- Pode ficar conectado 24/7 (celular carregando)?

---

### 1.3 Chave Pix

> **CRÍTICO**: Sem isso o bot não pode cobrar.

| Campo          | Exemplo              | Notas                              |
|----------------|----------------------|------------------------------------|
| Tipo de chave  | cnpj                 | cpf / cnpj / email / telefone / aleatoria |
| Chave Pix      | 60747738000149       | Exatamente como está no banco      |
| Nome do titular| NN Mercadinho        | Nome cadastrado na conta           |
| Banco          | SumUp                | Banco onde recebe o Pix            |

**Perguntas a fazer:**
- Qual banco usa para receber? (Nubank, Itaú, SumUp, etc.)
- A chave está ativa e funcionando?
- O CNPJ ou CPF está regularizado?

---

### 1.4 Horário de Funcionamento

| Campo               | Exemplo             |
|---------------------|---------------------|
| Horário de abertura | 07:00               |
| Horário de fechamento | 21:00             |
| Dias da semana      | Segunda a sábado    |
| Domingo abre?       | Sim / Não           |
| Horário domingo     | 08:00 às 12:30      |
| Mensagem fora horário | Personalizada     |

---

### 1.5 Delivery

| Campo                    | Exemplo       | Notas                                 |
|--------------------------|---------------|---------------------------------------|
| Taxa delivery próximo    | R$ 3,00       | Entregas dentro do raio definido      |
| Taxa delivery distante   | R$ 5,00       | Entregas fora do raio                 |
| Raio "próximo" (metros)  | 500m          | Distância limite para taxa menor      |
| Pedido mínimo            | R$ 15,00      | 0 = sem mínimo                        |
| Tempo estimado de entrega| 15-30 min     | Aparece para o cliente                |
| Horário delivery abertura| 08:00         | Pode ser diferente do funcionamento   |
| Horário delivery fechamento | 20:00      |                                       |
| Dias para delivery       | Seg a Sex     | Pode ser diferente do funcionamento   |
| Áreas atendidas          | Blocos A, B, C| Bairros / condomínios / raio          |

**Perguntas a fazer:**
- Entrega em qualquer endereço ou só em áreas específicas?
- Tem mototboy próprio ou usa plataformas (iFood, etc.)?
- Qual o tempo médio real de entrega?

---

### 1.6 Números dos Donos (Notificações)

> O sistema envia alertas de novo pedido e venda confirmada para esses números.

| Campo      | Formato           | Notas                           |
|------------|-------------------|---------------------------------|
| Dono 1     | +5571991356145    | Recebe todos os alertas + áudio |
| Dono 2     | +5571993266224    | Recebe só confirmação de venda  |
| Dono 3...N | +55...            | Adicionar em owners[]           |

---

### 1.7 Financeiro (Comissão da Plataforma)

| Campo                 | Exemplo | Notas                              |
|-----------------------|---------|------------------------------------|
| Comissão %            | 5.0%    | Calculado sobre cada venda confirmada |
| Valor "pedido alto"   | R$ 100  | Alerta especial para pedidos grandes |

---

### 1.8 Tom de Voz do Bot

| Campo             | Opções / Exemplo                      |
|-------------------|---------------------------------------|
| Tom geral         | informal / formal                     |
| Usa emojis?       | Sim / Não                             |
| Gírias regionais  | baianas / cariocas / paulistanas / null |
| Saudação padrão   | "Olá! Bem-vindo ao [Nome]! 👋"        |
| Despedida padrão  | "Obrigado! Até a próxima 😊"          |
| Tratamento        | você / senhor(a)                      |

**Perguntas a fazer:**
- O negócio é mais formal ou descontraído?
- Como os funcionários costumam atender os clientes pessoalmente?
- Tem palavras/expressões que NÃO pode usar?

---

### 1.9 Identidade Visual (Dashboard)

| Campo          | Exemplo   | Notas                        |
|----------------|-----------|------------------------------|
| Cor primária   | #2E7D32   | Verde, azul, etc. (hex)      |
| Cor secundária | #FFA000   | Cor de destaque               |
| Logo           | URL HTTPS | PNG transparente, 200x200px  |

---

### 1.10 Catálogo de Produtos

> Este é geralmente o item que mais demora. Planeje com antecedência.

**Formato CSV esperado:**
```csv
nome,preco,categoria,disponivel,external_id
Coca-Cola 2L,9.99,Bebidas,true,
Biscoito Oreo,4.50,Biscoitos,true,
Frango Congelado 1kg,22.90,Congelados,false,
```

**Campos:**
| Campo       | Tipo      | Notas                                    |
|-------------|-----------|------------------------------------------|
| nome        | string    | Nome do produto (obrigatório)            |
| preco       | decimal   | Ponto como separador (9.99)              |
| categoria   | string    | Categoria livre (será criada se não existir) |
| disponivel  | boolean   | true/false (default: true)               |
| external_id | string    | ID no sistema ERP (deixar vazio se não tiver) |

**Opções de importação:**
1. **CSV manual**: Cliente envia planilha → você faz upload no dashboard
2. **Integração ERP**: Ver seção 1.11 abaixo
3. **Parse automático**: Se tiver lista em PDF/imagem, pode usar o script `parse_estoque.py`

---

### 1.11 Integração de Sistema de Estoque (ERP)

> **A maioria dos clientes vai precisar disso a médio prazo.** Colete as informações abaixo mesmo se o cliente ainda não usa ERP — para saber o que planejar.

| Campo                    | Notas                                      |
|--------------------------|--------------------------------------------|
| Usa sistema de estoque?  | Sim / Não / "Planejo usar"                 |
| Qual sistema?            | Bling / Tiny / SistemX / Planilha / Outro  |
| Tem API disponível?      | Confirmar na documentação do sistema       |
| Sincronização desejada   | Preço / Estoque / Ambos                    |
| Frequência de sync       | Tempo real (webhook) / A cada X minutos    |

**Sistemas suportados nativamente:**
- **Bling**: OAuth2 + webhook em tempo real ✅
- **Tiny ERP**: API key + polling ✅
- **Genérico**: Webhook POST com payload configurável ✅
- **CSV**: Upload manual ou agendado ✅

**Para ativar integração Bling:**
1. Cliente acessa Bling → Configurações → API → Criar aplicativo
2. Fornece: `client_id`, `client_secret`
3. Você configura o webhook URL: `https://api.atende.app/api/integrations/{tenant_id}/webhook`

**Para ativar integração Tiny:**
1. Cliente acessa Tiny → Configurações → API → Gerar token
2. Fornece: `api_key`
3. Polling automático a cada `sync_intervalo_minutos`

---

## 🚀 2. PASSO A PASSO DE ONBOARDING

### Passo 1: Coletar dados (30 min)
Use o checklist da Seção 1 acima. Recomendado: call de 30 min com o cliente.

### Passo 2: Criar pasta do tenant (5 min)

```bash
# No servidor ou localmente
cd backend/app/tenants/
cp -r _template/ tenant_0X/   # substitua X pelo próximo número disponível
mv tenant_0X/config.yaml.template tenant_0X/config.yaml
```

### Passo 3: Preencher config.yaml (10 min)

Edite `tenant_0X/config.yaml` com todos os dados coletados.

### Passo 4: INSERT no banco de dados (5 min)

```sql
-- Execute via psql ou dashboard do banco
INSERT INTO tenants (id, slug, name, whatsapp_number, is_active, config)
VALUES (
  gen_random_uuid(),
  'nome-do-negocio',        -- slug: só minúsculas, hífens, sem espaço
  'Nome do Negócio',
  '5571999999999',          -- número do bot sem + ou espaços
  true,
  '{
    "nome": "Nome do Negócio",
    "pix_chave": "...",
    ...
  }'::jsonb
);
```

Ou via API (superadmin):
```bash
curl -X POST https://api.atende.app/api/tenants/ \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "nome-do-negocio",
    "name": "Nome do Negócio",
    "whatsapp_number": "5571999999999",
    "config": { ... }
  }'
```

### Passo 5: Criar usuário admin do tenant (3 min)

```bash
# Via API superadmin
curl -X POST https://api.atende.app/api/tenants/{tenant_id}/admin \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -d '{"email": "admin@cliente.com", "password": "...", "full_name": "..."}'
```

### Passo 6: Importar catálogo (15-30 min)

**Opção A — CSV:**
```bash
# Via dashboard: Products → Import → Upload CSV
# Ou via API:
curl -X POST https://api.atende.app/api/integrations/{tenant_id}/csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@catalogo.csv"
```

**Opção B — Integração ERP:**
Configure `integracao_estoque` no config.yaml e chame sync:
```bash
curl -X POST https://api.atende.app/api/integrations/{tenant_id}/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Passo 7: Provisionar PM2 (10 min)

```bash
# No EC2, criar processo PM2 para o tenant
pm2 start "uvicorn app.main:app --port 800X" --name "tenant-0X-api"
pm2 save
```

### Passo 8: Testar fluxo completo (15 min)

1. Enviar "Olá" para o número do bot
2. Verificar saudação personalizada
3. Fazer pedido de teste
4. Verificar notificação no WhatsApp do dono
5. Enviar comprovante PIX de teste
6. Verificar confirmação no dashboard

---

## ✅ 3. CHECKLIST DE GO-LIVE

- [ ] Config.yaml preenchido e validado (`python -c "import yaml; yaml.safe_load(open('config.yaml'))"`)
- [ ] Tenant criado no banco (SELECT * FROM tenants WHERE slug = '...')
- [ ] Número WhatsApp conectado e funcionando
- [ ] Admin do tenant criado e logando no dashboard
- [ ] Catálogo importado (mínimo 10 produtos)
- [ ] Chave Pix funcionando (teste de pagamento R$ 0,01)
- [ ] Notificação chegando no WhatsApp dos donos
- [ ] Dashboard abrindo com branding correto
- [ ] PM2 process rodando e reinicia automaticamente

---

## 📊 4. INFORMAÇÕES ADICIONAIS RECOMENDADAS

Além dos dados obrigatórios, considere coletar:

### Sobre o negócio
- Há quanto tempo existe o negócio?
- Tem funcionários que vão usar o dashboard ou só os donos?
- Qual o volume médio de pedidos por dia hoje?
- Atende delivery próprio, vai terceirizar ou vai integrar com iFood/Rappi?

### Sobre tecnologia
- O cliente tem acesso ao Wi-Fi/internet estável para manter o bot online?
- Tem celular Android ou iOS dedicado para o bot?
- Já usou algum sistema de gestão antes? Qual?
- Tem planilha de estoque atual? Em Excel, Google Sheets?

### Sobre expansão futura
- Pretende adicionar mais pontos de venda?
- Tem interesse em cardápio digital com QR Code?
- Quer relatório de vendas por produto / categoria?
- Tem interesse em programa de fidelidade?

---

## 📝 5. NOTAS IMPORTANTES

> ⚠️ **Nunca compartilhe** credenciais de superadmin com o cliente.
> Cada cliente tem apenas acesso ao próprio tenant.

> ⚠️ **Dados Pix**: confirme com o cliente que a chave está ativa
> fazendo um Pix de R$ 0,01 como teste ANTES do go-live.

> ⚠️ **WhatsApp Business API**: o número do bot não pode ser usado
> normalmente enquanto estiver conectado. Use um chip dedicado.

> 💡 **QR Code para cardápio**: planejado para versão futura — o cliente
> poderá gerar um QR que abre o cardápio interativo no WhatsApp do bot.

---

*Atendê Platform — onboarding guide v1.0*
*Tempo médio de onboarding: 1h30 a 2h*
