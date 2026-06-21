"""Saved profiles list — shown in the empty state when real profiles exist.

Renders one row per saved profile with two actions:
  - Load  : sets the active ticket and navigates to Home.py
  - Edit  : sets edit_profile_id and navigates to Profile.py (§3.3)

Reads from the encrypted repository via app.db_access so env-var handling
stays in one place. Silently renders nothing when the repository is not
configured (missing PATHWAY_AES_KEY) — the empty state falls back to its
normal new-profile / sample-profile layout.
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app import copy  # noqa: E402
from app.db_access import repo  # noqa: E402
from core.anonymizer import profile_to_ticket  # noqa: E402


def _hmac_pepper() -> bytes | None:
    raw = os.environ.get("PATHWAY_HMAC_PEPPER", "")
    if not raw:
        return None
    return base64.b64decode(raw)


def render() -> bool:
    """Render the saved profiles list.

    Returns True if at least one profile was rendered, False if the list
    is empty or the repository is unavailable. The caller uses this to
    decide whether to show the divider between saved profiles and the
    new-profile / sample-profile block.
    """
    repository = repo()
    if repository is None:
        return False

    try:
        summaries = repository.list_summaries()
    except Exception:
        return False

    if not summaries:
        return False

    st.markdown(
        f'<p class="pp-label" style="margin-bottom: 8px;">'
        f"{copy.SAVED_PROFILES_HEADING}</p>",
        unsafe_allow_html=True,
    )

    for summary in summaries:
        profile_id = summary["id"]
        display_name = summary["preferred_name"] or copy.ACTIVE_PROFILE_NO_NAME
        metro = summary.get("current_metro", "")

        col_name, col_load, col_edit = st.columns([4, 1, 1])

        with col_name:
            st.markdown(
                f'<div style="padding: 8px 0;">'
                f'  <span style="font-weight: 600; font-size: 14px;">'
                f"{display_name}</span>"
                f'  <span style="color: var(--slate-light); font-size: 12px;'
                f' margin-left: 8px;">{metro}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

        with col_load:
            if st.button(
                copy.SAVED_PROFILES_LOAD,
                key=f"load_{profile_id}",
                use_container_width=True,
            ):
                _load_profile(profile_id, repository)

        with col_edit:
            if st.button(
                copy.SAVED_PROFILES_EDIT,
                key=f"edit_{profile_id}",
                use_container_width=True,
            ):
                # Clean up any stale edit state from a previous session
                # before setting the new target — otherwise the pre-fill
                # guard in Profile.py (_lang_prefilled) could suppress
                # loading the new profile's languages.
                for key in ("_edit_profile", "_lang_prefilled"):
                    st.session_state.pop(key, None)
                st.session_state["edit_profile_id"] = profile_id
                st.switch_page("pages/Profile.py")

    return True


def _load_profile(profile_id: str, repository) -> None:
    """Load a saved profile into session state and navigate to Home."""
    pepper = _hmac_pepper()
    if pepper is None:
        st.error(
            "PATHWAY_HMAC_PEPPER is not set — cannot load profile. "
            "Check your environment configuration."
        )
        return

    try:
        profile = repository.get(profile_id)
    except KeyError:
        st.error("Profile not found — it may have been deleted.")
        return

    ticket = profile_to_ticket(profile, pepper)

    st.session_state["active_profile_id"] = profile_id
    st.session_state["active_ticket"] = ticket
    st.session_state["active_name"] = (
        profile.identity.preferred_name or profile.identity.legal_name
    )
    st.session_state["is_sample_profile"] = False
    # Clear stale pipeline result so Home.py re-runs the pipeline
    # for this profile rather than showing a previous result.
    st.session_state.pop("pipeline_result", None)
    st.session_state.pop("pipeline_result_ticket_id", None)

    st.switch_page("Home.py")
