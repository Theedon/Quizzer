import os

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...core import logger
from ..state import ChunkData, PDFPageData


def chunk_pdf_content(pages_data: list[PDFPageData]) -> list[ChunkData]:
    """Split raw page text into smaller graph-compatible chunks.

    Returns a list suitable for feeding into the quiz generator nodes.
    """
    try:
        docs = [
            Document(
                page_content=page["content"],
                metadata={"page_number": page["page_number"]},
            )
            for page in pages_data
        ]

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )

        split_docs = text_splitter.split_documents(docs)

        graph_chunks: list[ChunkData] = []
        chunk_num = 0
        for doc in split_docs:
            chunk_id = f"{chunk_num}_{os.urandom(4).hex()}"
            page_number = doc.metadata.get("page_number", 0)
            normalized_page_number = page_number if isinstance(page_number, int) else 0
            graph_chunks.append(
                {
                    "chunk_text": doc.page_content,
                    "page_number": normalized_page_number,
                    "iter_count": 0,
                    "is_quiz_relevant": False,
                    "chunk_id": chunk_id,
                }
            )
            chunk_num += 1

        return graph_chunks
    except Exception:
        logger.exception("Failed to chunk PDF content")
        raise
