"""Top header bar with the active-profile badge."""

from __future__ import annotations

from html import escape

import streamlit as st

from app import copy


def render(active_name: str | None) -> None:
    if active_name:
        badge_html = (
            f'<div class="pp-active-profile">'
            f'  <span class="label">{copy.ACTIVE_PROFILE_LABEL}</span>'
            f'  <span class="name">{escape(active_name)}</span>'
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
