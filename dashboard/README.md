# Dashboard — Atendê Platform

Interface administrativa multi-tenant construída com **Vite + React 19 + TypeScript + TanStack Router + shadcn/ui**.

---

## 🏗️ Por que dashboard/ separado do frontend/ existente?

O `frontend/` atual (Next.js no Lovable) é o **site público da plataforma** — landing page, planos, marketing. O `dashboard/` é o **produto em si**: a área restrita que cada cliente vai usar para gerenciar pedidos, ver conversas e configurar o bot.

**Domínio planejado:** `app.atende.com.br` (dashboard) vs `atende.com.br` (site público)

---

## 🗂️ Estrutura

```
dashboard/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx              # Bootstrap React + Router
│   ├── router.tsx            # Definição de rotas (TanStack Router)
│   ├── lib/
│   │   ├── api.ts            # Axios instance com interceptors JWT
│   │   ├── auth.ts           # Helpers de token + role detection
│   │   └── cn.ts             # clsx + tailwind-merge
│   ├── providers/
│   │   └── BrandingProvider.tsx  # CSS variables do tenant via JWT
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── superadmin/
│   │   │   ├── Dashboard.tsx     # Métricas consolidadas
│   │   │   ├── Tenants.tsx       # CRUD de tenants
│   │   │   └── TenantDetail.tsx  # Edição de config JSONB
│   │   └── tenant/
│   │       ├── Dashboard.tsx     # Métricas do tenant
│   │       ├── Orders.tsx        # Lista + troca de status
│   │       ├── Products.tsx      # Catálogo + CSV import
│   │       ├── Customers.tsx     # Clientes
│   │       └── Conversations.tsx # Chats em tempo real
│   └── components/
│       ├── Layout/
│       │   ├── Sidebar.tsx
│       │   └── Header.tsx
│       ├── Orders/
│       │   ├── OrderCard.tsx
│       │   └── StatusBadge.tsx
│       └── Products/
│           └── CSVImportModal.tsx
```

---

## 🚀 Setup

```bash
cd dashboard/
npm install
npm run dev      # Inicia em http://localhost:5173
npm run build    # Build de produção em dist/
```

---

## 🔒 Fluxo de Autenticação

1. Usuário faz login em `/login`
2. API retorna JWT com payload:
   ```json
   {
     "sub": "user-uuid",
     "role": "tenant_admin",
     "tenant_id": "00000000-...",
     "branding": {
       "cor_primaria": "#2E7D32",
       "cor_secundaria": "#FFA000",
       "logo_url": null,
       "tenant_name": "FN Mercadinho"
     }
   }
   ```
3. **BrandingProvider** extrai `branding` do JWT e injeta CSS variables:
   ```css
   :root {
     --color-primary: #2E7D32;
     --color-secondary: #FFA000;
     --tenant-name: "FN Mercadinho";
   }
   ```
4. Router redireciona baseado em `role`:
   - `superadmin` → `/admin/dashboard`
   - `tenant_admin | tenant_viewer` → `/dashboard`

---

## 🎨 Design System

| Token CSS | Padrão | Descrição |
|---|---|---|
| `--color-primary` | Tenant branding | Cor principal |
| `--color-secondary` | Tenant branding | Cor de destaque |
| `--color-bg` | `#0F0F13` | Fundo escuro |
| `--color-surface` | `#1A1A24` | Cards e painéis |
| `--color-border` | `rgba(255,255,255,0.08)` | Bordas sutis |
| `--radius` | `12px` | Raio padrão dos cards |

---

## 🔌 Integração WebSocket

Conversas em tempo real via `/ws/conversations?token=<jwt>`.
Componente `Conversations.tsx` usa `useWebSocket` hook para receber mensagens ao vivo.

---

## 📦 Dependências principais

| Pacote | Versão | Uso |
|---|---|---|
| `react` | 19 | UI |
| `@tanstack/react-router` | latest | Roteamento type-safe |
| `@tanstack/react-query` | latest | Server state |
| `shadcn/ui` | latest | Componentes base |
| `tailwindcss` | 3 | Utility CSS |
| `axios` | latest | HTTP client |
| `jose` | latest | Decode JWT client-side |
| `recharts` | latest | Gráficos |
| `lucide-react` | latest | Ícones |

---

## 🌐 Domínio e Deploy

> **Nota sobre domínio**: Para usar `app.atende.com.br`, você precisa:
> 1. Comprar o domínio `atende.com.br` (ex: Hostinger, GoDaddy, Registro.br ~R$40/ano)
> 2. Criar subdomínio `app.atende.com.br` apontando para seu servidor EC2 (registro A no DNS)
> 3. Configurar Nginx no EC2:
>    - `atende.com.br` → landing page (Lovable/Vercel)
>    - `api.atende.com.br` → FastAPI backend (porta 8000)
>    - `app.atende.com.br` → dashboard React (build servido pelo Nginx)
> 4. Instalar certificado SSL gratuito via Let's Encrypt: `certbot --nginx`

---

## 🚧 Status de Implementação

- [x] Estrutura de pastas criada
- [x] package.json com todas as dependências
- [x] Tipos TypeScript (api.ts, auth.ts)
- [x] BrandingProvider (CSS variables do tenant)
- [x] Login page
- [x] Layout com Sidebar
- [x] Dashboard tenant (stats + vendas)
- [x] Orders com troca de status
- [x] Products com CSV import
- [ ] Conversations com WebSocket (Fase 2)
- [ ] Superadmin pages (Fase 2)
- [ ] Gráficos avançados (Fase 2)
