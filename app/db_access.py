"""Shared helpers for accessing the encrypted profile repository.

Centralises env-var reads and the saved-candidate read/write logic so
app/Home.py and app/components/* don't each reimplement it.

app/pages/Profile.py has its own private copies of the AES-key/repo helpers
predating this module — left as-is rather than refactored, since that file
already works and this feature doesn't need to touch it.
"""

from __future__ import annotations

import base64
import os

from db.repository import ProfileRepository


def aes_key() -> bytes | None:
    raw = os.environ.get("PATHWAY_AES_KEY", "")
    if not raw:
        return None
    return base64.b64decode(raw)


def repo() -> ProfileRepository | None:
    key = aes_key()
    if key is None:
        return None
    db_path = os.environ.get("PATHWAY_DB_PATH", "./pathway.sqlite")
    return ProfileRepository(db_path, key)


def saved_candidate_codes(profile_id: str | None) -> set[str]:
    """Saved-candidate O*NET codes for a real (non-sample) profile.

    Returns an empty set for sample profiles (profile_id is None), missing
    PATHWAY_AES_KEY configuration, or a profile_id that no longer exists —
    all non-fatal, "nothing saved" conditions, not errors a caseworker
    should see.
    """
    if profile_id is None:
        return set()
    repository = repo()
    if repository is None:
        return set()
    try:
        return set(repository.get(profile_id).saved_candidate_codes)
    except KeyError:
        return set()


def toggle_saved_candidate(
    profile_id: str,
    occupation_code: str,
    occupation_title: str,
    currently_saved: bool,
) -> None:
    """Flip one occupation's saved state for this profile. No-op if the
    repository isn't reachable (missing env config).

    Saving (not un-saving) is the "mark chosen" action from
    next_phase_plan.md §3.6a: it records an initial 'saved' job_history
    entry, which is what makes the occupation show up on the History tab.
    Un-saving only removes it from saved_candidate_codes — history is an
    append-only log of what happened, so it is never deleted just because
    the caseworker un-saved the candidate later.

    Guarded against duplicate 'saved' entries: re-saving after un-saving
    the same occupation does not add a second entry if history already
    exists for it.
    """
    repository = repo()
    if repository is None:
        return

    codes = saved_candidate_codes(profile_id)
    if currently_saved:
        codes.discard(occupation_code)
    else:
        codes.add(occupation_code)
        existing_history = repository.get_history(profile_id)
        already_recorded = any(
            entry["occupation_code"] == occupation_code for entry in existing_history
        )
        if not already_recorded:
            repository.add_history_entry(
                profile_id, occupation_code, occupation_title, status="saved"
            )

    repository.update_saved_candidates(profile_id, sorted(codes))


def get_history(profile_id: str | None) -> list[dict]:
    """All job_history entries for a profile, newest first.

    Returns an empty list for sample profiles (profile_id is None), missing
    PATHWAY_AES_KEY configuration, or a profile_id that no longer exists —
    all non-fatal, "nothing recorded" conditions, not errors a caseworker
    should see.
    """
    if profile_id is None:
        return []
    repository = repo()
    if repository is None:
        return []
    try:
        return repository.get_history(profile_id)
    except KeyError:
        return []


def record_history_entry(
    profile_id: str,
    occupation_code: str,
    occupation_title: str,
    status: str,
    notes: str = "",
) -> None:
    """Record a new outcome for a saved candidate. No-op if the repository
    isn't reachable (missing env config)."""
    repository = repo()
    if repository is None:
        return
    repository.add_history_entry(profile_id, occupation_code, occupation_title, status, notes)
