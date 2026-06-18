"""Pathway planner — Streamlit entry point.

Layout: top header + two-column body (sidebar context + main tabbed panel).
The three tabs (Candidates / Excluded / Interventions) live inside this
single page; no separate `pages/` directory, no page reloads.

This file ships with a mock PipelineResult so the UI runs end-to-end before
the engine is wired. Surface replaces `_load_mock_result()` with a real
`engine.pipeline.run(ticket)` call once Engine is ready.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import streamlit as st

from models import (
    AvailableShifts,
    Candidate,
    CriteriaBreakdown,
    DocumentationBlockers,
    DocumentsHeld,
    EducationLevel,
    Excluded,
    ExclusionRule,
    GradedConstraints,
    GradedLevel,
    Intervention,
    InterventionReport,
    LegalProfile,
    Language,
    Occupation,
    PipelineResult,
    Skill,
    SkillCitability,
    SkillSource,
    Ticket,
    TrainingAppetite,
    WageRange,
    WorkAuthorization,
)
from app import copy
from app.components import (
    candidate_card,
    empty_state,
    excluded_list,
    header,
    interventions_list,
    sidebar,
)


st.set_page_config(
    page_title="Pathway planner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _inject_styles() -> None:
    """Load the shared CSS once per session."""
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    _inject_styles()

    if "active_ticket" not in st.session_state:
        # Demo: load the mock so the app shows real content out of the box.
        # Surface replaces this with a real load flow.
        st.session_state["active_ticket"], st.session_state["active_name"] = _mock_ticket_and_name()
        st.session_state["pipeline_result"] = _mock_pipeline_result()

    ticket: Ticket | None = st.session_state.get("active_ticket")
    name: str | None = st.session_state.get("active_name")
    result: PipelineResult | None = st.session_state.get("pipeline_result")

    header.render(name)

    if ticket is None or result is None:
        empty_state.render()
        return

    left, right = st.columns([1, 4], gap="medium")
    with left:
        sidebar.render(ticket, name or "")

    with right:
        tab_candidates, tab_excluded, tab_interventions = st.tabs(
            [
                f"{copy.TAB_CANDIDATES} ({len(result.candidates)})",
                f"{copy.TAB_EXCLUDED} ({len(result.excluded)})",
                f"{copy.TAB_INTERVENTIONS} ({len(result.interventions.entries)})",
            ]
        )

        with tab_candidates:
            if result.skills_to_review:
                _render_review_banner(len(result.skills_to_review))
            for i, c in enumerate(result.candidates, start=1):
                if i == 1:
                    candidate_card.render_expanded(c, rank=i)
                else:
                    candidate_card.render_collapsed(c, rank=i)

        with tab_excluded:
            excluded_list.render(result.excluded)

        with tab_interventions:
            interventions_list.render(result.interventions)

    st.markdown(
        f'<p style="text-align: center; color: var(--slate-light); '
        f'font-size: 11px; margin-top: 40px;">{copy.ACCOUNTABILITY}</p>',
        unsafe_allow_html=True,
    )


def _render_review_banner(n: int) -> None:
    text = copy.SKILLS_REVIEW_BANNER.format(n=n) if n == 1 else copy.SKILLS_REVIEW_BANNER_PLURAL.format(n=n)
    st.markdown(
        f'<div class="pp-review-banner">'
        f'  <span>{text}</span>'
        f'  <button class="pp-button-secondary" style="border-color: #C8956A; color: #6E3F12;">{copy.SKILLS_REVIEW_BUTTON}</button>'
        f'</div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# Mock data so the app runs end-to-end before the engine is wired.
# Surface deletes everything below and imports engine.pipeline.run() once
# Engine ships its public interface.
# =============================================================================


def _mock_ticket_and_name() -> tuple[Ticket, str]:
    ticket = Ticket(
        ticket_id="demo-hmac",
        languages=[
            Language(code="en", fluency_1_to_5=1),
            Language(code="so", fluency_1_to_5=2),
        ],
        current_metro="Seattle, WA",
        work_authorization=WorkAuthorization.NO,
        has_vehicle=False,
        has_valid_license=False,
        transit_access=False,
        education_highest=EducationLevel.ASSOCIATES,
        disabilities=["cognitive"],
        dependents=4,
        skills=[
            Skill(
                skill_id="2.A.1.d",
                skill_name="Speaking",
                level_1_to_5=2,
                citability=SkillCitability.TRANSFERABLE,
                safe_framing="Front-of-house customer communication",
                source=SkillSource.EXPLOITATION,
            ),
        ],
        exclusion_zones=[],
        exclusion_industries=[],
        exclusion_employers=[],
        documentation_blockers=DocumentationBlockers(
            requires_clean_record=True,
            requires_drivers_license=True,
            requires_ssn=False,
            requires_credit_check=False,
        ),
        graded_constraints=GradedConstraints(
            night_shift=GradedLevel.TRIGGER,
            isolated_workplace=GradedLevel.TRIGGER,
            customer_facing=GradedLevel.AVOID,
            male_dominated_team=GradedLevel.OK,
            uniformed_role=GradedLevel.OK,
            requires_overnight_travel=GradedLevel.AVOID,
        ),
        max_commute_minutes=24,
        available_shifts=AvailableShifts(morning=True, afternoon=True, evening=False),
        legal_profile=LegalProfile(
            record_categories=[],
            expungement_eligible=[],
            jurisdiction="WA",
        ),
        documents_held=DocumentsHeld(
            state_id=True,
            drivers_license=True,
            ssn=True,
            work_authorization_doc=False,
            passport=True,
            professional_licenses=["food_handler"],
        ),
        industries_of_interest=[],
        wage_minimum_hourly=Decimal("23.05"),
        training_appetite=TrainingAppetite.EXTENSIVE,
        long_term_goal="Find safe, daytime work close to home while continuing therapy.",
    )
    return ticket, "Daniela"


def _mock_pipeline_result() -> PipelineResult:
    occ_records = Occupation(
        code="29-2071.00",
        title="Medical records specialist",
        description="Compile, process, and maintain medical records...",
        median_wage_hourly=Decimal("25.30"),
    )
    occ_csr = Occupation(
        code="43-4051.00",
        title="Customer service representative",
        median_wage_hourly=Decimal("19.40"),
    )
    occ_clerk = Occupation(
        code="43-9061.00",
        title="Office clerk",
        median_wage_hourly=Decimal("18.20"),
    )

    breakdown_records = CriteriaBreakdown(
        skill_match=0.91, wage_fit=0.31, shift_fit=1.00, isolation_fit=0.62,
        customer_facing_fit=0.95, commute_fit=0.85, uniformed_role_fit=1.00,
        male_dominated_fit=0.85, schedule_fit=0.90,
    )
    breakdown_csr = CriteriaBreakdown(
        skill_match=0.82, wage_fit=0.45, shift_fit=0.90, isolation_fit=0.55,
        customer_facing_fit=0.40, commute_fit=0.85, uniformed_role_fit=1.00,
        male_dominated_fit=0.90, schedule_fit=0.85,
    )
    breakdown_clerk = CriteriaBreakdown(
        skill_match=0.74, wage_fit=0.38, shift_fit=0.95, isolation_fit=0.70,
        customer_facing_fit=0.85, commute_fit=0.85, uniformed_role_fit=1.00,
        male_dominated_fit=0.85, schedule_fit=0.85,
    )

    candidates = [
        Candidate(
            occupation=occ_records,
            fit_score=0.84,
            criteria_breakdown=breakdown_records,
            fit_explanation=(
                "Day-shift, structured documentation work with minimal customer "
                "contact. Schedule and commute both align with her constraints. "
                "Wage range starts below her floor — the median clears it, but "
                "verify whether a specific posting is hourly or salaried before "
                "forwarding."
            ),
            safe_resume_framings=[
                "Associates degree, organized records management",
                "Bilingual English / Somali communication",
                "Quality control analysis experience",
            ],
            risk_flags=[
                "Confirm the posting is not remote-only — work-authorization status applies",
            ],
            wage_range=WageRange(
                p10_hourly=Decimal("18.50"),
                p50_hourly=Decimal("25.30"),
                p90_hourly=Decimal("32.10"),
            ),
        ),
        Candidate(
            occupation=occ_csr,
            fit_score=0.79,
            criteria_breakdown=breakdown_csr,
            fit_explanation=(
                "High skill overlap and a fitting schedule, but the customer-facing "
                "rating runs against her stated preference."
            ),
            safe_resume_framings=[
                "Bilingual customer communication",
                "Conflict de-escalation experience",
            ],
            risk_flags=[],
            wage_range=WageRange(
                p10_hourly=Decimal("15.20"),
                p50_hourly=Decimal("19.40"),
                p90_hourly=Decimal("26.80"),
            ),
        ),
        Candidate(
            occupation=occ_clerk,
            fit_score=0.73,
            criteria_breakdown=breakdown_clerk,
            fit_explanation=(
                "Steady office environment, light public contact. Wage range sits "
                "below her floor across all percentiles."
            ),
            safe_resume_framings=[
                "Records organization and clerical experience",
                "Bilingual English / Somali",
            ],
            risk_flags=[],
            wage_range=WageRange(
                p10_hourly=Decimal("14.80"),
                p50_hourly=Decimal("18.20"),
                p90_hourly=Decimal("24.50"),
            ),
        ),
    ]

    excluded = [
        Excluded(
            occupation=Occupation(code="35-3023.00", title="Fast food server"),
            rule=ExclusionRule.INDUSTRY,
            detail="hospitality",
        ),
        Excluded(
            occupation=Occupation(code="53-3032.00", title="Heavy truck driver"),
            rule=ExclusionRule.DOCUMENTATION,
            detail="requires_drivers_license",
        ),
        Excluded(
            occupation=Occupation(code="33-9032.00", title="Security guard"),
            rule=ExclusionRule.CRIMINAL_RECORD,
            detail="prostitution_related",
        ),
    ]

    interventions = InterventionReport(
        entries=[
            Intervention(
                constraint="requires_drivers_license",
                jobs_unlocked=47,
                hint="DMV documentation pathway available through PartnerOrg",
                actionable=True,
            ),
            Intervention(
                constraint="requires_clean_record",
                jobs_unlocked=12,
                hint="Vacatur filing in WA for prostitution-related charges",
                actionable=True,
            ),
            Intervention(
                constraint="industry:hospitality",
                jobs_unlocked=8,
                hint="Excluded for safety; relaxation is not advised",
                actionable=False,
            ),
        ]
    )

    return PipelineResult(
        ticket_id="demo-hmac",
        candidates=candidates,
        excluded=excluded,
        interventions=interventions,
        skills_to_review=[],
    )


if __name__ == "__main__":
    main()
