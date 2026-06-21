"""LLM explanation step: wrap scored occupations in validated Candidate objects."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import anthropic
from pydantic import ValidationError

from engine.l3_fuzzy_topsis import ScoredOccupation
from engine.vacatur import applicable_pathways
from models import Candidate, HistoryEntrySummary, Occupation, Ticket, WageRange

_HOURS_PER_YEAR = Decimal(2080)
_TWO_PLACES = Decimal("0.01")

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "l4_reasoner.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_REQUIRED_LLM_KEYS = (
    "fit_explanation",
    "safe_resume_framings",
    "risk_flags",
    "upskill_next_step",
)


class LLMSchemaError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""


def _vacatur_pathways_for(ticket: Ticket) -> list[dict]:
    """Vacatur pathways applicable to this ticket's record, if any.

    `LegalProfile` has no `trafficking_related` boolean (the models contract
    is frozen — see models/AGENTS.md). Convention used here, matching
    engine/l5_sensitivity.py: a record counts as trafficking-related when it
    appears in `expungement_eligible`, since that field is documented as
    "subset of record_categories eligible for vacatur."
    """
    legal = ticket.legal_profile
    expungement_eligible = [c.value for c in legal.expungement_eligible]
    return applicable_pathways(
        record_categories=[c.value for c in legal.record_categories],
        expungement_eligible=expungement_eligible,
        jurisdiction=legal.jurisdiction,
        trafficking_related=bool(expungement_eligible),
    )


def _build_profile_payload(ticket: Ticket) -> dict:
    return {
        "current_metro": ticket.current_metro,
        "work_authorization": ticket.work_authorization.value,
        "has_vehicle": ticket.has_vehicle,
        "transit_access": ticket.transit_access,
        "education_highest": ticket.education_highest.value,
        "wage_minimum_hourly": f"${ticket.wage_minimum_hourly:.2f}",
        "available_shifts": ticket.available_shifts.model_dump(mode="json"),
        "max_commute_minutes": ticket.max_commute_minutes,
        "training_appetite": ticket.training_appetite.value,
        "long_term_goal": ticket.long_term_goal,
        "graded_constraints": ticket.graded_constraints.model_dump(mode="json"),
        "documentation_blockers": ticket.documentation_blockers.model_dump(mode="json"),
        "documents_held": ticket.documents_held.model_dump(mode="json"),
        "legal_profile": ticket.legal_profile.model_dump(mode="json"),
        "vacatur_pathways": _vacatur_pathways_for(ticket),
        "skills": [
            {
                "skill_id": skill.skill_id,
                "skill_name": skill.skill_name,
                "level_1_to_5": skill.level_1_to_5,
                "citability": skill.citability.value,
                "safe_framing": skill.safe_framing,
                "source": skill.source.value,
            }
            for skill in ticket.skills
        ],
    }


def _build_candidate_payload(scored: ScoredOccupation, history: list[HistoryEntrySummary]) -> dict:
    """`history` is pre-filtered to this candidate's occupation_code by the
    caller (see `explain()`) — passing the client's *entire* job_history
    into every one of the top-N LLM calls would mean repeating mostly
    irrelevant entries (records for other occupations) in every request,
    larger payloads for no benefit. Filtering once per candidate keeps each
    call's prior_history scoped to what's actually relevant to it.
    """
    occ = scored.occupation
    median = occ.median_wage_hourly
    return {
        "occupation": {
            "code": occ.code,
            "title": occ.title,
            "description": occ.description,
            "median_wage_hourly": float(median) if median is not None else None,
            "wage_pct10_annual": occ.wage_pct10_annual,
            "wage_pct90_annual": occ.wage_pct90_annual,
            "isolated_workplace": occ.isolated_workplace,
            "public_facing": occ.public_facing,
            "schedule_irregularity": occ.schedule_irregularity,
            "violence_exposure": occ.violence_exposure,
            "high_surveillance": occ.high_surveillance,
        },
        "fit_score": scored.fit_score,
        "criteria_breakdown": scored.criteria_breakdown.model_dump(),
        "prior_history": [h.model_dump(mode="json") for h in history],
    }


def _quantize_hourly(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES)


def _compute_wage_range(occupation: Occupation) -> WageRange:
    if occupation.wage_pct10_annual is None:
        raise LLMSchemaError(f"missing wage columns for {occupation.code}: wage_pct10_annual")
    if occupation.median_wage_hourly is None:
        raise LLMSchemaError(f"missing wage columns for {occupation.code}: median_wage_hourly")
    if occupation.wage_pct90_annual is None:
        raise LLMSchemaError(f"missing wage columns for {occupation.code}: wage_pct90_annual")

    p10_hourly = _quantize_hourly(Decimal(str(occupation.wage_pct10_annual)) / _HOURS_PER_YEAR)
    p50_hourly = _quantize_hourly(occupation.median_wage_hourly)
    p90_hourly = _quantize_hourly(Decimal(str(occupation.wage_pct90_annual)) / _HOURS_PER_YEAR)
    return WageRange(p10_hourly=p10_hourly, p50_hourly=p50_hourly, p90_hourly=p90_hourly)


def _strip_code_fences(text: str) -> str:
    """Remove optional markdown code fences wrapping JSON."""
    import re

    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _call_llm(client: anthropic.Anthropic, payload: dict) -> dict:
    user_content = (
        json.dumps(payload)
        + "\n\nRespond with valid JSON only. No preamble, no code fences, "
        "no explanation — start your response with `{` and end with `}`."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_content},
        ],
    )
    raw_text = _strip_code_fences(response.content[0].text)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMSchemaError(f"invalid JSON from LLM: {raw_text}") from exc

    if not isinstance(parsed, dict):
        raise LLMSchemaError(f"expected JSON object from LLM: {raw_text}")

    missing = [key for key in _REQUIRED_LLM_KEYS if key not in parsed]
    if missing:
        raise LLMSchemaError(
            f"missing LLM keys {missing}: {json.dumps(parsed)}"
        )

    return parsed


def explain(
    ticket: Ticket,
    ranked: list[ScoredOccupation],
    top_n: int = 5,
) -> list[Candidate]:
    client = anthropic.Anthropic()
    candidates: list[Candidate] = []

    # Hoisted out of the per-candidate loop: this is profile-level data
    # (skills, constraints, vacatur pathways, etc.) that never changes
    # across the up-to-top_n LLM calls below. It was previously rebuilt
    # from scratch — including a vacatur lookup — on every single
    # iteration, identical result each time. Computing it once here cuts
    # that redundant work without changing what gets sent.
    profile_payload = _build_profile_payload(ticket)

    for scored in ranked:
        if len(candidates) >= top_n:
            break

        # ~3% of occupations in the reference CSV have no BLS wage
        # percentile columns. L3 never filters on this (missing wage data
        # scores as neutral, per engine/AGENTS.md's "scoring step scores; it
        # never filters" rule), so this is the first point in the pipeline
        # where it's safe to drop a candidate — skip it rather than crash
        # the whole results render, and let the next-ranked one take its
        # place in the top-N.
        try:
            wage_range = _compute_wage_range(scored.occupation)
        except LLMSchemaError:
            continue

        relevant_history = [
            h for h in ticket.job_history if h.occupation_code == scored.occupation.code
        ]
        payload = {
            "profile": profile_payload,
            "candidate": _build_candidate_payload(scored, relevant_history),
        }
        llm_json = _call_llm(client, payload)

        try:
            candidates.append(
                Candidate(
                    occupation=scored.occupation,
                    fit_score=scored.fit_score,
                    criteria_breakdown=scored.criteria_breakdown,
                    fit_explanation=llm_json["fit_explanation"],
                    safe_resume_framings=llm_json["safe_resume_framings"],
                    risk_flags=llm_json["risk_flags"],
                    upskill_next_step=llm_json["upskill_next_step"],
                    wage_range=wage_range,
                )
            )
        except ValidationError as exc:
            raise LLMSchemaError(
                f"Candidate validation failed: {json.dumps(llm_json)}"
            ) from exc

    return candidates
