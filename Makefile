.PHONY: install lint format test eval e2e run-api run-ui docker-up docker-down

install:
	uv venv
	uv pip install -e .
	uv pip install ruff mypy pytest

lint:
	uv run ruff check src/ tests/
	uv run mypy src/ --ignore-missing-imports

format:
	uv run ruff check src/ tests/ --fix
	uv run ruff format src/ tests/

test:
	uv run pytest tests/ -v

eval:
	uv run python -m rfp_engine.evaluation.evaluator

e2e:
	uv run python scripts/generate_sample_rfp.py
	uv run python scripts/verify_e2e.py

run-api:
	uv run uvicorn rfp_engine.api.main:app --reload --port 8000

run-ui:
	uv run streamlit run app.py

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down
