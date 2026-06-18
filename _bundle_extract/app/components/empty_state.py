"""Empty state — when no profile is loaded.

Single centred card with two actions: Load profile, New profile. The judges
will not see this in a demo, but it should look intentional.
"""

from __future__ import annotations

import streamlit as st

from app import copy


def render() -> None:
    st.markdown(
        f'<div class="pp-empty">'
        f'  <p class="pp-empty-icon">📁</p>'
        f'  <h2 class="pp-empty-title">{copy.EMPTY_TITLE}</h2>'
        f'  <p class="pp-empty-body">{copy.EMPTY_BODY}</p>'
        f'  <div style="display: flex; gap: 8px; justify-content: center;">'
        f'    <button class="pp-button-primary">{copy.EMPTY_BUTTON_LOAD}</button>'
        f'    <button class="pp-button-secondary">{copy.EMPTY_BUTTON_NEW}</button>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
