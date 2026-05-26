"""Deterministic classification for extracted exam documents."""

from __future__ import annotations

import re
from typing import Any


QUESTION_MARKERS = (
    "questions",
    "question",
    "exercise",
    "exercises",
    "problems",
    "problem",
    "task",
    "tasks",
    "oppgave",
    "oppgaver",
)
SOLUTION_MARKERS = (
    "solutions",
    "solution",
    "answers",
    "answer key",
    "marking guide",
    "suggested solution",
    "solved answers",
    "løsningsforslag",
    "losningsforslag",
    "løsning",
    "losning",
    "løsninger",
    "losninger",
    "svar",
    "fasit",
    "sensorveiledning",
    "veiledning",
)
INTERLEAVED_WARNING = "Questions and answers appear interleaved on the same pages."
SOLUTION_FILENAME_RE = re.compile(
    r"(solution|solutions|answer|answers|fasit|løsn|losn|sensorveiledning)",
    re.IGNORECASE,
)
QUESTION_NUMBER_RE = re.compile(
    r"(?m)^\s*(?:question|exercise|problem|task|oppgave)?\s*\d+[.)]?\s+\S",
    re.IGNORECASE,
)
ANSWER_LINE_RE = re.compile(
    r"(?m)^\s*(?:answer|solution|svar|løsning|losning)\s*:",
    re.IGNORECASE,
)
STRONG_HEADING_WORDS = {
    marker.casefold()
    for marker in QUESTION_MARKERS + SOLUTION_MARKERS
}
WRAPPED_HEADING_MAX_NEXT_LENGTH = 30


def classify_extracted_document(extraction_result: dict[str, Any]) -> dict[str, Any]:
    """Classify extracted PDF JSON as questions, solutions, both, or unknown."""
    source_file = str(extraction_result.get("file_name") or "")
    pages = _pages(extraction_result)
    warnings: list[str] = []

    question_pages: list[int] = []
    solution_pages: list[int] = []
    detected_headings: list[str] = []
    filename_suggests_solution = bool(SOLUTION_FILENAME_RE.search(source_file))

    interleaved_pages: list[int] = []

    for page in pages:
        page_number = _page_number(page)
        text = str(page.get("clean_text") or "")
        page_question_markers = _find_markers(text, QUESTION_MARKERS)
        page_solution_markers = _find_markers(text, SOLUTION_MARKERS)
        allow_numbered_questions = not (
            page_solution_markers
            and not page_question_markers
            and (filename_suggests_solution or _has_standalone_solution_heading(text))
        )
        has_questions = page_has_question_markers(
            text,
            allow_numbered_questions=allow_numbered_questions,
        )
        has_solutions = page_has_solution_markers(text)

        if has_questions:
            question_pages.append(page_number)
        if has_solutions:
            solution_pages.append(page_number)
        if has_questions and has_solutions:
            interleaved_pages.append(page_number)
        detected_headings.extend(_detected_heading_lines(text, page_question_markers + page_solution_markers))

    has_question_markers = bool(question_pages)
    has_solution_markers = bool(solution_pages)

    if has_question_markers and has_solution_markers:
        document_type = "questions_and_solutions"
        confidence = "high"
    elif has_solution_markers or filename_suggests_solution:
        document_type = "solutions_only"
        confidence = "high" if has_solution_markers else "medium"
    elif has_question_markers:
        document_type = "questions_only"
        confidence = "high"
    else:
        document_type = "unknown"
        confidence = "low"
        warnings.append("Could not confidently classify document as questions or solutions.")

    if filename_suggests_solution and has_question_markers and not has_solution_markers:
        warnings.append("Filename suggests solutions, but only question markers were found.")
        confidence = "medium"

    if interleaved_pages and INTERLEAVED_WARNING not in warnings:
        warnings.append(INTERLEAVED_WARNING)
        if document_type == "questions_and_solutions" and len(interleaved_pages) < 2:
            confidence = "medium"

    return {
        "source_file": source_file,
        "document_type": document_type,
        "confidence": confidence,
        "question_pages": sorted(set(question_pages)),
        "solution_pages": sorted(set(solution_pages)),
        "detected_headings": _unique_preserving_order(detected_headings),
        "warnings": warnings,
    }


def page_has_question_markers(text: str, *, allow_numbered_questions: bool = True) -> bool:
    """Return true when a page appears to contain question content."""
    return bool(
        _find_markers(text, QUESTION_MARKERS)
        or (allow_numbered_questions and QUESTION_NUMBER_RE.search(text))
    )


