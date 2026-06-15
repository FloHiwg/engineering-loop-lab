UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: setup loop status reset check format test

setup:
	$(UV) sync --locked
	$(UV) run python -m loop_engineering_example.loop.workflow setup

loop:
	$(UV) run python -m loop_engineering_example.loop.workflow loop

status:
	$(UV) run python -m loop_engineering_example.loop.workflow status

reset:
	$(UV) run python -m loop_engineering_example.loop.workflow reset \
		$(if $(CONFIRM),--yes,)

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run pytest

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

test:
	$(UV) run pytest
