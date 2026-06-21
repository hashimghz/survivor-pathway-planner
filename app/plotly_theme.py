"""Plotly template matching the Vellum-on-white palette.

Import and apply once at app start:

    import plotly.io as pio
    from app.plotly_theme import PATHWAY_TEMPLATE
    pio.templates["pathway"] = PATHWAY_TEMPLATE
    pio.templates.default = "pathway"
"""

from __future__ import annotations

import plotly.graph_objects as go

# Vellum-on-white palette — keep in sync with app/style.css.
INK = "#1B1B1F"
SLATE = "#5C5854"
SLATE_LIGHT = "#8E8B87"
PLUM = "#5B2B5C"
FOREST = "#2D5A3D"
SIENNA = "#B5601B"
CRIMSON = "#8A1F1F"
BORDER = "#E5E5EA"
BAR_TRACK = "#F0F0F2"

# Semantic palette for severity-coded charts (the criteria breakdown, etc.).
SEVERITY_COLORS = [FOREST, SIENNA, CRIMSON]

# Categorical palette when meaning is structural, not severity.
CATEGORICAL_PALETTE = [PLUM, FOREST, SIENNA, SLATE, CRIMSON]


PATHWAY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, sans-serif", size=12, color=INK),
        title=dict(font=dict(family="Source Serif 4, serif", size=16, color=INK)),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=CATEGORICAL_PALETTE,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor=BORDER,
            linewidth=0.5,
            ticks="outside",
            tickcolor=BORDER,
            tickfont=dict(size=11, color=SLATE),
            title=dict(font=dict(size=12, color=SLATE)),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=BAR_TRACK,
            gridwidth=0.5,
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=SLATE),
            title=dict(font=dict(size=12, color=SLATE)),
        ),
        legend=dict(
            font=dict(size=11, color=SLATE),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(l=40, r=20, t=30, b=40),
    )
)


def severity_for(value: float) -> str:
    """Pick the bar/marker color for a fit score in [0, 1]."""
    if value >= 0.55:
        return FOREST
    if value >= 0.35:
        return SIENNA
    return CRIMSON
