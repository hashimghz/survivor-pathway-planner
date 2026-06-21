"""Fuzzy MCDA scoring for occupation candidates.

For each surviving occupation, computes a per-criterion fit score in [0, 1] by
mapping the client's graded preferences (trigger / avoid / ok) onto the
occupation's work-context ratings via triangular tolerance bands, then
aggregates the ten criterion scores into one fit score using a TOPSIS
distance-to-ideal formula with domain-tuned weights.

Internal use only. Public entry: ``score(ticket, occupations) -> list[ScoredOccupation]``.
The pipeline orchestrator calls this, and L4 wraps each ScoredOccupation into a
public Candidate.

Algorithm summary
-----------------
1. Per-criterion fit (10 dimensions, each in [0, 1]):
   - Six "graded" criteria map client preference to a tolerance band; an
     occupation attribute above the band penalises fit linearly. The penalty
     slope is steeper for ``trigger`` than for ``avoid``.
   - skill_match: level-weighted overlap of client skills with occupation
     skills.
   - wage_fit: the fraction of an occupation's BLS wage range expected to
     clear the client's hourly floor, approximating wage_pct10-to-pct90 as
     a uniform distribution.
   - commute_fit: stub — the data layer does not currently carry occupation
     location, so this returns 1.0 across the board. Wire up once posting
     locations land.
   - history_fit (next_phase_plan.md §3.6b): mild, uniform deprioritization
     for any occupation the client has a job_history entry for, regardless
     of outcome. Soft signal only — never a hard exclusion (that's a
     deliberate v1 simplification, flagged for revisit later).

2. TOPSIS aggregation:
   For benefit criteria with each score already in [0, 1]:
     d_pos = sqrt( sum w_i * (1 - s_i)^2 )   # distance to positive ideal
     d_neg = sqrt( sum w_i *      s_i^2  )   # distance to negative ideal
     fit   = d_neg / (d_pos + d_neg)

3. Sort by fit descending. L4 consumes the top-N.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from models import CriteriaBreakdown, GradedLevel, Occupation, Ticket

# ---------------------------------------------------------------------------
# Weights — sum to 1.0. Skewed toward skill_match, wage_fit, and isolation
# because those carry the strongest client-safety and economic signal.
# Move to engine/config/topsis_weights.yaml once tuning matters.
#
# `history_fit` (next_phase_plan.md §3.6b) is computed as a proportional
# trim of the original 9, not hardcoded alongside them — `_BASE_WEIGHTS`
# stays the single source of truth for the *relative* importance of the
# original criteria, and `_HISTORY_FIT_WEIGHT` is the only number that
# needs sign-off if this gets retuned later. Computing the trim rather than
# writing out nine more decimal literals also guarantees the sum is exactly
# 1.0 (mod float epsilon) instead of relying on someone's arithmetic.
# ---------------------------------------------------------------------------

_BASE_WEIGHTS: dict[str, float] = {
    "skill_match":         0.20,
    "wage_fit":            0.18,
    "isolation_fit":       0.14,
    "customer_facing_fit": 0.10,
    "shift_fit":           0.10,
    "schedule_fit":        0.08,
    "uniformed_role_fit":  0.07,
    "male_dominated_fit":  0.07,
    "commute_fit":         0.06,
}
assert abs(sum(_BASE_WEIGHTS.values()) - 1.0) < 1e-9, "base TOPSIS weights must sum to 1.0"

_HISTORY_FIT_WEIGHT = 0.08

WEIGHTS: dict[str, float] = {
    name: weight * (1.0 - _HISTORY_FIT_WEIGHT) for name, weight in _BASE_WEIGHTS.items()
}
WEIGHTS["history_fit"] = _HISTORY_FIT_WEIGHT
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "TOPSIS weights must sum to 1.0"


# ---------------------------------------------------------------------------
# Tolerance bands: the upper bound of acceptable exposure to a negative
# attribute, by graded preference level. The "fuzzy" lives here — these
# are the tops of triangular fuzzy numbers; exposure above the bound bleeds
# into the descending slope and reduces fit.
# ---------------------------------------------------------------------------

TOLERANCE: dict[GradedLevel, float] = {
    GradedLevel.TRIGGER: 0.10,
    GradedLevel.AVOID:   0.40,
    GradedLevel.OK:      1.00,
}


@dataclass
class ScoredOccupation:
    """Internal output of L3. Consumed by L4 which wraps in public Candidate."""

    occupation: Occupation
    fit_score: float
    criteria_breakdown: CriteriaBreakdown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exposure_fit(pref: GradedLevel, exposure: float) -> float:
    """Score in [0, 1] from the client's preference and the occupation's exposure.

    Within tolerance, full fit (1.0). Above tolerance, linear decay to 0.0 by
    the time exposure hits 1.0. Tighter tolerance (trigger) ⇒ steeper decay.
    """
    tolerance = TOLERANCE[pref]
    if exposure <= tolerance:
        return 1.0
    span = max(1e-6, 1.0 - tolerance)
    return max(0.0, 1.0 - (exposure - tolerance) / span)


def _normalize_rating(value: float | None, lo: float = 1.0, hi: float = 5.0) -> float:
    """Normalise an O*NET 1-5 rating to [0, 1]. Missing → 0.5 (neutral)."""
    if value is None:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


# ---------------------------------------------------------------------------
# Per-criterion fit functions. Each returns a float in [0, 1].
# ---------------------------------------------------------------------------

def _skill_match(ticket: Ticket, occupation: Occupation) -> float:
    """Skill overlap between the client's skills and the occupation's required skills.

    When L1 mapped_skills are available (from free-text input), computes a
    confidence-weighted Jaccard overlap between the client's mapped O*NET
    skill IDs and the occupation's skill IDs.

    Falls back to the original level-weighted overlap when mapped_skills is
    empty (legacy path using structured Skill objects).
    """
    if not occupation.skills:
        return 0.5

    occ_skill_ids = {s.id for s in occupation.skills}

    # L1 mapped skills path: confidence-weighted overlap
    if ticket.mapped_skills:
        # Build {onet_id: best_confidence} from L1 output, taking the top
        # match per input skill to avoid double-counting.
        client_weights: dict[str, float] = {}
        for entry in ticket.mapped_skills:
            for match in entry.get("matches", []):
                sid = match["onet_id"]
                conf = match["confidence"]
                if sid not in client_weights or conf > client_weights[sid]:
                    client_weights[sid] = conf

        if not client_weights:
            return 0.3  # L1 ran but found no matches — weak signal

        client_ids = set(client_weights.keys())
        intersection = client_ids & occ_skill_ids
        union = client_ids | occ_skill_ids

        if not union:
            return 0.5

        # Weighted Jaccard: sum of confidences for intersecting skills
        # divided by total confidence across the union.
        weighted_inter = sum(client_weights.get(sid, 0.5) for sid in intersection)
        weighted_union = sum(client_weights.get(sid, 0.5) for sid in union)

        return min(1.0, weighted_inter / weighted_union) if weighted_union > 0 else 0.5

    # Legacy path: structured Skill objects with level_1_to_5
    client_levels = {s.skill_id: s.level_1_to_5 for s in ticket.skills}
    matched_levels = sum(client_levels.get(sid, 0) for sid in occ_skill_ids)
    max_possible = 5.0 * len(occ_skill_ids)
    return min(1.0, matched_levels / max_possible)


def _wage_fit(ticket: Ticket, occupation: Occupation) -> float:
    """Fraction of an occupation's wage range expected to clear the client's floor."""
    floor = float(ticket.wage_minimum_hourly)
    p10 = float(occupation.wage_pct10_annual) / 2080 if occupation.wage_pct10_annual else None
    p50 = float(occupation.median_wage_hourly) if occupation.median_wage_hourly else None
    p90 = float(occupation.wage_pct90_annual) / 2080 if occupation.wage_pct90_annual else None

    if p50 is None:
        return 0.5
    if p10 is not None and floor <= p10:
        return 1.0
    if p90 is not None and floor > p90:
        return 0.0
    if p10 is None or p90 is None:
        return 0.7 if floor <= p50 else 0.3
    return max(0.0, min(1.0, (p90 - floor) / (p90 - p10)))


def _isolation_fit(ticket: Ticket, occupation: Occupation) -> float:
    pref = ticket.graded_constraints.isolated_workplace
    exposure = 1.0 if occupation.isolated_workplace else 0.0
    return _exposure_fit(pref, exposure)


def _customer_facing_fit(ticket: Ticket, occupation: Occupation) -> float:
    pref = ticket.graded_constraints.customer_facing
    exposure = _normalize_rating(occupation.public_facing)
    return _exposure_fit(pref, exposure)


def _night_shift_proxy(ticket: Ticket, occupation: Occupation) -> float:
    """night_shift preference against schedule_irregularity (weak but defensible proxy)."""
    pref = ticket.graded_constraints.night_shift
    exposure = _normalize_rating(occupation.schedule_irregularity)
    return _exposure_fit(pref, exposure)


def _shift_fit(ticket: Ticket, occupation: Occupation) -> float:
    """How well the client's available shifts cover an irregular schedule."""
    shifts = ticket.available_shifts
    available = sum([shifts.morning, shifts.afternoon, shifts.evening])
    if available == 0:
        return 0.0
    irreg = _normalize_rating(occupation.schedule_irregularity)
    needed = max(1, math.ceil(3 * irreg))
    return min(1.0, available / needed)


