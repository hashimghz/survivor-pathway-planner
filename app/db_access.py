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


def toggle_saved_candidate(profile_id: str, occupation_code: str, currently_saved: bool) -> None:
    """Flip one occupation's saved state for this profile. No-op if the
    repository isn't reachable (missing env config)."""
    repository = repo()
    if repository is None:
        return

    codes = saved_candidate_codes(profile_id)
    if currently_saved:
        codes.discard(occupation_code)
    else:
        codes.add(occupation_code)

    repository.update_saved_candidates(profile_id, sorted(codes))
