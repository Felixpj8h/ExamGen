"""Reusable text cleaning helpers for exam PDF extraction."""

from __future__ import annotations

import re
from collections import Counter


PAGE_NUMBER_PATTERNS = (
    re.compile(r"^\s*page\s+\d+\s+(?:of|/)\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*side\s+\d+\s+(?:av|/)\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),
    re.compile(r"^\s*\d+\s*$"),
)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving readable paragraph line breaks."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\t", "    ")
    normalized_lines: list[str] = []
    for line in normalized.split("\n"):
        if not line.strip():
            normalized_lines.append("")
            continue

        leading_spaces = re.match(r"^ *", line).group(0)
        body = line[len(leading_spaces) :]
        body = re.sub(r"[ \f\v]{2,}", " ", body).rstrip()
        normalized_lines.append(f"{leading_spaces}{body}")

    normalized = "\n".join(normalized_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip("\n")


def is_page_number_line(line: str) -> bool:
    """Return true when a line is only PDF pagination, not question numbering."""
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.match(stripped) for pattern in PAGE_NUMBER_PATTERNS)


def remove_page_number_lines(text: str) -> str:
    """Remove common page number lines without removing question numbers."""
    lines = [line for line in text.splitlines() if not is_page_number_line(line)]
    return normalize_whitespace("\n".join(lines))


def _canonical_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().casefold()


def _candidate_header_footer_lines(text: str, edge_lines: int) -> set[str]:
    lines = [line.strip() for line in normalize_whitespace(text).splitlines() if line.strip()]
    candidates = lines[:edge_lines] + lines[-edge_lines:]
    return {
        _canonical_line(line)
        for line in candidates
        if line and not is_page_number_line(line)
    }


def find_repeated_header_footer_lines(
    page_texts: list[str],
    *,
    min_page_ratio: float = 0.6,
    edge_lines: int = 3,
) -> set[str]:
    """Find lines that appear near page edges on most pages."""
    if len(page_texts) < 2:
        return set()

    counts: Counter[str] = Counter()
    for text in page_texts:
        counts.update(_candidate_header_footer_lines(text, edge_lines))

    minimum_pages = max(2, int(len(page_texts) * min_page_ratio + 0.999))
    return {line for line, count in counts.items() if count >= minimum_pages}


def remove_repeated_header_footer_lines(
    text: str,
    repeated_lines: set[str],
    *,
    edge_lines: int = 3,
) -> str:
    """Remove repeated header/footer lines only when they occur near page edges."""
    if not repeated_lines:
        return normalize_whitespace(text)

    lines = normalize_whitespace(text).splitlines()
    removable_indexes = set(range(min(edge_lines, len(lines))))
    removable_indexes.update(range(max(0, len(lines) - edge_lines), len(lines)))

    kept_lines = [
        line
        for index, line in enumerate(lines)
        if index not in removable_indexes or _canonical_line(line) not in repeated_lines
    ]
    return normalize_whitespace("\n".join(kept_lines))


def clean_page_text(text: str, repeated_lines: set[str] | None = None) -> str:
    """Clean one page of extracted text."""
    cleaned = normalize_whitespace(text)
    cleaned = remove_page_number_lines(cleaned)
    cleaned = remove_repeated_header_footer_lines(cleaned, repeated_lines or set())
    return normalize_whitespace(cleaned)


def clean_pages(page_texts: list[str]) -> list[str]:
    """Clean all pages using document-level repeated header/footer detection."""
    normalized_pages = [normalize_whitespace(text) for text in page_texts]
    repeated_lines = find_repeated_header_footer_lines(normalized_pages)
    return [clean_page_text(text, repeated_lines) for text in normalized_pages]
