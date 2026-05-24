"""Merge extracted questions and solutions into one exam bundle."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

MAX_MULTIPLE_CHOICE_OPTIONS = 6


def build_exam_bundle(
    questions_result: dict[str, Any],
    solutions_result: dict[str, Any] | None = None,
    extraction_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge solutions into matching question/subquestion records."""
    warnings: list[str] = []
    questions = deepcopy(questions_result.get("questions", []))
    solution_indexes = _build_solution_indexes(solutions_result)
    matched_solution_keys: set[tuple[str, str]] = set()
    matched_parent_keys: set[tuple[str, str]] = set()
    has_solutions = solutions_result is not None

    for question in questions:
        if not isinstance(question, dict):
            continue
        question["images"] = _images_for_question(question, extraction_result)
        question_key = str(question.get("id") or "")
        number_key = str(question.get("question_number") or "")
        for subquestion in question.get("subquestions", []):
            if not isinstance(subquestion, dict):
                continue
            solution, solution_key = _find_subsolution(
                solution_indexes,
                question_id=str(subquestion.get("id") or ""),
                question_number=number_key,
                label=str(subquestion.get("label") or ""),
            )
            if solution is None:
                subquestion["solution"] = None
                if has_solutions:
                    warnings.append(
                        f"No solution found for question {number_key}{subquestion.get('label', '')}."
                    )
            else:
                subquestion["solution"] = {
                    "answer": solution.get("answer"),
                    "explanation": solution.get("explanation"),
                    "grading_points": solution.get("grading_points", []),
                    "source": solution.get("source"),
                }
                _ensure_solution_answer_choice(subquestion)
                matched_solution_keys.add(solution_key)
                parent_key = solution_indexes["subsolution_parent_keys"].get(solution_key)
                if parent_key:
                    matched_parent_keys.add(parent_key)

        if not question.get("subquestions"):
            solution, solution_key = _find_question_level_solution(
                solution_indexes,
                question_id=question_key,
                question_number=number_key,
            )
            if solution is not None:
                question["solution"] = {
                    "answer": None,
                    "explanation": solution.get("solution_text"),
                    "grading_points": [],
                    "source": None,
                }
                _ensure_solution_answer_choice(question)
                matched_solution_keys.add(solution_key)
                matched_parent_keys.add(solution_key)
            else:
                question["solution"] = None
                if has_solutions:
                    warnings.append(f"No solution found for question {number_key}.")

    for key in solution_indexes["subsolution_keys"]:
        if key not in matched_solution_keys:
            warnings.append(f"Unmatched solution for {key[0]} {key[1]}.".strip())
    for key in solution_indexes["parent_content_keys"]:
        if key not in matched_parent_keys:
            warnings.append(f"Unmatched solution for {key[0]} {key[1]}.".strip())

    existing_warnings = list(questions_result.get("warnings", []))
    if solutions_result:
        existing_warnings.extend(solutions_result.get("warnings", []))

    return {
        "exam": {
            "title": questions_result.get("exam_title"),
            "course_code": questions_result.get("course_code"),
            "source_file": questions_result.get("source_file"),
        },
        "questions": questions,
        "warnings": _unique_warnings(existing_warnings + warnings),
    }


def _build_solution_indexes(solutions_result: dict[str, Any] | None) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    by_number_label: dict[tuple[str, str], dict[str, Any]] = {}
    question_level_by_id: dict[str, dict[str, Any]] = {}
    question_level_by_number: dict[str, dict[str, Any]] = {}
    subsolution_keys: set[tuple[str, str]] = set()
    parent_content_keys: set[tuple[str, str]] = set()
    subsolution_parent_keys: dict[tuple[str, str], tuple[str, str]] = {}
    if not solutions_result:
        return {
            "by_id": by_id,
            "by_number_label": by_number_label,
            "question_level_by_id": question_level_by_id,
            "question_level_by_number": question_level_by_number,
            "subsolution_keys": subsolution_keys,
            "parent_content_keys": parent_content_keys,
            "subsolution_parent_keys": subsolution_parent_keys,
        }

    for solution in solutions_result.get("solutions", []):
        if not isinstance(solution, dict):
            continue
        question_id = str(solution.get("question_id") or "")
        question_number = str(solution.get("question_number") or "")
        parent_key = (question_id or question_number, "")
        if _has_parent_solution_content(solution):
            question_level_by_id[question_id] = solution
            question_level_by_number[question_number] = solution
            parent_content_keys.add(parent_key)
        for subsolution in solution.get("subsolutions", []):
            if not isinstance(subsolution, dict):
                continue
            sub_id = str(subsolution.get("question_id") or "")
            label = str(subsolution.get("label") or "")
            sub_key = (sub_id or question_number, label)
            by_id[sub_id] = subsolution
            by_number_label[(question_number, label)] = subsolution
            subsolution_keys.add(sub_key)
            subsolution_parent_keys[sub_key] = parent_key
    return {
        "by_id": by_id,
        "by_number_label": by_number_label,
        "question_level_by_id": question_level_by_id,
        "question_level_by_number": question_level_by_number,
        "subsolution_keys": subsolution_keys,
        "parent_content_keys": parent_content_keys,
        "subsolution_parent_keys": subsolution_parent_keys,
    }


