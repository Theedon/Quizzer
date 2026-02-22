from typing import Any, Final, Literal

from langchain.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agent.llm import MODEL as LLM
from src.agent.prompts import GENERATE_QUIZ_PROMPT, REVIEW_QUIZ_PROMPT
from src.agent.schemas import MultipleQuiz, ReviewedQuiz
from src.agent.state import SubGraphState
from src.core import logger

# ============================================================================
# SUBGRAPH
# ============================================================================

MAX_SUBGRAPH_ITER: Final = 3


async def build_generator_subgraph() -> CompiledStateGraph:
    subgraph_builder = StateGraph(SubGraphState)

    subgraph_builder.add_node(node="quiz_generator", action=quiz_generator)
    subgraph_builder.add_node(node="quiz_reviewer", action=quiz_reviewer)

    subgraph_builder.add_edge(start_key=START, end_key="quiz_generator")
    subgraph_builder.add_edge(start_key="quiz_generator", end_key="quiz_reviewer")
    subgraph_builder.add_conditional_edges(
        source="quiz_reviewer",
        path=should_regenerate_quiz,
        path_map={
            "regenerate": "quiz_generator",
            "completed": END,
        },
    )

    subgraph = subgraph_builder.compile()
    return subgraph


async def quiz_generator(state: SubGraphState) -> dict[str, Any]:
    """Generate quiz from chunk using LLM."""

    logger.info("*****SUBGRAPH - QUIZ GENERATOR*****")

    chunk_text = state.get("chunk", {}).get("chunk_text", "")
    logger.debug(f"Generating quiz for chunk of length: {len(chunk_text)}...")

    if not chunk_text or not chunk_text.strip():
        # nothing to ask the model about – avoid empty‑content request
        logger.warning(
            "quiz_generator called with empty chunk_text; " "skipping LLM invocation"
        )
        return {"quiz": []}

    structured_llm = LLM.with_structured_output(MultipleQuiz)

    generator_prompt = GENERATE_QUIZ_PROMPT.format(chunk=chunk_text)
    generator_response = await structured_llm.ainvoke(
        [HumanMessage(content=generator_prompt)]
    )
    logger.debug(f"Generated quiz response: {generator_response}")
    quizzes: list[dict[str, Any]] = []
    if isinstance(generator_response, MultipleQuiz):
        quizzes = [quiz.model_dump() for quiz in generator_response.quizzes]
    elif isinstance(generator_response, dict):
        quizzes = generator_response.get("quizzes", [])

    # add page number to each quiz object for traceability
    quizzes = [
        {**quiz, "page_number": state.get("chunk", {}).get("page_number", 0)}
        for quiz in quizzes
    ]

    return {
        "quiz": quizzes,
    }


async def quiz_reviewer(state: SubGraphState) -> dict[str, Any]:
    """Review the generated quiz for relevance and quality, and determine if regeneration is needed."""

    logger.info("*****SUBGRAPH - QUIZ REVIEWER*****")
    chunk_text = state.get("chunk", {}).get("chunk_text", "")
    quiz = state.get("quiz", [])

    if not quiz:
        logger.warning(
            "quiz_reviewer called with empty quiz; "
            "skipping LLM invocation and marking as not relevant"
        )
        return {
            "is_quiz_relevant": False,
            "iter_count": state.get("iter_count", 0) + 1,
        }
    structured_llm = LLM.with_structured_output(ReviewedQuiz)

    review_prompt = REVIEW_QUIZ_PROMPT.format(
        chunk=chunk_text,
        quiz=str(quiz),
    )

    review_response = await structured_llm.ainvoke(
        [HumanMessage(content=review_prompt)]
    )

    logger.debug(f"Quiz review response: {review_response}")
    is_relevant = False
    if isinstance(review_response, ReviewedQuiz):
        is_relevant = review_response.is_relevant
    elif isinstance(review_response, dict):
        is_relevant = review_response.get("is_relevant", False)

    return {
        "is_quiz_relevant": is_relevant,
        "iter_count": state.get("iter_count", 0) + 1,
    }


async def should_regenerate_quiz(
    state: SubGraphState,
) -> Literal["regenerate", "completed"]:
    logger.trace(f"Quiz relevance: {state.get('is_quiz_relevant', False)}, ")
    if (
        state.get("is_quiz_relevant", False) is False
        and state.get("iter_count", 0) < MAX_SUBGRAPH_ITER
    ):
        return "regenerate"
    else:
        return "completed"
