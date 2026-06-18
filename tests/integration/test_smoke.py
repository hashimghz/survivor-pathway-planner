"""Integration tests for the full pipeline."""

from __future__ import annotations

import pytest

from models import Ticket


@pytest.mark.integration
@pytest.mark.xfail(reason="engine.pipeline.run not implemented yet")
def test_pipeline_smoke(stub_ticket: Ticket) -> None:
    """End-to-end smoke test; xfail until engine.pipeline is implemented."""
    from engine.pipeline import run

    result = run(stub_ticket)
    assert result.ticket_id == stub_ticket.ticket_id
