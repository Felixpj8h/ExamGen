import json
from pathlib import Path

import pytest

from exam_parser.ai_question_extractor import (
    QuestionExtractionError,
    build_question_extraction_prompt,
    extract_questions_with_gemini,
    normalize_obvious_math_squares,
    post_process_questions,
    validate_question_extraction_result,
)
from exam_parser.cli_extract_questions import main as cli_main


def sample_extraction() -> dict:
    return {
        "file_name": "exam.pdf",
        "page_count": 1,
        "is_text_based": True,
        "pages": [
            {
                "page_number": 1,
                "raw_text": "1. What is P(x)?",
                "clean_text": "1. Let P(x) be the statement.\na) P(orange).",
            }
        ],
        "full_text": "1. Let P(x) be the statement.\na) P(orange).",
    }


def sample_questions() -> dict:
    return {
        "source_file": "exam.pdf",
        "exam_title": "Sample exam",
        "course_code": "MNF130",
        "language": "english",
        "questions": [
            {
                "id": "1",
                "question_number": "1",
                "question_text": "Let P(x) be the statement.",
                "page_start": 1,
                "page_end": 1,
                "points": None,
                "topic": "predicate logic",
                "subquestions": [
                    {"id": "1a", "label": "a", "text": "P(orange).", "points": None}
                ],
            }
        ],
        "warnings": [],
    }


def test_prompt_contains_extracted_clean_text() -> None:
    prompt = build_question_extraction_prompt(sample_extraction())

    assert "1. Let P(x) be the statement." in prompt
    assert "a) P(orange)." in prompt


def test_prompt_tells_model_not_to_solve_questions() -> None:
    prompt = build_question_extraction_prompt(sample_extraction())

    assert "Do not solve anything." in prompt
    assert "Do not answer the exam questions." in prompt
    assert 'label "followup"' in prompt


def test_validation_accepts_correct_result() -> None:
    validate_question_extraction_result(sample_questions())


def test_validation_rejects_missing_questions() -> None:
    malformed = sample_questions()
    malformed.pop("questions")

    with pytest.raises(QuestionExtractionError):
        validate_question_extraction_result(malformed)


def test_validation_rejects_malformed_subquestions() -> None:
    malformed = sample_questions()
    malformed["questions"][0]["subquestions"] = [{"id": "1a", "label": "a"}]

    with pytest.raises(QuestionExtractionError):
        validate_question_extraction_result(malformed)


def test_post_process_splits_merged_q8_followup() -> None:
    result = sample_questions()
    result["questions"][0]["id"] = "q8"
    result["questions"][0]["subquestions"] = [
        {
            "id": "q8c",
            "label": "c",
            "text": "No professors are vain. Does (c) follow from (a) and (b)?",
            "points": None,
        }
    ]

    processed = post_process_questions(result)

    subquestions = processed["questions"][0]["subquestions"]
    assert subquestions == [
        {"id": "q8c", "label": "c", "text": "No professors are vain.", "points": None},
        {
            "id": "q8_followup",
            "label": "followup",
            "text": "Does (c) follow from (a) and (b)?",
            "points": None,
        },
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("∀n(n2 ≥0).", "∀n(n² ≥0)."),
        ("∃!x(x2 = 1).", "∃!x(x² = 1)."),
        ("Question 2", "Question 2"),
        ("Spring 2026", "Spring 2026"),
        ("C++", "C++"),
    ],
)
def test_normalize_obvious_math_squares(raw: str, expected: str) -> None:
    assert normalize_obvious_math_squares(raw) == expected


def test_post_process_warns_when_topics_are_identical_and_broad() -> None:
    result = sample_questions()
    result["questions"].append(
        {
            "id": "2",
            "question_number": "2",
            "question_text": "Translate the statement.",
            "page_start": 1,
            "page_end": 1,
            "points": None,
            "topic": "Discrete Mathematics",
            "subquestions": [],
        }
    )
    result["questions"][0]["topic"] = "Discrete Mathematics"

    processed = post_process_questions(result)

    assert "Topics may be too generic." in processed["warnings"]


def test_post_process_sets_mixed_language_for_norwegian_title_with_english_language() -> None:
    result = sample_questions()
    result["language"] = "English"
    result["exam_title"] = "Oppgaver for group sessions uke 6"

    processed = post_process_questions(result)

    assert processed["language"] == "mixed"


class _FakeResponse:
    text = json.dumps(sample_questions())


class _FakeModels:
    def generate_content(self, **kwargs):
        assert kwargs["model"] == "test-model"
        assert "Do not solve anything." in kwargs["contents"]
        assert kwargs["config"] == "fake-config"
        return _FakeResponse()


class _FakeClient:
    models = _FakeModels()


def test_extract_questions_with_gemini_uses_mocked_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(
        "exam_parser.ai_question_extractor._create_gemini_client",
        lambda api_key: _FakeClient(),
    )
    monkeypatch.setattr(
        "exam_parser.ai_question_extractor._generate_content_config",
        lambda temperature, max_output_tokens: "fake-config",
    )

    result = extract_questions_with_gemini(sample_extraction(), model_name="test-model")

    assert result["questions"][0]["id"] == "1"


def test_cli_loads_extraction_json_and_writes_mocked_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "extracted.json"
    output_path = tmp_path / "questions.json"
    input_path.write_text(json.dumps(sample_extraction()), encoding="utf-8")

    monkeypatch.setattr(
        "exam_parser.cli_extract_questions.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    exit_code = cli_main([str(input_path), "--out", str(output_path), "--model", "test-model"])

    assert exit_code == 0
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["source_file"] == "exam.pdf"
