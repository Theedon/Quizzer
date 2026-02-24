from operator import add
from typing import Annotated, Literal, TypedDict


class PDFPageData(TypedDict):
    page_number: int
    content: str


class ChunkData(TypedDict):
    chunk_text: str
    page_number: int
    iter_count: int
    is_quiz_relevant: bool
    chunk_id: str


class FinalQuizItem(TypedDict):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer: Literal["A", "B", "C", "D"]
    explanation: str
    page_number: int
    chunk_id: str


class GlobalQuizState(TypedDict):
    pdf_url_or_base64: str
    pdf_pages_data: list[PDFPageData]
    crawled_chunks: list[ChunkData]
    final_quiz: Annotated[list[FinalQuizItem], add]


class SubGraphState(TypedDict):
    chunk: ChunkData
    quiz: list[FinalQuizItem]
    iter_count: int
    is_quiz_relevant: bool
