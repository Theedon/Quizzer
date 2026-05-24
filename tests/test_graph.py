import pytest

from src.agent.graph import aggregator
from src.agent.state import FinalQuizItem, GlobalQuizState


def _make_quiz_item(question: str = "Q?") -> FinalQuizItem:
    return FinalQuizItem(
        question=question,
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        answer="A",
        explanation="N/A",
        page_number=1,
        chunk_id="test_chunk",
    )


@pytest.mark.asyncio
async def test_aggregator_does_not_re_emit_quiz_items() -> None:
    """Regression: aggregator must return {} so the add reducer doesn't double quiz items."""
    state = GlobalQuizState(
        pdf_url_or_base64="",
        pdf_pages_data=[],
        crawled_chunks=[],
        final_quiz=[_make_quiz_item("Q1?"), _make_quiz_item("Q2?")],
    )

    result = await aggregator(state)

    assert result == {}, (
        "aggregator returned quiz items — this would cause the add reducer to "
        "append them again, doubling every question in the output"
    )
