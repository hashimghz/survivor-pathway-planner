"""Top header bar with the active-profile badge."""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy


def render(active_name: str | None, is_sample: bool = False) -> None:
    # `active_name` is `None` only when no profile is loaded at all (the key
    # was never set, or was cleared by Exit). Once a profile loads it's
    # always a `str` (possibly empty, if a caseworker left "Preferred name"
    # blank on the form) — so checking `is not None` here, instead of
    # truthiness, is what correctly tells "no profile" apart from "a real,
    # active profile whose name happens to be blank." Truthiness alone
    # showed "No profile loaded" for the latter case, which was the bug.
    if active_name is not None:
        display_name = active_name or copy.ACTIVE_PROFILE_NO_NAME
        sample_html = (
            f'<span class="pp-badge avoid" style="margin-left: 8px;">'
            f'{escape(copy.SAMPLE_TAG_LABEL)}</span>'
            if is_sample
            else ""
        )
        badge_html = (
            f'<div class="pp-active-profile">'
            f'  <span class="label">{copy.ACTIVE_PROFILE_LABEL}</span>'
            f'  <span class="name">{escape(display_name)}</span>'
            f'  {sample_html}'
            f'</div>'
        )
    else:
        badge_html = (
            f'<div class="pp-active-profile">'
            f'  <span class="label">{copy.NO_PROFILE_LABEL}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="pp-header">'
        f'  <div class="pp-header-title">{copy.APP_TITLE}</div>'
        f'  {badge_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
