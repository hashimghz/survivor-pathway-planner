"""Skills-interpreted panel — surfaces what the engine mapped each free-text
skill to.

This is the single visible artifact proving the embedding step ran: without
it, the skill-mapping work is invisible to anyone looking at a demo. No layer
references (L1, embedding, model, etc.) in any string this component emits —
see app/copy.py's rules.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy
from models import Ticket


def render(ticket: Ticket) -> None:
    """Render the "how skills were interpreted" card.

    No-op when the ticket carries no mapped_skills — e.g. a profile that
    never had free-text skills entered.
    """
    if not ticket.mapped_skills:
        return

    rows = "".join(_row_html(entry) for entry in ticket.mapped_skills)

    st.markdown(
        f'<div class="pp-context-card" style="margin-bottom: 18px;">'
        f'  <p class="pp-label">{copy.SKILLS_INTERPRETED_HEADING}</p>'
        f'  {rows}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _row_html(entry: dict) -> str:
    input_skill = escape(str(entry.get("input", "")))
    matches = entry.get("matches", [])

    if not matches:
        return (
            f'<div class="pp-skills-row">'
            f'  <p class="pp-skills-input">"{input_skill}"</p>'
            f'  <p class="pp-skills-none">{copy.SKILLS_INTERPRETED_NO_MATCH}</p>'
            f'</div>'
        )

    matched = " · ".join(
        f'{escape(str(m["onet_name"]))} ({float(m["confidence"]):.2f})' for m in matches
    )
    return (
        f'<div class="pp-skills-row">'
        f'  <p class="pp-skills-input">"{input_skill}"</p>'
        f'  <p class="pp-skills-matches">{matched}</p>'
        f'</div>'
    )
