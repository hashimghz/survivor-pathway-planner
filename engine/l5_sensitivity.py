"""Sensitivity analysis: what would unlock more options if a constraint changed."""

from __future__ import annotations

from decimal import Decimal

from engine.l2_veto_filter import apply_veto
from engine.vacatur import applicable_pathways
from models import (
    Excluded,
    ExclusionRule,
    Industry,
    Intervention,
    InterventionReport,
    Occupation,
    Ticket,
    WorkAuthorization,
)


def _filter_rule(excluded: list[Excluded], rule: ExclusionRule) -> list[Excluded]:
    return [entry for entry in excluded if entry.rule == rule]


def _clean_record_hint(ticket: Ticket) -> str:
    """Hint for the requires_clean_record intervention.

    `LegalProfile` has no `trafficking_related` boolean (the models contract
    is frozen — see models/AGENTS.md). Convention used here instead: a
    record category counts as trafficking-related when it appears in
    `expungement_eligible`, since that field is documented as "subset of
    record_categories eligible for vacatur." Surface this convention if a
    contract change ever adds a real field.
    """
    legal = ticket.legal_profile
    record_categories = [c.value for c in legal.record_categories]
    expungement_eligible = [c.value for c in legal.expungement_eligible]
    trafficking_related = bool(expungement_eligible)

    pathways = applicable_pathways(
        record_categories=record_categories,
        expungement_eligible=expungement_eligible,
        jurisdiction=legal.jurisdiction,
        trafficking_related=trafficking_related,
    )
    if pathways:
        pathway = pathways[0]
        return f"Vacatur pathway available: {pathway['statute']} — {pathway['next_step']}"
    if expungement_eligible:
        return "Record sealing or expungement may apply — verify with local legal aid."
    return "Discuss documentation requirements with the survivor."


def _truly_unlocked(ticket: Ticket, candidates: list[Excluded], relax: dict) -> int:
    """How many of `candidates` would actually clear the veto if `relax` fixed.

    `apply_veto()` is first-match-wins: each excluded occupation only ever
    records the *first* rule that fired, in a fixed check order (industry,
    documentation, work_authorization, criminal_record, wage_floor). An
    occupation recorded under `requires_drivers_license` may also fail, say,
    the wage floor or the clean-record check — relaxing the license
    requirement alone would not actually unlock it. Naively counting
    `excluded` entries by their single recorded reason overstates each
    constraint's real impact (next_phase_plan.md §3.5).

    The honest way to answer "how many jobs would this intervention unlock"
    is to simulate the fix — build a copy of the ticket with only this one
    constraint relaxed — and re-run the full veto on just the occupations
    currently excluded for that reason. Anything still excluded by some
    *other* rule was never truly blocked by this constraint alone.
    """
    if not candidates:
        return 0
    relaxed_ticket = ticket.model_copy(update=relax)
    occupations = [entry.occupation for entry in candidates]
    kept, _ = apply_veto(relaxed_ticket, occupations)
    return len(kept)


def compute(
    ticket: Ticket,
    excluded: list[Excluded],
    occupations: list[Occupation],
) -> InterventionReport:
    del occupations

    blockers = ticket.documentation_blockers

    drivers_license_candidates = [
        entry
        for entry in excluded
        if entry.rule == ExclusionRule.DOCUMENTATION and entry.detail == "requires_drivers_license"
    ]
    ssn_candidates = [
        entry
        for entry in excluded
        if entry.rule == ExclusionRule.DOCUMENTATION and entry.detail == "requires_ssn"
    ]
    record_candidates = _filter_rule(excluded, ExclusionRule.CRIMINAL_RECORD)
    work_auth_candidates = _filter_rule(excluded, ExclusionRule.WORK_AUTHORIZATION)
    wage_candidates = _filter_rule(excluded, ExclusionRule.WAGE_FLOOR)

    entries: list[Intervention] = [
        Intervention(
            constraint="requires_drivers_license",
            jobs_unlocked=_truly_unlocked(
                ticket,
                drivers_license_candidates,
                {
                    "documentation_blockers": blockers.model_copy(
                        update={"requires_drivers_license": False}
                    )
                },
            ),
            hint="DMV documentation pathway",
            actionable=True,
        ),
        Intervention(
            constraint="requires_ssn",
            jobs_unlocked=_truly_unlocked(
                ticket,
                ssn_candidates,
                {"documentation_blockers": blockers.model_copy(update={"requires_ssn": False})},
            ),
            hint="SSA replacement pathway",
            actionable=True,
        ),
        Intervention(
            constraint="requires_clean_record",
            jobs_unlocked=_truly_unlocked(
                ticket,
                record_candidates,
                {
                    "documentation_blockers": blockers.model_copy(
                        update={"requires_clean_record": False}
                    )
                },
            ),
            hint=_clean_record_hint(ticket),
            actionable=True,
        ),
        Intervention(
            constraint="work_authorization",
            jobs_unlocked=_truly_unlocked(
                ticket,
                work_auth_candidates,
                {"work_authorization": WorkAuthorization.YES},
            ),
            hint="T-visa application; refer to PartnerOrg",
            actionable=True,
        ),
        Intervention(
            constraint="wage_minimum_hourly",
            jobs_unlocked=_truly_unlocked(
                ticket,
                wage_candidates,
                {"wage_minimum_hourly": Decimal("0")},
            ),
            hint="Discuss wage floor flexibility with survivor",
            actionable=True,
        ),
    ]

    for industry in ticket.exclusion_industries:
        # OTHER is a free-text sentinel, not a SOC-backed industry — nothing is
        # ever excluded under it, so it would only emit a noisy "0 options" row.
        if industry == Industry.OTHER:
            continue
        industry_candidates = [
            entry
            for entry in excluded
            if entry.rule == ExclusionRule.INDUSTRY and entry.detail == industry.value
        ]
        entries.append(
            Intervention(
                constraint=f"industry:{industry.value}",
                jobs_unlocked=_truly_unlocked(
                    ticket,
                    industry_candidates,
                    {
                        "exclusion_industries": [
                            i for i in ticket.exclusion_industries if i != industry
                        ]
                    },
                ),
                hint="Excluded for safety; relaxation not advised",
                actionable=False,
            )
        )

    if ticket.exclusion_zones:
        zone_candidates = _filter_rule(excluded, ExclusionRule.GEOGRAPHY)
        entries.append(
            Intervention(
                constraint="exclusion_zones",
                # NOTE: apply_veto() has no geography check at all today — see
                # docstring above engine.l2_veto_filter.apply_veto and the
                # final-sweep note in next_phase_plan.md. ExclusionRule.GEOGRAPHY
                # is structurally unreachable (Occupation carries no lat/lng),
                # so zone_candidates is always [] and this is always 0 — not a
                # bug introduced by this fix, just an honest reflection that
                # the underlying check doesn't exist yet.
                jobs_unlocked=_truly_unlocked(ticket, zone_candidates, {"exclusion_zones": []}),
                hint="Geographic exclusion; relaxation not advised",
                actionable=False,
            )
        )

    entries.sort(key=lambda entry: entry.jobs_unlocked, reverse=True)
    return InterventionReport(entries=entries)
