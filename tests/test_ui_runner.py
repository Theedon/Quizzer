from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.ui import runner as runner_module
from src.ui.runner import GenerationProgress, run_generation


def _quiz(qid: str, page: int) -> dict:
    return {
        "question": f"q-{qid}",
        "option_a": "a",
        "option_b": "b",
        "option_c": "c",
        "option_d": "d",
        "answer": "A",
        "explanation": "because",
        "page_number": page,
        "chunk_id": qid,
    }


@pytest.mark.asyncio
async def test_run_generation_maps_updates_to_progress(monkeypatch):
    fake_updates = [
        {"page_ingestor": {"pdf_pages_data": [{"page_number": i, "content": ""} for i in range(1, 4)]}},
        {"chunking": {"crawled_chunks": [{}, {}]}},
        {"subgraph_generator": {"final_quiz": [_quiz("c1", 1)]}},
        {"subgraph_generator": {"final_quiz": [_quiz("c2", 2)]}},
        {"aggregator": {"final_quiz": [_quiz("c1", 1), _quiz("c2", 2)]}},
    ]

    async def fake_graph_ainvoke(
        pdf_url_or_base64: str,
        thread_id: str | None = None,
        on_update=None,
        cancel_event=None,
        provider: str | None = None,
        model_name: str | None = None,
        concurrency: int | None = None,
    ) -> Any:
        for update in fake_updates:
            if on_update is not None:
                await on_update(update)
        return {"final_quiz": [_quiz("c1", 1), _quiz("c2", 2)]}

    monkeypatch.setattr(runner_module, "graph_ainvoke", fake_graph_ainvoke)

    snapshots: list[GenerationProgress] = []

    def push(snap: GenerationProgress) -> None:
        snapshots.append(snap)

    result = await run_generation("dummy.pdf", push)

    assert len(result) == 2
    phases = [s.phase for s in snapshots]
    assert phases[0] == "ingesting"
    assert "chunking" in phases
    assert "generating" in phases
    assert "aggregating" in phases
    assert phases[-1] == "done"

    final = snapshots[-1]
    assert final.total_pages == 3
    assert final.total_chunks == 2
    assert final.chunks_done == 2
    assert len(final.quizzes) == 2
    assert final.fraction == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_run_generation_records_error(monkeypatch):
    async def fake_graph_ainvoke(
        *_args,
        on_update=None,
        cancel_event=None,
        provider=None,
        model_name=None,
        concurrency=None,
        **_kwargs,
    ):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner_module, "graph_ainvoke", fake_graph_ainvoke)

    snapshots: list[GenerationProgress] = []

    with pytest.raises(RuntimeError):
        await run_generation("dummy.pdf", lambda s: snapshots.append(s))

    assert snapshots[-1].phase == "error"
    assert "boom" in (snapshots[-1].error or "")


def test_fraction_zero_when_total_chunks_unknown():
    """fraction returns 0.0 when total_chunks is 0 (ingesting/chunking phases)."""
    p = GenerationProgress(phase="ingesting", total_chunks=0, chunks_done=0)
    assert p.fraction == 0.0

    p = GenerationProgress(phase="chunking", total_pages=5, total_chunks=0)
    assert p.fraction == 0.0


@pytest.mark.asyncio
async def test_run_generation_supports_async_callback(monkeypatch):
    """on_progress can be either sync or async; the runner awaits when needed."""

    async def fake_graph_ainvoke(
        *_args, on_update=None, cancel_event=None, provider=None, model_name=None, concurrency=None, **_kwargs
    ):
        if on_update is not None:
            await on_update({"page_ingestor": {"pdf_pages_data": [{}]}})
            await on_update({"chunking": {"crawled_chunks": [{}]}})
            await on_update({"subgraph_generator": {"final_quiz": [_quiz("c1", 1)]}})
            await on_update({"aggregator": {"final_quiz": [_quiz("c1", 1)]}})
        return {"final_quiz": [_quiz("c1", 1)]}

    monkeypatch.setattr(runner_module, "graph_ainvoke", fake_graph_ainvoke)

    snapshots: list[GenerationProgress] = []

    async def push(snap: GenerationProgress) -> None:
        snapshots.append(snap)

    result = await run_generation("dummy.pdf", push)

    assert len(result) == 1
    assert snapshots[-1].phase == "done"


@pytest.mark.asyncio
async def test_run_generation_cancels_early(monkeypatch):
    """When cancel_event is set, generation stops and returns partial results."""
    cancel_event = asyncio.Event()

    fake_updates = [
        {"page_ingestor": {"pdf_pages_data": [{"page_number": i, "content": ""} for i in range(1, 4)]}},
        {"chunking": {"crawled_chunks": [{}, {}, {}, {}]}},
        {"subgraph_generator": {"final_quiz": [_quiz("c1", 1)]}},
        # cancel_event will be set after the first subgraph update
        {"subgraph_generator": {"final_quiz": [_quiz("c2", 2)]}},
        {"subgraph_generator": {"final_quiz": [_quiz("c3", 3)]}},
        {"subgraph_generator": {"final_quiz": [_quiz("c4", 4)]}},
        {"aggregator": {"final_quiz": [_quiz("c1", 1), _quiz("c2", 2), _quiz("c3", 3), _quiz("c4", 4)]}},
    ]

    call_count = 0

    async def fake_graph_ainvoke(
        pdf_url_or_base64: str,
        thread_id: str | None = None,
        on_update=None,
        cancel_event: asyncio.Event | None = None,
        provider: str | None = None,
        model_name: str | None = None,
        concurrency: int | None = None,
    ) -> Any:
        nonlocal call_count
        for update in fake_updates:
            if cancel_event is not None and cancel_event.is_set():
                break
            if on_update is not None:
                await on_update(update)
            call_count += 1
            # Set cancel after first subgraph_generator update
            if call_count == 3:
                cancel_event.set()
        return {"final_quiz": [_quiz("c1", 1)]}

    monkeypatch.setattr(runner_module, "graph_ainvoke", fake_graph_ainvoke)

    snapshots: list[GenerationProgress] = []

    def push(snap: GenerationProgress) -> None:
        snapshots.append(snap)

    result = await run_generation("dummy.pdf", push, cancel_event=cancel_event)

    # Should return partial results (only what was collected before cancellation)
    assert len(result) >= 1
    assert len(result) < 4  # not all 4 chunks completed

    # Final snapshot should be "done"
    assert snapshots[-1].phase == "done"

    # The quizzes returned should match what was collected
    assert len(result) == len(snapshots[-1].quizzes)
