from exam_parser.pdf.document_classifier import (
    INTERLEAVED_WARNING,
    classify_extracted_document,
    merge_wrapped_headings,
)


def extraction(file_name: str, pages: list[str]) -> dict:
    return {
        "file_name": file_name,
        "page_count": len(pages),
        "is_text_based": True,
        "pages": [
            {"page_number": index + 1, "raw_text": text, "clean_text": text}
            for index, text in enumerate(pages)
        ],
        "full_text": "\n\n".join(pages),
    }


def test_oppgaver_without_solution_markers_is_questions_only() -> None:
    result = classify_extracted_document(extraction("exam.pdf", ["Oppgaver\n1. Show that P(x)."]))

    assert result["document_type"] == "questions_only"
    assert result["confidence"] == "high"
    assert result["question_pages"] == [1]
    assert result["solution_pages"] == []


def test_losningsforslag_after_questions_is_questions_and_solutions() -> None:
    result = classify_extracted_document(
        extraction("exam.pdf", ["Oppgaver\n1. Show that P(x).", "L\u00f8sningsforslag\n1. True."])
    )

    assert result["document_type"] == "questions_and_solutions"
    assert result["question_pages"] == [1]
    assert result["solution_pages"] == [2]


def test_questions_then_solutions_is_questions_and_solutions() -> None:
    result = classify_extracted_document(
        extraction("exam.pdf", ["Questions\n1. What is P(x)?", "Solutions\n1. P(x) is true."])
    )

    assert result["document_type"] == "questions_and_solutions"
    assert INTERLEAVED_WARNING not in result["warnings"]


def test_solution_filename_helps_classify_solutions_only() -> None:
    result = classify_extracted_document(extraction("exam_solutions.pdf", ["Answers\n1. True\n2. False"]))

    assert result["document_type"] == "solutions_only"
    assert result["confidence"] == "high"


def test_unknown_document_returns_low_confidence() -> None:
    result = classify_extracted_document(extraction("notes.pdf", ["General course information."]))

    assert result["document_type"] == "unknown"
    assert result["confidence"] == "low"
    assert result["warnings"]


def test_interleaved_question_answer_pages_are_in_both_page_lists() -> None:
    result = classify_extracted_document(
        extraction(
            "Task2.pdf",
            [
                "1. Predicates\n(a) P(orange).\nAnswer: True\n(b) P(lemon).\nAnswer: False",
                "2. Quantifiers\nAnswer: For all x, P(x).",
            ],
        )
    )

    assert result["document_type"] == "questions_and_solutions"
    assert result["question_pages"] == [1, 2]
    assert result["solution_pages"] == [1, 2]
    assert INTERLEAVED_WARNING in result["warnings"]


def test_merge_wrapped_headings_merges_short_heading_continuations() -> None:
    assert merge_wrapped_headings(
        ["MNF130 - Oppgaver uke 6: Questions with correct", "answers"]
    ) == ["MNF130 - Oppgaver uke 6: Questions with correct answers"]


def test_merge_wrapped_headings_does_not_merge_normal_question_lines() -> None:
    assert merge_wrapped_headings(
        ["1. Let P(x) be the statement", "these truth values?"]
    ) == ["1. Let P(x) be the statement", "these truth values?"]


def test_merge_wrapped_headings_does_not_merge_answer_lines() -> None:
    assert merge_wrapped_headings(
        ["Answer: True. The word orange", "contains the letter a."]
    ) == ["Answer: True. The word orange", "contains the letter a."]


def test_merge_wrapped_headings_does_not_merge_full_sentences() -> None:
    assert merge_wrapped_headings(
        ["Based on the uploaded Task 1 PDF.", "Answers are added below each subquestion."]
    ) == ["Based on the uploaded Task 1 PDF.", "Answers are added below each subquestion."]


def test_heading_detection_merges_wrapped_headings() -> None:
    result = classify_extracted_document(
        extraction(
            "Task2.pdf",
            [
                "MNF130 - Oppgaver uke 6: Questions with correct answers\n"
                "Based on the uploaded Task 1 PDF. Answers are added below each subquestion for practice and checking.\n"
                "Note: The answer key uses x\u00b2/n\u00b2 notation where the PDF text extraction showed the exponent split onto a new line.\n"
                "1. P(orange).\nAnswer: True",
            ],
        )
    )

    assert result["detected_headings"] == [
        "MNF130 - Oppgaver uke 6: Questions with correct answers"
    ]
    assert not any(heading.startswith("Based on") for heading in result["detected_headings"])
    assert not any(heading.startswith("Note:") for heading in result["detected_headings"])
