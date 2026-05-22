"""Extract structured official solutions from solution text with Gemini."""

from __future__ import annotations

import json
import os
from typing import Any

from exam_parser.ai_question_extractor import (
    DEFAULT_MODEL_NAME,
    QuestionExtractionError,
    _create_gemini_client,
    _extract_response_text,
    _parse_json_response,
)


SOLUTION_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source_file": {"type": "string"},
        "source_type": {"type": "string"},
        "exam_title": {"type": "string", "nullable": True},
        "course_code": {"type": "string", "nullable": True},
        "solutions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "question_number": {"type": "string"},
                    "solution_text": {"type": "string", "nullable": True},
                    "page_start": {"type": "integer", "nullable": True},
                    "page_end": {"type": "integer", "nullable": True},
                    "subsolutions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {"type": "string"},
                                "label": {"type": "string"},
                                "answer": {"type": "string", "nullable": True},
                                "explanation": {"type": "string", "nullable": True},
                                "grading_points": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "points": {"type": "number", "nullable": True},
                                "page_start": {"type": "integer", "nullable": True},
                                "page_end": {"type": "integer", "nullable": True},
                                "source": {"type": "string"},
                            },
                            "required": [
                                "question_id",
                                "label",
                                "answer",
                                "explanation",
                                "grading_points",
                                "points",
                                "page_start",
                                "page_end",
                                "source",
                            ],
                        },
                    },
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "question_id",
                    "question_number",
                    "solution_text",
                    "page_start",
                    "page_end",
                    "subsolutions",
                    "warnings",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "source_file",
        "source_type",
        "exam_title",
        "course_code",
        "solutions",
        "warnings",
    ],
}

SOURCE_TYPES = {"separate_solution_pdf", "same_pdf", "ai_generated", "manual"}
SUBSOLUTION_SOURCES = {"official_solution_pdf", "same_pdf", "ai_generated", "manual"}


class SolutionExtractionError(Exception):
    """Raised when AI solution extraction cannot complete cleanly."""


def build_solution_extraction_prompt(
    extraction_result_or_solution_section: dict[str, Any],
    questions_result: dict[str, Any] | None = None,
    *,
    source_type: str = "separate_solution_pdf",
) -> str:
    """Build the Gemini prompt for official solution extraction."""
    source_file = str(extraction_result_or_solution_section.get("file_name") or "")
    solution_text = _solution_text(extraction_result_or_solution_section)
    if not solution_text and source_type != "ai_generated":
        raise SolutionExtractionError("Input contains no solution text to parse.")

    questions_json = json.dumps(questions_result or {}, ensure_ascii=False, indent=2)
    if source_type == "ai_generated":
        return _build_ai_generated_solution_prompt(
            source_file=source_file,
            source_text=solution_text,
            questions_json=questions_json,
        )

    return f"""You are extracting structured official solutions from text.

Rules:
- Do not solve missing questions yourself.
- Use only the provided solution text.
- The provided text may be a standalone solution document or a combined document containing both questions and answers.
- For combined documents, ignore the question statements and extract only answer keys, official solutions, explanations, marking guidance, or clearly provided correct answers.
- Do not treat phrases like "Questions with correct answers" as a reliable section split by themselves.
- Match solutions to the provided questions by question_number and subquestion label.
- If question IDs are available in the provided questions, use those IDs.
- Map solutions back to question IDs, question numbers, subquestion labels, and page_start/page_end when possible.
- If the solution PDF gives only short answers, preserve them as answers and use explanation null.
- If the solution gives detailed reasoning, put the reasoning in explanation.
- If grading criteria or point breakdowns are present, put them in grading_points.
- If points are explicitly present, extract them.
- If a solution is missing, return null and add a warning.
- If you cannot confidently identify any solution content, return an empty solutions list and add a warning explaining that no reliable solutions were found.
- If uncertain, add a warning instead of guessing.
- Return JSON only matching the schema.
- Set source_type to "{source_type}".
- Set each subsolution source to "{_subsolution_source(source_type)}".

JSON schema:
{json.dumps(SOLUTION_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Provided questions JSON:
{questions_json}

Solution source file: {source_file}

Solution text:
{solution_text}
"""


