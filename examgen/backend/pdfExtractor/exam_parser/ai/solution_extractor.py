"""Extract structured official solutions from solution text with Gemini."""

from __future__ import annotations

import json
import os
from typing import Any

from exam_parser.ai.question_extractor import (
    DEFAULT_MODEL_NAME,
    QuestionExtractionError,
    _create_gemini_client,
    _extract_response_text,
    _parse_json_response,
)
from exam_parser.post.question_items import iter_answer_items, solution_source_from_type


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
- Use exact question IDs and subquestion IDs from the provided questions JSON. Do not invent IDs such as q1_1 when the provided subquestion ID is different.
- Map solutions back to question IDs, question numbers, subquestion labels, and page_start/page_end when possible.
- If the solution PDF gives only short answers, preserve them as answers and use explanation null.
- If the solution gives detailed reasoning, put the reasoning in explanation.
- If an answer or explanation contains code, format the code as a fenced Markdown code block with the best language tag, for example ```java, ```haskell, ```python, or ```text.
- Preserve code line breaks and indentation inside fenced code blocks as closely as possible.
- Keep prose outside code fences and code/type declarations inside code fences.
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
- Do not invent new IDs such as q1_1, q2_3, or q4_1 unless those exact IDs appear in the provided questions JSON.
- Return one solution object for every main question in the provided questions JSON.
- If a main question has subquestions, return one subsolution for every provided subquestion and use the exact subquestion id and label.
- If a main question has no subquestions, put the complete answer in solution_text and keep subsolutions empty.
- Do not split a no-subquestion task into artificial subsolutions based on method names, table rows, blanks, items, or code identifiers.
- Put concise final answers in answer.
- Put reasoning or explanation in explanation.
- If an answer or explanation contains code, format the code as a fenced Markdown code block with the best language tag, for example ```java, ```haskell, ```python, or ```text.
- Preserve code line breaks and indentation inside fenced code blocks as closely as possible.
- Keep prose outside code fences and code/type declarations inside code fences.
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
        model_name = os.getenv("GEMINI_SOLUTION_MODEL") or os.getenv("GEMINI_MODEL", model_name)
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

    result = post_process_solutions(result, source_type=source_type, questions_result=questions_result)
    validate_solution_extraction_result(result)
    validate_solution_alignment(result, questions_result, source_type=source_type)
    return result


def extract_ai_solutions_per_question_with_gemini(
    extraction_result_or_solution_section: dict[str, Any],
    questions_result: dict[str, Any],
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = 0.0,
    max_output_tokens: int = 8192,
) -> dict[str, Any]:
    """Generate AI-marked practice solutions one main question at a time."""
    partial_results: list[dict[str, Any]] = []
    for question in questions_result.get("questions", []):
        if not isinstance(question, dict):
            continue
        partial_questions = _single_question_result(questions_result, question)
        try:
            partial_results.append(
                extract_solutions_with_gemini(
                    extraction_result_or_solution_section,
                    questions_result=partial_questions,
                    model_name=model_name,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    source_type="ai_generated",
                )
            )
        except SolutionExtractionError as exc:
            question_number = question.get("question_number") or question.get("id") or "unknown"
            raise SolutionExtractionError(
                f"AI-generated solution failed for question {question_number}: {exc}"
            ) from exc

    merged = _merge_ai_solution_results(partial_results, questions_result)
    validate_solution_extraction_result(merged)
    validate_solution_alignment(merged, questions_result, source_type="ai_generated")
    return merged


def _single_question_result(
    questions_result: dict[str, Any],
    question: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_file": questions_result.get("source_file", ""),
        "exam_title": questions_result.get("exam_title"),
        "course_code": questions_result.get("course_code"),
        "language": questions_result.get("language", ""),
        "questions": [question],
        "warnings": [],
    }


def _merge_ai_solution_results(
    partial_results: list[dict[str, Any]],
    questions_result: dict[str, Any],
) -> dict[str, Any]:
    source_file = str(questions_result.get("source_file") or "")
    warnings = ["AI-generated solutions; not official answer key."]
    solutions: list[dict[str, Any]] = []
    for partial in partial_results:
        source_file = str(partial.get("source_file") or source_file)
        warnings.extend(partial.get("warnings", []))
        for solution in partial.get("solutions", []):
            if isinstance(solution, dict):
                solutions.append(solution)
    return {
        "source_file": source_file,
        "source_type": "ai_generated",
        "exam_title": questions_result.get("exam_title"),
        "course_code": questions_result.get("course_code"),
        "solutions": solutions,
        "warnings": _dedupe_solution_warnings(warnings),
    }


