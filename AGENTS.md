# AGENTS.md — Survivor Career Pathway Planner

## Project context

A decision-support tool for caseworkers at organizations supporting trafficking survivors. The system matches survivors' skills to reachable occupations while respecting safety, legal, trauma-related, and documentation constraints. It produces ranked candidates with named, traceable reasons.

**The caseworker always decides.** This system surfaces options, explanations, and tradeoffs. It does not auto-decide, auto-apply, or auto-recommend without human review. This framing is brief-mandated and must be reflected in every layer, every prompt, and every UI string.

## Stack (pinned)

- Python 3.12
- `uv` — package management
- `ruff` — lint + format
- `pytest` — test runner
- `pydantic` v2 — data validation; contracts live in `models/`
- `sentence-transformers` 3.x with `BAAI/bge-small-en-v1.5`
- `scikit-learn` — cosine similarity, normalization
- `streamlit` 1.x — UI
- `plotly` 5.x — charts
- `SQLite` — file-backed, encrypted PII at rest
- `cryptography` — AES-256-GCM, HMAC-SHA-256
- `anthropic` SDK — Claude API, model `claude-sonnet-4-6`
- `vcrpy` — LLM response caching for tests
- Docker + docker-compose — single service

## Repo layout

```
models/      contracts (FROZEN after Day 0; see models/AGENTS.md)
core/        crypto, anonymizer
db/          SQLite repository
data/        O*NET + BLS loaders, pre-embedded skill catalog
fixtures/    synthetic profiles + golden outputs
engine/      pipeline layers L1-L5 (see engine/AGENTS.md)
app/         Streamlit UI (see app/AGENTS.md)
tests/       unit (per-module) + integration (end-to-end)
```

## Commands

```bash
uv sync                            # install
uv run pre-commit install          # set up hooks
uv run ruff check .                # lint
uv run ruff format .               # format
uv run pytest                      # all tests
uv run pytest -m unit              # fast tests only
uv run streamlit run app/Home.py   # local dev UI
docker compose up                  # full stack (demo target)
```

## Boundaries

### Always
- Import shared types from `models/`. Never redefine a contract type locally.
- Anonymize before any layer downstream of `core/anonymizer.py`. The pipeline operates on `Ticket`, never on `Profile`.
- Mark every excluded candidate with the named `ExclusionRule` that excluded it.
- LLM calls use `temperature=0` and JSON-schema-enforced output. Validate with pydantic on parse.
- Compute confidence scores from real signal (cosine values, TOPSIS distances). Never hardcode.
- Compute wage ranges from BLS data via `data.bls_wage_lookup(onet_code)`. Never hardcode.
- Run `ruff check` and `pytest -m unit` before declaring a task done.

### Ask first
- Any change to a schema in `models/`. Requires the `contract-change` PR label and acknowledgment from all three agents.
- Any new top-level dependency.
- Any new LLM prompt that is not JSON-schema-enforced.
- Any change to the encryption scheme, HMAC pepper handling, or anonymization boundary.

### Never
- Put real survivor data anywhere. Fixtures are synthetic only, grounded in published literature (Polaris National Survivor Study, IWPR).
- Let the LLM make the ranking decision. L4 explains the ranking L3 produced; it does not reorder.
- Set LLM temperature above 0 in production paths.
- Reach across agent ownership boundaries (engine into app, app into engine internals).
- Filter in L3. L3 only scores. Filtering is L2's job.
- Re-check hard constraints in L3 or downstream. They were already cut in L2.
- Embed the O*NET catalog at runtime in the pipeline. It is pre-embedded; load from `data/onet_skills.parquet`.
- Use NetworkX or any graph-search library. The architecture is anonymizer → L1 → L2 → L3 → L4, with L5 as a sidecar off L2. No graph search anywhere.

## Workflow

- Each agent works in an isolated git worktree on its own branch (`agent/bedrock`, `agent/engine`, `agent/surface`).
- Sync to `main` every ~4 hours: merge, re-run the integration smoke test, update fixtures if needed.
- CI gate: `ruff` + `mypy models/` + `pytest` (unit + integration) + `docker build` + a `models.py` hash check that fails on schema drift without the `contract-change` label.
- Cache LLM responses via `vcrpy` cassettes in `tests/cassettes/`. CI does not hit the live API.

## What this is not

A job matcher. A career-search engine. An auto-recommender. It is a decision-support tool for a trained caseworker who is responsible for the recommendation. Every UI string and prompt template reflects that.
