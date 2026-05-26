"""Shared helpers for question/solution item alignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator


SOURCE_TYPE_TO_SUBSOLUTION_SOURCE = {
    "separate_solution_pdf": "official_solution_pdf",
    "same_pdf": "same_pdf",
    "ai_generated": "ai_generated",
    "manual": "manual",
}


@dataclass(frozen=True)
class AnswerItem:
    """One answerable unit in a question extraction result."""

    id: str
    label: str
    question_id: str
    question_number: str
    text: str
    context: str | None
    topic: str | None
    interaction_type: str
    choices: list[str]
    parent_question: dict[str, Any]
    item: dict[str, Any]
    is_subquestion: bool


def solution_source_from_type(source_type: str) -> str:
    """Map a solution source_type to the per-solution source value used by the bundle."""
    try:
        return SOURCE_TYPE_TO_SUBSOLUTION_SOURCE[source_type]
    except KeyError as exc:
        raise ValueError(f"Unknown source_type: {source_type}") from exc


def iter_answer_items(questions_result: dict[str, Any]) -> Iterator[AnswerItem]:
    """Yield every frontend-answerable item from a questions JSON result."""
    for question in questions_result.get("questions", []):
        if not isinstance(question, dict):
            continue
        question_id = str(question.get("id") or "")
        question_number = str(question.get("question_number") or "")
        question_context = question.get("context") if isinstance(question.get("context"), str) else None
        question_topic = question.get("topic") if isinstance(question.get("topic"), str) else None
        subquestions = question.get("subquestions")
        if isinstance(subquestions, list) and subquestions:
            for subquestion in subquestions:
                if not isinstance(subquestion, dict):
                    continue
                yield AnswerItem(
                    id=str(subquestion.get("id") or ""),
                    label=str(subquestion.get("label") or ""),
                    question_id=question_id,
                    question_number=question_number,
                    text=str(subquestion.get("text") or ""),
                    context=question_context,
                    topic=question_topic,
                    interaction_type=str(subquestion.get("interaction_type") or "free_text"),
                    choices=[
                        choice
                        for choice in subquestion.get("choices", [])
                        if isinstance(choice, str)
                    ],
                    parent_question=question,
                    item=subquestion,
                    is_subquestion=True,
                )
            continue

        yield AnswerItem(
            id=question_id,
            label="",
            question_id=question_id,
            question_number=question_number,
            text=str(question.get("question_text") or ""),
            context=question_context,
            topic=question_topic,
            interaction_type=str(question.get("interaction_type") or "free_text"),
            choices=[choice for choice in question.get("choices", []) if isinstance(choice, str)],
            parent_question=question,
            item=question,
            is_subquestion=False,
        )
