UV_CACHE_DIR := $(CURDIR)/.uv-cache
UV := env UV_CACHE_DIR=$(UV_CACHE_DIR) uv
VENV_BIN := $(CURDIR)/.venv/bin

.PHONY: sync test run migrate revision

sync:
	$(UV) sync --extra dev

test:
	$(VENV_BIN)/pytest

run:
	$(VENV_BIN)/uvicorn backend.main:app --host 127.0.0.1 --port 8000

migrate:
	$(VENV_BIN)/alembic upgrade head

revision:
	$(VENV_BIN)/alembic revision --autogenerate -m "$(MSG)"
