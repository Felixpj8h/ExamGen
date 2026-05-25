import pytest

from exam_parser.question_items import iter_answer_items, solution_source_from_type


def test_iter_answer_items_yields_main_question_without_subquestions() -> None:
    result = {
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Explain IO.",
                "context": "Use Haskell.",
                "topic": "IO",
                "interaction_type": "free_text",
                "choices": [],
                "subquestions": [],
            }
        ]
    }

    items = list(iter_answer_items(result))

    assert len(items) == 1
    assert items[0].id == "q1"
    assert items[0].label == ""
    assert items[0].text == "Explain IO."
    assert items[0].context == "Use Haskell."
    assert items[0].is_subquestion is False


def test_iter_answer_items_yields_subquestions_and_followup() -> None:
    result = {
        "questions": [
            {
                "id": "q8",
                "question_number": "8",
                "question_text": "Logical implication.",
                "context": None,
                "topic": "logic",
                "subquestions": [
                    {"id": "q8a", "label": "a", "text": "Premise A."},
                    {"id": "q8_followup", "label": "followup", "text": "Does it follow?"},
                ],
            }
        ]
    }

    items = list(iter_answer_items(result))

    assert [item.id for item in items] == ["q8a", "q8_followup"]
    assert [item.label for item in items] == ["a", "followup"]
    assert all(item.question_id == "q8" for item in items)
    assert all(item.is_subquestion for item in items)


@pytest.mark.parametrize(
    ("source_type", "expected"),
    [
        ("separate_solution_pdf", "official_solution_pdf"),
        ("same_pdf", "same_pdf"),
        ("ai_generated", "ai_generated"),
        ("manual", "manual"),
    ],
)
def test_solution_source_from_type(source_type: str, expected: str) -> None:
    assert solution_source_from_type(source_type) == expected


def test_solution_source_from_type_rejects_unknown_source() -> None:
    with pytest.raises(ValueError):
        solution_source_from_type("unknown")
