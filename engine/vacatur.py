"""Criminal-record relief pathways: post-conviction vacatur for trafficking
clients.

Per the Polaris National Survivor Study, criminal records from coerced
activity are the largest documented employment barrier for this population.
Several states let clients petition a court to vacate convictions for
offenses committed as a direct result of being trafficked. This module is a
keyed lookup from (jurisdiction, record categories) to those pathways.

Wording is deliberately non-prescriptive: "pathway available," "refer to
legal aid." Never instructive on filing strategy — that's legal advice, and
out of scope (see project handoff, Section 8).

Public entry: ``applicable_pathways(...) -> list[dict]``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Jurisdiction lookup. Keyed by two-letter state code. Citations verified
# against current statute text and legal-aid summaries (see PR description
# for sources); re-verify before relying on this for anything beyond a demo.
# ---------------------------------------------------------------------------

_PATHWAYS: dict[str, dict[str, str]] = {
    "FL": {
        "statute": "Fla. Stat. §943.0583",
        "title": "Petition to vacate convictions for human trafficking clients",
        "rationale": (
            "Florida law lets clients petition the court to vacate "
            "convictions, arrests, and related records for offenses "
            "committed as a direct result of being a victim of human "
            "trafficking."
        ),
        "next_step": "Refer to a local legal aid organization for petition preparation.",
    },
    "NY": {
        "statute": "N.Y. Crim. Proc. Law §440.10(1)(i)",
        "title": "Motion to vacate judgment for trafficking clients",
        "rationale": (
            "New York law lets clients move to vacate a judgment for an "
            "offense where participation was a result of having been a "
            "victim of trafficking."
        ),
        "next_step": "Refer to a local legal aid organization for motion preparation.",
    },
    "CA": {
        "statute": "Cal. Penal Code §236.14",
        "title": "Petition for vacatur of convictions for trafficking clients",
        "rationale": (
            "California law lets clients petition to vacate a "
            "nonviolent-offense conviction or arrest that was a direct "
            "result of being a victim of human trafficking."
        ),
        "next_step": "Refer to a local legal aid organization for petition preparation.",
    },
}


def applicable_pathways(
    record_categories: list[str],
    expungement_eligible: list[str],
    jurisdiction: str,
    trafficking_related: bool,
) -> list[dict]:
    """Return applicable post-conviction relief pathways.

    Returns [] when there's nothing to surface: no record, no jurisdiction
    match, or the record isn't flagged as trafficking-related. Never
    fabricates a pathway for an unsupported jurisdiction — silence there is
    intentional, not a bug.

    Each dict in the returned list:
        {
            "statute": "FL §943.0583",
            "title": "Petition to vacate convictions for human trafficking clients",
            "rationale": "Florida law lets clients petition...",
            "next_step": "Refer to a local legal aid organization for petition preparation.",
        }
    """
    if not record_categories or not trafficking_related:
        return []

    del expungement_eligible  # not used to select a pathway; categories are.

    pathway = _PATHWAYS.get(jurisdiction.strip().upper())
    if pathway is None:
        return []

    return [dict(pathway)]
