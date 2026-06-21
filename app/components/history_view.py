"""History tab — outcome tracking for saved candidates.

Lives only on the results page (app/Home.py), never on the intake form — see
next_phase_plan.md §1/§2. One section per saved candidate (an occupation with
at least one job_history entry): its current status, full timeline, and a
small form to record the next outcome.

job_history is an append-only log (see db/repository.py) — there is no
"update" of an existing entry, only adding a new one. "Current status" is
therefore just the most recent entry per occupation, which get_history's
ORDER BY recorded_at DESC already surfaces as the first row in each group.

No layer references in any string this component emits.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape

import streamlit as st

from app import copy, db_access
from db.repository import HISTORY_STATUSES


def render(profile_id: str | None) -> None:
    """Render the History tab content.

    `profile_id` is None for sample profiles (not backed by a DB row) — in
    that case this renders a disabled-state message instead of a form,
    mirroring the existing CARD_SAVE_SAMPLE_DISABLED pattern on candidate
    cards.
    """
    if profile_id is None:
        st.markdown(
            f'<p style="color: var(--slate); font-size: 13px;">'
            f"{escape(copy.HISTORY_SAMPLE_DISABLED)}</p>",
            unsafe_allow_html=True,
        )
        return

    entries = db_access.get_history(profile_id)
    if not entries:
        st.markdown(
            f'<p style="color: var(--slate); font-size: 13px;">'
            f"{escape(copy.HISTORY_EMPTY)}</p>",
            unsafe_allow_html=True,
        )
        return

    by_occupation: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        by_occupation[entry["occupation_code"]].append(entry)

    for code, occ_entries in by_occupation.items():
        # get_history already orders by recorded_at DESC, so occ_entries[0]
        # is each occupation's most recent entry.
        _render_occupation_block(profile_id, code, occ_entries)


def _render_occupation_block(profile_id: str, code: str, occ_entries: list[dict]) -> None:
    latest = occ_entries[0]
    title = latest["occupation_title"]
    status_label = copy.HISTORY_STATUS_LABELS.get(latest["status"], latest["status"])

    st.markdown(
        f'<div class="pp-card" style="margin-bottom: 12px;">'
        f'  <p class="pp-card-meta">{escape(code)}</p>'
        f'  <p class="pp-card-title" style="font-size: 16px;">{escape(title)}</p>'
        f'  <p class="pp-label" style="margin: 10px 0 2px;">{escape(copy.HISTORY_CURRENT_STATUS_LABEL)}</p>'
        f'  <p style="margin: 0;">{escape(status_label)}'
        f'    <span style="color: var(--slate-light); font-size: 12px;">'
        f"     · {escape(_format_date(latest['recorded_at']))}</span></p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if len(occ_entries) > 1:
        with st.expander(copy.HISTORY_TIMELINE_LABEL.format(n=len(occ_entries))):
            for entry in occ_entries:
                note = entry.get("caseworker_notes") or ""
                note_html = f" — {escape(note)}" if note else ""
                entry_status = copy.HISTORY_STATUS_LABELS.get(entry["status"], entry["status"])
                st.markdown(
                    f'<p style="font-size: 13px; margin: 4px 0;">'
                    f'<span class="pp-mono" style="color: var(--slate-light);">'
                    f"{_format_date(entry['recorded_at'])}</span> "
                    f"— {escape(entry_status)}{note_html}</p>",
                    unsafe_allow_html=True,
                )

    col_status, col_notes, col_button = st.columns([2, 3, 1])
    with col_status:
        new_status = st.selectbox(
            copy.HISTORY_STATUS_INPUT_LABEL,
            options=list(HISTORY_STATUSES),
            format_func=lambda s: copy.HISTORY_STATUS_LABELS.get(s, s),
            key=f"history_status_{code}",
            label_visibility="collapsed",
        )
    with col_notes:
        notes = st.text_input(
            copy.HISTORY_NOTES_LABEL,
            key=f"history_notes_{code}",
            label_visibility="collapsed",
            placeholder=copy.HISTORY_NOTES_LABEL,
        )
    with col_button:
        if st.button(
            copy.HISTORY_RECORD_BUTTON,
            key=f"history_record_{code}",
            use_container_width=True,
        ):
            db_access.record_history_entry(profile_id, code, title, new_status, notes)
            st.rerun()


def _format_date(recorded_at: str) -> str:
    """Date portion only — recorded_at is stored as isoformat() + 'Z'."""
    return recorded_at[:10] if recorded_at else ""
