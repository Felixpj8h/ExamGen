"""Extract structured exam questions from PDF extraction JSON with Gemini."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from exam_parser.schemas import QUESTION_EXTRACTION_SCHEMA


DEFAULT_MODEL_NAME = "gemini-3.1-flash-lite-preview"
TOO_GENERIC_TOPICS_WARNING = "Topics may be too generic."
MAX_MULTIPLE_CHOICE_OPTIONS = 6

FOLLOWUP_LABEL = "followup"
FOLLOWUP_PATTERNS = (
    r"Does\s+\([a-z]\)\s+follow\s+from\s+\([a-z]\)\s+and\s+\([a-z]\)\?",
    r"Explain your answer\.",
    r"Justify your answer\.",
    r"Give a reason for your answer\.",
    r"Is this valid\?",
    r"Why or why not\?",
)
FOLLOWUP_RE = re.compile(
    r"(?P<body>.+?[.!?])\s+(?P<followup>(?:" + "|".join(FOLLOWUP_PATTERNS) + r"))\s*$",
    re.IGNORECASE | re.DOTALL,
)
SQUARE_RE = re.compile(r"\b([nxyab])2\b")
MATH_CONTEXT_RE = re.compile(r"[∀∃≤≥=<>+\-*/^]")
NORWEGIAN_HINT_RE = re.compile(
    r"\b(oppgaver|oppgavene|oppgave|emnekode|eksamen|eksamensoppgave|uke)\b",
    re.IGNORECASE,
)
BROAD_TOPIC_VALUES = {
    "discrete mathematics",
    "discrete math",
    "mathematics",
    "math",
    "logic",
}
INTERACTION_TYPES = {
    "free_text",
    "true_false",
    "multiple_choice",
    "numeric",
    "proof",
    "translation",
}
TRUE_FALSE_CHOICES = ["True", "False"]
TRUE_FALSE_PROMPT_RE = re.compile(
    r"\b(truth values?|true or false|is (?:the )?statement true|sann(?:e|t)?|usann(?:e|t)?)\b",
    re.IGNORECASE,
)
MULTIPLE_CHOICE_RE = re.compile(
    r"(?s)(?:^|\n)\s*(?:A|B|C|D|[A-Da-d])[\).]\s+\S.*(?:\n|\s+)(?:B|C|D|[B-Da-d])[\).]\s+\S"
)
NUMERIC_PROMPT_RE = re.compile(r"\b(calculate|compute|find the value|how many|numeric|number)\b", re.IGNORECASE)
PROOF_PROMPT_RE = re.compile(r"\b(prove|show that|justify|explain why)\b", re.IGNORECASE)
TRANSLATION_PROMPT_RE = re.compile(r"\b(translate|express .* in logic|write .* in english)\b", re.IGNORECASE)
GENERAL_EXAM_CONTEXT_RE = re.compile(
    r"\b("
    r"velkommen|eksamenen teller|tillatte hjelpemidler|hjelpemidler|lykke til|"
    r"kandidat|candidate|innholdsfortegnelse|table of contents|"
    r"duration|allowed aids|exam instructions|antall oppgaver|sluttkarakter"
    r")\b",
    re.IGNORECASE,
)


class QuestionExtractionError(Exception):
    """Raised when AI question extraction cannot complete cleanly."""


def _validate_extraction_input(extraction_result: dict[str, Any]) -> None:
    if not isinstance(extraction_result, dict):
        raise QuestionExtractionError("Extraction result must be a JSON object.")
    if extraction_result.get("is_text_based") is not True:
        raise QuestionExtractionError("Input extraction must have is_text_based set to true.")
    pages = extraction_result.get("pages")
    if not isinstance(pages, list):
        raise QuestionExtractionError("Input extraction must contain a pages list.")
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise QuestionExtractionError(f"Page {index} must be an object.")
        if "clean_text" not in page:
            raise QuestionExtractionError(f"Page {index} is missing clean_text.")


def _combined_page_text(extraction_result: dict[str, Any]) -> str:
    page_blocks: list[str] = []
    for page in extraction_result.get("pages", []):
        clean_text = str(page.get("clean_text") or "").strip()
        if not clean_text:
            continue
        page_number = page.get("page_number")
        image_lines = [
            f"- {image.get('id')} bbox={image.get('bbox')}"
            for image in page.get("images", [])
            if isinstance(image, dict) and image.get("id")
        ]
        image_block = "\n\nImages on this page:\n" + "\n".join(image_lines) if image_lines else ""
        page_blocks.append(f"[PAGE {page_number}]\n{clean_text}{image_block}")
    return "\n\n".join(page_blocks).strip()


def build_question_extraction_prompt(extraction_result: dict[str, Any]) -> str:
    """Build the prompt sent to Gemini for exam question extraction."""
    _validate_extraction_input(extraction_result)
    combined_text = _combined_page_text(extraction_result)
    if not combined_text:
        raise QuestionExtractionError("Input extraction contains no clean_text to parse.")

    source_file = str(extraction_result.get("file_name") or "")
    page_count = extraction_result.get("page_count")

    return f"""You are extracting structured exam questions from text that has already been extracted from a text-based PDF.

