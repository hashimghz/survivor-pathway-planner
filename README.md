# Survivor Pathway Planner

Decision-support tool for caseworkers. See [AGENTS.md](AGENTS.md) for architecture and boundaries.

## Local setup

```bash
uv sync
uv run pre-commit install
```

## Run tests

```bash
uv run ruff check .
uv run pytest
```

## Docker (demo)

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY and generate secrets (see .env.example comments)

docker compose up --build
```

Streamlit UI: http://localhost:8501
