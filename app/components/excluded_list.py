"""Excluded panel.

Renders the list of excluded occupations grouped by exclusion rule. The point
of this tab is honesty: every job that was cut and the named reason. No scores,
no charts — these are out of contention.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape

import streamlit as st

from app import copy
from models import Excluded


def render(excluded: list[Excluded]) -> None:
    if not excluded:
        st.markdown(
            f'<p style="color: var(--slate); font-size: 13px;">{escape(copy.EXCLUDED_EMPTY)}</p>',
            unsafe_allow_html=True,
        )
        return

    by_rule: dict[str, list[Excluded]] = defaultdict(list)
    for e in excluded:
        by_rule[e.rule.value].append(e)

    # Render groups in a stable order: most-excluded rule first.
    ordered_rules = sorted(by_rule.keys(), key=lambda r: -len(by_rule[r]))

    parts = []
    for rule in ordered_rules:
        rule_label = copy.EXCLUSION_RULE_LABELS.get(rule, rule.replace("_", " ").title())
        items = by_rule[rule]
        parts.append('<div class="pp-excluded-group">')
        parts.append(
            f'<div class="pp-excluded-group-head">'
            f'  <span class="pp-excluded-group-title">{escape(rule_label)}</span>'
            f'  <span class="pp-label">{len(items)}</span>'
            f'</div>'
        )
        for e in items:
            parts.append(
                f'<div class="pp-excluded-row">'
                f'  <span class="left">'
                f'    <span class="code">{escape(e.occupation.code)}</span>'
                f'    {escape(e.occupation.title)}'
                f'  </span>'
                f'  <span class="right">{escape(e.detail)}</span>'
                f'</div>'
            )
        parts.append('</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)
