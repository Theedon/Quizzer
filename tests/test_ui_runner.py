from __future__ import annotations

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
    async def fake_graph_ainvoke(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner_module, "graph_ainvoke", fake_graph_ainvoke)

    snapshots: list[GenerationProgress] = []

    with pytest.raises(RuntimeError):
        await run_generation("dummy.pdf", lambda s: snapshots.append(s))

    assert snapshots[-1].phase == "error"
    assert "boom" in (snapshots[-1].error or "")


@pytest.mark.asyncio
async def test_run_generation_supports_async_callback(monkeypatch):
    """on_progress can be either sync or async; the runner awaits when needed."""

    async def fake_graph_ainvoke(*_args, on_update=None, **_kwargs):
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
