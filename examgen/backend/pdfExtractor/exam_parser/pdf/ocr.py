"""Gemini vision OCR helpers for low-text PDF pages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import fitz

DEFAULT_OCR_MODEL_NAME = "gemini-3.1-flash-lite"
OCR_PROMPT = """Transcribe this exam PDF page exactly as source text.

Rules:
- Return only the transcribed text.
- Do not answer, solve, explain, summarize, or add new content.
- Preserve question wording, math notation, tables, code, labels, and line breaks as closely as possible.
- Preserve Norwegian/English wording as written.
- If text is unreadable, write [unreadable] only for that local span.
"""


class OCRError(Exception):
    """Raised when AI OCR cannot complete."""


def resolved_ocr_model_name(model_name: str | None = None) -> str:
    return (
        model_name
        or os.getenv("GEMINI_OCR_MODEL")
        or os.getenv("GEMINI_MODEL")
        or DEFAULT_OCR_MODEL_NAME
    )


def ocr_pdf_pages_with_gemini(
    pdf_path: str | Path,
    page_numbers: list[int],
    *,
    model_name: str | None = None,
    render_scale: float = 2.0,
) -> dict[int, str]:
    """OCR selected 1-based PDF page numbers with Gemini vision."""
    if not page_numbers:
        return {}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise OCRError("Missing GEMINI_API_KEY environment variable for OCR.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise OCRError(
            "Missing dependency: install the official Google GenAI SDK with "
            "`python -m pip install google-genai`."
        ) from exc

    client = genai.Client(api_key=api_key)
    resolved_model = resolved_ocr_model_name(model_name)
    results: dict[int, str] = {}

    try:
        with fitz.open(pdf_path) as document:
            for page_number in page_numbers:
                if page_number < 1 or page_number > document.page_count:
                    raise OCRError(f"OCR page number is out of range: {page_number}")
                image_bytes = _render_page_png_bytes(
                    document.load_page(page_number - 1),
                    render_scale=render_scale,
                )
                response = client.models.generate_content(
                    model=resolved_model,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        OCR_PROMPT,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="text/plain",
                    ),
                )
                results[page_number] = _extract_response_text(response)
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(f"Gemini OCR request failed: {exc}") from exc

    return results


def _render_page_png_bytes(page: Any, *, render_scale: float) -> bytes:
    scale = max(1.0, float(render_scale))
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pixmap.tobytes("png")


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text.strip()

    try:
        parts = response.candidates[0].content.parts
        joined = "".join(getattr(part, "text", "") for part in parts)
    except (AttributeError, IndexError, TypeError):
        joined = ""
    return joined.strip()
