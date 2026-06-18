"""Load survivor profiles and occupations from raw data files."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

from models import Occupation, OccupationSkill, Profile


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


def load_occupations(path: Path | str = "data/raw/occupations.csv") -> list[Occupation]:
    df = pd.read_csv(path)
    return [_row_to_occupation(row) for _, row in df.iterrows()]
