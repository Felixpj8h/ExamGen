import json
from pathlib import Path

import pytest

from exam_parser.ai_question_extractor import (
    QuestionExtractionError,
    build_question_extraction_prompt,
    extract_questions_with_gemini,
    infer_interaction_type,
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
                "interaction_type": "free_text",
                "choices": [],
                "subquestions": [
                    {
                        "id": "1a",
                        "label": "a",
                        "text": "P(orange).",
                        "points": None,
                        "interaction_type": "free_text",
                        "choices": [],
                    }
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
    assert "interaction_type must be one of" in prompt
    assert 'choices to ["True", "False"]' in prompt


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
        {
            "id": "q8c",
            "label": "c",
            "text": "No professors are vain.",
            "points": None,
            "interaction_type": "free_text",
            "choices": [],
        },
        {
            "id": "q8_followup",
            "label": "followup",
            "text": "Does (c) follow from (a) and (b)?",
            "points": None,
            "interaction_type": "free_text",
            "choices": [],
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


def test_post_process_adds_true_false_interaction_metadata_to_subquestions() -> None:
    result = sample_questions()
    result["questions"][0]["question_text"] = "What are these truth values?"
    result["questions"][0].pop("interaction_type")
    result["questions"][0].pop("choices")
    result["questions"][0]["subquestions"][0].pop("interaction_type")
    result["questions"][0]["subquestions"][0].pop("choices")

    processed = post_process_questions(result)

    subquestion = processed["questions"][0]["subquestions"][0]
    assert subquestion["interaction_type"] == "true_false"
    assert subquestion["choices"] == ["True", "False"]


def test_post_process_preserves_explicit_multiple_choice_metadata() -> None:
    result = sample_questions()
    subquestion = result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = ["A", "B", "C", "D"]

    processed = post_process_questions(result)

    assert processed["questions"][0]["subquestions"][0]["interaction_type"] == "multiple_choice"
    assert processed["questions"][0]["subquestions"][0]["choices"] == ["A", "B", "C", "D"]


def test_post_process_recovers_missing_raw_multiple_choice_options() -> None:
    extraction = sample_extraction()
    extraction["pages"][0]["raw_text"] = (
        'c) Hva er verdien til uttrykket length $ "Hello" ++ "World"?\n'
        "Velg ett alternativ\n"
        "10\n"
        '"HelloWorld"\n'
        "5\n"
        '"HWeolrllod"\n'
        "[('H','W'),('e','o'),('l','r'),('l','l'),('o','d')]\n"
        "2/15\n"
    )
    result = sample_questions()
    result["questions"][0]["subquestions"][0] = {
        "id": "q1c",
        "label": "c",
        "text": 'Hva er verdien til uttrykket length $ "Hello" ++ "World"?',
        "points": None,
        "interaction_type": "multiple_choice",
        "choices": [
            '"HelloWorld"',
            '"HWeolrllod"',
            "[('H','W'),('e','o'),('l','r'),('l','l'),('o','d')]",
        ],
    }

    processed = post_process_questions(result, extraction_result=extraction)

    assert processed["questions"][0]["subquestions"][0]["choices"] == [
        "10",
        '"HelloWorld"',
        "5",
        '"HWeolrllod"',
        "[('H','W'),('e','o'),('l','r'),('l','l'),('o','d')]",
    ]


def test_post_process_does_not_pull_distant_multiple_choice_blocks() -> None:
    extraction = sample_extraction()
    extraction["pages"][0]["raw_text"] = (
        "Hva er verdien av a?\n"
        "Velg ett alternativ\n"
        "Hva er verdien av b?\n"
        "Velg ett alternativ\n"
        "1\n2\n3\n4\n"
        "Hva er verdien av c?\n"
        "13\n5\n[\"a\"]\n[\"b\"]\n"
    )
    result = sample_questions()
    subquestion = result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = [
        "1",
        "2",
        "3",
        "4",
        "Hva er verdien av c?",
        "13",
        "5",
        '["a"]',
    ]

    processed = post_process_questions(result, extraction_result=extraction)

    assert processed["questions"][0]["subquestions"][0]["choices"] == ["1", "2", "3", "4", "13", "5"]


def test_post_process_recovers_grouped_numeric_choices_without_next_question_options() -> None:
    extraction = sample_extraction()
    extraction["pages"][0]["raw_text"] = (
        "Hva er verdien av head (tail [1,2,3]) ?\n"
        "Velg ett alternativ:\n"
        "Hva er verdien av snd ([1,2],3)?\n"
        "Velg ett alternativ\n"
        "Hva er verdien av length [2,4,6,8] / 2?\n"
        "Velg ett alternativ\n"
        "Hva er verdien av length [1,4..13]?\n"
        "[1]\n"
        "2\n"
        "[2,3]\n"
        "1\n"
        "Ingen verdi, grunnet kjørefeil/error\n"
        "3\n"
        "(2,3)\n"
    )
    result = sample_questions()
    subquestion = result["questions"][0]["subquestions"][0]
    subquestion["text"] = "Hva er verdien av head (tail [1,2,3]) ?"
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = ["[1]", "[2,3]", "Ingen verdi, grunnet kjørefeil/error"]

    processed = post_process_questions(result, extraction_result=extraction)

    assert processed["questions"][0]["subquestions"][0]["choices"] == [
        "[1]",
        "2",
        "[2,3]",
        "1",
        "Ingen verdi, grunnet kjørefeil/error",
    ]


def test_post_process_uses_compact_range_when_choices_repeat_later() -> None:
    extraction = sample_extraction()
    extraction["pages"][0]["raw_text"] = (
        "Hva er verdien av head (tail [1,2,3]) ?\n"
        "Velg ett alternativ:\n"
        "[1]\n"
        "2\n"
        "[2,3]\n"
        "1\n"
        "Ingen verdi, grunnet kjørefeil/error\n"
        "3\n"
        "[2,3]\n"
        "2\n"
        "Ingen verdi, grunnet kjørefeil/error\n"
    )
    result = sample_questions()
    subquestion = result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = ["[1]", "[2,3]", "Ingen verdi, grunnet kjørefeil/error"]

    processed = post_process_questions(result, extraction_result=extraction)

    assert processed["questions"][0]["subquestions"][0]["choices"] == [
        "[1]",
        "2",
        "[2,3]",
        "1",
        "Ingen verdi, grunnet kjørefeil/error",
    ]


def test_post_process_does_not_treat_instruction_text_as_choice() -> None:
    extraction = sample_extraction()
    extraction["pages"][0]["raw_text"] = (
        "Hva er en gyldig typing av uncurry (+)?\n"
        "Velg ett alternativ:\n"
        "Hva er en gyldig typing av (.)?\n"
        "Husk at f . g = \\x -> f (g x).\n"
        "Integer -> (Integer, Integer)\n"
        "(Integer -> Integer) -> Integer\n"
        "(Integer , Integer) -> Integer\n"
        "Integer -> (Integer -> Integer)\n"
        "Uttrykket gir en typefeil.\n"
    )
    result = sample_questions()
    subquestion = result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = [
        "Husk at f . g = \\x -> f (g x).",
        "Integer -> (Integer, Integer)",
        "(Integer -> Integer) -> Integer",
        "(Integer , Integer) -> Integer",
        "Integer -> (Integer -> Integer)",
        "Uttrykket gir en typefeil.",
    ]

    processed = post_process_questions(result, extraction_result=extraction)

    assert processed["questions"][0]["subquestions"][0]["choices"] == [
        "Integer -> (Integer, Integer)",
        "(Integer -> Integer) -> Integer",
        "(Integer , Integer) -> Integer",
        "Integer -> (Integer -> Integer)",
        "Uttrykket gir en typefeil.",
    ]


def test_infer_interaction_type_defaults_to_free_text_when_uncertain() -> None:
    assert infer_interaction_type("Discuss the concept briefly.") == "free_text"


def test_validation_rejects_invalid_interaction_type() -> None:
    malformed = sample_questions()
    malformed["questions"][0]["subquestions"][0]["interaction_type"] = "slider"

    with pytest.raises(QuestionExtractionError):
        validate_question_extraction_result(malformed)


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
