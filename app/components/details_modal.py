"""Candidate details modal — full breakdown opened from the Details action.

Shows all nine criteria dimensions, full explanation, framings, risks,
optional upskill step, and wage percentiles. No layer references in any
string this component emits.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy, db_access
from models import Candidate, CriteriaBreakdown

HIGH_FIT_THRESHOLD = 0.55
LOW_FIT_THRESHOLD = 0.35

DETAILS_CRITERIA_ORDER = [
    ("skill_match", "Skill match"),
    ("wage_fit", "Wage fit"),
    ("commute_fit", "Commute fit"),
    ("shift_fit", "Shift fit"),
    ("isolation_fit", "Isolation fit"),
    ("customer_facing_fit", "Customer-facing"),
    ("uniformed_role_fit", "Uniformed role"),
    ("male_dominated_fit", "Male-dominated team"),
    ("schedule_fit", "Schedule fit"),
]


def _severity_class(value: float) -> str:
    if value >= HIGH_FIT_THRESHOLD:
        return "high"
    if value >= LOW_FIT_THRESHOLD:
        return "mid"
    return "low"


def _criteria_rows_html(breakdown: CriteriaBreakdown) -> str:
    rows = []
    for attr, label in DETAILS_CRITERIA_ORDER:
        v = getattr(breakdown, attr)
        sev = _severity_class(v)
        pct = round(v * 100)
        rows.append(
            f'<div class="label">{escape(label)}</div>'
            f'<div class="pp-bar">'
            f'<div class="pp-bar-fill {sev}" style="width: {pct}%;"></div>'
            f"</div>"
            f'<div class="value">{v:.2f}</div>'
        )
    return f'<div class="pp-criteria">{"".join(rows)}</div>'


def _framings_html(candidate: Candidate) -> str:
    if not candidate.safe_resume_framings:
        return ""
    items = "".join(f"<p>· {escape(f)}</p>" for f in candidate.safe_resume_framings)
    return (
        f'<div class="pp-framings">'
        f'  <p class="pp-label">{copy.CARD_FRAMINGS_LABEL}</p>'
        f"  {items}"
        f"</div>"
    )


def _risks_html(candidate: Candidate) -> str:
    if not candidate.risk_flags:
        return ""
    items = "".join(f"<p>· {escape(r)}</p>" for r in candidate.risk_flags)
    return (
        f'<div class="pp-framings">'
        f'  <p class="pp-label">{copy.CARD_RISKS_LABEL}</p>'
        f"  {items}"
        f"</div>"
    )


def _upskill_html(candidate: Candidate) -> str:
    if not candidate.upskill_next_step:
        return ""
    return (
        f'<div class="pp-framings">'
        f'  <p class="pp-label">{copy.CARD_UPSKILL_LABEL}</p>'
        f"  <p>· {escape(candidate.upskill_next_step)}</p>"
        f"</div>"
    )


def _wage_html(candidate: Candidate) -> str:
    wr = candidate.wage_range
    p10 = float(wr.p10_hourly)
    p50 = float(wr.p50_hourly)
    p90 = float(wr.p90_hourly)

    span = p90 - p10 if p90 > p10 else 1
    median_pct = max(0, min(100, round(((p50 - p10) / span) * 100)))

    # The track's own left/right edges ARE this occupation's p10 and p90
    # (that's what the endpoint labels show), so the filled range always
    # spans the full track. The median tick is the only marker that varies.
    bar = (
        f'<div class="pp-wage">'
        f'  <span class="pp-label">{copy.CARD_WAGE_LABEL}</span>'
        f'  <span class="endpoint">${p10:.2f}</span>'
        f'  <div class="pp-wage-track">'
        f'    <div class="pp-wage-range" style="left: 0%; right: 0%;"></div>'
        f'    <div class="pp-wage-median" style="left: {median_pct}%;"></div>'
        f"  </div>"
        f'  <span class="endpoint">${p90:.2f}</span>'
        f"</div>"
    )

    percentiles = (
        f'<div class="pp-criteria" style="margin-bottom: 0;">'
        f'  <div class="label">P10</div><div></div>'
        f'  <div class="value pp-mono">${p10:.2f}/hr</div>'
        f'  <div class="label">P50</div><div></div>'
        f'  <div class="value pp-mono">${p50:.2f}/hr</div>'
        f'  <div class="label">P90</div><div></div>'
        f'  <div class="value pp-mono">${p90:.2f}/hr</div>'
        f"</div>"
    )
    return bar + percentiles


def _header_html(candidate: Candidate) -> str:
    occ = candidate.occupation
    return (
        f'<p class="pp-card-meta">{escape(occ.code)}</p>'
        f'<p class="pp-card-title">{escape(occ.title)}</p>'
    )


def _details_html(candidate: Candidate) -> str:
    return (
        f"{_header_html(candidate)}"
        f"{_criteria_rows_html(candidate.criteria_breakdown)}"
        f'<p class="pp-explanation">{escape(candidate.fit_explanation)}</p>'
        f"{_framings_html(candidate)}"
        f"{_risks_html(candidate)}"
        f"{_upskill_html(candidate)}"
        f"{_wage_html(candidate)}"
    )


def render(candidate: Candidate, profile_id: str | None = None) -> None:
    """Open a dialog showing the full candidate detail view.

    Includes a Save toggle when `profile_id` is set (a real, non-sample
    profile) — this is the only Save entry point for candidates ranked
    below #1, since collapsed cards only expose a Details button.
    """
    title = candidate.occupation.title
    occupation_code = candidate.occupation.code

    @st.dialog(title)
    def _body() -> None:
        st.markdown(_details_html(candidate), unsafe_allow_html=True)

        if profile_id is None:
            st.button(
                copy.CARD_BUTTON_SAVE,
                key=f"modal_save_{occupation_code}",
                type="primary",
                disabled=True,
                help=copy.CARD_SAVE_SAMPLE_DISABLED,
            )
            return

        is_saved = occupation_code in db_access.saved_candidate_codes(profile_id)
        label = copy.CARD_BUTTON_SAVED if is_saved else copy.CARD_BUTTON_SAVE
        if st.button(
            label,
            key=f"modal_save_{occupation_code}",
            type="secondary" if is_saved else "primary",
        ):
            db_access.toggle_saved_candidate(
                profile_id, occupation_code, candidate.occupation.title, is_saved
            )
            st.rerun()

    _body()
