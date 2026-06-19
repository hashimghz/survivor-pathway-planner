"""Empty state — when no profile is loaded.

Primary action is "New profile" (the real intake flow). A secondary,
clearly-labeled sample-profile picker lets anyone see the engine working at a
glance without filling out the form — it is explicitly not the product's
identity, just a shortcut for viewing.
"""

from __future__ import annotations

import streamlit as st

from app import copy
from fixtures.demo_profiles import DEMO_PROFILES


def render() -> None:
    st.markdown(
        f'<div class="pp-empty">'
        f'  <p class="pp-empty-icon">📁</p>'
        f'  <h2 class="pp-empty-title">{copy.EMPTY_TITLE}</h2>'
        f'  <p class="pp-empty-body">{copy.EMPTY_BODY}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        if st.button(copy.EMPTY_BUTTON_NEW, type="primary", use_container_width=True):
            st.switch_page("pages/Profile.py")

        st.markdown(
            f'<p class="pp-label" style="text-align: center; margin-top: 20px;">'
            f"{copy.EMPTY_SAMPLE_HEADING}</p>"
            f'<p class="pp-empty-body" style="font-size: 12px;">{copy.EMPTY_SAMPLE_BODY}</p>',
            unsafe_allow_html=True,
        )

        labels = {key: label for key, label, _name, _ticket in DEMO_PROFILES}
        choice = st.selectbox(
            copy.EMPTY_SAMPLE_SELECT_LABEL,
            options=list(labels.keys()),
            format_func=lambda k: labels[k],
            key="sample_profile_choice",
            label_visibility="collapsed",
        )
        if st.button(copy.EMPTY_SAMPLE_BUTTON, use_container_width=True):
            _load_sample(choice)
            st.rerun()


def _load_sample(key: str) -> None:
    for sample_key, _label, name, ticket in DEMO_PROFILES:
        if sample_key == key:
            st.session_state["active_ticket"] = ticket
            st.session_state["active_name"] = name
            st.session_state["is_sample_profile"] = True
            # A sample isn't backed by a DB row — clear any stale id left
            # over from a previously-loaded real profile, so Save can't
            # accidentally write onto the wrong profile.
            st.session_state.pop("active_profile_id", None)
            # Deliberately NOT clearing pipeline_result / pipeline_result_
            # ticket_id here. Sample tickets have fixed ids (e.g.
            # "demo-baseline"), so reloading the same sample after Exit
            # should hit Home.py's existing ticket_id cache check and
            # redisplay instantly, not re-run L4. Popping it here
            # unconditionally defeated that on every reload, even of the
            # same sample.
            return
