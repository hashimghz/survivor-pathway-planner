"""Hard-constraint veto step: filter occupations by named ExclusionRule."""

from __future__ import annotations

from models import Excluded, ExclusionRule, Industry, Occupation, Ticket, WorkAuthorization


def _infer_industry(code: str) -> Industry | None:
    if code.startswith("39-9011"):
        return Industry.DOMESTIC_WORK
    major = code[:2]
    if major in ("35", "39"):
        return Industry.HOSPITALITY
    if major == "53":
        return Industry.TRANSPORTATION
    if major == "45":
        return Industry.AGRICULTURE
    return None


def _check_industry(ticket: Ticket, occupation: Occupation) -> ExclusionRule | None:
    inferred = _infer_industry(occupation.code)
    if inferred is not None and inferred in ticket.exclusion_industries:
        return ExclusionRule.INDUSTRY
    return None


def _check_documentation(ticket: Ticket, occupation: Occupation) -> ExclusionRule | None:
    del occupation
    if (
        ticket.documentation_blockers.requires_drivers_license
        and not ticket.documents_held.drivers_license
    ):
        return ExclusionRule.DOCUMENTATION
    if ticket.documentation_blockers.requires_ssn and not ticket.documents_held.ssn:
        return ExclusionRule.DOCUMENTATION
    return None


def _check_work_authorization(ticket: Ticket, occupation: Occupation) -> ExclusionRule | None:
    del occupation
    if ticket.work_authorization == WorkAuthorization.NO:
        return ExclusionRule.WORK_AUTHORIZATION
    return None


def _check_criminal_record(ticket: Ticket, occupation: Occupation) -> ExclusionRule | None:
    del occupation
    if (
        ticket.documentation_blockers.requires_clean_record
        and ticket.legal_profile.record_categories
    ):
        return ExclusionRule.CRIMINAL_RECORD
    return None


def _check_wage_floor(ticket: Ticket, occupation: Occupation) -> ExclusionRule | None:
    median = occupation.median_wage_hourly
    if median is not None and median < ticket.wage_minimum_hourly:
        return ExclusionRule.WAGE_FLOOR
    return None


def _exclusion_detail(
    rule: ExclusionRule,
    ticket: Ticket,
    occupation: Occupation,
) -> str:
    if rule == ExclusionRule.INDUSTRY:
        inferred = _infer_industry(occupation.code)
        assert inferred is not None
        return inferred.value
    if rule == ExclusionRule.DOCUMENTATION:
        if (
            ticket.documentation_blockers.requires_drivers_license
            and not ticket.documents_held.drivers_license
        ):
            return "requires_drivers_license"
        return "requires_ssn"
    if rule == ExclusionRule.WORK_AUTHORIZATION:
        return "no work auth"
    if rule == ExclusionRule.CRIMINAL_RECORD:
        return ticket.legal_profile.record_categories[0].value
    median = occupation.median_wage_hourly
    assert median is not None
    floor = ticket.wage_minimum_hourly
    return f"median ${float(median):.2f} < floor ${float(floor):.2f}"


def apply_veto(
    ticket: Ticket,
    occupations: list[Occupation],
) -> tuple[list[Occupation], list[Excluded]]:
    kept: list[Occupation] = []
    excluded: list[Excluded] = []

    checks = (
        _check_industry,
        _check_documentation,
        _check_work_authorization,
        _check_criminal_record,
        _check_wage_floor,
    )

    for occupation in occupations:
        rule: ExclusionRule | None = None
        for check in checks:
            rule = check(ticket, occupation)
            if rule is not None:
                break

        if rule is None:
            kept.append(occupation)
        else:
            excluded.append(
                Excluded(
                    occupation=occupation,
                    rule=rule,
                    detail=_exclusion_detail(rule, ticket, occupation),
                )
            )

    return kept, excluded
