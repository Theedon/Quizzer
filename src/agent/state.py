from operator import add
from typing import Annotated, Any, TypedDict


class GlobalQuizState(TypedDict):
    pdf_url_or_base64: str
    pdf_pages_data: list[dict[str, Any]]
    crawled_chunks: list[dict[str, Any]]
    final_quiz: Annotated[list[dict[str, Any]], add]


class SubGraphState(TypedDict):
    chunk: dict[str, Any]
    quiz: list[dict[str, Any]]
    iter_count: int
    is_quiz_relevant: bool
