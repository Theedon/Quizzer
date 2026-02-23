import os
from typing import Any, Final, Literal, cast

from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy, Send

from src.agent.llm import MODEL as LLM
from src.agent.prompts import GENERATE_QUIZ_PROMPT, REVIEW_QUIZ_PROMPT
from src.agent.schemas import MultipleQuiz, ReviewedQuiz
from src.agent.state import GlobalQuizState, SubGraphState
from src.agent.utils import chunk_pdf_content, ingest_pdf
from src.core import logger

# ============================================================================
# MAIN GRAPH
# ============================================================================


async def build_graph() -> CompiledStateGraph:

    memory = InMemorySaver()
    builder = StateGraph(GlobalQuizState)

    # Nodes
    builder.add_node(node="page_ingestor", action=page_ingestor)
    builder.add_node(node="chunking", action=chunking)
    builder.add_node(
        node="subgraph_generator",
        action=subgraph_generator,
    )

    builder.add_node(node="aggregator", action=aggregator)

    # Edges
    builder.add_edge(start_key=START, end_key="page_ingestor")
    builder.add_edge(start_key="page_ingestor", end_key="chunking")
    builder.add_conditional_edges(source="chunking", path=route_chunks_to_subgraph)
    builder.add_edge(start_key="subgraph_generator", end_key="aggregator")

    builder.add_edge(start_key="aggregator", end_key=END)

    # Compile graph
    graph = builder.compile(checkpointer=memory)
    # graph.get_graph().draw_mermaid_png(output_file_path="graph.png")

    return graph


async def page_ingestor(state: GlobalQuizState) -> dict[str, Any]:
    """
    Receives raw PDF content and prepares it for crawling/chunking.
    """

    logger.info("--------🚦 NODE - PAGE INGESTOR--------")
    pdf_content: list[dict[str, Any]] = ingest_pdf(state.get("pdf_url_or_base64", ""))
    logger.debug(f"Ingested PDF content length: {len(pdf_content)} pages")
    # logger.debug(f"Sample of PDF content: {pdf_content[:2]}")

    return {
        "pdf_pages_data": pdf_content,
    }


async def chunking(state: GlobalQuizState) -> dict[str, Any]:
    """
    Breaks down PDF into processable chunks for quiz generation.
    """
    logger.info("--------🚦 NODE - CHUNKING--------")
    chunks = chunk_pdf_content(state.get("pdf_pages_data", []))
    logger.debug(f"Generated {len(chunks)} chunks from PDF content -< {chunks[:2]}")
    return {"crawled_chunks": chunks}


def route_chunks_to_subgraph(state: GlobalQuizState) -> list[Send]:
    chunks = state.get("crawled_chunks", [])
    return [Send("subgraph_generator", {"chunk": chunk}) for chunk in chunks]


async def subgraph_generator(state: SubGraphState) -> dict[str, Any]:
    """
    Generate quiz from chunk using LLM.
    """
    subgraph = await build_generator_subgraph()
    subgraph_state = SubGraphState(
        chunk=state.get("chunk", {}),
        quiz=[],
        iter_count=0,
        is_quiz_relevant=False,
    )
    logger.info(
        f"firing up subgraph generator for chunk_id: {state.get('chunk', {}).get('chunk_id', 'unknown')}"
    )
    subgraph_result = await subgraph.ainvoke(subgraph_state)
    return {"final_quiz": subgraph_result.get("quiz", [])}


async def aggregator(state: GlobalQuizState) -> dict[str, Any]:
    logger.info("--------🚦 NODE - AGGREGATOR--------")
    logger.trace(f"Aggregating quiz results from state: {state.get('final_quiz', [])}")
    return {"final_quiz": state.get("final_quiz", [])}


# ============================================================================
# SUBGRAPH
# ============================================================================

MAX_SUBGRAPH_ITER: Final = 3

retry_policy = RetryPolicy(jitter=True)


async def build_generator_subgraph() -> CompiledStateGraph:
    subgraph_builder = StateGraph(SubGraphState)

    subgraph_builder.add_node(
        node="quiz_generator", action=quiz_generator, retry_policy=retry_policy
    )
    subgraph_builder.add_node(
        node="quiz_reviewer", action=quiz_reviewer, retry_policy=retry_policy
    )

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

    normalized_quizzes: list[dict[str, Any]] = []
    for quiz in quizzes:
        options = quiz.get("options", {}) if isinstance(quiz, dict) else {}
        answer = (
            str(quiz.get("answer", "")).strip().upper()
            if isinstance(quiz, dict)
            else ""
        )
        normalized_quiz = {
            "question": quiz.get("question", "") if isinstance(quiz, dict) else "",
            "option_a": quiz.get("option_a")
            or (options.get("A") if isinstance(options, dict) else ""),
            "option_b": quiz.get("option_b")
            or (options.get("B") if isinstance(options, dict) else ""),
            "option_c": quiz.get("option_c")
            or (options.get("C") if isinstance(options, dict) else ""),
            "option_d": quiz.get("option_d")
            or (options.get("D") if isinstance(options, dict) else ""),
            "answer": answer if answer in {"A", "B", "C", "D"} else "A",
        }
        normalized_quizzes.append(normalized_quiz)

    # add page number and chunk id to each quiz object for traceability
    quizzes = [
        {
            **quiz,
            "page_number": state.get("chunk", {}).get("page_number", 0),
            "chunk_id": state.get("chunk", {}).get("chunk_id", 0),
        }
        for quiz in normalized_quizzes
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


# ============================================================================
# GRAPH INVOCATION
# ============================================================================


async def graph_ainvoke(
    pdf_url_or_base64: str = "temp/sample.pdf",
    thread_id: str = f"qthread_{os.urandom(8).hex()}",
) -> GlobalQuizState:
    initial_state: GlobalQuizState = GlobalQuizState(
        pdf_url_or_base64=pdf_url_or_base64,
        pdf_pages_data=[{}],
        crawled_chunks=[],
        final_quiz=[],
    )

    graph = await build_graph()
    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id,
            "max_concurrency": 3,
        }
    }

    logger.info("--------🚦 graph execution stream started--------")
    final_state: GlobalQuizState = initial_state
    async for update in graph.astream(
        initial_state,
        config=config,
        stream_mode="updates",
    ):
        summary = {
            node_name: list(node_update.keys()) if isinstance(node_update, dict) else []
            for node_name, node_update in update.items()
        }
        logger.info(f"Graph Update -  {summary}\n\n")
        for node_update in update.values():
            if isinstance(node_update, dict):
                final_state = cast(GlobalQuizState, {**final_state, **node_update})

    logger.info("--------✅ graph execution stream completed--------")

    return final_state
