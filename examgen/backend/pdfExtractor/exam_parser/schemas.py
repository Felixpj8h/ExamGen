"""Typed shapes and JSON schema for AI-extracted exam questions."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


InteractionType = Literal[
    "free_text",
    "true_false",
    "multiple_choice",
    "numeric",
    "proof",
    "translation",
]


class ExtractedSubquestion(TypedDict):
    id: str
    label: str
    text: str
    points: float | int | None
    interaction_type: InteractionType
    choices: list[str]


class ExtractedQuestion(TypedDict):
    id: str
    question_number: str
    question_text: str
    context: str | None
    page_start: int | None
    page_end: int | None
    points: float | int | None
    topic: str | None
    interaction_type: InteractionType
    choices: list[str]
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
                    "context": {
                        "type": "string",
                        "nullable": True,
                        "description": (
                            "Question-specific context needed to solve this main question, such as introductions, "
                            "definitions, helper code, data model setup, function/type signatures, rules, examples, "
                            "or figure references. Do not include general exam instructions, table of contents, "
                            "candidate metadata, time/date, allowed aids, or unrelated text."
                        ),
                    },
                    "page_start": {"type": "integer", "nullable": True},
                    "page_end": {"type": "integer", "nullable": True},
                    "points": {"type": "number", "nullable": True},
                    "topic": {"type": "string", "nullable": True},
                    "interaction_type": {
                        "type": "string",
                        "enum": [
                            "free_text",
                            "true_false",
                            "multiple_choice",
                            "numeric",
                            "proof",
                            "translation",
                        ],
                    },
                    "choices": {"type": "array", "items": {"type": "string"}},
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
                                "interaction_type": {
                                    "type": "string",
                                    "enum": [
                                        "free_text",
                                        "true_false",
                                        "multiple_choice",
                                        "numeric",
                                        "proof",
                                        "translation",
                                    ],
                                },
                                "choices": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "id",
                                "label",
                                "text",
                                "points",
                                "interaction_type",
                                "choices",
                            ],
                        },
                    },
                },
                "required": [
                    "id",
                    "question_number",
                    "question_text",
                    "context",
                    "page_start",
                    "page_end",
                    "points",
                    "topic",
                    "interaction_type",
                    "choices",
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