def _build_ai_generated_solution_prompt(
    *,
    source_file: str,
    source_text: str,
    questions_json: str,
) -> str:
    return f"""You are generating structured practice solutions for exam questions.

Rules:
- Generate solutions only for the provided questions JSON.
- Do not add questions that are not present in the provided questions JSON.
- Match solutions to the provided questions by question_id, question_number, and subquestion label.
- Use the exact question IDs and subquestion IDs from the provided questions JSON.
- Put concise final answers in answer.
- Put reasoning or explanation in explanation.
- Put grading_points as a short list of what a correct answer should include.
- Use null for points unless explicit points are already present in the provided question data.
- Add a warning that these are AI-generated solutions and not official solutions.
- Return JSON only matching the schema.
- Set source_type to "ai_generated".
- Set each subsolution source to "ai_generated".

JSON schema:
{json.dumps(SOLUTION_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Provided questions JSON:
{questions_json}

Source file: {source_file}

Extracted PDF text for context only:
{source_text}
"""


def extract_solutions_with_gemini(
    extraction_result_or_solution_section: dict[str, Any],
    questions_result: dict[str, Any] | None = None,
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = 0.0,
    max_output_tokens: int = 8192,
    source_type: str = "separate_solution_pdf",
) -> dict[str, Any]:
    """Convert extracted solution text into structured solutions JSON with Gemini."""
    if source_type not in SOURCE_TYPES:
        raise SolutionExtractionError(f"Invalid source_type: {source_type}")
    if model_name == DEFAULT_MODEL_NAME:
        model_name = os.getenv("GEMINI_MODEL", model_name)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SolutionExtractionError("Missing GEMINI_API_KEY environment variable.")

    prompt = build_solution_extraction_prompt(
        extraction_result_or_solution_section,
        questions_result,
        source_type=source_type,
    )
    try:
        client = _create_gemini_client(api_key)
        config = _generate_solution_content_config(temperature, max_output_tokens)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        result = _parse_json_response(_extract_response_text(response))
    except QuestionExtractionError as exc:
        raise SolutionExtractionError(str(exc)) from exc
    except Exception as exc:
        raise SolutionExtractionError(f"Gemini API request failed: {exc}") from exc

    result = post_process_solutions(result, source_type=source_type)
    validate_solution_extraction_result(result)
    return result


def post_process_solutions(result: dict[str, Any], *, source_type: str) -> dict[str, Any]:
    """Normalize source fields and warning containers in solutions JSON."""
    result["source_type"] = source_type
    result.setdefault("warnings", [])
    if source_type == "ai_generated":
        warning = "AI-generated solutions; not official answer key."
        if warning not in result["warnings"]:
            result["warnings"].append(warning)
    source = _subsolution_source(source_type)
    for solution in result.get("solutions", []):
        if not isinstance(solution, dict):
            continue
        solution.setdefault("warnings", [])
        solution.setdefault("page_start", None)
        solution.setdefault("page_end", None)
        for subsolution in solution.get("subsolutions", []):
            if isinstance(subsolution, dict):
                subsolution.setdefault("grading_points", [])
                subsolution.setdefault("page_start", None)
                subsolution.setdefault("page_end", None)
                subsolution["source"] = source
    return result


def validate_solution_extraction_result(result: dict[str, Any]) -> None:
    """Validate solutions JSON shape."""
    if not isinstance(result, dict):
        raise SolutionExtractionError("Solutions result must be an object.")
    for field in ("source_file", "source_type", "solutions", "warnings"):
        if field not in result:
            raise SolutionExtractionError(f"Solutions result is missing {field}.")
    if result["source_type"] not in SOURCE_TYPES:
        raise SolutionExtractionError("Invalid solutions source_type.")
    if not isinstance(result["solutions"], list):
        raise SolutionExtractionError("solutions must be a list.")
    if not result["solutions"]:
        raise SolutionExtractionError(
            "No solutions were extracted. The model could not confidently identify solution content."
        )
    if not isinstance(result["warnings"], list):
        raise SolutionExtractionError("warnings must be a list.")
    has_content = False
    for solution_index, solution in enumerate(result["solutions"], start=1):
        _validate_solution(solution, solution_index)
        if _solution_has_content(solution):
            has_content = True
    if not has_content:
        raise SolutionExtractionError("Solutions result contains no answer or explanation content.")


