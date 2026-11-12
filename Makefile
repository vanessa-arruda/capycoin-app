BACKEND := uv run --directory app-backend

DB_CONTAINER := capycoin-postgres
DB_IMAGE := docker.io/library/postgres:17
DB_PORT ?= 5432
IMAGE ?= capycoin-be:latest

be-install:
	uv sync --directory app-backend

be-dev:
	$(BACKEND) uvicorn main:app --reload

be-format:
	$(BACKEND) black .

be-lint:
	$(BACKEND) flake8 .

be-migrate:
	$(BACKEND) alembic upgrade head

be-test:
	$(BACKEND) pytest

be-image:
	podman build --format docker -f app-backend/Containerfile -t $(IMAGE) app-backend

be-db-up:
	podman container exists $(DB_CONTAINER) || podman create --name $(DB_CONTAINER) \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=capycoin \
		-p 127.0.0.1:$(DB_PORT):5432 -v capycoin-pgdata:/var/lib/postgresql/data $(DB_IMAGE)
	podman start $(DB_CONTAINER)
	until podman exec $(DB_CONTAINER) pg_isready -U postgres -q; do sleep 1; done

be-db-down:
	podman stop $(DB_CONTAINER)
