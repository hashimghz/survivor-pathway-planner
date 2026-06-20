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


class ProfileRepository:
    def __init__(self, db_path: str, aes_key: bytes) -> None:
        self._db_path = db_path
        self._aes_key = aes_key
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_CREATE_TABLE_SQL)
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
