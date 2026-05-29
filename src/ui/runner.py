from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langgraph.types import StateSnapshot

from ..agent.graph import graph_ainvoke
from ..agent.state import FinalQuizItem
from ..core import logger

Phase = Literal[
    "idle", "ingesting", "chunking", "generating", "aggregating", "done", "error"
]


class TokenCounterCallback(AsyncCallbackHandler):
    def __init__(self) -> None:
        self.total_tokens: int = 0

    async def on_llm_end(self, response: LLMResult, **kwargs: object) -> None:
        for gen_list in response.generations:
            for gen in gen_list:
                msg = getattr(gen, "message", None)
                usage = getattr(msg, "usage_metadata", None) if msg else None
                if usage:
                    self.total_tokens += usage.get("total_tokens", 0)
                    return
        # provider-specific fallback
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            self.total_tokens += usage.get("total_tokens", 0)


@dataclass
class GenerationProgress:
    phase: Phase = "idle"
    total_pages: int = 0
    total_chunks: int = 0
    chunks_done: int = 0
    quizzes: list[FinalQuizItem] = field(default_factory=list)
    error: str | None = None
    total_tokens: int = 0

    @property
    def fraction(self) -> float:
        if self.total_chunks <= 0:
            return 0.0
        return min(self.chunks_done / self.total_chunks, 1.0)


OnProgress = Callable[[GenerationProgress], Awaitable[None] | None]


async def run_generation(
    pdf_path: str,
    on_progress: OnProgress,
    cancel_event: asyncio.Event | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    concurrency: int | None = None,
    api_key: str | None = None,
) -> list[FinalQuizItem]:
    token_counter = TokenCounterCallback()
    progress = GenerationProgress(phase="ingesting")
    await _emit(on_progress, progress)

    cancelled = False

    async def on_update(update: dict) -> None:
        nonlocal cancelled
        for node_name, node_update in update.items():
            if not isinstance(node_update, dict):
                continue

            if node_name == "page_ingestor":
                pages = node_update.get("pdf_pages_data", []) or []
                progress.total_pages = len(pages)
                progress.phase = "chunking"

            elif node_name == "chunking":
                chunks = node_update.get("crawled_chunks", []) or []
                progress.total_chunks = len(chunks)
                progress.phase = "generating"

            elif node_name == "subgraph_generator":
                new_items = node_update.get("final_quiz", []) or []
                progress.quizzes.extend(new_items)
                progress.chunks_done += 1
                progress.phase = "generating"

            elif node_name == "aggregator":
                progress.phase = "aggregating"

        progress.total_tokens = token_counter.total_tokens
        await _emit(on_progress, progress)

        if cancel_event is not None and cancel_event.is_set():
            cancelled = True

    try:
        result = await graph_ainvoke(
            pdf_url_or_base64=pdf_path,
            on_update=on_update,
            cancel_event=cancel_event,
            provider=provider,
            model_name=model_name,
            concurrency=concurrency,
            api_key=api_key,
            callbacks=[token_counter],
        )
    except Exception as exc:
        logger.exception("Generation failed")
        progress.phase = "error"
        progress.error = str(exc)
        await _emit(on_progress, progress)
        raise

    if cancelled or (cancel_event is not None and cancel_event.is_set()):
        logger.info("Generation cancelled by user")
        progress.phase = "done"
        await _emit(on_progress, progress)
        return list(progress.quizzes)

    state_values = result.values if isinstance(result, StateSnapshot) else result
    final_quiz: list[FinalQuizItem] = list(state_values.get("final_quiz", []) or [])

    progress.quizzes = final_quiz
    progress.total_tokens = token_counter.total_tokens
    if progress.total_chunks:
        progress.chunks_done = progress.total_chunks
    progress.phase = "done"
    await _emit(on_progress, progress)

    return final_quiz


async def _emit(on_progress: OnProgress, progress: GenerationProgress) -> None:
    snapshot = GenerationProgress(
        phase=progress.phase,
        total_pages=progress.total_pages,
        total_chunks=progress.total_chunks,
        chunks_done=progress.chunks_done,
        quizzes=list(progress.quizzes),
        error=progress.error,
        total_tokens=progress.total_tokens,
    )
    result = on_progress(snapshot)
    if result is not None:
        await result
