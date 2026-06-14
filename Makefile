UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: setup check format inspect-systems lint test reproduce-division-by-zero

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

inspect-systems:
	$(UV) run python -m loop_engineering_example.inspect

reproduce-division-by-zero:
	$(UV) run python -m loop_engineering_example.reproduce
