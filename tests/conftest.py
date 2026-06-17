"""Shared pytest fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest

from models import (
    DocumentationStatus,
    EducationLevel,
    Goals,
    GradedConstraintLevel,
    GradedConstraints,
    HardConstraints,
    LegalProfile,
    RawSkill,
    Shift,
    SkillCitability,
    SkillSource,
    StabilityNeeds,
    Ticket,
    TrainingAppetite,
    WorkAuthorization,
)


@pytest.fixture
def stub_ticket() -> Ticket:
    """Minimal anonymous ticket for integration smoke tests."""
    return Ticket(
        ticket_id="stub-ticket-001",
        skills_raw=[
            RawSkill(
                skill_id="skill-001",
                text="customer service",
                level_1_to_5=3,
                citability=SkillCitability.TRANSFERABLE,
                safe_framing="Provided customer support in a retail environment",
                source=SkillSource.PRIOR_EMPLOYMENT,
            )
        ],
        languages=[],
        current_metro="Tampa, FL",
        education_highest=EducationLevel.HIGH_SCHOOL_OR_GED,
        hard_constraints=HardConstraints(
            work_authorization=WorkAuthorization.YES,
            has_vehicle=False,
            has_valid_license=False,
            transit_access=True,
            requires_clean_record=False,
            requires_drivers_license=False,
            requires_ssn=True,
            requires_credit_check=False,
        ),
        graded_constraints=GradedConstraints(
            night_shift=GradedConstraintLevel.AVOID,
            isolated_workplace=GradedConstraintLevel.AVOID,
            customer_facing=GradedConstraintLevel.OK,
            male_dominated_team=GradedConstraintLevel.OK,
            uniformed_role=GradedConstraintLevel.AVOID,
        ),
        stability_needs=StabilityNeeds(
            requires_overnight_travel=GradedConstraintLevel.TRIGGER,
            max_commute_minutes=45,
            available_shifts=[Shift.MORNING],
            wage_minimum_hourly=Decimal("15.00"),
        ),
        legal_profile=LegalProfile(jurisdiction="FL"),
        documentation_status=DocumentationStatus(
            state_id=True,
            drivers_license=False,
            ssn=True,
            work_authorization_doc=True,
            passport=False,
        ),
        goals=Goals(training_appetite=TrainingAppetite.SHORT_COURSE),
    )
