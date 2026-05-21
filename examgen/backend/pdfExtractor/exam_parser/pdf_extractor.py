"""PDF text extraction logic for text-based exam documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from exam_parser.text_cleaner import clean_pages, normalize_whitespace


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be validated or extracted."""


def validate_pdf_path(pdf_path: str | Path) -> Path:
    """Validate that the input path exists and points to a PDF file."""
    path = Path(pdf_path).expanduser()
    if not path.exists():
        raise PDFExtractionError(f"File does not exist: {path}")
    if not path.is_file():
        raise PDFExtractionError(f"Path is not a file: {path}")
    if path.suffix.casefold() != ".pdf":
        raise PDFExtractionError(f"File must have a .pdf extension: {path}")
    try:
        with path.open("rb") as file:
            if file.read(5) != b"%PDF-":
                raise PDFExtractionError(f"File does not appear to be a valid PDF: {path}")
    except OSError as exc:
        raise PDFExtractionError(f"Could not read file: {path}") from exc
    return path


def _extract_raw_pages(path: Path) -> list[str]:
    try:
        with fitz.open(path) as document:
            if document.page_count == 0:
                raise PDFExtractionError("PDF contains no pages.")
            return [document.load_page(index).get_text("text") for index in range(document.page_count)]
    except PDFExtractionError:
        raise
    except fitz.FileDataError as exc:
        raise PDFExtractionError(f"Could not read PDF data: {path}") from exc
    except fitz.EmptyFileError as exc:
        raise PDFExtractionError(f"PDF file is empty: {path}") from exc
    except Exception as exc:
        raise PDFExtractionError(f"Failed to extract text from PDF: {path}") from exc


def is_probably_text_based(
    page_texts: list[str],
    *,
    min_chars_per_page: int = 30,
    min_text_page_ratio: float = 0.5,
) -> bool:
    """Heuristically decide whether the PDF is probably text-based."""
    if not page_texts:
        return False

    pages_with_text = sum(
        1 for text in page_texts if len(normalize_whitespace(text)) >= min_chars_per_page
    )
    return pages_with_text / len(page_texts) >= min_text_page_ratio


def extract_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract raw and cleaned page-level text from a text-based PDF."""
    path = validate_pdf_path(pdf_path)
    raw_pages = _extract_raw_pages(path)
    clean_texts = clean_pages(raw_pages)

    pages = [
        {
            "page_number": index + 1,
            "raw_text": raw_text,
            "clean_text": clean_text,
        }
        for index, (raw_text, clean_text) in enumerate(zip(raw_pages, clean_texts, strict=True))
    ]

    return {
        "file_name": path.name,
        "page_count": len(raw_pages),
        "is_text_based": is_probably_text_based(raw_pages),
        "pages": pages,
        "full_text": "\n\n".join(text for text in clean_texts if text),
    }
