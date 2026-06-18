#!/usr/bin/env python3
"""Verify models/__init__.py matches the checked-in schema hash."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "models" / "__init__.py"
HASH_FILE = ROOT / "models" / ".schema-hash"


def compute_hash() -> str:
    return hashlib.sha256(SCHEMA_FILE.read_bytes()).hexdigest()


def main() -> int:
    expected = HASH_FILE.read_text(encoding="utf-8").strip()
    actual = compute_hash()
    if actual == expected:
        print(f"Schema hash OK: {actual}")
        return 0
    print(f"Schema hash mismatch.\n  expected: {expected}\n  actual:   {actual}")
    print("Update models/.schema-hash with `make update-schema-hash` in a contract-change PR.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