def post_process_solutions(
    result: dict[str, Any],
    *,
    source_type: str,
    questions_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize source fields and warning containers in solutions JSON."""
    result["source_type"] = source_type
    result.setdefault("warnings", [])
    result["warnings"] = _dedupe_solution_warnings(result["warnings"])
    if source_type == "ai_generated":
        warning = "AI-generated solutions; not official answer key."
        if warning not in result["warnings"]:
            result["warnings"].append(warning)
    alignment_indexes = _build_question_alignment_indexes(questions_result)
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
                _align_subsolution_to_question(subsolution, solution, alignment_indexes)
    return result


def _dedupe_solution_warnings(warnings: list[Any]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        if not isinstance(warning, str) or not warning.strip():
            continue
        normalized = warning.strip()
        if "ai-generated" in normalized.casefold() and "official" in normalized.casefold():
            normalized = "AI-generated solutions; not official answer key."
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _build_question_alignment_indexes(questions_result: dict[str, Any] | None) -> dict[str, Any]:
    by_id: set[str] = set()
    by_number_label: dict[tuple[str, str], tuple[str, str]] = {}
    by_generated_id: dict[str, tuple[str, str]] = {}
    if not questions_result:
        return {"by_id": by_id, "by_number_label": by_number_label, "by_generated_id": by_generated_id}

    for question in questions_result.get("questions", []):
        if not isinstance(question, dict):
            continue
        question_number = str(question.get("question_number") or "")
        question_id = str(question.get("id") or "")
        if question_id:
            by_id.add(question_id)
        for subquestion in question.get("subquestions", []):
            if not isinstance(subquestion, dict):
                continue
            sub_id = str(subquestion.get("id") or "")
            label = str(subquestion.get("label") or "")
            if sub_id:
                by_id.add(sub_id)
            normalized_label = _normalize_solution_label(label, question_number)
            by_number_label[(question_number, normalized_label)] = (sub_id, label)
            by_number_label[(question_number, label)] = (sub_id, label)
            if question_number and normalized_label:
                by_generated_id[f"q{question_number}_{normalized_label}"] = (sub_id, label)
                by_generated_id[f"q{question_number}.{normalized_label}"] = (sub_id, label)
    return {"by_id": by_id, "by_number_label": by_number_label, "by_generated_id": by_generated_id}


def _align_subsolution_to_question(
    subsolution: dict[str, Any],
    parent_solution: dict[str, Any],
    indexes: dict[str, Any],
) -> None:
    if not indexes["by_id"]:
        return
    sub_id = str(subsolution.get("question_id") or "")
    if sub_id in indexes["by_id"]:
        return
    parent_number = str(parent_solution.get("question_number") or "")
    label = str(subsolution.get("label") or "")
    normalized_label = _normalize_solution_label(label, parent_number)

    match = indexes["by_generated_id"].get(sub_id)
    if match is None:
        match = indexes["by_number_label"].get((parent_number, normalized_label))
    if match is None:
        match = indexes["by_number_label"].get((parent_number, label))
    if match is None:
        return

    exact_id, exact_label = match
    if exact_id:
        subsolution["question_id"] = exact_id
    if exact_label:
        subsolution["label"] = exact_label


def _normalize_solution_label(label: str, question_number: str = "") -> str:
    normalized = str(label or "").strip()
    if question_number and normalized.startswith(f"{question_number}."):
        return normalized[len(question_number) + 1 :]
    return normalized


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


def validate_solution_alignment(
    result: dict[str, Any],
    questions_result: dict[str, Any] | None,
    *,
    source_type: str,
) -> None:
    """Reject AI-generated solution payloads that do not cover the question set."""
    if source_type != "ai_generated" or not questions_result:
        return

    expected = _expected_answer_item_ids(questions_result)
    if not expected:
        return
    actual = _actual_answer_item_ids(result, questions_result)
    missing = sorted(expected - actual)
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "..." if len(missing) > 8 else ""
        raise SolutionExtractionError(
            f"AI-generated solutions did not cover all questions. Missing: {preview}{suffix}"
        )


def _expected_answer_item_ids(questions_result: dict[str, Any]) -> set[str]:
    return {item.id for item in iter_answer_items(questions_result) if item.id}


def _actual_answer_item_ids(result: dict[str, Any], questions_result: dict[str, Any]) -> set[str]:
    question_ids_without_subquestions = {
        item.id
        for item in iter_answer_items(questions_result)
        if item.id and not item.is_subquestion
    }
    actual: set[str] = set()
    for solution in result.get("solutions", []):
        if not isinstance(solution, dict):
            continue
        question_id = str(solution.get("question_id") or "")
        if question_id in question_ids_without_subquestions and _has_parent_solution_text(solution):
            actual.add(question_id)
        for subsolution in solution.get("subsolutions", []):
            if not isinstance(subsolution, dict):
                continue
            sub_id = str(subsolution.get("question_id") or "")
            if sub_id and _has_subsolution_content(subsolution):
                actual.add(sub_id)
    return actual


def _has_parent_solution_text(solution: dict[str, Any]) -> bool:
    text = solution.get("solution_text")
    return isinstance(text, str) and bool(text.strip())


def _has_subsolution_content(subsolution: dict[str, Any]) -> bool:
    for field in ("answer", "explanation"):
        value = subsolution.get(field)
        if isinstance(value, str) and value.strip():
            return True
    grading_points = subsolution.get("grading_points")
    return isinstance(grading_points, list) and any(
        isinstance(point, str) and point.strip() for point in grading_points
    )


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
    return solution_source_from_type(source_type)
