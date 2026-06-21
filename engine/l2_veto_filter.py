"""Hard-constraint veto step: filter occupations by named ExclusionRule."""

from __future__ import annotations

from models import Excluded, ExclusionRule, Industry, Occupation, Ticket, WorkAuthorization


# O*NET-SOC code → Industry, resolved most-specific first. Each code maps to at
# most one Industry, so overlapping sectors are disambiguated by ordering:
# detailed (7-char "XX-XXXX") rules win over minor-group (4-char "XX-X") rules,
# which win over the broad major-group (2-char "XX") fallbacks at the bottom.
#
# Detailed prefixes carve a single occupation out of a broader group, e.g.
# 37-2012 (Maids and Housekeeping Cleaners) → domestic_work, while the rest of
# 37-2 (janitors, building cleaners, pest control) → janitorial_custodial.
_DETAILED_RULES: tuple[tuple[str, Industry], ...] = (
    ("31-9011", Industry.MASSAGE_PARLOR),                # Massage Therapists
    ("37-2012", Industry.DOMESTIC_WORK),                 # Maids and Housekeeping Cleaners
    ("35-2013", Industry.DOMESTIC_WORK),                 # Cooks, Private Household
    ("39-9011", Industry.CHILDCARE),                     # Childcare Workers, Nannies
    ("41-9091", Industry.PEDDLING_DOOR_TO_DOOR_SALES),   # Door-to-Door / street vendors
    ("43-4051", Industry.CALL_CENTER_CUSTOMER_SERVICE),  # Customer Service Representatives
)

_MINOR_RULES: tuple[tuple[str, Industry], ...] = (
    ("31-1", Industry.PERSONAL_CARE_AIDE),          # Home Health / Personal Care Aides, CNAs
    ("31-2", Industry.HEALTHCARE_SUPPORT),          # OT/PT assistants and aides
    ("31-9", Industry.HEALTHCARE_SUPPORT),          # Dental/Medical assistants (massage carved above)
    ("35-2", Industry.RESTAURANT_BACK_OF_HOUSE),    # Cooks (private household carved above)
    ("35-3", Industry.RESTAURANT_FRONT_OF_HOUSE),   # Bartenders, servers, baristas, counter
    ("35-9", Industry.RESTAURANT_BACK_OF_HOUSE),    # Dishwashers, bussers, food-prep helpers
    ("37-2", Industry.JANITORIAL_CUSTODIAL),        # Janitors, building cleaners, pest control
    ("37-3", Industry.LANDSCAPING_GROUNDSKEEPING),  # Landscaping and groundskeeping
    ("39-3", Industry.NIGHTLIFE_ENTERTAINMENT),     # Gambling, gaming, recreation/amusement
    ("39-5", Industry.SALON_NAIL),                  # Barbers, hairdressers, manicurists
    ("43-2", Industry.CALL_CENTER_CUSTOMER_SERVICE),  # Switchboard / telephone operators
    ("53-7", Industry.WAREHOUSING_LOGISTICS),       # Material-moving: conveyor, crane, laborers
)

_MAJOR_RULES: tuple[tuple[str, Industry], ...] = (
    ("35", Industry.HOSPITALITY),       # remaining food service (chefs, supervisors)
    ("39", Industry.HOSPITALITY),       # remaining personal service (concierge, bellhop, tour)
    ("45", Industry.AGRICULTURE),
    ("47", Industry.CONSTRUCTION),
    ("51", Industry.MANUFACTURING),
    ("53", Industry.TRANSPORTATION),    # remaining 53 (drivers, transit) after 53-7 carve-out
)


def _infer_industry(code: str) -> Industry | None:
    """Infer the single Industry an O*NET-SOC code belongs to, or None.

    Resolves most-specific first (detailed → minor → major). Returns None for
    codes that don't fall under any tracked industry.

    Some Industry values are intentionally never returned here because no clean
    SOC code corresponds to them:
      - OTHER: a sentinel paired with a free-text field, not an occupation.
      - BEGGING_PANHANDLING: not formal employment; no SOC code.
      - CARNIVAL_TRAVELING_ENTERTAINMENT: no distinct SOC code (the closest,
        amusement/recreation attendants, falls under 39-3 nightlife above).
      - RETAIL_OVERNIGHT: a shift modifier, not a SOC distinction; daytime and
        overnight retail share the same 41-2 codes (mapped to RETAIL_DAYTIME).
    Selecting any of these as an industry to avoid is recorded on the profile
    but does not drive a code-based veto.
    """
    # 33-9 (Security Guards, crossing guards, etc.) → security_services. The
    # rest of major group 33 (police, fire, corrections) is left unmapped: it
    # isn't an "industry" a survivor would list, and blanketing it would be wrong.
    if code.startswith("33-9"):
        return Industry.SECURITY_SERVICES

    for prefix, industry in _DETAILED_RULES:
        if code.startswith(prefix):
            return industry
    for prefix, industry in _MINOR_RULES:
        if code.startswith(prefix):
            return industry
    # 41-2 (cashiers, retail salespersons, counter clerks) → retail_daytime,
    # after the 41-9091 detailed carve-out above.
    if code.startswith("41-2"):
        return Industry.RETAIL_DAYTIME
    # 43 office/admin fallback, after 43-2 and 43-4051 carve-outs above.
    if code.startswith("43"):
        return Industry.OFFICE_ADMINISTRATIVE
    for prefix, industry in _MAJOR_RULES:
        if code.startswith(prefix):
            return industry
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