def _commute_fit(ticket: Ticket, occupation: Occupation) -> float:
    """Stub: no posting-location data yet. Default to 1.0 across the board."""
    return 1.0


def _uniformed_role_fit(ticket: Ticket, occupation: Occupation) -> float:
    """No O*NET column for uniform requirements. Penalise slightly on trigger."""
    pref = ticket.graded_constraints.uniformed_role
    return 0.7 if pref == GradedLevel.TRIGGER else 1.0


def _male_dominated_fit(ticket: Ticket, occupation: Occupation) -> float:
    """No O*NET column for team composition. Penalise slightly on trigger."""
    pref = ticket.graded_constraints.male_dominated_team
    return 0.7 if pref == GradedLevel.TRIGGER else 1.0


def _history_fit(occupation: Occupation, history_codes: frozenset[str]) -> float:
    """Mild, uniform deprioritization for a previously-tried occupation.

    next_phase_plan.md §1: "regardless of what the outcome was" — a `hired`
    entry scores the same as a `rejected` one. 0.3 matches the codebase's
    existing "weak signal" convention (see `_skill_match`'s no-match case)
    rather than introducing a new magic number. Soft signal only: this never
    removes an occupation from results, just nudges it down when scores are
    otherwise close.

    `history_codes` is a pre-built set, not `ticket.job_history` directly —
    callers build it once per `score()` call (see below) so this stays an
    O(1) lookup per occupation instead of re-scanning the full history list
    for every one of the ~1,000 occupations being scored.
    """
    return 0.3 if occupation.code in history_codes else 1.0


