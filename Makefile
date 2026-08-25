.PHONY: lint test smoke

lint:
	ruff check .
	ruff format --check .

test:
	pytest -q

smoke:
	python scripts/smoke_mcp.py
