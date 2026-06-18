# Pathway planner

A decision-support tool for caseworkers at organisations supporting trafficking survivors. Matches survivors' skills to reachable occupations while respecting safety, legal, trauma-related, and documentation constraints. The caseworker decides; the tool surfaces options.

## Quick start

```bash
# 1. install
uv sync

# 2. set up local env
cp .env.example .env
# fill in PATHWAY_AES_KEY, PATHWAY_HMAC_PEPPER, ANTHROPIC_API_KEY

# 3. install git hooks (strips Cursor co-author trailers)
bash scripts/install_hooks.sh

# 4. run the UI (uses mock data until the engine is wired)
uv run streamlit run app/Home.py
```

The UI opens at http://localhost:8501 with a demo profile already loaded.

## Project layout

| Directory | What lives here | Owner |
|---|---|---|
| `models/` | pydantic contracts (frozen Day 0) | — |
| `core/` | crypto, anonymiser | Bedrock |
| `db/` | SQLite repository | Bedrock |
| `data/raw/` | teammate's source data | Bedrock |
| `data/processed/` | derived data, if any | Bedrock |
| `fixtures/` | synthetic profiles, golden outputs | Bedrock |
| `engine/` | pipeline modules (veto, score, explain, sensitivity) | Engine |
| `app/` | Streamlit UI | Surface |
| `scripts/` | utilities and git hooks | Bedrock |
| `tests/` | unit + integration | per agent |

## Reading order

1. `AGENTS.md` — the constitution. Read this first.
2. `models/__init__.py` — the contracts. Every layer flows through these.
3. `app/AGENTS.md` — the design rules. Non-negotiable for the demo.
4. `engine/AGENTS.md` — the pipeline architecture.
5. `AGENT_KICKOFF_PROMPTS.md` — prompts to paste into Cursor worktrees.

## Design language

The UI uses a custom palette ("Vellum") and typography (Source Serif 4 + Inter + JetBrains Mono). Defined in `.streamlit/config.toml` and `app/style.css`. **The UI never surfaces internal pipeline terminology** — the caseworker sees one coherent result, never `L1`, `TOPSIS`, `embedding`, `model`, or any internal name. See `app/copy.py` for the canonical user-facing strings.

## Workflow

- Three agents (Bedrock, Engine, Surface) work in isolated git worktrees.
- All git operations are performed by the human. Agents do not commit, push, merge, or rebase.
- The commit-msg hook in `scripts/hooks/` strips any Cursor co-author trailer from commit messages.
