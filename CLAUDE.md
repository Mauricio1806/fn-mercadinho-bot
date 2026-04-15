# FN Mercadinho — Chatbot WhatsApp

## Projeto
Chatbot de atendimento via WhatsApp para mercadinho de condomínio em Salvador/BA.
Stack: FastAPI + Next.js + PostgreSQL + Redis + Evolution API + Claude API.

## Linguagem
- Backend: Python 3.12+ com FastAPI
- Frontend: TypeScript com Next.js
- Infraestrutura: Docker

## Configuração do Negócio
O arquivo `config/business.yaml` contém TODOS os dados do negócio.
Alguns campos estão com "TODO" — o sistema deve funcionar com placeholders.
Os donos vão preenchendo em paralelo ao desenvolvimento.
NUNCA hardcode dados do negócio no código — sempre ler do config.

## Regras de Desenvolvimento
- Python: usar type hints em TUDO
- TDD: teste ANTES do código
- Async: usar async/await para I/O (banco, Redis, HTTP)
- Validação: Pydantic em toda entrada de dados
- Commits atômicos com mensagens descritivas em português
- NUNCA commitar secrets (.env no .gitignore)
- Documentar funções complexas com docstrings
- Seguir PEP 8 + Black formatter + Ruff linter

## Segurança (CRÍTICO — sistema para cliente externo)
- Input sanitization em TODA mensagem do WhatsApp
- Rate limiting: max 30 msgs/min por número
- Webhook signature validation (Evolution API)
- Env vars validadas com Pydantic Settings
- JWT com expiração curta (15min access, 7d refresh)
- CORS restritivo
- SQL injection impossível (SQLAlchemy ORM)
- XSS prevention no frontend
- Dados de Pix NUNCA no frontend
- Audit log para ações admin
- bcrypt com rounds ≥ 12

## Convenções
- Nomes no código: inglês
- Mensagens para cliente: português BR informal
- Branches: feat/*, fix/*, chore/*
- Testes: pytest + pytest-asyncio
- Coverage mínimo: 80%

## Comandos
```
make dev        # Sobe tudo (docker + backend + frontend)
make test       # Roda todos os testes
make migrate    # Roda migrations
make seed       # Popula catálogo do business.yaml
make lint       # Ruff + Black check
```
