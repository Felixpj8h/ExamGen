import pytest

from exam_parser.ai_solution_extractor import (
    SolutionExtractionError,
    build_solution_extraction_prompt,
    post_process_solutions,
    validate_solution_extraction_result,
)


def test_solution_prompt_handles_combined_pdf_full_text() -> None:
    extraction = {
        "file_name": "combined.pdf",
        "pages": [
            {
                "page_number": 1,
                "clean_text": "Questions with correct answers\n1. P(orange).\nCorrect answer: True.",
            }
        ],
    }
    questions = {
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "subquestions": [{"id": "q1a", "label": "a"}],
            }
        ]
    }

    prompt = build_solution_extraction_prompt(extraction, questions, source_type="same_pdf")

    assert "combined document containing both questions and answers" in prompt
    assert "Do not solve missing questions yourself." in prompt
    assert "Questions with correct answers" in prompt
    assert '"id": "q1"' in prompt


def test_solution_validation_rejects_empty_solutions() -> None:
    result = {
        "source_file": "combined.pdf",
        "source_type": "same_pdf",
        "exam_title": None,
        "course_code": None,
        "solutions": [],
        "warnings": ["No reliable solutions found."],
    }

    with pytest.raises(SolutionExtractionError):
        validate_solution_extraction_result(result)


def test_solution_validation_rejects_content_free_solutions() -> None:
    result = {
        "source_file": "combined.pdf",
        "source_type": "same_pdf",
        "exam_title": None,
        "course_code": None,
        "solutions": [
            {
                "question_id": "q1",
                "question_number": "1",
                "solution_text": None,
                "page_start": None,
                "page_end": None,
                "subsolutions": [
                    {
                        "question_id": "q1a",
                        "label": "a",
                        "answer": None,
                        "explanation": None,
                        "grading_points": [],
                        "points": None,
                        "page_start": None,
                        "page_end": None,
                        "source": "same_pdf",
                    }
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    with pytest.raises(SolutionExtractionError):
        validate_solution_extraction_result(result)


def test_ai_generated_prompt_marks_solutions_as_ai_generated() -> None:
    prompt = build_solution_extraction_prompt(
        {"file_name": "exam.pdf", "pages": []},
        {"questions": [{"id": "q1", "question_number": "1", "subquestions": []}]},
        source_type="ai_generated",
    )

    assert 'Set source_type to "ai_generated".' in prompt
    assert 'Set each subsolution source to "ai_generated".' in prompt
    assert "not official solutions" in prompt


def test_post_process_ai_generated_solutions_adds_warning_and_sources() -> None:
    result = {
        "source_file": "exam.pdf",
        "source_type": "same_pdf",
        "exam_title": None,
        "course_code": None,
        "solutions": [
            {
                "question_id": "q1",
                "question_number": "1",
                "solution_text": None,
                "subsolutions": [
                    {
                        "question_id": "q1a",
                        "label": "a",
                        "answer": "True",
                        "explanation": "Generated explanation.",
                        "grading_points": [],
                        "points": None,
                        "source": "same_pdf",
                    }
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }

    processed = post_process_solutions(result, source_type="ai_generated")

    assert processed["source_type"] == "ai_generated"
    assert "AI-generated solutions; not official answer key." in processed["warnings"]
    assert processed["solutions"][0]["subsolutions"][0]["source"] == "ai_generated"
