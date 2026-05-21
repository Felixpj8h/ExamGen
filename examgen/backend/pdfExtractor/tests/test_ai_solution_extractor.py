import pytest

from exam_parser.ai_solution_extractor import (
    SolutionExtractionError,
    build_solution_extraction_prompt,
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
