"""L1 skill mapper: map free-text skills to O*NET skill clusters via sentence embeddings.

Uses BAAI/bge-small-en-v1.5 embeddings cached in data/processed/skill_embeddings.npz.
Heavy imports (sentence_transformers) are lazy-loaded to avoid slowing pytest startup.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CACHE_PATH = _PROJECT_ROOT / "data" / "processed" / "skill_embeddings.npz"
_EXPECTED_MODEL = "BAAI/bge-small-en-v1.5"

# Module-level globals for lazy caching
_model = None
_cache_ids: np.ndarray | None = None
_cache_names: np.ndarray | None = None
_cache_embeddings: np.ndarray | None = None


def _load_cache() -> None:
    """Load the pre-built skill embedding cache from disk."""
    global _cache_ids, _cache_names, _cache_embeddings  # noqa: PLW0603

    data = np.load(str(_CACHE_PATH), allow_pickle=True)
    stored_model = str(data["model_name"][0])
    if stored_model != _EXPECTED_MODEL:
        msg = (
            f"Skill embedding cache was built with '{stored_model}' "
            f"but expected '{_EXPECTED_MODEL}'. Rebuild with build_skill_corpus.py."
        )
        raise RuntimeError(msg)

    _cache_ids = data["ids"]
    _cache_names = data["names"]
    _cache_embeddings = data["embeddings"]


def _load_model() -> None:
    """Lazy-load the sentence-transformer model."""
    global _model  # noqa: PLW0603

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(_EXPECTED_MODEL)


def warm() -> None:
    """Preload model and cache. Call at app startup to avoid first-request latency."""
    if _cache_ids is None:
        _load_cache()
    if _model is None:
        _load_model()


def map_skills(
    skill_texts: list[str],
    top_k: int = 5,
    threshold: float = 0.55,
) -> list[dict]:
    """Map free-text skills to O*NET skill clusters.

    Args:
        skill_texts: Free-text skill descriptions from the survivor profile.
        top_k: Maximum matches to return per input skill.
        threshold: Minimum cosine similarity to include a match. Default 0.55
            is a starting value, tunable based on verification.

    Returns:
        A list of dicts, one per input skill::

            {
                "input": "customer service",
                "matches": [
                    {"onet_id": "2.B.1.a", "onet_name": "Social Perceptiveness", "confidence": 0.83},
                    ...
                ]
            }

        ``matches`` may be empty if no O*NET skill scores above ``threshold``.
        Sorted by confidence descending. Capped at ``top_k``.
    """
    warm()

    # Encode inputs with the same model and normalization as the cache
    input_embeddings = _model.encode(skill_texts, normalize_embeddings=True)

    # Cosine similarity via matrix multiply (both sides L2-normalized)
    similarities = input_embeddings @ _cache_embeddings.T  # (n_inputs, 35)

    results: list[dict] = []
    for i, text in enumerate(skill_texts):
        scores = similarities[i]
        # Indices where score exceeds threshold, sorted by score descending
        above = np.where(scores >= threshold)[0]
        ranked = above[np.argsort(-scores[above])][:top_k]

        matches = [
            {
                "onet_id": str(_cache_ids[j]),
                "onet_name": str(_cache_names[j]),
                "confidence": round(float(scores[j]), 4),
            }
            for j in ranked
        ]
        results.append({"input": text, "matches": matches})

    return results
