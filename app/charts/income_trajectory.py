"""Income trajectory chart — projected income over time for the top matches.

Built entirely from each Candidate's already-computed `wage_range` (real BLS
percentile data, never hardcoded). The projection itself is a stated
modeling assumption, not invented data — see CHART_TRAJECTORY_CAPTION in
app/copy.py, which renders alongside the chart so the assumption is visible,
not buried.

No layer references in any string this component emits.
"""

from __future__ import annotations

from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from app import copy
from app.plotly_theme import CATEGORICAL_PALETTE
from models import Candidate

MONTHS: list[int] = [0, 6, 12, 24]
TOP_N = 3
_HOURS_PER_YEAR = 2080


def render(candidates: list[Candidate]) -> None:
    """Render the income trajectory chart for up to the top 3 candidates.

    Degrades gracefully to a plain note when there are no candidates to
    chart — never crashes on an empty or short candidate list.
    """
    top = candidates[:TOP_N]
    if not top:
        st.markdown(
            f'<p class="pp-label">{copy.CHART_TRAJECTORY_EMPTY}</p>',
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure()

    for i, candidate in enumerate(top):
        color = CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)]
        p10, p50, p90 = _annual_percentiles(candidate)

        # Confidence band: this occupation's full p10-p90 wage range, held
        # constant across the time axis. It describes the occupation's pay
        # spread, not a time-varying forecast interval.
        fig.add_trace(
            go.Scatter(
                x=MONTHS + MONTHS[::-1],
                y=[p90] * len(MONTHS) + [p10] * len(MONTHS),
                fill="toself",
                fillcolor=_with_alpha(color, 0.12),
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Projected trajectory: placement near p10, moving toward the
        # occupation's median over the window. See module docstring.
        fig.add_trace(
            go.Scatter(
                x=MONTHS,
                y=_project_income(p10, p50),
                mode="lines+markers",
                name=candidate.occupation.title,
                line=dict(color=color, width=2.5),
                marker=dict(size=6, color=color),
            )
        )

    fig.update_layout(
        title=copy.CHART_TRAJECTORY_TITLE,
        xaxis_title=copy.CHART_TRAJECTORY_XAXIS,
        yaxis_title=copy.CHART_TRAJECTORY_YAXIS,
        yaxis_tickformat="$,.0f",
        height=340,
        margin=dict(l=50, r=20, t=50, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        f'<p style="font-size: 12px; color: var(--slate-light); margin-top: -8px;">'
        f"{copy.CHART_TRAJECTORY_CAPTION}</p>",
        unsafe_allow_html=True,
    )


def _annual_percentiles(candidate: Candidate) -> tuple[float, float, float]:
    wr = candidate.wage_range
    return (
        _annual(wr.p10_hourly),
        _annual(wr.p50_hourly),
        _annual(wr.p90_hourly),
    )


def _annual(hourly: Decimal) -> float:
    return float(hourly) * _HOURS_PER_YEAR


def _project_income(p10_annual: float, p50_annual: float) -> list[float]:
    """Linear projection from initial placement (p10) toward the
    occupation's median (p50) across MONTHS. A defensible heuristic per the
    project handoff, not a guarantee — surfaced in the chart caption.
    """
    horizon = MONTHS[-1]
    return [
        p10_annual + (p50_annual - p10_annual) * (month / horizon)
        for month in MONTHS
    ]


def _with_alpha(hex_color: str, alpha: float) -> str:
    """Convert a '#RRGGBB' hex color to an 'rgba(r,g,b,a)' string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"
