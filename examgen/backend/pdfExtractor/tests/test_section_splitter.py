from exam_parser.pdf.section_splitter import (
    INTERLEAVED_WARNING,
    NO_CLEAR_SPLIT_WARNING,
    split_questions_and_solutions,
)


def extraction(pages: list[str]) -> dict:
    return {
        "file_name": "combined.pdf",
        "page_count": len(pages),
        "is_text_based": True,
        "pages": [
            {"page_number": index + 1, "raw_text": text, "clean_text": text}
            for index, text in enumerate(pages)
        ],
        "full_text": "\n\n".join(pages),
    }


def test_split_at_solutions_heading() -> None:
    result = split_questions_and_solutions(
        extraction(["Questions\n1. What is P(x)?", "Solutions\n1. True."])
    )

    assert result["question_section"]["text"] == "Questions\n1. What is P(x)?"
    assert result["solution_section"]["text"] == "Solutions\n1. True."


def test_split_at_losningsforslag_heading() -> None:
    result = split_questions_and_solutions(
        extraction(["Oppgaver\n1. Hva er sant?", "L\u00f8sningsforslag\n1. Sant."])
    )

    assert "Oppgaver" in result["question_section"]["text"]
    assert "L\u00f8sningsforslag" in result["solution_section"]["text"]


def test_preserves_pages_before_and_after_split() -> None:
    result = split_questions_and_solutions(
        extraction(["Questions\n1. A", "2. B", "Solutions\n1. A", "2. B"])
    )

    assert result["question_section"]["pages"] == [1, 2]
    assert result["solution_section"]["pages"] == [3, 4]


def test_warns_if_no_clear_split_exists() -> None:
    result = split_questions_and_solutions(extraction(["Questions\n1. A\n2. B"]))

    assert NO_CLEAR_SPLIT_WARNING in result["warnings"]
    assert result["solution_section"]["text"] == ""


def test_warns_on_likely_interleaved_format() -> None:
    result = split_questions_and_solutions(
        extraction(["1. What is P(x)?\nAnswer 1 True\n2. What is Q(x)?\nAnswer 2 False"])
    )

    assert INTERLEAVED_WARNING in result["warnings"]
