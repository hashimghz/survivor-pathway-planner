"""SQLite repository for encrypted Profile persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid

from core.crypto import decrypt_pii, encrypt_pii
from models import Identity, Profile

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    encrypted_identity BLOB NOT NULL,
    non_pii_json TEXT NOT NULL,
    preferred_name_plain TEXT NOT NULL,
    current_metro TEXT NOT NULL
);
"""

_CREATE_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_history (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    occupation_code TEXT NOT NULL,
    occupation_title TEXT NOT NULL,
    status TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    caseworker_notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS job_history_profile_idx
    ON job_history(profile_id);
"""

# Valid status values for job_history entries.
# Ordered from earliest to latest in a typical pathway lifecycle.
HISTORY_STATUSES = (
    "saved",
    "applied",
    "interviewing",
    "offered",
    "accepted",
    "rejected",
    "withdrawn",
)


class ProfileRepository:
    def __init__(self, db_path: str, aes_key: bytes) -> None:
        self._db_path = db_path
        self._aes_key = aes_key
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_CREATE_TABLE_SQL)
            # executescript handles multiple statements (the index + table).
            conn.executescript(_CREATE_HISTORY_TABLE_SQL)
            conn.commit()

    def save(self, profile: Profile) -> str:
        profile_id = str(uuid.uuid4())
        identity_json = profile.identity.model_dump_json()
        encrypted_identity = encrypt_pii(identity_json, self._aes_key)
        non_pii_json = profile.model_dump_json(exclude={"identity"})

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO profiles (
                    id,
                    encrypted_identity,
                    non_pii_json,
                    preferred_name_plain,
                    current_metro
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    encrypted_identity,
                    non_pii_json,
                    profile.identity.preferred_name,
                    profile.current_metro,
                ),
            )
            conn.commit()

        return profile_id

    def get(self, profile_id: str) -> Profile:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT encrypted_identity, non_pii_json
                FROM profiles
                WHERE id = ?
                """,
                (profile_id,),
            ).fetchone()

        if row is None:
            raise KeyError(profile_id)

        identity = Identity.model_validate_json(
            decrypt_pii(row["encrypted_identity"], self._aes_key)
        )
        non_pii = json.loads(row["non_pii_json"])
        return Profile(identity=identity, **non_pii)

    def update_saved_candidates(self, profile_id: str, saved_candidate_codes: list[str]) -> None:
        """Persist the caseworker's saved-candidate list for a profile.

        Only touches `non_pii_json` — never decrypts or rewrites
        `encrypted_identity`. Raises KeyError if profile_id doesn't exist.
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT non_pii_json FROM profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()

            if row is None:
                raise KeyError(profile_id)

            non_pii = json.loads(row["non_pii_json"])
            non_pii["saved_candidate_codes"] = list(saved_candidate_codes)

            conn.execute(
                "UPDATE profiles SET non_pii_json = ? WHERE id = ?",
                (json.dumps(non_pii), profile_id),
            )
            conn.commit()

    def list_summaries(self) -> list[dict]:
        """One summary row per saved profile.

        `preferred_name_plain` is deliberately unencrypted (unlike
        `legal_name`, which only ever lives inside `encrypted_identity`).
        When a caseworker left "Preferred name" blank on the form, that
        column is empty — rather than showing a blank name, this falls
        back to `legal_name` *only at display time*, decrypting just that
        one row. The fallback is never written back to
        `preferred_name_plain`; a real legal name should never end up
        sitting in plaintext on disk just because a different field was
        left blank.
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, preferred_name_plain, current_metro, encrypted_identity
                FROM profiles
                ORDER BY id
                """
            ).fetchall()

        summaries: list[dict] = []
        for row in rows:
            display_name = row["preferred_name_plain"]
            if not display_name:
                identity = Identity.model_validate_json(
                    decrypt_pii(row["encrypted_identity"], self._aes_key)
                )
                display_name = identity.legal_name

            summaries.append(
                {
                    "id": row["id"],
                    "preferred_name": display_name,
                    "current_metro": row["current_metro"],
                }
            )

        return summaries

    def add_history_entry(
        self,
        profile_id: str,
        occupation_code: str,
        occupation_title: str,
        status: str,
        caseworker_notes: str = "",
    ) -> str:
        """Record a pathway outcome for a saved profile.

        Args:
            profile_id: The profile this entry belongs to.
            occupation_code: O*NET occupation code (e.g. '43-4051.00').
            occupation_title: Human-readable title for display without joining.
            status: One of HISTORY_STATUSES — 'saved', 'applied', 'interviewing',
                'offered', 'accepted', 'rejected', 'withdrawn'.
            caseworker_notes: Optional free-text notes about this outcome.

        Returns:
            The new history entry id.

        Raises:
            KeyError: If profile_id does not exist.
            ValueError: If status is not in HISTORY_STATUSES.
        """
        if status not in HISTORY_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {HISTORY_STATUSES}"
            )

        # Verify profile exists before writing history for it.
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT id FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        if row is None:
            raise KeyError(profile_id)

        import datetime
        entry_id = str(uuid.uuid4())
        recorded_at = datetime.datetime.utcnow().isoformat() + "Z"

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO job_history (
                    id, profile_id, occupation_code,
                    occupation_title, status, recorded_at, caseworker_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    profile_id,
                    occupation_code,
                    occupation_title,
                    status,
                    recorded_at,
                    caseworker_notes,
                ),
            )
            conn.commit()

        return entry_id

    def get_history(self, profile_id: str) -> list[dict]:
        """Return all history entries for a profile, newest first.

        Each entry is a plain dict with keys:
            id, profile_id, occupation_code, occupation_title,
            status, recorded_at, caseworker_notes.

        Returns an empty list if no history exists yet — not an error.
        Raises KeyError if the profile itself does not exist.
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT id FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        if row is None:
            raise KeyError(profile_id)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, profile_id, occupation_code, occupation_title,
                       status, recorded_at, caseworker_notes
                FROM job_history
                WHERE profile_id = ?
                ORDER BY recorded_at DESC
                """,
                (profile_id,),
            ).fetchall()

        return [dict(row) for row in rows]