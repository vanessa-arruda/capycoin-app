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
