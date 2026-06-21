"""Candidate card component.

Every candidate renders as one collapsible card. Collapsed is a one-line
summary; expanded shows the full breakdown (criteria bars, explanation,
framings, risks, wage range, actions) — identical content whether it's the
top-ranked card or any other. Expand/collapse state lives in
st.session_state per card, independent of the other cards (more than one
can be open at once).

No layer references in any string this component emits.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy, db_access
from app.components import details_modal
from models import Candidate

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

    # The track's own left/right edges ARE this occupation's p10 and p90
    # (that's what the endpoint labels show), so the filled range always
    # spans the full track — there's no separate sub-range to compute. The
    # median tick is the only marker that varies by data.
    return (
        f'<div class="pp-wage">'
        f'  <span class="pp-label">{copy.CARD_WAGE_LABEL}</span>'
        f'  <span class="endpoint">${p10:.2f}</span>'
        f'  <div class="pp-wage-track">'
        f'    <div class="pp-wage-range" style="left: 0%; right: 0%;"></div>'
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


def _expanded_html(candidate: Candidate, rank: int) -> str:
    sev = _severity_class(candidate.fit_score)
    occ = candidate.occupation
    return (
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
        f'</div>'
    )


def _collapsed_html(candidate: Candidate, rank: int) -> str:
    sev = _severity_class(candidate.fit_score)
    occ = candidate.occupation
    return (
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


def render(
    candidate: Candidate,
    rank: int,
    profile_id: str | None = None,
    default_expanded: bool = False,
) -> None:
    """Render one candidate card, collapsed or expanded per its own toggle
    state. `default_expanded` only seeds the very first render of this
    card (e.g. rank 1 opens by default); after that the user's toggle wins.
    """
    occ = candidate.occupation
    expand_key = f"card_expanded_{occ.code}_{rank}"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = default_expanded
    is_expanded = st.session_state[expand_key]

    html = _expanded_html(candidate, rank) if is_expanded else _collapsed_html(candidate, rank)
    st.markdown(html, unsafe_allow_html=True)
    _render_actions(candidate, rank, profile_id, is_expanded, expand_key)


def _render_actions(
    candidate: Candidate,
    rank: int,
    profile_id: str | None,
    is_expanded: bool,
    expand_key: str,
) -> None:
    """Real, clickable action row. Replaces the decorative <button> tags
    that used to sit inside the markdown HTML — those had no Streamlit
    widget behind them, so clicking did nothing.
    """
    occupation_code = candidate.occupation.code
    key_suffix = f"{occupation_code}_{rank}"
    toggle_label = copy.CARD_BUTTON_COLLAPSE if is_expanded else copy.CARD_BUTTON_EXPAND

    columns = st.columns(3) if is_expanded else st.columns(2)
    col_save = columns[0] if is_expanded else None
    col_details = columns[1] if is_expanded else columns[0]
    col_toggle = columns[2] if is_expanded else columns[1]

    if col_save is not None:
        with col_save:
            if profile_id is None:
                st.button(
                    copy.CARD_BUTTON_SAVE,
                    key=f"save_{key_suffix}",
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                    help=copy.CARD_SAVE_SAMPLE_DISABLED,
                )
            else:
                is_saved = occupation_code in db_access.saved_candidate_codes(profile_id)
                label = copy.CARD_BUTTON_SAVED if is_saved else copy.CARD_BUTTON_SAVE
                if st.button(
                    label,
                    key=f"save_{key_suffix}",
                    type="secondary" if is_saved else "primary",
                    use_container_width=True,
                ):
                    db_access.toggle_saved_candidate(
                        profile_id, occupation_code, candidate.occupation.title, is_saved
                    )
                    st.rerun()

    with col_details:
        if st.button(
            copy.CARD_BUTTON_DETAILS,
            key=f"details_{key_suffix}",
            use_container_width=True,
        ):
            details_modal.render(candidate, profile_id=profile_id)

    with col_toggle:
        if st.button(
            toggle_label,
            key=f"toggle_{key_suffix}",
            use_container_width=True,
        ):
            st.session_state[expand_key] = not is_expanded
            st.rerun()
