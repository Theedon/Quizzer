from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.agent import graph as graph_module
from src.agent.graph import graph_ainvoke


@pytest.mark.asyncio
async def test_on_update_exception_does_not_abort_graph(monkeypatch):
    """A raising on_update callback should be caught and logged, not propagated."""

    fake_updates = [
        {"page_ingestor": {"pdf_pages_data": []}},
        {"chunking": {"crawled_chunks": []}},
        {"aggregator": {"final_quiz": []}},
    ]

    fake_final_state = AsyncMock()
    fake_final_state.values = {"final_quiz": []}

    async def fake_astream(initial_state, *, config, stream_mode):
        for update in fake_updates:
            yield update

    mock_graph = AsyncMock()
    mock_graph.astream = fake_astream
    mock_graph.aget_state = AsyncMock(return_value=fake_final_state)

    monkeypatch.setattr(graph_module, "build_graph", lambda: mock_graph)

    # on_update that always raises
    async def exploding_callback(update):
        raise RuntimeError("UI slot error")

    # Should NOT raise despite the callback exploding on every update
    result = await graph_ainvoke(
        pdf_url_or_base64="test.pdf",
        on_update=exploding_callback,
    )
    assert result == fake_final_state


@pytest.mark.asyncio
async def test_on_update_healthy_callback_still_receives_updates(monkeypatch):
    """A well-behaved on_update callback should still receive every update."""

    fake_updates = [
        {"page_ingestor": {"pdf_pages_data": []}},
        {"chunking": {"crawled_chunks": []}},
        {"aggregator": {"final_quiz": []}},
    ]

    fake_final_state = AsyncMock()
    fake_final_state.values = {"final_quiz": []}

    async def fake_astream(initial_state, *, config, stream_mode):
        for update in fake_updates:
            yield update

    mock_graph = AsyncMock()
    mock_graph.astream = fake_astream
    mock_graph.aget_state = AsyncMock(return_value=fake_final_state)

    monkeypatch.setattr(graph_module, "build_graph", lambda: mock_graph)

    received: list[dict] = []

    async def good_callback(update):
        received.append(update)

    await graph_ainvoke(
        pdf_url_or_base64="test.pdf",
        on_update=good_callback,
    )

    assert len(received) == len(fake_updates)
