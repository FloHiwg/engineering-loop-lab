UV := UV_CACHE_DIR=.uv-cache uv

.PHONY: \
	agent-ambiguous-demo agent-demo setup check demo format inspect-demo \
	inspect-systems lint loop-reset loop-status loop-step test \
	reproduce-division-by-zero

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
	$(UV) run python -m loop_engineering_example.loop.inspect

inspect-demo:
	$(UV) run python -m loop_engineering_example.loop.inspect --root runs/demo

loop-reset:
	$(UV) run python -m loop_engineering_example.loop.runner reset

loop-step:
	$(UV) run python -m loop_engineering_example.loop.runner step

loop-status:
	$(UV) run python -m loop_engineering_example.loop.runner status

demo:
	$(UV) run python -m loop_engineering_example.loop.runner demo

agent-demo:
	$(UV) run python -m loop_engineering_example.loop.runner agent-demo \
		--root runs/agent-demo

agent-ambiguous-demo:
	$(UV) run python -m loop_engineering_example.loop.runner agent-demo \
		--root runs/agent-ambiguous-demo \
		--fixtures scenarios/ambiguous-ticket

reproduce-division-by-zero:
	$(UV) run python -m loop_engineering_example.app.reproduce