Rules:
- Do not answer the exam questions.
- Do not solve anything.
- Do not add questions that are not present in the text.
- Preserve all original question text.
- Preserve mathematical and logical notation exactly where possible.
- Preserve Norwegian/English wording as written.
- Keep main questions and subquestions separate.
- Extract question-specific context into the question context field.
- Context means text that belongs to that main question and is needed or useful to solve it, such as:
  - introductory setup for the task
  - definitions, helper functions, type signatures, rules, assumptions, examples, or code blocks
  - data models or initial values used by the subquestions
  - figure/image references tied to the question
- Preserve paragraph breaks and line breaks inside context.
- Format code inside context as fenced Markdown code blocks with the best language tag, for example ```haskell for Haskell code, ```python for Python, ```java for Java, or ```text if uncertain.
- Keep explanatory prose outside code fences and code/type declarations inside code fences.
- Inside code fences, preserve the original code line breaks and indentation as closely as possible.
- Do not collapse code into one paragraph, do not add extra blank lines, and do not rewrite code into another programming language.
- If indentation is unclear from PDF extraction, use conservative 2-space indentation for nested or continued code lines.
- Do not put general exam metadata or instructions in context, such as table of contents, candidate number, date/time, allowed aids, grading overview, welcome text, page headers/footers, or generic exam instructions.
- If there is no question-specific context, set context to null.
- Lettered subquestions are only the text directly belonging to that label.
- If an unlabelled sentence after the final subquestion asks an additional task, represent it as a separate subquestion with label "followup".
- Example:
  (c) No professors are vain.
  Does (c) follow from (a) and (b)?
  should become:
  q8c: "No professors are vain."
  q8_followup: "Does (c) follow from (a) and (b)?"
- If a question continues across pages, merge it into one question and set page_start/page_end accordingly.
- If point values are not explicitly written, use null.
- Use "mixed" as language if headings/metadata and questions use different languages.
- Use specific topic labels when obvious. Avoid using only the broad course name for every question.
- If unsure about the topic, use null instead of guessing.
- For every question and subquestion, set interaction_type for frontend rendering.
- interaction_type must be one of: free_text, true_false, multiple_choice, numeric, proof, translation.
- Use true_false for prompts asking for truth values, true/false, sant/usant, or yes/no validity where the expected answer is binary.
- Use multiple_choice only when explicit answer choices/options are present in the text.
- Set choices to ["True", "False"] for true_false questions.
- Set choices to the visible option labels/text for multiple_choice questions.
- Use choices as [] for free_text, numeric, proof, or translation.
- If uncertain, include a warning instead of guessing.
- Return only JSON matching the schema.

Important edge cases:
- Questions can continue across page boundaries.
- Subquestions may be written as:
  - (a), (b), (c)
  - a), b), c)
  - 1a, 1b
