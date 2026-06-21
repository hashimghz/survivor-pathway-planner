"""Pathway planner — Streamlit entry point.

Layout: top header + two-column body (sidebar context + main tabbed panel).
The three tabs (Candidates / Excluded / Interventions) live inside this
single page; no separate page reload between tabs.

This is the engine's real entry point: `engine.pipeline.run(ticket)` is
called directly below, no mock data. The primary way a ticket gets here is a
caseworker submitting a real survivor through `app/pages/Profile.py`. When no
profile is active, the empty state leads with that as the main action, plus
an explicitly-labeled sample-profile shortcut (see
`app/components/empty_state.py` and `fixtures/demo_profiles.py`) for viewing
the engine at a glance without a real intake.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import plotly.io as pio
import streamlit as st

from app import copy
from app.charts import income_trajectory
from app.components import (
    candidate_card,
    empty_state,
    excluded_list,
    header,
    history_view,
    interventions_list,
    sidebar,
    skills_interpreted,
)
from app.plotly_theme import PATHWAY_TEMPLATE
from engine.pipeline import run as run_pipeline
from models import PipelineResult, Ticket

pio.templates["pathway"] = PATHWAY_TEMPLATE
pio.templates.default = "pathway"

st.set_page_config(
    page_title="Pathway planner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def _warm_resources() -> bool:
    """Preload everything heavy once per server process, before the first
    real request reaches it: L1's sentence-transformer model + skill
    embedding cache, and the occupations reference data.

    Both used to lazy-load on first use — the L1 model on the first
    map_skills() call, and the occupations CSV on *every* pipeline run
    with no caching at all (see data/loader.py). Both now load here
    instead, once per process. @st.cache_resource means this function's
    body only actually runs once across every session on this server —
    later calls (including every script rerun) return instantly from
    cache, so wrapping the call site in a spinner only shows real wait
    time on that first run, not on every rerun after.
    """
    from data.loader import warm as warm_occupations
    from engine.l1_skill_mapper import warm as warm_skill_mapper

    warm_skill_mapper()
    warm_occupations()
    return True


with st.spinner("Loading reference data..."):
    _warm_resources()


def _inject_styles() -> None:
    """Load the shared CSS once per session."""
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    _inject_styles()

    ticket: Ticket | None = st.session_state.get("active_ticket")
    name: str | None = st.session_state.get("active_name")
    is_sample = bool(st.session_state.get("is_sample_profile", False))

    # Cache pipeline result by ticket_id so widget reruns don't re-invoke L4.
    cached_id = st.session_state.get("pipeline_result_ticket_id")
    if ticket is not None and cached_id != ticket.ticket_id:
        with st.spinner("Analyzing options..."):
            st.session_state["pipeline_result"] = run_pipeline(ticket)
            st.session_state["pipeline_result_ticket_id"] = ticket.ticket_id

    result: PipelineResult | None = st.session_state.get("pipeline_result")
    header.render(name, is_sample=is_sample)

    if ticket is None or result is None:
        empty_state.render()
        return

    _render_exit_profile_button()
    skills_interpreted.render(ticket)

    # Samples aren't backed by a DB row, so Save (and the History tab) have
    # nothing to write to — profile_id stays None for them. Computed here,
    # above the tabs, since both the Candidates tab (Save) and the History
    # tab need it.
    profile_id = None if is_sample else st.session_state.get("active_profile_id")

    left, right = st.columns([1, 4], gap="medium")
    with left:
        sidebar.render(ticket, name or "")

    with right:
        tab_candidates, tab_excluded, tab_interventions, tab_history = st.tabs(
            [
                f"{copy.TAB_CANDIDATES} ({len(result.candidates)})",
                f"{copy.TAB_EXCLUDED} ({len(result.excluded)})",
                f"{copy.TAB_INTERVENTIONS} ({len(result.interventions.entries)})",
                copy.TAB_HISTORY,
            ]
        )

        with tab_candidates:
            if result.skills_to_review:
                _render_review_banner(len(result.skills_to_review))
            income_trajectory.render(result.candidates)
            for i, c in enumerate(result.candidates, start=1):
                candidate_card.render(c, rank=i, profile_id=profile_id, default_expanded=(i == 1))

        with tab_excluded:
            excluded_list.render(result.excluded)

        with tab_interventions:
            interventions_list.render(result.interventions)

        with tab_history:
            history_view.render(profile_id)

    st.markdown(
        f'<p style="text-align: center; color: var(--slate-light); '
        f'font-size: 11px; margin-top: 40px;">{copy.ACCOUNTABILITY}</p>',
        unsafe_allow_html=True,
    )


def _render_exit_profile_button() -> None:
    """Clears the active ticket/profile and returns to the empty state.

    This is the only way back to the pre-result screen — without it, once
    a profile loads there was no way to get back to "New profile" /
    "Try a sample profile" except editing the URL or restarting the app.

    Deliberately leaves `pipeline_result` / `pipeline_result_ticket_id` in
    place. The cache is already keyed by ticket_id (see main()'s "cached_id
    != ticket.ticket_id" check), so a genuinely new ticket recomputes
    regardless. The only thing leaving it alone buys is: re-entering the
    *same* ticket — which, for the fixed-id sample profiles, happens any
    time someone exits and reloads the same sample — redisplays instantly
    instead of re-running L4 (a real LLM call) for an identical result.
    Clearing it here would only add latency/cost with no correctness
    benefit.
    """
    _, btn_col = st.columns([5, 1])
    with btn_col:
        if st.button(
            copy.EXIT_PROFILE_BUTTON,
            key="exit_profile",
            use_container_width=True,
        ):
            for key in (
                "active_ticket",
                "active_name",
                "active_profile_id",
                "is_sample_profile",
            ):
                st.session_state.pop(key, None)
            st.rerun()


def _render_review_banner(n: int) -> None:
    text = copy.SKILLS_REVIEW_BANNER.format(n=n) if n == 1 else copy.SKILLS_REVIEW_BANNER_PLURAL.format(n=n)
    st.markdown(
        f'<div class="pp-review-banner">'
        f'  <span>{text}</span>'
        f'  <button class="pp-button-secondary" style="border-color: #C8956A; color: #6E3F12;">{copy.SKILLS_REVIEW_BUTTON}</button>'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
