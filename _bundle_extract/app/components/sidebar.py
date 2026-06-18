"""Sidebar context cards.

Renders the survivor's identity summary, key constraint values, and the
trigger / avoid graded constraints. Reads from a Ticket (not Profile) — the
sidebar shows what the engine knows, which is the anonymous payload, not PII.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from models import Ticket, GradedLevel


_GRADED_LABELS = {
    "night_shift": "Night shift",
    "isolated_workplace": "Isolated workplace",
    "customer_facing": "Customer facing",
    "male_dominated_team": "Male-dominated team",
    "uniformed_role": "Uniformed role",
    "requires_overnight_travel": "Overnight travel",
}


def render(ticket: Ticket, display_name: str) -> None:
    """Render the sidebar context for the active survivor."""

    work_auth = _humanise_work_auth(ticket.work_authorization.value)
    vehicle = "Yes" if ticket.has_vehicle else "No"
    transit = "Yes" if ticket.transit_access else "No"
    commute = f"{ticket.max_commute_minutes} min"
    wage_floor = f"${float(ticket.wage_minimum_hourly):.2f}"
    education = _humanise_education(ticket.education_highest.value)

    context_html = (
        f'<div class="pp-context-card">'
        f'  <p class="pp-label">CONTEXT</p>'
        f'  <p class="pp-context-name">{escape(display_name)}</p>'
        f'  <p class="pp-context-meta">{escape(ticket.current_metro)}</p>'
        f'  <div class="pp-context-row"><span class="k">Work auth</span><span class="v">{work_auth}</span></div>'
        f'  <div class="pp-context-row"><span class="k">Vehicle</span><span class="v">{vehicle}</span></div>'
        f'  <div class="pp-context-row"><span class="k">Transit</span><span class="v">{transit}</span></div>'
        f'  <div class="pp-context-row"><span class="k">Commute</span><span class="v">{commute}</span></div>'
        f'  <div class="pp-context-row"><span class="k">Wage floor</span><span class="v">{wage_floor}</span></div>'
        f'  <div class="pp-context-row"><span class="k">Education</span><span class="v">{education}</span></div>'
        f'</div>'
    )
    st.markdown(context_html, unsafe_allow_html=True)

    triggers = []
    avoids = []
    for attr, label in _GRADED_LABELS.items():
        level = getattr(ticket.graded_constraints, attr)
        if level == GradedLevel.TRIGGER:
            triggers.append(label)
        elif level == GradedLevel.AVOID:
            avoids.append(label)

    if triggers or avoids:
        parts = ['<div class="pp-context-card">']
        if triggers:
            parts.append('<p class="pp-label">TRIGGERS</p>')
            parts.append('<div style="display: flex; flex-direction: column; gap: 5px; align-items: flex-start; margin-bottom: 10px;">')
            for t in triggers:
                parts.append(f'<span class="pp-badge trigger">{escape(t)}</span>')
            parts.append('</div>')
        if avoids:
            parts.append('<p class="pp-label">AVOID</p>')
            parts.append('<div style="display: flex; flex-direction: column; gap: 5px; align-items: flex-start;">')
            for a in avoids:
                parts.append(f'<span class="pp-badge avoid">{escape(a)}</span>')
            parts.append('</div>')
        parts.append('</div>')
        st.markdown("".join(parts), unsafe_allow_html=True)


def _humanise_work_auth(value: str) -> str:
    return {"yes": "Yes", "no": "No", "in_process": "In process"}.get(value, value)


def _humanise_education(value: str) -> str:
    return {
        "none": "None",
        "some_hs": "Some high school",
        "ged": "GED",
        "some_college": "Some college",
        "associates": "Associates",
        "bachelors": "Bachelors",
        "graduate": "Graduate",
    }.get(value, value)
