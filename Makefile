UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: setup check format lint test

setup:
	$(UV) sync --locked

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run pytest

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

lint:
	$(UV) run ruff check .

test:
	$(UV) run pytest
