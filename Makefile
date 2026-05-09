# Dev
up:
	docker compose up

down:
	docker compose down

build:
	docker compose build

dev:
	cd app-backend && uvicorn main:app --reload

install:
	cd app-backend && pip install -r requirements.txt

migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

test-backend:
	docker compose exec backend pytest tests/ -v

format:
	cd app-backend && black .

lint:
	cd app-backend && flake8 .

# Production
prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-migrate:
	docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f
