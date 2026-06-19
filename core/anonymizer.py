"""Profile-to-ticket anonymisation: strip PII, preserve non-PII fields."""

from __future__ import annotations

import uuid

from core.crypto import derive_ticket_id
from models import Profile, Ticket


def profile_to_ticket(profile: Profile, pepper: bytes) -> Ticket:
    ticket_id = derive_ticket_id(str(uuid.uuid4()), pepper)
    # saved_candidate_codes is caseworker curation of engine *output* — it
    # has no place on the engine's *input* payload.
    excluded = {"identity", "saved_candidate_codes"}
    return Ticket(ticket_id=ticket_id, **profile.model_dump(exclude=excluded))