def page_has_solution_markers(text: str) -> bool:
    """Return true when a page appears to contain answer or solution content."""
    return bool(_find_markers(text, SOLUTION_MARKERS) or ANSWER_LINE_RE.search(text))


def detect_interleaved_pages(extraction_result: dict[str, Any]) -> list[int]:
    """Return page numbers that contain both question and solution markers."""
    interleaved: list[int] = []
    for page in _pages(extraction_result):
        text = str(page.get("clean_text") or "")
        if page_has_question_markers(text) and page_has_solution_markers(text):
            interleaved.append(_page_number(page))
    return sorted(set(interleaved))


def _pages(extraction_result: dict[str, Any]) -> list[dict[str, Any]]:
    pages = extraction_result.get("pages")
    return pages if isinstance(pages, list) else []


def _page_number(page: dict[str, Any]) -> int:
    value = page.get("page_number")
    return value if isinstance(value, int) else 0


def _find_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    searchable = text.casefold()
    for marker in markers:
        if re.search(rf"\b{re.escape(marker.casefold())}\b", searchable):
            found.append(marker)
    return found


def _detected_heading_lines(text: str, markers: list[str]) -> list[str]:
    if not markers:
        return []
    headings: list[str] = []
    folded_markers = [marker.casefold() for marker in markers]
    for line_index, line in enumerate(merge_wrapped_headings(text.splitlines())):
        stripped = line.strip()
        if not _is_heading_candidate(stripped, line_index):
            continue
        folded = stripped.casefold()
        if any(marker in folded for marker in folded_markers):
            headings.append(stripped)
    return headings


def merge_wrapped_headings(lines: list[str]) -> list[str]:
    """Merge conservative two-line heading wraps into a single line."""
    merged: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        if not current:
            merged.append(current)
            index += 1
            continue

        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if _should_merge_wrapped_heading(current, next_line, index):
            merged.append(f"{current} {next_line}".strip())
            index += 2
            continue

        merged.append(current)
        index += 1
    return merged


def _should_merge_wrapped_heading(current: str, next_line: str, line_index: int) -> bool:
    if not current or not next_line:
        return False
    if current.endswith((".", "?", "!", ":")):
        return False
    if len(next_line) > WRAPPED_HEADING_MAX_NEXT_LENGTH:
        return False
    if _looks_like_answer_or_solution_line(current):
        return False
    if not _find_markers(current, STRONG_HEADING_WORDS_TUPLE):
        return False

    combined = f"{current} {next_line}".strip()
    return _is_heading_candidate(combined, line_index)


def _is_heading_candidate(line: str, line_index: int) -> bool:
    if not line or len(line) > 90:
        return False
    folded = line.casefold()
    if folded.startswith(("based on", "note:")):
        return False
    if _looks_like_answer_or_solution_line(line):
        return False
    has_strong_marker = any(marker in folded for marker in STRONG_HEADING_WORDS)
    if line.endswith(".") and not _is_exact_heading_marker(folded):
        return False
    if line_index <= 4 and has_strong_marker:
        return True
    if _is_exact_heading_marker(folded):
        return True
    if has_strong_marker and (_looks_title_like(line) or ":" in line):
        return True
    return False


def _is_exact_heading_marker(folded_line: str) -> bool:
    normalized = folded_line.strip(" :\t")
    return normalized in STRONG_HEADING_WORDS


def _looks_like_answer_or_solution_line(line: str) -> bool:
    folded = line.casefold().strip()
    if _is_exact_heading_marker(folded):
        return False
    return bool(
        re.match(
            r"^(?:answer|solution|svar|l\u00f8sning|losning)\s*:\s+\S",
            folded,
            re.IGNORECASE,
        )
    )


def _has_standalone_solution_heading(text: str) -> bool:
    for line in text.splitlines()[:5]:
        normalized = line.strip().casefold().strip(" :\t")
        if normalized in {marker.casefold() for marker in SOLUTION_MARKERS}:
            return True
    return False


def _looks_title_like(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]
    if not letters:
        return False
    uppercase = sum(1 for character in letters if character.isupper())
    if uppercase / len(letters) > 0.45:
        return True
    words = [word.strip(":-") for word in line.split()]
    title_words = [word for word in words if word[:1].isupper()]
    return len(title_words) >= max(1, len(words) // 2)


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


STRONG_HEADING_WORDS_TUPLE = tuple(STRONG_HEADING_WORDS)
