"""Interventions panel.

Renders the relaxation findings as a ranked list. The point of this tab is
leverage: what specifically would unlock more options. Each entry is an
intervention the caseworker could pursue (or, for safety-critical entries,
explicitly cannot).
"""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy
from models import InterventionReport


def render(report: InterventionReport) -> None:
    if not report.entries:
        st.markdown(
            f'<p style="color: var(--slate); font-size: 13px;">{escape(copy.INTERVENTIONS_EMPTY)}</p>',
            unsafe_allow_html=True,
        )
        return

    actionable = [e for e in report.entries if e.actionable]
    non_actionable = [e for e in report.entries if not e.actionable]

    parts = []

    if actionable:
        parts.append(f'<p class="pp-label" style="margin-bottom: 8px;">{copy.INTERVENTIONS_HEADING_ACTIONABLE}</p>')
        parts.append('<div>')
        for entry in actionable:
            parts.append(
                f'<div class="pp-intervention">'
                f'  <div class="pp-intervention-head">'
                f'    <span class="pp-intervention-title">{escape(_humanise(entry.constraint))}</span>'
                f'    <span class="pp-intervention-count">{entry.jobs_unlocked} {copy.INTERVENTIONS_JOBS_SUFFIX}</span>'
                f'  </div>'
                f'  <div class="pp-intervention-hint">{escape(entry.hint)}</div>'
                f'</div>'
            )
        parts.append('</div>')

    if non_actionable:
        parts.append(f'<p class="pp-label" style="margin: 24px 0 8px;">{copy.INTERVENTIONS_HEADING_NOT_ACTIONABLE}</p>')
        parts.append('<div>')
        for entry in non_actionable:
            parts.append(
                f'<div class="pp-intervention not-actionable">'
                f'  <div class="pp-intervention-head">'
                f'    <span class="pp-intervention-title">{escape(_humanise(entry.constraint))}</span>'
                f'    <span class="pp-intervention-count">{entry.jobs_unlocked} {copy.INTERVENTIONS_JOBS_SUFFIX}</span>'
                f'  </div>'
                f'  <div class="pp-intervention-hint">{escape(entry.hint)}</div>'
                f'</div>'
            )
        parts.append('</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)


def _humanise(constraint: str) -> str:
    """Turn an internal constraint name into a sentence-cased title."""
    table = {
        "requires_clean_record":    "Clean record requirement",
        "requires_drivers_license": "Driver's license",
        "requires_ssn":             "Social Security number",
        "requires_credit_check":    "Credit check",
        "work_authorization":       "Work authorization",
        "wage_minimum_hourly":      "Wage floor",
        "max_commute_minutes":      "Commute distance",
    }
    if constraint in table:
        return table[constraint]
    return constraint.replace("_", " ").capitalize()
