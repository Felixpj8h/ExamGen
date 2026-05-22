from exam_parser.exam_bundle import build_exam_bundle


def questions() -> dict:
    return {
        "source_file": "exam.pdf",
        "exam_title": "Sample",
        "course_code": "MNF130",
        "language": "english",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Truth values.",
                "page_start": 1,
                "page_end": 1,
                "points": None,
                "topic": "predicates",
                "subquestions": [
                    {"id": "q1a", "label": "a", "text": "P(orange).", "points": None},
                    {"id": "q1b", "label": "b", "text": "P(lemon).", "points": None},
                ],
            },
            {
                "id": "q8",
                "question_number": "8",
                "question_text": "Syllogism.",
                "page_start": 2,
                "page_end": 2,
                "points": None,
                "topic": "logical implication / quantifiers",
                "subquestions": [
                    {
                        "id": "q8_followup",
                        "label": "followup",
                        "text": "Does (c) follow from (a) and (b)?",
                        "points": None,
                    }
                ],
            },
        ],
        "warnings": [],
    }


def solutions() -> dict:
    return {
        "source_file": "solutions.pdf",
        "source_type": "separate_solution_pdf",
        "exam_title": "Sample",
        "course_code": "MNF130",
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
                        "explanation": "The word orange contains a.",
                        "grading_points": ["Correct truth value"],
                        "points": None,
                        "source": "official_solution_pdf",
                    },
                    {
                        "question_id": "q1b",
                        "label": "b",
                        "answer": "False",
                        "explanation": "The word lemon does not contain a.",
                        "grading_points": ["Correct truth value"],
                        "points": None,
                        "source": "official_solution_pdf",
                    }
                ],
                "warnings": [],
            },
            {
                "question_id": "q8",
                "question_number": "8",
                "solution_text": None,
                "subsolutions": [
                    {
                        "question_id": "q8_followup",
                        "label": "followup",
                        "answer": "No",
                        "explanation": "The conclusion does not follow.",
                        "grading_points": [],
                        "points": None,
                        "source": "official_solution_pdf",
                    }
                ],
                "warnings": [],
            },
        ],
        "warnings": [],
    }


def test_q1a_solution_attaches_to_q1a() -> None:
    bundle = build_exam_bundle(questions(), solutions())

    q1a = bundle["questions"][0]["subquestions"][0]
    assert q1a["solution"]["answer"] == "True"
    assert q1a["solution"]["source"] == "official_solution_pdf"


def test_q8_followup_solution_attaches_correctly() -> None:
    bundle = build_exam_bundle(questions(), solutions())

    followup = bundle["questions"][1]["subquestions"][0]
    assert followup["solution"]["answer"] == "No"


def test_missing_solution_becomes_null_when_solutions_were_provided() -> None:
    solution_result = solutions()
    solution_result["solutions"][0]["subsolutions"] = [
        subsolution
        for subsolution in solution_result["solutions"][0]["subsolutions"]
        if subsolution["question_id"] != "q1b"
    ]

    bundle = build_exam_bundle(questions(), solution_result)

    q1b = bundle["questions"][0]["subquestions"][1]
    assert q1b["solution"] is None
    assert any("No solution found for question 1b" in warning for warning in bundle["warnings"])


def test_unmatched_solution_creates_warning() -> None:
    solution_result = solutions()
    solution_result["solutions"].append(
        {
            "question_id": "q99",
            "question_number": "99",
            "solution_text": None,
            "subsolutions": [
                {
                    "question_id": "q99a",
                    "label": "a",
                    "answer": "Extra",
                    "explanation": None,
                    "grading_points": [],
                    "points": None,
                    "source": "official_solution_pdf",
                }
            ],
            "warnings": [],
        }
    )

    bundle = build_exam_bundle(questions(), solution_result)

    assert any("Unmatched solution for q99a a." in warning for warning in bundle["warnings"])


def test_existing_question_fields_are_preserved() -> None:
    bundle = build_exam_bundle(questions(), solutions())

    q1 = bundle["questions"][0]
    assert q1["question_text"] == "Truth values."
    assert q1["topic"] == "predicates"
    assert q1["page_start"] == 1


def test_question_images_attach_by_page_range() -> None:
    extraction_result = {
        "pages": [
            {
                "page_number": 1,
                "images": [
                    {
                        "id": "page_1_img_1",
                        "src": "/sample-assets/exam/page_1_img_1.png",
                        "path": "assets/exam/page_1_img_1.png",
                        "page_number": 1,
                        "bbox": [10, 20, 100, 120],
                        "width": 180,
                        "height": 200,
                    }
                ],
            },
            {
                "page_number": 3,
                "images": [
                    {
                        "id": "page_3_img_1",
                        "src": "/sample-assets/exam/page_3_img_1.png",
                        "path": "assets/exam/page_3_img_1.png",
                        "page_number": 3,
                        "bbox": [10, 20, 100, 120],
                        "width": 180,
                        "height": 200,
                    }
                ],
            },
        ]
    }

    bundle = build_exam_bundle(questions(), solutions(), extraction_result=extraction_result)

    assert bundle["questions"][0]["images"] == [
        {
            "id": "page_1_img_1",
            "src": "/sample-assets/exam/page_1_img_1.png",
            "path": "assets/exam/page_1_img_1.png",
            "page_number": 1,
            "bbox": [10, 20, 100, 120],
            "width": 180,
            "height": 200,
            "alt": "Image from page 1",
        }
    ]
    assert bundle["questions"][1]["images"] == []


def test_parent_solution_with_matched_subsolutions_does_not_create_parent_unmatched_warning() -> None:
    solution_result = solutions()
    solution_result["solutions"][0]["solution_text"] = "Answers for question 1."

    bundle = build_exam_bundle(questions(), solution_result)

    assert "Unmatched solution for q1 ." not in bundle["warnings"]


def test_all_matching_subsolutions_produce_empty_warnings() -> None:
    bundle = build_exam_bundle(questions(), solutions())

    assert bundle["warnings"] == []


def test_multiple_choice_choices_include_solution_answer_when_ai_missed_it() -> None:
    question_result = questions()
    subquestion = question_result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = ['"HelloWorld"', '"HWeolrllod"']
    solution_result = solutions()
    solution_result["solutions"][0]["subsolutions"][0]["answer"] = "10"

    bundle = build_exam_bundle(question_result, solution_result)

    assert bundle["questions"][0]["subquestions"][0]["choices"] == [
        "10",
        '"HelloWorld"',
        '"HWeolrllod"',
    ]
