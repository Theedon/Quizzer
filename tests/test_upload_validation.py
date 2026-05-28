from io import BytesIO

from src.ui.app import is_valid_pdf


def test_valid_pdf_header():
    content = BytesIO(b"%PDF-1.7 rest of content")
    assert is_valid_pdf(content) is True
    assert content.read(1) == b"%"  # verify seek(0) worked


def test_invalid_header():
    content = BytesIO(b"PK\x03\x04 this is a zip")
    assert is_valid_pdf(content) is False


def test_empty_file():
    content = BytesIO(b"")
    assert is_valid_pdf(content) is False


def test_short_file():
    content = BytesIO(b"%PD")
    assert is_valid_pdf(content) is False
