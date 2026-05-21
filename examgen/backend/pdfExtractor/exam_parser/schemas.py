"""Typed shapes and JSON schema for AI-extracted exam questions."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class ExtractedSubquestion(TypedDict):
    id: str
    label: str
    text: str
    points: float | int | None


class ExtractedQuestion(TypedDict):
    id: str
    question_number: str
    question_text: str
    page_start: int | None
    page_end: int | None
    points: float | int | None
    topic: str | None
    subquestions: list[ExtractedSubquestion]


class QuestionExtractionResult(TypedDict):
    source_file: str
    exam_title: str | None
    course_code: str | None
    language: str
    questions: list[ExtractedQuestion]
    warnings: list[str]


LanguageHint = Literal["english", "norwegian", "mixed"]


QUESTION_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source_file": {"type": "string"},
        "exam_title": {"type": "string", "nullable": True},
        "course_code": {"type": "string", "nullable": True},
        "language": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question_number": {"type": "string"},
                    "question_text": {"type": "string"},
                    "page_start": {"type": "integer", "nullable": True},
                    "page_end": {"type": "integer", "nullable": True},
                    "points": {"type": "number", "nullable": True},
                    "topic": {"type": "string", "nullable": True},
                    "subquestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {
                                    "type": "string",
                                    "description": 'Letter label such as "a", or "followup" for an unlabelled follow-up task.',
                                },
                                "text": {"type": "string"},
                                "points": {"type": "number", "nullable": True},
                            },
                            "required": ["id", "label", "text", "points"],
                        },
                    },
                },
                "required": [
                    "id",
                    "question_number",
                    "question_text",
                    "page_start",
                    "page_end",
                    "points",
                    "topic",
                    "subquestions",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "source_file",
        "exam_title",
        "course_code",
        "language",
        "questions",
        "warnings",
    ],
}
