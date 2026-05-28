"""Generate a fresh exam from an existing exam and reference material."""

from __future__ import annotations

import json
import os
from typing import Any

from exam_parser.ai.question_extractor import (
    DEFAULT_MODEL_NAME,
    QuestionExtractionError,
    _combined_page_text,
    _create_gemini_client,
    _extract_response_text,
    _generate_content_config,
    _parse_json_response,
    post_process_questions,
    validate_question_extraction_result,
)
from exam_parser.schemas import QUESTION_EXTRACTION_SCHEMA


GENERATED_EXAM_WARNING = "AI-generated exam and solutions; not official exam material."


class GeneratedExamExtractionError(Exception):
    """Raised when AI exam generation cannot complete cleanly."""


def build_generated_exam_prompt(
    exam_extraction: dict[str, Any],
    reference_extraction: dict[str, Any],
    original_questions_result: dict[str, Any],
) -> str:
    """Build the Gemini prompt for creating a new exam."""
    original_questions_json = json.dumps(original_questions_result, ensure_ascii=False, indent=2)
    exam_text = _combined_page_text(exam_extraction)
    reference_text = _combined_page_text(reference_extraction)
    if not exam_text:
        raise GeneratedExamExtractionError("Exam PDF contains no text to use as a style reference.")
    if not reference_text:
        raise GeneratedExamExtractionError("Reference PDF contains no text to use as syllabus or solution material.")

    return f"""You are generating a fresh practice exam as structured JSON.

Rules:
- Generate a new exam, not a copy of the original exam.
- Match the original exam's approximate number of main questions, subquestion structure, interaction types, topic mix, and difficulty.
- Use the reference PDF as source material. It may be a syllabus, notes, official answers, marking guidance, or a mixed document.
- If the reference PDF is a syllabus or notes, turn that material into solvable exam tasks.
- If the reference PDF is a solution key, use it as a topic and correctness guide, not as text to copy.
- Do not reuse exact question wording unless a term, formula, type signature, or code identifier must stay exact.
- Preserve Norwegian/English style from the original exam when obvious.
- Put question-specific setup, definitions, examples, code, tables, or formulas in context.
- Format code inside context as fenced Markdown code blocks with the best language tag.
- Set page_start and page_end to null because generated questions do not come from original pages.
- Use stable generated IDs: q1, q2, q3 for main questions and q1a, q1b for subquestions.
- For every question and subquestion, set interaction_type and choices according to the schema.
- Add this warning exactly once in warnings: {GENERATED_EXAM_WARNING}
- Return only JSON matching the schema.

JSON schema:
{json.dumps(QUESTION_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Original extracted question structure:
{original_questions_json}

Original exam text for style reference:
{exam_text}

Reference PDF text for syllabus/solution material:
{reference_text}
"""


def extract_generated_exam_questions_with_gemini(
    exam_extraction: dict[str, Any],
    reference_extraction: dict[str, Any],
    original_questions_result: dict[str, Any],
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = 0.2,
    max_output_tokens: int = 16384,
) -> dict[str, Any]:
    """Create structured questions for a new exam using Gemini."""
    if model_name == DEFAULT_MODEL_NAME:
        model_name = os.getenv("GEMINI_QUESTION_MODEL") or os.getenv("GEMINI_MODEL", model_name)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeneratedExamExtractionError("Missing GEMINI_API_KEY environment variable.")

    prompt = build_generated_exam_prompt(exam_extraction, reference_extraction, original_questions_result)
    try:
        client = _create_gemini_client(api_key)
        config = _generate_content_config(temperature, max_output_tokens)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        result = _parse_json_response(_extract_response_text(response))
    except QuestionExtractionError as exc:
        raise GeneratedExamExtractionError(str(exc)) from exc
    except Exception as exc:
        raise GeneratedExamExtractionError(f"Gemini API request failed: {exc}") from exc

    result = post_process_questions(result)
    _ensure_generated_warning(result)
    validate_question_extraction_result(result)
    return result


def _ensure_generated_warning(result: dict[str, Any]) -> None:
    warnings = result.setdefault("warnings", [])
    if not isinstance(warnings, list):
        result["warnings"] = [GENERATED_EXAM_WARNING]
        return
    if GENERATED_EXAM_WARNING not in warnings:
        warnings.append(GENERATED_EXAM_WARNING)
