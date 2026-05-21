"""Compatibility entrypoint for the exam_parser package.

Prefer importing from exam_parser.pdf_extractor in new backend code.
"""

from exam_parser.pdf_extractor import PDFExtractionError, extract_pdf

__all__ = ["PDFExtractionError", "extract_pdf"]
