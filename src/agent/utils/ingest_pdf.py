import base64
from io import BytesIO

import pymupdf

from ...core import logger
from ..state import PDFPageData


def ingest_pdf(pdf_path_or_base64: str) -> list[PDFPageData]:
    """
    Reads PDF from path or base64, extracts text, and stores in state.
    """

    try:

        if pdf_path_or_base64.endswith(".pdf"):
            # Handle PDF file path

            reader = pymupdf.open(pdf_path_or_base64)
            pages_data: list[PDFPageData] = []
            for i in range(reader.page_count):
                page = reader.load_page(i)
                raw_page_text = page.get_text("text")
                if not isinstance(raw_page_text, str):
                    continue
                page_text = raw_page_text
                if page_text.strip():  # Only add non-empty pages
                    pages_data.append({"page_number": i + 1, "content": page_text})
            reader.close()
            return pages_data

        elif pdf_path_or_base64.startswith("data:application/pdf;base64,"):
            # Handle base64-encoded PDF

            base64_data = pdf_path_or_base64.split(",")[1]
            pdf_bytes = base64.b64decode(base64_data)
            pdf_file = BytesIO(pdf_bytes)
            reader = pymupdf.open(pdf_file)
            pages_data: list[PDFPageData] = []
            for i in range(reader.page_count):
                page = reader.load_page(i)
                raw_page_text = page.get_text("text")
                if not isinstance(raw_page_text, str):
                    continue
                page_text = raw_page_text
                if page_text.strip():  # Only add non-empty pages
                    pages_data.append({"page_number": i + 1, "content": page_text})
            reader.close()
            return pages_data

        else:
            logger.exception("Invalid PDF input. Must be a file path or base64 string.")
            raise ValueError(
                "Input must be a PDF file path or a base64-encoded PDF string."
            )
    except Exception:
        logger.exception("Failed to ingest PDF content")
        raise
