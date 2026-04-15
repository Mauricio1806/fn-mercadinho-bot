.PHONY: dev dev-docker test migrate seed lint security build clean logs

# ── Desenvolvimento local ──────────────────────────────────────────────────
dev-docker:
	docker compose up -d postgres redis evolution-api
	@echo "Aguardando banco..."
	@sleep 3
	$(MAKE) migrate
	cd backend && uvicorn app.main:app --reload --port 8000

dev:
	docker compose up -d postgres redis
	@echo "Aguardando banco..."
	@sleep 3
	$(MAKE) migrate
	cd backend && uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

# ── Testes ─────────────────────────────────────────────────────────────────
test:
	cd backend && pytest -v --cov=app --cov-report=term-missing

test-fast:
	cd backend && pytest -v -x --no-cov

test-watch:
	cd backend && ptw -- -v

# ── Banco de dados ─────────────────────────────────────────────────────────
migrate:
	cd backend && alembic upgrade head

migrate-down:
	cd backend && alembic downgrade -1

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python -m app.database.seed

# ── Qualidade ──────────────────────────────────────────────────────────────
lint:
	cd backend && ruff check . && black --check .

lint-fix:
	cd backend && ruff check --fix . && black .

typecheck:
	cd backend && mypy app/

# ── Docker ─────────────────────────────────────────────────────────────────
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend

logs-all:
	docker compose logs -f

clean:
	docker compose down -v
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true

# ── Setup inicial ──────────────────────────────────────────────────────────
setup:
	cp backend/.env.example backend/.env
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	@echo "\n✅ Setup concluído! Edite backend/.env com suas chaves."
	@echo "   Depois: make dev-docker"
