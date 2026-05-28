from exam_parser.ai.generated_exam_extractor import normalize_generated_question_ids


def test_normalize_generated_question_ids_restores_join_key_contract() -> None:
    result = {
        "questions": [
            {
                "id": "model-id",
                "question_number": "1",
                "subquestions": [
                    {"id": "wrong", "label": ".3"},
                    {"id": "also-wrong", "label": "1.4"},
                ],
            },
            {
                "id": "another-model-id",
                "question_number": "5.1",
                "subquestions": [],
            },
        ]
    }

    normalize_generated_question_ids(result)

    assert result["questions"][0]["id"] == "q1"
    assert result["questions"][0]["subquestions"][0]["id"] == "q1_3"
    assert result["questions"][0]["subquestions"][1]["id"] == "q1_4"
    assert result["questions"][1]["id"] == "q5_1"
