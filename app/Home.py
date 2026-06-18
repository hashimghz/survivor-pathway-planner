"""Pathway planner — Streamlit entry point.

Layout: top header + two-column body (sidebar context + main tabbed panel).
The three tabs (Candidates / Excluded / Interventions) live inside this
single page; no separate `pages/` directory, no page reloads.

This file ships with a mock PipelineResult so the UI runs end-to-end before
the engine is wired. Surface replaces `_load_mock_result()` with a real
`engine.pipeline.run(ticket)` call once Engine is ready.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from decimal import Decimal

import streamlit as st

from app import copy

from app.components import (
    candidate_card,
    empty_state,
    excluded_list,
    header,
    interventions_list,
    sidebar,
)
from models import (
    AvailableShifts,
    DocumentationBlockers,
    DocumentsHeld,
    EducationLevel,
    GradedConstraints,
    GradedLevel,
    Language,
    LegalProfile,
    PipelineResult,
    Skill,
    SkillCitability,
    SkillSource,
    Ticket,
    TrainingAppetite,
    WorkAuthorization,
)
from engine.pipeline import run as run_pipeline

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

    # First load: seed demo profile so the UI has something to show.
    if "active_ticket" not in st.session_state:
        ticket_seed, name_seed = _demo_ticket_and_name()
        st.session_state["active_ticket"] = ticket_seed
        st.session_state["active_name"] = name_seed

    ticket: Ticket | None = st.session_state.get("active_ticket")
    name: str | None = st.session_state.get("active_name")

    # Cache pipeline result by ticket_id so widget reruns don't re-invoke L4.
    cached_id = st.session_state.get("pipeline_result_ticket_id")
    if ticket is not None and cached_id != ticket.ticket_id:
        with st.spinner("Analyzing options..."):
            st.session_state["pipeline_result"] = run_pipeline(ticket)
            st.session_state["pipeline_result_ticket_id"] = ticket.ticket_id

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


def _demo_ticket_and_name() -> tuple[Ticket, str]:
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


if __name__ == "__main__":
    main()
