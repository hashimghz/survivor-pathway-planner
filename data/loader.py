"""Load client profiles and occupations from raw data files."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

from models import Occupation, OccupationSkill, Profile

_DEFAULT_OCCUPATIONS_PATH = "data/raw/occupations.csv"

# Module-level cache, keyed by path. The occupations reference data never
# changes during the process's life, so it's parsed once and reused —
# mirrors the lazy-cache pattern in engine/l1_skill_mapper.py. Deliberately
# plain Python (no Streamlit import here) so this module stays usable
# outside the app, e.g. from tests and scripts.
_occupations_cache: dict[str, list[Occupation]] = {}


def load_survivors(path: Path | str = "data/raw/survivors.json") -> list[Profile]:
    with Path(path).open(encoding="utf-8") as f:
        return [Profile.model_validate(s) for s in json.load(f)]


def _row_to_occupation(row: pd.Series) -> Occupation:
    skills_value = row["skills"]
    if pd.notna(skills_value):
        skills = [OccupationSkill(**skill) for skill in ast.literal_eval(skills_value)]
    else:
        skills = []

    return Occupation(
        code=row["code"],
        title=row["title"],
        description=row["description"] if pd.notna(row["description"]) else "",
        job_zone=row["job_zone"] if pd.notna(row["job_zone"]) else None,
        education_level=row["education_level"] if pd.notna(row["education_level"]) else None,
        contact_with_others=row["contact_with_others"]
        if pd.notna(row["contact_with_others"])
        else None,
        physical_proximity=row["physical_proximity"]
        if pd.notna(row["physical_proximity"])
        else None,
        violence_exposure=row["violence_exposure"]
        if pd.notna(row["violence_exposure"])
        else None,
        public_facing=row["public_facing"] if pd.notna(row["public_facing"]) else None,
        schedule_irregularity=row["schedule_irregularity"]
        if pd.notna(row["schedule_irregularity"])
        else None,
        isolated_workplace=bool(row["isolated_workplace"])
        if pd.notna(row["isolated_workplace"])
        else False,
        high_surveillance=bool(row["high_surveillance"])
        if pd.notna(row["high_surveillance"])
        else False,
        median_wage_annual=row["median_wage_annual"]
        if pd.notna(row["median_wage_annual"])
        else None,
        wage_pct10_annual=row["wage_pct10_annual"]
        if pd.notna(row["wage_pct10_annual"])
        else None,
        wage_pct90_annual=row["wage_pct90_annual"]
        if pd.notna(row["wage_pct90_annual"])
        else None,
        median_wage_hourly=row["median_wage_hourly"]
        if pd.notna(row["median_wage_hourly"])
        else None,
        total_employment=row["total_employment"] if pd.notna(row["total_employment"]) else None,
        skills=skills,
        training_required=row["training_required"] if pd.notna(row["training_required"]) else None,
    )


def _load_occupations_uncached(path: Path | str) -> list[Occupation]:
    df = pd.read_csv(path)
    return [_row_to_occupation(row) for _, row in df.iterrows()]


def load_occupations(path: Path | str = _DEFAULT_OCCUPATIONS_PATH) -> list[Occupation]:
    """Load occupations, parsed once per unique path and cached for the
    life of the process.

    Previously this re-read and re-parsed the full CSV (988 rows, each
    through pydantic validation) on every call — including once per
    pipeline run, since engine/pipeline.py calls this unconditionally.
    The data never changes at runtime, so that was pure waste. Callers
    that need to force a fresh read (e.g. tests against a different file)
    can still do so by passing a different `path`.
    """
    key = str(path)
    if key not in _occupations_cache:
        _occupations_cache[key] = _load_occupations_uncached(path)
    return _occupations_cache[key]


def warm(path: Path | str = _DEFAULT_OCCUPATIONS_PATH) -> None:
    """Eagerly populate the occupations cache.

    Call at app startup so the first real pipeline run doesn't pay the
    CSV-parse cost — mirrors engine.l1_skill_mapper.warm().
    """
    load_occupations(path)
