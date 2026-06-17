# engine/AGENTS.md — Pipeline

## Owner
Agent 2 (Engine).

## What this directory owns

```
engine/
├── l1_skill_mapping.py    # free-text skills → O*NET canonical IDs
├── l2_veto_filter.py      # hard-constraint deterministic filter
├── l3_fuzzy_topsis.py     # MCDA scoring over graded criteria
├── l4_llm_reasoner.py     # Claude API call for explanation + safe framing
├── l5_sensitivity.py      # relaxation analysis on excluded set
├── pipeline.py            # orchestrator; public interface
├── prompts/
│   └── l4_reasoner.txt    # versioned prompt template
└── tests/                 # per-layer unit tests
```

## Public interface

The only thing outside this directory may import:

```python
from engine.pipeline import run

result: PipelineResult = run(ticket)
```

Everything else is internal. No `from engine.l3_fuzzy_topsis import ...` from `app/`.

## Hard rules

- Every layer is a **pure function** with a typed signature: `f(ticket_or_input, *deps) -> output_type`. No globals, no module-level state, no surprise I/O.
- All types imported from `models/`. Do not redefine. If a field is missing, raise it in PR review — don't patch around it.
- Load the pre-embedded O*NET catalog from `data/onet_skills.parquet`. Never embed the catalog at runtime in the pipeline.
- Embed only the survivor's free-text skill strings at runtime (small, fast).
- L2 returns `tuple[list[FilteredCandidate], list[ExcludedCandidate]]`. Every entry in the excluded list carries the named `ExclusionRule` that cut it.
- L3 scores; it never filters. A weak score lowers rank, never removes a candidate.
- L4 explains; it never reorders. The top-N L4 sees is the top-N L3 produced.
- L5 runs on L2's excluded set, not on the ranked output. It can run in parallel with L3 in `pipeline.run()`.
- No hard-constraint logic in L3 or L4. Hard constraints were cut in L2 and do not reappear.

## L1 specifics

- Model: `BAAI/bge-small-en-v1.5`, loaded once at module import (singleton).
- Top-1 match per skill against the pre-embedded O*NET catalog via cosine similarity.
- Below 0.6 confidence → `LowConfidenceMapping`, surfaced to UI for caseworker review. Never silently dropped.
- `citability`, `safe_framing`, `source` pass through unchanged from `RawSkill`. L1 does not re-judge what the caseworker entered.

## L2 specifics

- Each hard constraint is a separate function `check_<rule>(occupation, hard_constraints) -> ExcludedCandidate | None`.
- All rules run for each occupation; first failure determines `failed_rule`. Capture the first, not "any".
- The `requires_clean_record` rule consults `LegalProfile.expungement_eligible`: a record category that is eligible for vacatur still excludes today, but L5 will surface it as a relaxation candidate with `intervention_hint="vacatur filing for <category>"`.

## L3 specifics

- Fuzzy TOPSIS, not classic TOPSIS. `trigger` / `avoid` / `ok` levels translate to triangular fuzzy numbers, not scalars.
- Skill match dimension uses O*NET's structured skill importance ratings against `MappedSkill.onet_skill_id` overlap. Not raw embeddings — that's L1's job.
- Weights are loaded from `engine/config/topsis_weights.yaml`. Tunable, but defaults are documented.
- Output preserves the full `CriteriaBreakdown` so the UI can render per-dimension fit, not just the aggregate score.

## L4 specifics

- Model: `claude-sonnet-4-6`.
- `temperature=0`.
- Prompt template in `engine/prompts/l4_reasoner.txt`, versioned. Template variables are inserted via `.format()` — no string concatenation.
- Output validated against `EnrichedCandidate` pydantic schema on parse. Malformed JSON → raise `LLMSchemaError`, do not silently degrade.
- Tests cache LLM responses via `vcrpy` cassettes in `tests/cassettes/l4/`. CI does not hit the live API.
- **No PII in the prompt.** The prompt sees `Ticket` (anonymous) + the ranked candidate's structured fields. If you find yourself reaching for `Profile.legal_name`, stop — the architecture is wrong.

## L5 specifics

- For each hard constraint present in the ticket, recompute L2 with that constraint relaxed and count the delta in surviving candidates.
- Each entry carries an `actionable` boolean — safety-critical constraints (industry exclusions, exclusion zones) are not actionable and L5 says so explicitly.
- Sort entries by `jobs_unlocked` descending.

## Test contract

- Each layer has a unit test that loads a golden ticket from `fixtures/golden_outputs/` and asserts the layer's output matches the golden output for that stage.
- `pipeline.run()` has an integration test that runs the full chain on each synthetic profile and matches `PipelineResult` against the golden final output.
- Tests marked `@pytest.mark.unit` are pre-commit-fast (<5s total). No LLM, no embedding model load.
- Tests marked `@pytest.mark.integration` may use cached LLM responses but run end-to-end.
- Embedding model and LLM client are injected, not imported globally inside test files — keeps unit tests fast.
