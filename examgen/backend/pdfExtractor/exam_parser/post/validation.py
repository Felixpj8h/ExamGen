"""Shared validation entry points for extracted question and solution JSON."""

from exam_parser.ai.question_extractor import validate_question_extraction_result  # noqa: F401
from exam_parser.ai.solution_extractor import validate_solution_extraction_result  # noqa: F401

__all__ = [
    "validate_question_extraction_result",
    "validate_solution_extraction_result",
]
