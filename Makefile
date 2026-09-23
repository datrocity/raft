.PHONY: setup test cov lint format watch

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"

test:
	.venv/bin/pytest tests

cov:
	.venv/bin/pytest --cov=raft --cov-report=term-missing tests

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .

watch:
	.venv/bin/pytest --looponfail tests
