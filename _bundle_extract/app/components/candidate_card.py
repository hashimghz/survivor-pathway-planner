"""Candidate card component.

Renders one Candidate as the expanded card from the mockup (head + criteria
bars + fit explanation prose + safe resume framings + wage range + actions),
or as a collapsed single-line row.

No layer references in any string this component emits.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape

import streamlit as st

from models import Candidate
from app import copy


# Score thresholds: see app/AGENTS.md. These match the cutoffs the engine
# uses for "borderline" candidates and the UI uses for severity colour.
HIGH_FIT_THRESHOLD = 0.55
LOW_FIT_THRESHOLD = 0.35


def _severity_class(value: float) -> str:
    if value >= HIGH_FIT_THRESHOLD:
        return "high"
    if value >= LOW_FIT_THRESHOLD:
        return "mid"
    return "low"


# Order matters: this is the order the criteria render in the card.
CRITERIA_ORDER = [
    ("skill_match",          "Skill match"),
    ("wage_fit",             "Wage fit"),
    ("shift_fit",            "Shift fit"),
    ("isolation_fit",        "Isolation fit"),
    ("customer_facing_fit",  "Customer-facing"),
    ("commute_fit",          "Commute fit"),
]


def _criteria_rows_html(candidate: Candidate) -> str:
    breakdown = candidate.criteria_breakdown
    rows = []
    for attr, label in CRITERIA_ORDER:
        v = getattr(breakdown, attr)
        sev = _severity_class(v)
        pct = round(v * 100)
        rows.append(
            f'<div class="label">{escape(label)}</div>'
            f'<div class="pp-bar"><div class="pp-bar-fill {sev}" style="width: {pct}%;"></div></div>'
            f'<div class="value">{v:.2f}</div>'
        )
    return f'<div class="pp-criteria">{"".join(rows)}</div>'


def _framings_html(candidate: Candidate) -> str:
    if not candidate.safe_resume_framings:
        return ""
    items = "".join(
        f"<p>· {escape(f)}</p>" for f in candidate.safe_resume_framings
    )
    return (
        f'<div class="pp-framings">'
        f'  <p class="pp-label">{copy.CARD_FRAMINGS_LABEL}</p>'
        f'  {items}'
        f'</div>'
    )


def _wage_html(candidate: Candidate) -> str:
    wr = candidate.wage_range
    p10 = float(wr.p10_hourly)
    p50 = float(wr.p50_hourly)
    p90 = float(wr.p90_hourly)

    # Position the median marker proportionally along the p10–p90 track.
    span = p90 - p10 if p90 > p10 else 1
    median_pct = max(0, min(100, round(((p50 - p10) / span) * 100)))

    # The filled portion of the wage track represents the inter-percentile span;
    # for the demo we render it as left:30% right:25% which always frames the median.
    return (
        f'<div class="pp-wage">'
        f'  <span class="pp-label">{copy.CARD_WAGE_LABEL}</span>'
        f'  <span class="endpoint">${p10:.2f}</span>'
        f'  <div class="pp-wage-track">'
        f'    <div class="pp-wage-range" style="left: 18%; right: 12%;"></div>'
        f'    <div class="pp-wage-median" style="left: {median_pct}%;"></div>'
        f'  </div>'
        f'  <span class="endpoint">${p90:.2f}</span>'
        f'</div>'
    )


def _risks_html(candidate: Candidate) -> str:
    if not candidate.risk_flags:
        return ""
    items = "".join(f"<p>· {escape(r)}</p>" for r in candidate.risk_flags)
    return (
        f'<div class="pp-framings">'
        f'  <p class="pp-label">{copy.CARD_RISKS_LABEL}</p>'
        f'  {items}'
        f'</div>'
    )


def render_expanded(candidate: Candidate, rank: int) -> None:
    """Render a candidate as the full expanded card."""
    sev = _severity_class(candidate.fit_score)
    occ = candidate.occupation

    html = (
        f'<div class="pp-card">'
        f'  <div class="pp-card-head">'
        f'    <div>'
        f'      <p class="pp-card-meta">#{rank} · {escape(occ.code)}</p>'
        f'      <p class="pp-card-title">{escape(occ.title)}</p>'
        f'    </div>'
        f'    <div class="pp-card-score">'
        f'      <p class="pp-label">{copy.CARD_FIT_LABEL}</p>'
        f'      <p class="value {sev}">{candidate.fit_score:.2f}</p>'
        f'    </div>'
        f'  </div>'
        f'  {_criteria_rows_html(candidate)}'
        f'  <p class="pp-explanation">{escape(candidate.fit_explanation)}</p>'
        f'  {_framings_html(candidate)}'
        f'  {_risks_html(candidate)}'
        f'  {_wage_html(candidate)}'
        f'  <div class="pp-actions">'
        f'    <button class="pp-button-primary">{copy.CARD_BUTTON_SAVE}</button>'
        f'    <button class="pp-button-secondary">{copy.CARD_BUTTON_DETAILS}</button>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_collapsed(candidate: Candidate, rank: int) -> None:
    """Render a candidate as a single-line row (collapsed state)."""
    sev = _severity_class(candidate.fit_score)
    occ = candidate.occupation

    html = (
        f'<div class="pp-card pp-card-collapsed">'
        f'  <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px;">'
        f'    <div style="min-width: 0;">'
        f'      <p class="pp-card-meta">#{rank} · {escape(occ.code)}</p>'
        f'      <p class="pp-card-title" style="font-size: 15px;">{escape(occ.title)}</p>'
        f'    </div>'
        f'    <div style="display: flex; align-items: center; gap: 10px;">'
        f'      <p class="value {sev}" style="font-size: 17px; font-weight: 500; '
        f'         font-variant-numeric: tabular-nums; margin: 0; '
        f'         color: var(--{sev}-color, var(--forest));">{candidate.fit_score:.2f}</p>'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
