# Pathway planner

A decision-support tool for caseworkers supporting trafficking survivors. Matches survivors to occupations while respecting safety, legal, and economic constraints. The caseworker decides; this tool surfaces options.

## Background

Trafficking survivors face compounding barriers when seeking economic stability: trauma-shaped constraints around work environment and schedule, legal complications (criminal records often acquired during exploitation), missing documentation, and wage requirements that low-wage retail can't meet. Existing job-matching tools optimize for placement metrics, not survivor agency.

This tool inverts that. It treats the caseworker as the decision-maker, surfaces ranked options with explicit safety and economic tradeoffs, and shows what specific interventions — vacatur filings, DMV pathways, T-visa applications — would unlock more options.

Built for the USAII Global AI Hackathon 2026, "AI for Systems & Society" track, Brief 5 (Safe Passage / Survivor Care), Direction B.

## How it works

Given an anonymized survivor profile, the system:

1. **Filters** out occupations that violate hard constraints — excluded industries, missing documentation, criminal-record requirements, wage floor. Each exclusion records the named rule that cut it.
2. **Scores** the surviving occupations on nine dimensions (skill match, wage fit, isolation, customer-facing intensity, schedule alignment, and more), using a fuzzy MCDA approach with TOPSIS distance-to-ideal aggregation.
3. **Explains** the top candidates with Claude — generating fit prose, safe resume framings (respecting the caseworker's citability calls on each skill), and risk flags worth verifying before forwarding a posting.
4. **Analyzes** what specific changes would unlock more options — separating actionable interventions from non-actionable safety exclusions.

The UI presents results across three tabs: Candidates, Excluded, Interventions. The caseworker reads them and decides what to discuss with the survivor.

## Architecture


PII (legal name, phone, DOB) is encrypted at rest. The pipeline operates on anonymous Tickets — the LLM prompt never sees identity fields.

## Stack

- Python 3.12 with uv and ruff
- Streamlit and Plotly for the UI
- Pydantic v2 for contracts
- SQLite + `cryptography` for encrypted persistence
- Anthropic Claude (Sonnet 4.6, temperature 0, JSON-enforced output) for explanations
- Docker for reproducible runs

## Running

### Prerequisites

- Docker
- An Anthropic API key

### Set up

Generate two 32-byte secrets for at-rest encryption and ticket-ID derivation:

```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Run twice. Put the outputs in `.env`:
```
PATHWAY_AES_KEY=<first output>
PATHWAY_HMAC_PEPPER=<second output>
ANTHROPIC_API_KEY=<your Anthropic key>
```

### Launch

```bash
docker compose up --build
```

Open `http://localhost:8501`.

The app loads with a demo profile (Daniela). She has `work_authorization=no`, so every occupation is filtered — which makes the Interventions tab the most interesting view: it surfaces "T-visa application; refer to PartnerOrg" as the highest-leverage caseworker action. To see the candidates pipeline at full strength, switch to another synthetic profile via the load flow.

## Design principles

- **The caseworker decides.** Every string in the UI avoids "recommend," "best match," "you should." Instead: "candidate," "consider," "worth verifying." The caseworker is responsible for the recommendation; this tool is responsible for surfacing tradeoffs.
- **No surveillance.** This is decision support, not behavioral tracking. The threat model treats the survivor as the person being protected.
- **PII stays encrypted.** Identity fields are encrypted at rest. The pipeline operates on anonymous tickets. The LLM never sees names.
- **Excluded is honest.** Every filtered occupation appears in the Excluded tab with the named rule that cut it. No silent ranking-down.
- **Interventions show leverage.** Where a single constraint change would unlock many options, and the change is something a caseworker can actually pursue, the Interventions tab names it.

## Data

- **O*NET occupations** (988 SOC codes) enriched with BLS wage percentiles (p10, median, p90) and O*NET work-context ratings (contact_with_others, physical_proximity, violence_exposure, public_facing, schedule_irregularity).
- **Synthetic survivor profiles** for development. No real survivor data is in this repo.

## Status

Hackathon-stage prototype.