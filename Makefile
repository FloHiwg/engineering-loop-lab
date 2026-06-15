UV := UV_CACHE_DIR=.uv-cache uv
SCENARIO ?= concrete

ifeq ($(SCENARIO),concrete)
FIXTURES := mock-systems
else ifeq ($(SCENARIO),ambiguous)
FIXTURES := scenarios/ambiguous-ticket
else
$(error SCENARIO must be concrete or ambiguous)
endif

RUN_ROOT := runs/$(SCENARIO)

.PHONY: setup check demo format inspect test reproduce-division-by-zero

setup:
	$(UV) sync --locked

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run pytest

test:
	$(UV) run pytest

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

demo:
	$(UV) run python -m loop_engineering_example.loop.runner demo \
		--root $(RUN_ROOT) \
		--fixtures $(FIXTURES)

inspect:
	$(UV) run python -m loop_engineering_example.loop.runner inspect \
		--root $(RUN_ROOT)

reproduce-division-by-zero:
	$(UV) run python -m loop_engineering_example.app.reproduce
