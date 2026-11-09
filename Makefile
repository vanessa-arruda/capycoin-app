BACKEND := uv run --directory app-backend

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