def _validate_solution(solution: Any, solution_index: int) -> None:
    if not isinstance(solution, dict):
        raise SolutionExtractionError(f"Solution {solution_index} must be an object.")
    for field in ("question_id", "question_number"):
        if not isinstance(solution.get(field), str):
            raise SolutionExtractionError(f"Solution {solution_index} has invalid {field}.")
    if solution.get("solution_text") is not None and not isinstance(solution["solution_text"], str):
        raise SolutionExtractionError(f"Solution {solution_index} solution_text must be string or null.")
    for field in ("page_start", "page_end"):
        value = solution.get(field)
        if value is not None and not isinstance(value, int):
            raise SolutionExtractionError(f"Solution {solution_index} {field} must be integer or null.")
    if not isinstance(solution.get("subsolutions"), list):
        raise SolutionExtractionError(f"Solution {solution_index} subsolutions must be a list.")
    if not isinstance(solution.get("warnings"), list):
        raise SolutionExtractionError(f"Solution {solution_index} warnings must be a list.")
    for sub_index, subsolution in enumerate(solution["subsolutions"], start=1):
        _validate_subsolution(subsolution, solution_index, sub_index)


def _validate_subsolution(subsolution: Any, solution_index: int, sub_index: int) -> None:
    if not isinstance(subsolution, dict):
        raise SolutionExtractionError(
            f"Solution {solution_index} subsolution {sub_index} must be an object."
        )
    for field in ("question_id", "label", "source"):
        if not isinstance(subsolution.get(field), str):
            raise SolutionExtractionError(
                f"Solution {solution_index} subsolution {sub_index} has invalid {field}."
            )
    if subsolution["source"] not in SUBSOLUTION_SOURCES:
        raise SolutionExtractionError(
            f"Solution {solution_index} subsolution {sub_index} has invalid source."
        )
    for nullable_string in ("answer", "explanation"):
        value = subsolution.get(nullable_string)
        if value is not None and not isinstance(value, str):
            raise SolutionExtractionError(
                f"Solution {solution_index} subsolution {sub_index} has invalid {nullable_string}."
            )
    if not isinstance(subsolution.get("grading_points"), list):
        raise SolutionExtractionError(
            f"Solution {solution_index} subsolution {sub_index} grading_points must be a list."
        )
    if subsolution.get("points") is not None and not isinstance(subsolution["points"], (int, float)):
        raise SolutionExtractionError(
            f"Solution {solution_index} subsolution {sub_index} points must be number or null."
        )
    for field in ("page_start", "page_end"):
        value = subsolution.get(field)
        if value is not None and not isinstance(value, int):
            raise SolutionExtractionError(
                f"Solution {solution_index} subsolution {sub_index} {field} must be integer or null."
            )


def _solution_has_content(solution: dict[str, Any]) -> bool:
    if isinstance(solution.get("solution_text"), str) and solution["solution_text"].strip():
        return True
    for subsolution in solution.get("subsolutions", []):
        if not isinstance(subsolution, dict):
            continue
        for field in ("answer", "explanation"):
            value = subsolution.get(field)
            if isinstance(value, str) and value.strip():
                return True
        grading_points = subsolution.get("grading_points")
        if isinstance(grading_points, list) and any(
            isinstance(point, str) and point.strip() for point in grading_points
        ):
            return True
    return False


def _generate_solution_content_config(temperature: float, max_output_tokens: int) -> Any:
    from google.genai import types

    config_kwargs: dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json",
        "response_schema": SOLUTION_EXTRACTION_SCHEMA,
    }
    try:
        return types.GenerateContentConfig(**config_kwargs)
    except TypeError:
        config_kwargs.pop("response_schema")
        return types.GenerateContentConfig(**config_kwargs)


def _solution_text(extraction_result_or_solution_section: dict[str, Any]) -> str:
    if isinstance(extraction_result_or_solution_section.get("text"), str):
        return extraction_result_or_solution_section["text"].strip()
    pages = extraction_result_or_solution_section.get("pages")
    if isinstance(pages, list):
        return "\n\n".join(
            str(page.get("clean_text") or "").strip()
            for page in pages
            if isinstance(page, dict) and str(page.get("clean_text") or "").strip()
        ).strip()
    return str(extraction_result_or_solution_section.get("full_text") or "").strip()


def _subsolution_source(source_type: str) -> str:
    if source_type == "separate_solution_pdf":
        return "official_solution_pdf"
    return source_type
