# app/AGENTS.md — Streamlit UI

## Owner
Agent 3 (Surface).

## What this directory owns

```
app/
├── Home.py            # entry page, project framing
├── pages/
│   ├── 1_Profile.py   # caseworker enters / loads a survivor profile
│   ├── 2_Results.py   # ranked candidates with breakdown
│   ├── 3_FilteredOut.py   # excluded candidates with named rules
│   ├── 4_Sensitivity.py   # L5 relaxation report
│   └── 5_LowConfidence.py # L1 mappings under threshold
├── charts/
│   ├── criteria_radar.py
│   ├── wage_range_bar.py
│   └── sensitivity_bar.py
└── copy/
    └── strings.py     # centralized user-facing text for tone review
```

## Hard rules

- Consume only `engine.pipeline.run(ticket: Ticket) -> PipelineResult`. Do not import from `engine/l*.py` directly. Do not reach into engine internals.
- All types imported from `models/`.
- Wage charts compute from BLS data via `data.bls_wage_lookup(onet_code) -> WageRange`. Never hardcode wage values.
- Confidence values render from real signal (cosine, TOPSIS). Never invent.
- No PII in `st.session_state` beyond `ticket_id`. The full `Profile` lives in the DB; the UI fetches it through `db/`, anonymizes via `core/anonymizer.py`, and renders results from `Ticket` + `PipelineResult` only.
- All user-facing copy lives in `app/copy/strings.py`. No bare string literals in page files. This makes tone review possible in one place.
- Caseworker-decides framing: avoid *recommendation*, *best match*, *should*, *will*. Prefer *option*, *candidate*, *consider*, *the caseworker may want to*. The Home page states the framing explicitly.

## Required deliverables (MVP, not stretch)

These are load-bearing demo assets. Do not deprioritize them under time pressure.

1. **Profile entry page** — structured form keyed off the `Profile` schema. Free-text skill capture with citability + safe_framing + source per skill.
2. **Results page** — ranked candidates with `CriteriaBreakdown` rendered as a radar or grouped bar chart per candidate. Each candidate card shows TOPSIS score, fit explanation (from L4), safe resume framings, risk flags, upskill next step, and `WageRange` chart.
3. **Filtered-out panel** — every `ExcludedCandidate` with the named `ExclusionRule` and detail string that excluded it. Filterable by rule.
4. **Sensitivity / relaxation report** — L5 entries as ranked bars, each with `intervention_hint`. Non-actionable entries are visually distinguished but still shown — the caseworker needs to know they exist.
5. **Low-confidence mappings panel** — L1's uncertain skill mappings surfaced for caseworker disambiguation. Each entry shows the raw text and the top-3 candidate O*NET skills with confidence scores.

## Test contract

- E2E test in `tests/integration/test_app_flow.py` runs each synthetic profile through Streamlit's testing API (`AppTest`) and asserts:
  - The Results page renders the expected number of ranked candidates.
  - The FilteredOut panel renders the expected number of excluded candidates.
  - The Sensitivity panel renders the expected top relaxation entries.
  - The LowConfidence panel renders any expected uncertain mappings.
- The same test asserts no PII string from the synthetic profile (`legal_name`, `safe_phone`) appears anywhere in the rendered Results, FilteredOut, or Sensitivity panels.

## Performance

- The first `pipeline.run()` will be slow because the embedding model loads. Show a spinner with a clear message; don't let the page look frozen.
- Cache `pipeline.run(ticket)` by `ticket_id` in `st.session_state` so re-renders don't re-trigger the pipeline.
- Do not call `pipeline.run()` on every widget interaction. Only on explicit "Find candidates" submission.
