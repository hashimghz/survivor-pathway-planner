"""Profile-to-ticket anonymisation: strip PII, preserve non-PII fields."""

from __future__ import annotations

import uuid

from core.crypto import derive_ticket_id
from models import Profile, Ticket


def profile_to_ticket(
    profile: Profile,
    pepper: bytes,
    job_history: list[dict] | None = None,
) -> Ticket:
    """Build the anonymous Ticket the pipeline operates on.

    `job_history` is the profile's job_history rows (db/repository.py's
    `get_history()` shape — plain dicts), fetched by the *caller* before
    calling this. This function stays a pure transform (Profile + pepper ->
    Ticket) and never does its own DB I/O, per next_phase_plan.md §2 — so
    a profile with real history still anonymises correctly even if the
    caller forgets to pass it (defaults to no history, never an error).
    Pydantic coerces each dict into a HistoryEntrySummary, silently
    dropping the `id`/`profile_id` keys those rows carry that have no
    meaning once anonymised.
    """
    ticket_id = derive_ticket_id(str(uuid.uuid4()), pepper)
    # saved_candidate_codes is caseworker curation of engine *output* — it
    # has no place on the engine's *input* payload.
    excluded = {"identity", "saved_candidate_codes"}
    return Ticket(
        ticket_id=ticket_id,
        job_history=job_history or [],
        **profile.model_dump(exclude=excluded),
    )
