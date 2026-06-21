"""Build skill embedding cache from occupations.csv.

One-shot script. Run manually or call from app startup if cache missing.
Idempotent: if the cache already exists, prints a notice and exits.

Usage:
    uv run python engine/build_skill_corpus.py
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OCCUPATIONS_CSV = PROJECT_ROOT / "data" / "raw" / "occupations.csv"
CACHE_DIR = PROJECT_ROOT / "data" / "processed"
CACHE_FILE = CACHE_DIR / "skill_embeddings.npz"

MODEL_NAME = "BAAI/bge-small-en-v1.5"


def extract_unique_skills(df: pd.DataFrame) -> list[tuple[str, str]]:
    """Extract unique (id, name) tuples from the skills column.

    The skills column contains stringified Python lists of dicts:
        "[{'id': '2.A.1.a', 'name': 'Reading Comprehension'}, ...]"

    Returns a list sorted by id for stable ordering across runs.
    """
    seen: dict[str, str] = {}
    for skills_str in df["skills"].dropna():
        if not isinstance(skills_str, str) or not skills_str.strip():
            continue
        try:
            skills_list = ast.literal_eval(skills_str)
        except (ValueError, SyntaxError):
            # Malformed row — skip rather than crash
            continue
        if not isinstance(skills_list, list):
            continue
        for skill in skills_list:
            if not isinstance(skill, dict):
                continue
            sid = skill.get("id")
            sname = skill.get("name")
            if sid and sname and sid not in seen:
                seen[sid] = sname
    return sorted(seen.items())


def build_cache(force: bool = False) -> None:
    """Build the skill embedding cache.

    Args:
        force: If True, rebuild even when cache exists.
    """
    if CACHE_FILE.exists() and not force:
        print(f"Cache already exists at {CACHE_FILE}.")
        print("Delete it or pass force=True to rebuild.")
        return

    if not OCCUPATIONS_CSV.exists():
        raise FileNotFoundError(
            f"Occupations data not found at {OCCUPATIONS_CSV}"
        )

    print(f"Loading occupations from {OCCUPATIONS_CSV}")
    df = pd.read_csv(OCCUPATIONS_CSV)
    print(f"  loaded {len(df)} occupation rows")

    print("Extracting unique O*NET skills...")
    skills = extract_unique_skills(df)
    if not skills:
        raise RuntimeError("No skills extracted — check CSV format")
    print(f"  found {len(skills)} unique skills")

    ids = np.array([s[0] for s in skills], dtype=object)
    names = np.array([s[1] for s in skills], dtype=object)

    print(f"Loading embedding model: {MODEL_NAME}")
    print("  (first run downloads ~130 MB)")
    model = SentenceTransformer(MODEL_NAME)

    print("Embedding skill names...")
    embeddings = model.encode(
        [s[1] for s in skills],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype(np.float32)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        CACHE_FILE,
        ids=ids,
        names=names,
        embeddings=embeddings,
        model_name=np.array([MODEL_NAME], dtype=object),
    )

    size_kb = CACHE_FILE.stat().st_size / 1024
    print(f"\nSaved cache to {CACHE_FILE}")
    print(f"  embedding shape: {embeddings.shape}")
    print(f"  file size: {size_kb:.1f} KB")


if __name__ == "__main__":
    build_cache()