def _find_subsolution(
    indexes: dict[str, Any],
    *,
    question_id: str,
    question_number: str,
    label: str,
) -> tuple[dict[str, Any] | None, tuple[str, str]]:
    if question_id in indexes["by_id"]:
        return indexes["by_id"][question_id], (question_id, label)
    key = (question_number, label)
    if key in indexes["by_number_label"]:
        subsolution = indexes["by_number_label"][key]
        return subsolution, (str(subsolution.get("question_id") or question_number), label)
    return None, ("", "")


def _find_question_level_solution(
    indexes: dict[str, Any],
    *,
    question_id: str,
    question_number: str,
) -> tuple[dict[str, Any] | None, tuple[str, str]]:
    if question_id in indexes["question_level_by_id"]:
        return indexes["question_level_by_id"][question_id], (question_id, "")
    if question_number in indexes["question_level_by_number"]:
        solution = indexes["question_level_by_number"][question_number]
        return solution, (str(solution.get("question_id") or question_number), "")
    return None, ("", "")


def _unique_warnings(warnings: list[Any]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for warning in warnings:
        if not isinstance(warning, str) or not warning:
            continue
        if warning in seen:
            continue
        seen.add(warning)
        unique.append(warning)
    return unique


def _has_parent_solution_content(solution: dict[str, Any]) -> bool:
    solution_text = solution.get("solution_text")
    return isinstance(solution_text, str) and bool(solution_text.strip())


def _ensure_solution_answer_choice(item: dict[str, Any]) -> None:
    if item.get("interaction_type") != "multiple_choice":
        return
    solution = item.get("solution")
    if not isinstance(solution, dict):
        return
    answer = solution.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return
    choices = item.get("choices")
    if not isinstance(choices, list):
        choices = []
    string_choices = _sanitize_choice_list([choice for choice in choices if isinstance(choice, str)])
    if any(_normalize_choice(choice) == _normalize_choice(answer) for choice in string_choices):
        item["choices"] = string_choices
        return
    item["choices"] = _sanitize_choice_list([answer, *string_choices], keep_first=True)


def _normalize_choice(choice: str) -> str:
    return choice.strip().strip("\"'").casefold()


def _sanitize_choice_list(choices: list[str], *, keep_first: bool = False) -> list[str]:
    sanitized: list[str] = []
    seen: set[str] = set()
    for index, choice in enumerate(choices):
        stripped = choice.strip()
        normalized = _normalize_choice(stripped)
        if not stripped or normalized in seen:
            continue
        if index != 0 or not keep_first:
            folded = stripped.casefold()
            if _looks_like_non_choice_text(stripped):
                continue
        sanitized.append(stripped)
        seen.add(normalized)
        if len(sanitized) >= MAX_MULTIPLE_CHOICE_OPTIONS:
            break
    return sanitized


def _images_for_question(
    question: dict[str, Any],
    extraction_result: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not extraction_result:
        return list(question.get("images", [])) if isinstance(question.get("images"), list) else []

    page_start = question.get("page_start")
    page_end = question.get("page_end") or page_start
    if not isinstance(page_start, int) or not isinstance(page_end, int):
        return list(question.get("images", [])) if isinstance(question.get("images"), list) else []

    images: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for page in extraction_result.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or not page_start <= page_number <= page_end:
            continue
        for image in page.get("images", []):
            if not isinstance(image, dict):
                continue
            image_id = str(image.get("id") or "")
            if image_id in seen_ids:
                continue
            seen_ids.add(image_id)
            images.append(
                {
                    "id": image_id,
                    "src": image.get("src") or image.get("path"),
                    "path": image.get("path"),
                    "page_number": image.get("page_number"),
                    "bbox": image.get("bbox"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                    "alt": f"Image from page {image.get('page_number')}",
                }
            )
    return images


def _looks_like_non_choice_text(text: str) -> bool:
    folded = text.casefold()
    return folded.startswith(
        (
            "hva er ",
            "hvilken ",
            "which ",
            "what ",
            "husk at ",
            "hint:",
            "remember ",
            "note:",
            "anta at ",
        )
    ) or folded.endswith("?")
