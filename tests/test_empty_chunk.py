import pytest

from src.agent.graph import MAX_SUBGRAPH_ITER, quiz_reviewer, should_regenerate_quiz


async def test_reviewer_sets_max_iter_for_empty_quiz():
    """When quiz is empty, reviewer should set iter_count to MAX_SUBGRAPH_ITER to skip retries."""
    state = {
        "chunk": {
            "chunk_text": "",
            "page_number": 1,
            "chunk_id": "1_abc",
        },
        "quiz": [],
        "iter_count": 0,
        "is_quiz_relevant": False,
    }
    result = await quiz_reviewer(state)
    assert result["iter_count"] == MAX_SUBGRAPH_ITER
    assert result["is_quiz_relevant"] is False


async def test_should_regenerate_completes_at_max_iter():
    """When iter_count equals MAX_SUBGRAPH_ITER, should route to completed."""
    state = {
        "is_quiz_relevant": False,
        "iter_count": MAX_SUBGRAPH_ITER,
    }
    result = await should_regenerate_quiz(state)
    assert result == "completed"


async def test_should_regenerate_uses_not_instead_of_is_false():
    """Falsy values other than literal False should also route correctly."""
    state = {
        "is_quiz_relevant": 0,  # falsy but not False
        "iter_count": 0,
    }
    result = await should_regenerate_quiz(state)
    assert result == "regenerate"
