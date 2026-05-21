"""Deterministic splitting of combined question and solution documents."""

from __future__ import annotations

import re
from typing import Any

from exam_parser.document_classifier import SOLUTION_MARKERS


NO_CLEAR_SPLIT_WARNING = "No clear question/solution split found."
INTERLEAVED_WARNING = "Solutions may be interleaved with questions; use combined extraction."

STRONG_SOLUTION_HEADING_RE = re.compile(
    r"^\s*(?:solutions?|answers?|answer key|marking guide|suggested solution|solved answers|"
    r"løsningsforslag|losningsforslag|løsninger?|losninger?|fasit|sensorveiledning)\s*:?\s*$",
    re.IGNORECASE,
)
INLINE_SOLUTION_RE = re.compile(
    r"(?m)^\s*(?:solution|answer|løsning|losning|svar)\s*(?:to)?\s*(?:\d+|[a-z]\))",
    re.IGNORECASE,
)


def split_questions_and_solutions(extraction_result: dict[str, Any]) -> dict[str, Any]:
    """Split a combined extracted document at the first strong solution heading."""
    source_file = str(extraction_result.get("file_name") or "")
    pages = extraction_result.get("pages") if isinstance(extraction_result.get("pages"), list) else []
    warnings: list[str] = []

    split_location = _find_first_solution_heading(pages)
    if split_location is None:
        full_text = "\n\n".join(str(page.get("clean_text") or "") for page in pages)
        if _looks_interleaved(full_text):
            warnings.append(INTERLEAVED_WARNING)
        else:
            warnings.append(NO_CLEAR_SPLIT_WARNING)
        return {
            "source_file": source_file,
            "question_section": {"pages": [], "text": ""},
            "solution_section": {"pages": [], "text": ""},
            "warnings": warnings,
        }

    split_page_index, split_line_index = split_location
    question_pages: list[int] = []
    solution_pages: list[int] = []
    question_texts: list[str] = []
    solution_texts: list[str] = []

    for index, page in enumerate(pages):
        page_number = page.get("page_number")
        text = str(page.get("clean_text") or "")
        if index < split_page_index:
            question_pages.append(page_number)
            question_texts.append(text)
        elif index > split_page_index:
            solution_pages.append(page_number)
            solution_texts.append(text)
        else:
            lines = text.splitlines()
            before = "\n".join(lines[:split_line_index]).strip()
            after = "\n".join(lines[split_line_index:]).strip()
            if before:
                question_pages.append(page_number)
                question_texts.append(before)
            if after:
                solution_pages.append(page_number)
                solution_texts.append(after)

    if not question_texts or not solution_texts:
        warnings.append(NO_CLEAR_SPLIT_WARNING)

    return {
        "source_file": source_file,
        "question_section": {
            "pages": [page for page in question_pages if isinstance(page, int)],
            "text": "\n\n".join(text for text in question_texts if text).strip(),
        },
        "solution_section": {
            "pages": [page for page in solution_pages if isinstance(page, int)],
            "text": "\n\n".join(text for text in solution_texts if text).strip(),
        },
        "warnings": warnings,
    }


def section_to_extraction_result(
    split_result: dict[str, Any],
    section_name: str,
    *,
    file_suffix: str,
) -> dict[str, Any]:
    """Convert a split section into the existing extraction JSON shape."""
    section = split_result.get(section_name)
    if not isinstance(section, dict):
        section = {"pages": [], "text": ""}
    page_numbers = section.get("pages") if isinstance(section.get("pages"), list) else []
    text = str(section.get("text") or "")
    pages = [
        {
            "page_number": page_number,
            "raw_text": "",
            "clean_text": text if index == 0 else "",
        }
        for index, page_number in enumerate(page_numbers)
        if isinstance(page_number, int)
    ]
    if not pages and text:
        pages = [{"page_number": 1, "raw_text": "", "clean_text": text}]
    source_file = str(split_result.get("source_file") or "document.pdf")
    return {
        "file_name": f"{source_file}:{file_suffix}",
        "page_count": len(pages),
        "is_text_based": True,
        "pages": pages,
        "full_text": text,
    }


def _find_first_solution_heading(pages: list[Any]) -> tuple[int, int] | None:
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        lines = str(page.get("clean_text") or "").splitlines()
        for line_index, line in enumerate(lines):
            if STRONG_SOLUTION_HEADING_RE.match(line.strip()):
                return page_index, line_index
    return None


def _looks_interleaved(text: str) -> bool:
    return bool(INLINE_SOLUTION_RE.search(text)) and not any(
        re.search(rf"(?m)^\s*{re.escape(marker)}\s*:?\s*$", text, re.IGNORECASE)
        for marker in SOLUTION_MARKERS
    )
