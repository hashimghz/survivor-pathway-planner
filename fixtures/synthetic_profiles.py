"""Synthetic survivor profiles for tests and golden fixtures."""

from __future__ import annotations

from data.loader import load_survivors
from models import Profile


def synthetic_profiles() -> list[Profile]:
    return load_survivors()
