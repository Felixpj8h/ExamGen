from exam_parser.text_cleaner import (
    clean_pages,
    normalize_whitespace,
    remove_page_number_lines,
)


def test_normalize_whitespace_preserves_readable_line_breaks() -> None:
    text = "  Question   1  \n\n\n  What\tis Python?  \n  Answer here.  "

    assert normalize_whitespace(text) == "  Question 1\n\n  What is Python?\n  Answer here."


def test_page_number_removal() -> None:
    text = "Page 1 of 10\nQuestion 1\nSide 2 av 10\n1.\nStandalone question text\n- 3 -"

    assert remove_page_number_lines(text) == "Question 1\n1.\nStandalone question text"


def test_repeated_header_footer_removal() -> None:
    pages = [
        "Exam 2026\n1. First question\nPage 1 of 3",
        "Exam 2026\n2. Second question\nPage 2 of 3",
        "Exam 2026\n3. Third question\nPage 3 of 3",
    ]

    assert clean_pages(pages) == [
        "1. First question",
        "2. Second question",
        "3. Third question",
    ]


def test_preserves_question_numbers() -> None:
    text = "Page 1 of 2\n1.\nQuestion 1\n1a)\na)\nOppgave 1\nSide 1 av 2"

    assert remove_page_number_lines(text) == "1.\nQuestion 1\n1a)\na)\nOppgave 1"
