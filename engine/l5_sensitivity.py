"""Sensitivity analysis: what would unlock more options if a constraint changed."""

from __future__ import annotations

from models import (
    Excluded,
    ExclusionRule,
    Industry,
    Intervention,
    InterventionReport,
    Occupation,
    Ticket,
)


def _count_documentation(excluded: list[Excluded], detail: str) -> int:
    return sum(
        1
        for entry in excluded
        if entry.rule == ExclusionRule.DOCUMENTATION and entry.detail == detail
    )


def _count_rule(excluded: list[Excluded], rule: ExclusionRule) -> int:
    return sum(1 for entry in excluded if entry.rule == rule)


def _count_industry(excluded: list[Excluded], industry: Industry) -> int:
    return sum(
        1
        for entry in excluded
        if entry.rule == ExclusionRule.INDUSTRY and entry.detail == industry.value
    )


def _clean_record_hint(ticket: Ticket) -> str:
    if ticket.legal_profile.expungement_eligible:
        return "Vacatur filing for prostitution-related charges"
    return "Record sealing may apply"


def compute(
    ticket: Ticket,
    excluded: list[Excluded],
    occupations: list[Occupation],
) -> InterventionReport:
    del occupations

    entries: list[Intervention] = [
        Intervention(
            constraint="requires_drivers_license",
            jobs_unlocked=_count_documentation(excluded, "requires_drivers_license"),
            hint="DMV documentation pathway",
            actionable=True,
        ),
        Intervention(
            constraint="requires_ssn",
            jobs_unlocked=_count_documentation(excluded, "requires_ssn"),
            hint="SSA replacement pathway",
            actionable=True,
        ),
        Intervention(
            constraint="requires_clean_record",
            jobs_unlocked=_count_rule(excluded, ExclusionRule.CRIMINAL_RECORD),
            hint=_clean_record_hint(ticket),
            actionable=True,
        ),
        Intervention(
            constraint="work_authorization",
            jobs_unlocked=_count_rule(excluded, ExclusionRule.WORK_AUTHORIZATION),
            hint="T-visa application; refer to PartnerOrg",
            actionable=True,
        ),
        Intervention(
            constraint="wage_minimum_hourly",
            jobs_unlocked=_count_rule(excluded, ExclusionRule.WAGE_FLOOR),
            hint="Discuss wage floor flexibility with survivor",
            actionable=True,
        ),
    ]

    for industry in ticket.exclusion_industries:
        entries.append(
            Intervention(
                constraint=f"industry:{industry.value}",
                jobs_unlocked=_count_industry(excluded, industry),
                hint="Excluded for safety; relaxation not advised",
                actionable=False,
            )
        )

    if ticket.exclusion_zones:
        entries.append(
            Intervention(
                constraint="exclusion_zones",
                jobs_unlocked=_count_rule(excluded, ExclusionRule.GEOGRAPHY),
                hint="Geographic exclusion; relaxation not advised",
                actionable=False,
            )
        )

    entries.sort(key=lambda entry: entry.jobs_unlocked, reverse=True)
    return InterventionReport(entries=entries)
