"""Utilities for extracting clean text from text-based exam PDFs."""

from exam_parser.pdf_extractor import PDFExtractionError, extract_pdf

__all__ = ["PDFExtractionError", "extract_pdf"]