def _build_breakdown(
    ticket: Ticket,
    occupation: Occupation,
    history_codes: frozenset[str] = frozenset(),
) -> CriteriaBreakdown:
    return CriteriaBreakdown(
        skill_match         = _skill_match(ticket, occupation),
        wage_fit            = _wage_fit(ticket, occupation),
        commute_fit         = _commute_fit(ticket, occupation),
        shift_fit           = _shift_fit(ticket, occupation),
        isolation_fit       = _isolation_fit(ticket, occupation),
        customer_facing_fit = _customer_facing_fit(ticket, occupation),
        uniformed_role_fit  = _uniformed_role_fit(ticket, occupation),
        male_dominated_fit  = _male_dominated_fit(ticket, occupation),
        schedule_fit        = _night_shift_proxy(ticket, occupation),
        history_fit         = _history_fit(occupation, history_codes),
    )


# ---------------------------------------------------------------------------
# TOPSIS aggregation
# ---------------------------------------------------------------------------

def _aggregate(breakdown: CriteriaBreakdown) -> float:
    """Weighted TOPSIS-style score in [0, 1]."""
    scores = {k: getattr(breakdown, k) for k in WEIGHTS}
    d_pos = math.sqrt(sum(WEIGHTS[k] * (1.0 - s) ** 2 for k, s in scores.items()))
    d_neg = math.sqrt(sum(WEIGHTS[k] * s ** 2 for k, s in scores.items()))
    if d_pos + d_neg == 0:
        return 0.0
    return d_neg / (d_pos + d_neg)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def score(ticket: Ticket, occupations: list[Occupation]) -> list[ScoredOccupation]:
    """Score and rank occupations. Output sorted by fit_score descending."""
    # Built once per call, not once per occupation — ticket.job_history is
    # small (a handful of entries at most) and occupations can be ~1,000, so
    # this turns a potential O(occupations × history) scan into O(occupations
    # + history) with an O(1) lookup inside the per-occupation loop.
    history_codes = frozenset(entry.occupation_code for entry in ticket.job_history)

    scored: list[ScoredOccupation] = []
    for occ in occupations:
        breakdown = _build_breakdown(ticket, occ, history_codes)
        fit = _aggregate(breakdown)
        scored.append(
            ScoredOccupation(occupation=occ, fit_score=fit, criteria_breakdown=breakdown)
        )
    scored.sort(key=lambda s: s.fit_score, reverse=True)
    return scored
