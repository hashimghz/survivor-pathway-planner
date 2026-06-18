"""Public pipeline entry point: veto, score, explain, sensitivity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from data.loader import load_occupations
from engine.l2_veto_filter import apply_veto
from engine.l3_fuzzy_topsis import score
from engine.l4_llm_reasoner import explain
from engine.l5_sensitivity import compute
from models import PipelineResult, Ticket


def run(ticket: Ticket) -> PipelineResult:
    occupations = load_occupations()
    passed, excluded = apply_veto(ticket, occupations)

    with ThreadPoolExecutor(max_workers=2) as executor:
        ranked_future = executor.submit(score, ticket, passed)
        interventions_future = executor.submit(compute, ticket, excluded, occupations)
        ranked = ranked_future.result()
        interventions = interventions_future.result()

    candidates = explain(ticket, ranked, top_n=5)

    return PipelineResult(
        ticket_id=ticket.ticket_id,
        candidates=candidates,
        excluded=excluded,
        interventions=interventions,
        skills_to_review=[],
    )