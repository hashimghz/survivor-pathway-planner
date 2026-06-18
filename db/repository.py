"""SQLite repository for encrypted Profile persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid

from core.crypto import decrypt_pii, encrypt_pii
from models import Identity, Profile

_CREATE_TABLE_SQL = """
CREATE TABLE profiles (
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

    def list_summaries(self) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, preferred_name_plain, current_metro
                FROM profiles
                ORDER BY id
                """
            ).fetchall()

        return [
            {
                "id": row["id"],
                "preferred_name": row["preferred_name_plain"],
                "current_metro": row["current_metro"],
            }
            for row in rows
        ]
