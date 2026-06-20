"""Official demo/test profiles — for at-a-glance viewing only.

These three Tickets correspond exactly to the three test profiles defined in
the project handoff (Section 6): Baseline, Vacatur differentiator, and Heavy
constraints (stress test). They exist so anyone can see the engine working
without filling out the intake form first.

They are NOT the product's primary flow. The primary flow is a caseworker
submitting a real survivor through `app/pages/Profile.py`. The UI must always
make clear when one of these is loaded (see `is_sample` flag usage in
app/Home.py) so it's never mistaken for a real intake.

A few of the handoff's narrative details don't have a dedicated field on the
Ticket model (max weekly hours, shelter days remaining, "HS diploma" as
distinct from "some high school", a trafficking-related boolean on
LegalProfile). Where that happened, the closest available field or enum value
was used and noted in a comment below. None of these are blocking — they're
flagged here for whoever does the Phase 7 vacatur build, since
`trafficking_related` in particular will need either a real model field or a
documented convention (this file uses: trafficking-related ⇒ every category
in `record_categories` is also listed in `expungement_eligible`).
"""

from __future__ import annotations

from decimal import Decimal

from models import (
    AvailableShifts,
    DocumentationBlockers,
    DocumentsHeld,
    EducationLevel,
    GradedConstraints,
    GradedLevel,
    Industry,
    Language,
    LegalProfile,
    RecordCategory,
    Ticket,
    TrainingAppetite,
    WorkAuthorization,
)


def _baseline() -> Ticket:
    """Profile 1 — low constraints, marketable skills. Broad match expected."""
    return Ticket(
        ticket_id="demo-baseline",
        languages=[Language(code="en", fluency_1_to_5=5)],
        current_metro="Tampa, FL",
        work_authorization=WorkAuthorization.YES,
        has_vehicle=True,
        has_valid_license=True,
        transit_access=True,
        # No "completed HS diploma" enum value exists distinct from SOME_HS;
        # SOME_HS is the closest available option.
        education_highest=EducationLevel.SOME_HS,
        disabilities=[],
        dependents=0,
        skills=[],
        existing_skills=[
            "customer service",
            "food preparation",
            "basic Spanish",
            "cash handling",
        ],
        exclusion_zones=[],
        exclusion_industries=[],
        exclusion_employers=[],
        documentation_blockers=DocumentationBlockers(
            requires_clean_record=False,
            requires_drivers_license=False,
            requires_ssn=False,
            requires_credit_check=False,
        ),
        graded_constraints=GradedConstraints(
            night_shift=GradedLevel.OK,
            isolated_workplace=GradedLevel.OK,
            customer_facing=GradedLevel.OK,
            male_dominated_team=GradedLevel.OK,
            uniformed_role=GradedLevel.OK,
            requires_overnight_travel=GradedLevel.OK,
        ),
        max_commute_minutes=45,
        available_shifts=AvailableShifts(morning=True, afternoon=True, evening=True),
        legal_profile=LegalProfile(
            record_categories=[],
            expungement_eligible=[],
            jurisdiction="FL",
        ),
        documents_held=DocumentsHeld(
            state_id=True,
            drivers_license=True,
            ssn=True,
            work_authorization_doc=True,
            passport=False,
        ),
        industries_of_interest=[],
        wage_minimum_hourly=Decimal("15.00"),
        training_appetite=TrainingAppetite.MODERATE,
        long_term_goal="Find stable, daytime work in the Tampa area.",
    )


