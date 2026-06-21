"""Saved profiles list — shown in the empty state when real profiles exist.

Renders one row per saved profile: name, metro, date saved (date only, never
a timestamp — see next_phase_plan.md §3.4), current job status, and three
actions:
  - Load   : sets the active ticket and navigates to Home.py
  - Edit   : sets edit_profile_id and navigates to Profile.py (§3.3)
  - Delete : permanently removes the profile and its job_history, gated
             behind an explicit confirm step (a popover, not a single
             click) since this is irreversible.

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


def _format_date(created_at: str) -> str:
    """Date portion only, per next_phase_plan.md §3.4 ("only ever displays
    the date, not a timestamp"). Empty/unparseable values (rows saved before
    the created_at column existed) fall back to a placeholder rather than
    showing a raw ISO string or crashing."""
    if not created_at or len(created_at) < 10:
        return copy.SAVED_PROFILES_DATE_UNKNOWN
    return created_at[:10]


def _format_status(current_status: str | None) -> str:
    if current_status is None:
        return copy.SAVED_PROFILES_STATUS_NONE
    return copy.HISTORY_STATUS_LABELS.get(current_status, current_status)


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
        _render_row(summary, repository)

    return True


def _render_row(summary: dict, repository) -> None:
    profile_id = summary["id"]
    display_name = summary["preferred_name"] or copy.ACTIVE_PROFILE_NO_NAME
    metro = summary.get("current_metro", "")
    date_label = _format_date(summary.get("created_at", ""))
    status_label = _format_status(summary.get("current_status"))

    col_name, col_date, col_status, col_load, col_edit, col_delete = st.columns(
        [3, 1.2, 1.4, 1, 1, 1]
    )

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

    with col_date:
        st.markdown(
            f'<div style="padding: 8px 0; color: var(--slate); font-size: 13px;">'
            f"{date_label}</div>",
            unsafe_allow_html=True,
        )

    with col_status:
        st.markdown(
            f'<div style="padding: 8px 0; color: var(--slate); font-size: 13px;">'
            f"{status_label}</div>",
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

    with col_delete:
        with st.popover(copy.SAVED_PROFILES_DELETE, use_container_width=True):
            st.markdown(
                f'<p style="font-size: 13px; margin-bottom: 10px;">'
                f"{copy.SAVED_PROFILES_DELETE_CONFIRM_PROMPT}</p>",
                unsafe_allow_html=True,
            )
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    copy.SAVED_PROFILES_DELETE_CONFIRM_BUTTON,
                    key=f"delete_confirm_{profile_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    _delete_profile(profile_id, repository)
            with cancel_col:
                # No handler needed — closing the popover (or just doing
                # nothing) is the cancel path. The button exists so the
                # affordance is visible, not because it needs logic.
                st.button(
                    copy.SAVED_PROFILES_DELETE_CANCEL,
                    key=f"delete_cancel_{profile_id}",
                    use_container_width=True,
                )


def _delete_profile(profile_id: str, repository) -> None:
    try:
        repository.delete(profile_id)
    except KeyError:
        st.error("Profile not found — it may have already been deleted.")
        return

    # If the deleted profile was the active one, clear it so the UI doesn't
    # keep showing results for a profile that no longer exists.
    if st.session_state.get("active_profile_id") == profile_id:
        for key in (
            "active_ticket",
            "active_name",
            "active_profile_id",
            "is_sample_profile",
            "pipeline_result",
            "pipeline_result_ticket_id",
        ):
            st.session_state.pop(key, None)

    st.rerun()


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

    job_history = repository.get_history(profile_id)
    ticket = profile_to_ticket(profile, pepper, job_history=job_history)

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