- Main questions may be written as:
  - 1.
  - Question 1
  - Oppgave 1
- Page numbers, headers, and footers may still exist in the text.
- Some math may be extracted as x2 instead of x². Preserve what is present for now.

JSON schema:
{json.dumps(QUESTION_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Source file: {source_file}
Page count: {page_count}

Extracted PDF text:
{combined_text}
"""


def _create_gemini_client(api_key: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise QuestionExtractionError(
            "Missing dependency: install the official Google GenAI SDK with "
            "`python -m pip install google-genai`."
        ) from exc
    return genai.Client(api_key=api_key)


def _generate_content_config(temperature: float, max_output_tokens: int) -> Any:
    from google.genai import types

    config_kwargs: dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json",
        "response_schema": QUESTION_EXTRACTION_SCHEMA,
    }
    try:
        return types.GenerateContentConfig(**config_kwargs)
    except TypeError:
        config_kwargs.pop("response_schema")
        return types.GenerateContentConfig(**config_kwargs)


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    try:
        parts = response.candidates[0].content.parts
        joined = "".join(getattr(part, "text", "") for part in parts)
    except (AttributeError, IndexError, TypeError):
        joined = ""
    if joined.strip():
        return joined.strip()
    raise QuestionExtractionError("Gemini returned an empty response.")


def _parse_json_response(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise QuestionExtractionError("Gemini returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise QuestionExtractionError("Gemini JSON response must be an object.")
    return parsed


def post_process_questions(
    result: dict[str, Any],
    extraction_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply deterministic cleanup to Gemini's structured question output."""
    processed = result
    _ensure_warning_list(processed)
    _normalize_language(processed)
    _normalize_question_context(processed)
    _normalize_question_text(processed)
    _normalize_interaction_metadata(processed)
    if extraction_result is not None:
        _recover_multiple_choice_options_from_raw(processed, extraction_result)
    _split_merged_followups(processed)
    _warn_about_generic_topics(processed)
    return processed


def _ensure_warning_list(result: dict[str, Any]) -> None:
    warnings = result.get("warnings")
    if not isinstance(warnings, list):
        result["warnings"] = []


def _normalize_language(result: dict[str, Any]) -> None:
    language = result.get("language")
    if isinstance(language, str):
        normalized = language.strip().lower()
        result["language"] = normalized
    else:
        return

    title = result.get("exam_title") or ""
    course_code = result.get("course_code") or ""
    searchable = f"{title} {course_code}"
    if result["language"] == "english" and NORWEGIAN_HINT_RE.search(searchable):
        result["language"] = "mixed"


def _normalize_question_context(result: dict[str, Any]) -> None:
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        context = question.get("context")
        if not isinstance(context, str):
            question["context"] = None
            continue
        normalized = context.strip()
        if not normalized or _looks_like_general_exam_context(normalized):
            question["context"] = None
        else:
            question["context"] = normalized


def _looks_like_general_exam_context(context: str) -> bool:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    if not lines:
        return True
    if len(lines) <= 4 and all(GENERAL_EXAM_CONTEXT_RE.search(line) for line in lines):
        return True
    context_words = re.findall(r"\w+", context)
    if not context_words:
        return True
    general_matches = GENERAL_EXAM_CONTEXT_RE.findall(context)
    return len(general_matches) >= 3 and len(general_matches) / max(1, len(context_words)) > 0.08


def _normalize_question_text(result: dict[str, Any]) -> None:
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        question_text = question.get("question_text")
        if isinstance(question_text, str):
            question["question_text"] = normalize_obvious_math_squares(question_text)
        context = question.get("context")
        if isinstance(context, str):
            question["context"] = normalize_obvious_math_squares(context)
        for subquestion in question.get("subquestions", []):
            if isinstance(subquestion, dict) and isinstance(subquestion.get("text"), str):
                subquestion["text"] = normalize_obvious_math_squares(subquestion["text"])


def _normalize_interaction_metadata(result: dict[str, Any]) -> None:
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        question_context = str(question.get("question_text") or "")
        _ensure_interaction_fields(question, context=question_context, inherited_context=question_context)
        for subquestion in question.get("subquestions", []):
            if isinstance(subquestion, dict):
                _ensure_interaction_fields(
                    subquestion,
                    context=str(subquestion.get("text") or ""),
                    inherited_context=question_context,
                )


def _ensure_interaction_fields(
    item: dict[str, Any],
    *,
    context: str,
    inherited_context: str,
) -> None:
    interaction_type = item.get("interaction_type")
    choices = item.get("choices")
    if interaction_type not in INTERACTION_TYPES:
        interaction_type = infer_interaction_type(context, inherited_context=inherited_context)
    if not isinstance(choices, list) or not all(isinstance(choice, str) for choice in choices):
        choices = []
    if interaction_type == "true_false":
        choices = TRUE_FALSE_CHOICES
    elif interaction_type == "multiple_choice":
        choices = _sanitize_choice_list(choices)
    else:
        choices = []
    item["interaction_type"] = interaction_type
    item["choices"] = choices


def _recover_multiple_choice_options_from_raw(
    result: dict[str, Any],
    extraction_result: dict[str, Any],
) -> None:
    pages_by_number = {
        page.get("page_number"): str(page.get("raw_text") or "")
        for page in extraction_result.get("pages", [])
        if isinstance(page, dict)
    }
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        page_numbers = _question_page_numbers(question)
        raw_lines = _raw_lines_for_pages(pages_by_number, page_numbers)
        if not raw_lines:
            continue
        for subquestion in question.get("subquestions", []):
            if isinstance(subquestion, dict):
                _recover_item_choices_from_raw(subquestion, raw_lines)
        _recover_item_choices_from_raw(question, raw_lines)


def _question_page_numbers(question: dict[str, Any]) -> list[int]:
    page_start = question.get("page_start")
    page_end = question.get("page_end") or page_start
    if not isinstance(page_start, int) or not isinstance(page_end, int):
        return []
    return list(range(page_start, page_end + 1))


def _raw_lines_for_pages(pages_by_number: dict[Any, str], page_numbers: list[int]) -> list[str]:
    lines: list[str] = []
    for page_number in page_numbers:
        raw_text = pages_by_number.get(page_number, "")
        lines.extend(line.strip() for line in raw_text.splitlines() if line.strip())
    return lines


def _recover_item_choices_from_raw(item: dict[str, Any], raw_lines: list[str]) -> None:
    if item.get("interaction_type") != "multiple_choice":
        return
    choices = item.get("choices")
    if not isinstance(choices, list) or not all(isinstance(choice, str) for choice in choices):
        return
    choices = _sanitize_choice_list(choices)
    if not 2 <= len(choices) <= MAX_MULTIPLE_CHOICE_OPTIONS:
        item["choices"] = choices
        return

    choice_range = _compact_choice_range(raw_lines, choices)
    if choice_range is None:
        item["choices"] = choices
        return

    first_choice_index, last_choice_index = choice_range
    if last_choice_index - first_choice_index > MAX_MULTIPLE_CHOICE_OPTIONS + 2:
        item["choices"] = choices
        return

    start = max(0, first_choice_index - 1)
    end = last_choice_index
    recovered = list(choices)
    seen = {_normalize_choice_text(choice) for choice in recovered}
    for line in raw_lines[start : end + 1]:
        if len(recovered) >= MAX_MULTIPLE_CHOICE_OPTIONS:
            break
        normalized = _normalize_choice_text(line)
        if normalized in seen or not _looks_like_choice_line(line):
            continue
        recovered.insert(_choice_insert_index(raw_lines, recovered, line), line)
        seen.add(normalized)
    item["choices"] = _sanitize_choice_list(recovered)


def _compact_choice_range(raw_lines: list[str], choices: list[str]) -> tuple[int, int] | None:
    """Find the tightest raw-text span that contains the extracted choices in order."""
    positions_by_choice: list[list[int]] = []
    for choice in choices:
        normalized_choice = _normalize_choice_text(choice)
        positions = [
            index
            for index, line in enumerate(raw_lines)
            if _normalize_choice_text(line) == normalized_choice
        ]
        if not positions:
            continue
        positions_by_choice.append(positions)

    if len(positions_by_choice) < 2:
        return None

    best: tuple[int, int] | None = None

    def visit(position_group_index: int, previous_index: int, selected: list[int]) -> None:
        nonlocal best
        if position_group_index == len(positions_by_choice):
            span = (selected[0], selected[-1])
            if best is None or span[1] - span[0] < best[1] - best[0]:
                best = span
            return
        for position in positions_by_choice[position_group_index]:
            if position <= previous_index:
                continue
            if best is not None and selected and position - selected[0] >= best[1] - best[0]:
                continue
            visit(position_group_index + 1, position, [*selected, position])

    visit(0, -1, [])
    return best


def _choice_insert_index(raw_lines: list[str], choices: list[str], candidate: str) -> int:
    candidate_index = _first_line_index(raw_lines, candidate)
    for choice_index, choice in enumerate(choices):
        existing_index = _first_line_index(raw_lines, choice)
        if existing_index != -1 and candidate_index != -1 and candidate_index < existing_index:
            return choice_index
    return len(choices)


def _first_line_index(raw_lines: list[str], text: str) -> int:
    normalized = _normalize_choice_text(text)
    for index, line in enumerate(raw_lines):
        if _normalize_choice_text(line) == normalized:
            return index
    return -1


def _looks_like_choice_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _looks_like_question_prompt(stripped):
        return False
    if stripped.casefold() in {"velg ett alternativ", "maks poeng"}:
        return False
    if re.fullmatch(r"\d+/\d+", stripped):
        return False
    if re.fullmatch(r"\d{1,3}", stripped):
        return True
    return any(token in stripped for token in ('"', "'", "[", "]", "->", "::", "Integer", "String", "Char"))


def _normalize_choice_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().strip("\"'").casefold()


def _sanitize_choice_list(choices: list[str]) -> list[str]:
    sanitized: list[str] = []
    seen: set[str] = set()
    for choice in choices:
        stripped = choice.strip()
        normalized = _normalize_choice_text(stripped)
        if not stripped or normalized in seen or _looks_like_question_prompt(stripped):
            continue
        sanitized.append(stripped)
        seen.add(normalized)
        if len(sanitized) >= MAX_MULTIPLE_CHOICE_OPTIONS:
            break
    return sanitized


def _looks_like_question_prompt(text: str) -> bool:
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


def infer_interaction_type(text: str, *, inherited_context: str = "") -> str:
    """Conservatively infer frontend interaction type from question text."""
    combined = f"{inherited_context}\n{text}".strip()
    if TRUE_FALSE_PROMPT_RE.search(combined):
        return "true_false"
    if MULTIPLE_CHOICE_RE.search(text):
        return "multiple_choice"
    if TRANSLATION_PROMPT_RE.search(combined):
        return "translation"
    if PROOF_PROMPT_RE.search(combined):
        return "proof"
    if NUMERIC_PROMPT_RE.search(combined):
        return "numeric"
    return "free_text"


def normalize_obvious_math_squares(text: str) -> str:
    """Normalize obvious extracted square notation in mathematical contexts only."""

    def replace_match(match: re.Match[str]) -> str:
        start, end = match.span()
        window = text[max(0, start - 12) : min(len(text), end + 12)]
        if not MATH_CONTEXT_RE.search(window):
            return match.group(0)
        return f"{match.group(1)}²"

    return SQUARE_RE.sub(replace_match, text)


def _split_merged_followups(result: dict[str, Any]) -> None:
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        subquestions = question.get("subquestions")
        if not isinstance(subquestions, list):
            continue

        next_subquestions: list[Any] = []
        for subquestion in subquestions:
            if not isinstance(subquestion, dict):
                next_subquestions.append(subquestion)
                continue
            split = _split_subquestion_followup(question, subquestion)
            next_subquestions.extend(split)
        question["subquestions"] = next_subquestions


def _split_subquestion_followup(
    question: dict[str, Any], subquestion: dict[str, Any]
) -> list[dict[str, Any]]:
    text = subquestion.get("text")
    label = subquestion.get("label")
    if not isinstance(text, str) or not isinstance(label, str):
        return [subquestion]
    if label.casefold() == FOLLOWUP_LABEL:
        return [subquestion]

    match = FOLLOWUP_RE.match(text.strip())
    if not match:
        return [subquestion]

    body = match.group("body").strip()
    followup = match.group("followup").strip()
    if not body or not followup:
        return [subquestion]

    updated_subquestion = dict(subquestion)
    updated_subquestion["text"] = body

    followup_id = _build_followup_id(question, subquestion)
    followup_subquestion = {
        "id": followup_id,
        "label": FOLLOWUP_LABEL,
        "text": followup,
        "points": None,
        "interaction_type": infer_interaction_type(followup, inherited_context=str(question.get("question_text") or "")),
        "choices": [],
    }
    _ensure_interaction_fields(
        followup_subquestion,
        context=followup,
        inherited_context=str(question.get("question_text") or ""),
    )
    return [updated_subquestion, followup_subquestion]


def _build_followup_id(question: dict[str, Any], subquestion: dict[str, Any]) -> str:
    question_id = question.get("id")
    if isinstance(question_id, str) and question_id.strip():
        return f"{question_id}_{FOLLOWUP_LABEL}"
    subquestion_id = subquestion.get("id")
    if isinstance(subquestion_id, str) and subquestion_id.strip():
        return f"{subquestion_id}_{FOLLOWUP_LABEL}"
    return FOLLOWUP_LABEL


def _warn_about_generic_topics(result: dict[str, Any]) -> None:
    questions = result.get("questions")
    if not isinstance(questions, list) or len(questions) < 2:
        return

    topics = [
        question.get("topic").strip().casefold()
        for question in questions
        if isinstance(question, dict)
        and isinstance(question.get("topic"), str)
        and question["topic"].strip()
    ]
    if len(topics) != len(questions):
        return
    if len(set(topics)) == 1 and topics[0] in BROAD_TOPIC_VALUES:
        warnings = result.setdefault("warnings", [])
        if isinstance(warnings, list) and TOO_GENERIC_TOPICS_WARNING not in warnings:
            warnings.append(TOO_GENERIC_TOPICS_WARNING)


def validate_question_extraction_result(result: dict[str, Any]) -> None:
    """Validate the structured question extraction result."""
    if not isinstance(result, dict):
        raise QuestionExtractionError("Question extraction result must be an object.")

    required_fields = {
        "source_file": str,
        "language": str,
        "questions": list,
        "warnings": list,
    }
    for field, expected_type in required_fields.items():
        if field not in result:
            raise QuestionExtractionError(f"Question extraction result is missing {field}.")
        if not isinstance(result[field], expected_type):
            raise QuestionExtractionError(f"{field} has the wrong type.")

    for nullable_string in ("exam_title", "course_code"):
        if nullable_string not in result:
            raise QuestionExtractionError(
                f"Question extraction result is missing {nullable_string}."
            )
        if result[nullable_string] is not None and not isinstance(result[nullable_string], str):
            raise QuestionExtractionError(f"{nullable_string} must be a string or null.")

    if not result["questions"]:
        raise QuestionExtractionError("Gemini returned an empty questions list.")
    if not all(isinstance(warning, str) for warning in result["warnings"]):
        raise QuestionExtractionError("warnings must contain only strings.")

    for index, question in enumerate(result["questions"], start=1):
        _validate_question(question, index)


def _validate_question(question: Any, index: int) -> None:
    if not isinstance(question, dict):
        raise QuestionExtractionError(f"Question {index} must be an object.")

    string_fields = ("id", "question_number", "question_text")
    for field in string_fields:
        if not isinstance(question.get(field), str) or not question[field].strip():
            raise QuestionExtractionError(f"Question {index} has invalid {field}.")

    context = question.get("context")
    if context is not None and not isinstance(context, str):
        raise QuestionExtractionError(f"Question {index} context must be a string or null.")

    for field in ("page_start", "page_end"):
        value = question.get(field)
        if value is not None and not isinstance(value, int):
            raise QuestionExtractionError(f"Question {index} {field} must be an integer or null.")

    points = question.get("points")
    if points is not None and not isinstance(points, (int, float)):
        raise QuestionExtractionError(f"Question {index} points must be a number or null.")

    topic = question.get("topic")
    if topic is not None and not isinstance(topic, str):
        raise QuestionExtractionError(f"Question {index} topic must be a string or null.")
    _validate_interaction_fields(question, f"Question {index}")

    subquestions = question.get("subquestions")
    if not isinstance(subquestions, list):
        raise QuestionExtractionError(f"Question {index} subquestions must be a list.")
    for sub_index, subquestion in enumerate(subquestions, start=1):
        _validate_subquestion(subquestion, index, sub_index)


def _validate_subquestion(subquestion: Any, question_index: int, sub_index: int) -> None:
    if not isinstance(subquestion, dict):
        raise QuestionExtractionError(
            f"Question {question_index} subquestion {sub_index} must be an object."
        )
    for field in ("id", "label", "text"):
        if not isinstance(subquestion.get(field), str) or not subquestion[field].strip():
            raise QuestionExtractionError(
                f"Question {question_index} subquestion {sub_index} has invalid {field}."
            )
    if (
        subquestion["label"].casefold() != FOLLOWUP_LABEL
        and FOLLOWUP_RE.match(subquestion["text"].strip())
    ):
        raise QuestionExtractionError(
            f"Question {question_index} subquestion {sub_index} appears to contain a merged follow-up task."
        )
    points = subquestion.get("points")
    if points is not None and not isinstance(points, (int, float)):
        raise QuestionExtractionError(
            f"Question {question_index} subquestion {sub_index} points must be a number or null."
        )
    _validate_interaction_fields(subquestion, f"Question {question_index} subquestion {sub_index}")


def _validate_interaction_fields(item: dict[str, Any], label: str) -> None:
    interaction_type = item.get("interaction_type")
    choices = item.get("choices")
    if interaction_type not in INTERACTION_TYPES:
        raise QuestionExtractionError(f"{label} has invalid interaction_type.")
    if not isinstance(choices, list) or not all(isinstance(choice, str) for choice in choices):
        raise QuestionExtractionError(f"{label} choices must be a list of strings.")
    if interaction_type == "true_false" and choices != TRUE_FALSE_CHOICES:
        raise QuestionExtractionError(f"{label} true_false choices must be ['True', 'False'].")
    if interaction_type != "multiple_choice" and interaction_type != "true_false" and choices:
        raise QuestionExtractionError(f"{label} choices must be empty unless multiple_choice or true_false.")


def extract_questions_with_gemini(
    extraction_result: dict[str, Any],
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = 0.0,
    max_output_tokens: int = 8192,
) -> dict[str, Any]:
    """Convert PDF extraction JSON into structured exam questions using Gemini."""
    if model_name == DEFAULT_MODEL_NAME:
        model_name = os.getenv("GEMINI_MODEL", model_name)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise QuestionExtractionError("Missing GEMINI_API_KEY environment variable.")

    prompt = build_question_extraction_prompt(extraction_result)
    client = _create_gemini_client(api_key)

    try:
        config = _generate_content_config(temperature, max_output_tokens)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
    except Exception as exc:
        raise QuestionExtractionError(f"Gemini API request failed: {exc}") from exc

    result = post_process_questions(
        _parse_json_response(_extract_response_text(response)),
        extraction_result=extraction_result,
    )
    validate_question_extraction_result(result)
    return result