def _vacatur() -> Ticket:
    """Profile 2 — criminal record + vacatur differentiator.

    requires_clean_record is left False here (rather than vetoing every
    occupation outright) so L3/L4 still produce a ranked match set; the
    finer-grained "this specific occupation needs a background check" signal
    is what Phase 7 is meant to add, not a blanket L2 veto.
    """
    return Ticket(
        ticket_id="demo-vacatur",
        languages=[Language(code="en", fluency_1_to_5=5)],
        current_metro="Tampa, FL",
        work_authorization=WorkAuthorization.YES,
        has_vehicle=False,
        has_valid_license=False,
        transit_access=True,
        education_highest=EducationLevel.GED,
        disabilities=[],
        dependents=1,
        skills=[],
        existing_skills=["cosmetology", "hair braiding", "social media", "retail"],
        exclusion_zones=[],
        exclusion_industries=[],
        exclusion_employers=[],
        documentation_blockers=DocumentationBlockers(
            requires_clean_record=False,
            requires_drivers_license=False,
            requires_ssn=False,
            requires_credit_check=False,
        ),
        graded_constraints=GradedConstraints(
            night_shift=GradedLevel.OK,
            isolated_workplace=GradedLevel.TRIGGER,
            customer_facing=GradedLevel.OK,
            male_dominated_team=GradedLevel.TRIGGER,
            uniformed_role=GradedLevel.OK,
            requires_overnight_travel=GradedLevel.TRIGGER,
        ),
        max_commute_minutes=30,
        available_shifts=AvailableShifts(morning=True, afternoon=True, evening=False),
        legal_profile=LegalProfile(
            record_categories=[
                RecordCategory.PROSTITUTION_RELATED,
                RecordCategory.THEFT_PROPERTY,
            ],
            # Convention: trafficking-related records are listed here too,
            # since both categories stem from the trafficking situation and
            # FL §943.0583 covers them. See module docstring.
            expungement_eligible=[
                RecordCategory.PROSTITUTION_RELATED,
                RecordCategory.THEFT_PROPERTY,
            ],
            jurisdiction="FL",
        ),
        documents_held=DocumentsHeld(
            state_id=True,
            drivers_license=False,
            ssn=True,
            work_authorization_doc=True,
            passport=False,
        ),
        industries_of_interest=[Industry.SALON_NAIL],
        wage_minimum_hourly=Decimal("18.00"),
        training_appetite=TrainingAppetite.MODERATE,
        long_term_goal="Work toward steady income while exploring cosmetology licensure.",
    )


def _heavy_constraints() -> Ticket:
    """Profile 3 — stress test. Match set should shrink dramatically.

    No dedicated field exists for "max 20 hours/week" or "90 days of shelter
    housing remaining"; the former is approximated via limited available
    shifts, the latter is folded into long_term_goal as context text.
    """
    return Ticket(
        ticket_id="demo-heavy-constraints",
        languages=[
            Language(code="ru", fluency_1_to_5=5),
            Language(code="en", fluency_1_to_5=2),
        ],
        current_metro="Tampa, FL",
        work_authorization=WorkAuthorization.IN_PROCESS,
        has_vehicle=False,
        has_valid_license=False,
        transit_access=False,
        education_highest=EducationLevel.NONE,
        disabilities=[
            "Chronic back pain (15 lb lift limit)",
            "PTSD (in treatment)",
        ],
        dependents=2,
        skills=[],
        existing_skills=[
            "housekeeping",
            "eldercare",
            "sewing",
            "conversational Russian",
        ],
        exclusion_zones=[],
        exclusion_industries=[],
        exclusion_employers=[],
        documentation_blockers=DocumentationBlockers(
            requires_clean_record=False,
            requires_drivers_license=False,
            requires_ssn=False,
            requires_credit_check=False,
        ),
        graded_constraints=GradedConstraints(
            night_shift=GradedLevel.AVOID,
            isolated_workplace=GradedLevel.OK,
            customer_facing=GradedLevel.AVOID,
            male_dominated_team=GradedLevel.OK,
            uniformed_role=GradedLevel.OK,
            requires_overnight_travel=GradedLevel.TRIGGER,
        ),
        max_commute_minutes=20,
        available_shifts=AvailableShifts(morning=True, afternoon=False, evening=False),
        legal_profile=LegalProfile(
            record_categories=[],
            expungement_eligible=[],
            jurisdiction="FL",
        ),
        documents_held=DocumentsHeld(
            state_id=False,
            drivers_license=False,
            ssn=False,
            work_authorization_doc=False,
            passport=True,
        ),
        industries_of_interest=[Industry.DOMESTIC_WORK],
        wage_minimum_hourly=Decimal("15.00"),
        training_appetite=TrainingAppetite.SHORT,
        long_term_goal=(
            "Secure steady part-time income while T-visa processing and PTSD "
            "treatment continue; currently in shelter housing with limited "
            "time remaining."
        ),
    )


# (key, display label, display name, ticket-builder) — in handoff Section 6 order.
DEMO_PROFILES: list[tuple[str, str, str, Ticket]] = [
    (
        "baseline",
        "Baseline — broad match",
        "Sample: Baseline",
        _baseline(),
    ),
    (
        "vacatur",
        "Criminal record + vacatur",
        "Sample: Vacatur pathway",
        _vacatur(),
    ),
    (
        "heavy_constraints",
        "Heavy constraints — stress test",
        "Sample: Heavy constraints",
        _heavy_constraints(),
    ),
]
