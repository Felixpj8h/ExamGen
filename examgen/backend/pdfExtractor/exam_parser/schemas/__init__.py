"""JSON schema definitions used by the extraction pipeline."""

from exam_parser.schemas.questions import (
    ExtractedQuestion,
    ExtractedSubquestion,
    InteractionType,
    LanguageHint,
    QUESTION_EXTRACTION_SCHEMA,
    QuestionExtractionResult,
)

__all__ = [
    "ExtractedQuestion",
    "ExtractedSubquestion",
    "InteractionType",
    "LanguageHint",
    "QUESTION_EXTRACTION_SCHEMA",
    "QuestionExtractionResult",
]

