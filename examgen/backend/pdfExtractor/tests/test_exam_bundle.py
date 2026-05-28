from exam_parser.post.exam_bundle import build_exam_bundle


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


def test_multiple_choice_does_not_add_answer_label_when_labelled_option_exists() -> None:
    question_result = questions()
    subquestion = question_result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = [
        "A. To allow objects to be treated as instances of their parent class",
        "B. To restrict access to private class members",
    ]
    solution_result = solutions()
    solution_result["solutions"][0]["subsolutions"][0]["answer"] = "A"

    bundle = build_exam_bundle(question_result, solution_result)

    assert bundle["questions"][0]["subquestions"][0]["choices"] == [
        "A. To allow objects to be treated as instances of their parent class",
        "B. To restrict access to private class members",
    ]


def test_multiple_choice_choices_are_sanitized_when_ai_added_too_many_options() -> None:
    question_result = questions()
    subquestion = question_result["questions"][0]["subquestions"][0]
    subquestion["interaction_type"] = "multiple_choice"
    subquestion["choices"] = [
        "Hva er verdien av length [1,4..5]?",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
    ]
    solution_result = solutions()
    solution_result["solutions"][0]["subsolutions"][0]["answer"] = "3"

    bundle = build_exam_bundle(question_result, solution_result)

    assert bundle["questions"][0]["subquestions"][0]["choices"] == ["1", "2", "3", "4", "5", "6"]


def test_generated_numeric_solution_id_attaches_by_question_number_and_label() -> None:
    question_result = {
        "source_file": "exam.pdf",
        "exam_title": "Sample",
        "course_code": "INF122",
        "language": "norwegian",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Verdier.",
                "page_start": 1,
                "page_end": 1,
                "points": None,
                "topic": "Haskell",
                "subquestions": [
                    {"id": "q1a", "label": "1", "text": "head (tail [1,2,3])", "points": None},
                ],
            }
        ],
        "warnings": [],
    }
    solution_result = {
        "source_file": "exam.pdf",
        "source_type": "ai_generated",
        "exam_title": "Sample",
        "course_code": "INF122",
        "solutions": [
            {
                "question_id": "q1",
                "question_number": "1",
                "solution_text": None,
                "page_start": None,
                "page_end": None,
                "subsolutions": [
                    {
                        "question_id": "q1_1",
                        "label": "1.1",
                        "answer": "2",
                        "explanation": "tail [1,2,3] is [2,3], then head is 2.",
                        "grading_points": [],
                        "points": None,
                        "page_start": None,
                        "page_end": None,
                        "source": "ai_generated",
                    }
                ],
                "warnings": [],
            }
        ],
        "warnings": [
            "These are AI-generated solutions and not official solutions.",
            "AI-generated solutions; not official answer key.",
        ],
    }

    bundle = build_exam_bundle(question_result, solution_result)

    subquestion = bundle["questions"][0]["subquestions"][0]
    assert subquestion["solution"]["answer"] == "2"
    assert not any("Unmatched solution for q1_1" in warning for warning in bundle["warnings"])
    assert bundle["warnings"].count("AI-generated solutions; not official answer key.") == 1


def test_question_level_ai_solution_keeps_ai_source() -> None:
    question_result = {
        "source_file": "exam.pdf",
        "exam_title": "Sample",
        "course_code": "INF222",
        "language": "english",
        "questions": [
            {
                "id": "q1_5",
                "question_number": "1.5",
                "question_text": "Typing disciplines",
                "context": "For each description, write the best matching term.",
                "page_start": 2,
                "page_end": 2,
                "points": None,
                "topic": "Type systems",
                "interaction_type": "free_text",
                "choices": [],
                "subquestions": [],
            }
        ],
        "warnings": [],
    }
    solution_result = {
        "source_file": "exam.pdf",
        "source_type": "ai_generated",
        "exam_title": "Sample",
        "course_code": "INF222",
        "solutions": [
            {
                "question_id": "q1_5",
                "question_number": "1.5",
                "solution_text": "A structurally typed. B statically typed.",
                "subsolutions": [],
                "warnings": [],
            }
        ],
        "warnings": ["AI-generated solutions; not official answer key."],
    }

    bundle = build_exam_bundle(question_result, solution_result)

    assert bundle["questions"][0]["solution"]["source"] == "ai_generated"


def test_matched_parent_solution_suppresses_artificial_subsolution_warnings() -> None:
    question_result = {
        "source_file": "exam.pdf",
        "exam_title": "Sample",
        "course_code": "INF222",
        "language": "english",
        "questions": [
            {
                "id": "q1_1",
                "question_number": "1.1",
                "question_text": "Parameter passing modes",
                "context": "interface BagIndex { ... }",
                "page_start": 1,
                "page_end": 1,
                "points": None,
                "topic": "Parameter passing",
                "interaction_type": "free_text",
                "choices": [],
                "subquestions": [],
            }
        ],
        "warnings": [],
    }
    solution_result = {
        "source_file": "exam.pdf",
        "source_type": "ai_generated",
        "exam_title": "Sample",
        "course_code": "INF222",
        "solutions": [
            {
                "question_id": "q1_1",
                "question_number": "1.1",
                "solution_text": "Use obs for read-only values and upd/out for written values.",
                "subsolutions": [
                    {
                        "question_id": "q1_1",
                        "label": "insert",
                        "answer": "obs Element e, upd Bag b",
                        "explanation": "Artificial split from the model.",
                        "grading_points": [],
                        "points": None,
                        "page_start": None,
                        "page_end": None,
                        "source": "ai_generated",
                    }
                ],
                "warnings": [],
            }
        ],
        "warnings": ["AI-generated solutions; not official answer key."],
    }

    bundle = build_exam_bundle(question_result, solution_result)

    assert bundle["questions"][0]["solution"]["source"] == "ai_generated"
    assert not any("Unmatched solution for q1_1 insert" in warning for warning in bundle["warnings"])
