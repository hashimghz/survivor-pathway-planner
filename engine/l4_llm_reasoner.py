"""LLM explanation step: wrap scored occupations in validated Candidate objects."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import anthropic
from pydantic import ValidationError

from engine.l3_fuzzy_topsis import ScoredOccupation
from models import Candidate, Occupation, Ticket, WageRange

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


def _build_candidate_payload(scored: ScoredOccupation) -> dict:
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


def _call_llm(client: anthropic.Anthropic, payload: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": json.dumps(payload)},
            {"role": "assistant", "content": "{"},
        ],
    )
    raw_text = "{" + response.content[0].text
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

    for scored in ranked[:top_n]:
        payload = {
            "profile": _build_profile_payload(ticket),
            "candidate": _build_candidate_payload(scored),
        }
        llm_json = _call_llm(client, payload)
        wage_range = _compute_wage_range(scored.occupation)

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
