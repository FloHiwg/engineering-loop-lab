UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: setup check format lint test publication-check

setup:
	$(UV) sync --locked

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run pytest
	$(UV) run python scripts/check_publication.py

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

lint:
	$(UV) run ruff check .

test:
	$(UV) run pytest

publication-check:
	$(UV) run python scripts/check_publication.py
