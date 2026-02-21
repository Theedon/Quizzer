from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core import logger


def chunk_pdf_content(pages_data: list[dict]):
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

        graph_chunks = []
        for doc in split_docs:
            graph_chunks.append(
                {
                    "chunk_text": doc.page_content,
                    "page_number": doc.metadata.get("page_number"),
                    "draft_quiz": [],
                    "iter_count": 0,
                    "is_quiz_relevant": False,
                }
            )

        return graph_chunks
    except Exception as e:
        logger.exception("Failed to chunk PDF content")
        raise
