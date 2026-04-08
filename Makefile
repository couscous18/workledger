PYTHON ?= python3

.PHONY: test lint format demo smoke docs serve ci openapi openapi-check

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src

format:
	uv run ruff check --fix .
	uv run ruff format .

demo:
	uv run wl demo all --project-dir .workledger/demo --open-report

smoke:
	uv run wl demo capex --project-dir .workledger/smoke --open-report

docs:
	uv run mkdocs build

openapi:
	uv run python3 -c 'import json; from pathlib import Path; from workledger_server.app import create_app; Path("schemas/openapi.json").write_text(json.dumps(create_app().openapi(), indent=2), encoding="utf-8")'

openapi-check:
	uv run python3 -c 'import json; from pathlib import Path; from workledger_server.app import create_app; expected=json.loads(Path("schemas/openapi.json").read_text(encoding="utf-8")); actual=create_app().openapi(); raise SystemExit(0 if actual == expected else 1)'

serve:
	uv run workledger-server

ci: lint test openapi-check
