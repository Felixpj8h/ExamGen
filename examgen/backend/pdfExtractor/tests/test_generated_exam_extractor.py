from exam_parser.ai.generated_exam_extractor import (
    build_generated_exam_prompt,
    normalize_generated_diagrams,
    normalize_generated_matrix_choices,
    normalize_generated_question_ids,
)
from exam_parser.ai.question_extractor import validate_question_extraction_result


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


def test_normalize_generated_matrix_choices_downgrades_missing_matrix_metadata() -> None:
    result = {
        "questions": [
            {
                "id": "q7",
                "question_number": "7",
                "interaction_type": "matrix_choice",
                "choices": ["A,B,C,D,E", "A,B,D,E,C"],
                "subquestions": [
                    {
                        "id": "q7a",
                        "label": "a",
                        "text": "BFS",
                        "interaction_type": "matrix_choice",
                        "choices": [],
                    }
                ],
            }
        ]
    }

    normalize_generated_matrix_choices(result)

    question = result["questions"][0]
    subquestion = question["subquestions"][0]
    assert question["interaction_type"] == "multiple_choice"
    assert question["choices"] == ["A,B,C,D,E", "A,B,D,E,C"]
    assert "matrix" not in question
    assert subquestion["interaction_type"] == "free_text"
    assert subquestion["choices"] == []


def test_normalize_generated_matrix_choices_keeps_valid_matrix_metadata() -> None:
    result = {
        "questions": [
            {
                "id": "q7",
                "question_number": "7",
                "interaction_type": "matrix_choice",
                "choices": ["old"],
                "matrix": {
                    "rows": ["BFS", "DFS", "BFS"],
                    "columns": ["A,B,C,D,E", "A,B,D,E,C"],
                },
                "subquestions": [],
            }
        ]
    }

    normalize_generated_matrix_choices(result)

    question = result["questions"][0]
    assert question["interaction_type"] == "matrix_choice"
    assert question["choices"] == ["A,B,C,D,E", "A,B,D,E,C"]
    assert question["matrix"] == {
        "rows": ["BFS", "DFS"],
        "columns": ["A,B,C,D,E", "A,B,D,E,C"],
    }


def test_generated_question_schema_accepts_valid_graph_diagram() -> None:
    result = {
        "source_file": "generated_exam",
        "exam_title": "Generated",
        "course_code": "INF",
        "language": "english",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Graph traversal",
                "context": "Run BFS from A.",
                "page_start": None,
                "page_end": None,
                "points": None,
                "topic": "Graph algorithms",
                "interaction_type": "free_text",
                "choices": [],
                "diagrams": [
                    {
                        "id": "q1_graph",
                        "type": "graph",
                        "title": "Traversal graph",
                        "nodes": [
                            {"id": "A", "label": "A"},
                            {"id": "B", "label": "B"},
                        ],
                        "edges": [
                            {"id": "ab", "source": "A", "target": "B", "weight": 3, "directed": True}
                        ],
                        "start_node": "A",
                        "highlighted_nodes": ["A"],
                        "highlighted_edges": ["ab"],
                    }
                ],
                "subquestions": [],
            }
        ],
        "warnings": [],
    }

    validate_question_extraction_result(result)


def test_generated_question_schema_accepts_valid_tree_diagram() -> None:
    result = {
        "source_file": "generated_exam",
        "exam_title": "Generated",
        "course_code": "INF",
        "language": "english",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Tree recursion",
                "context": "data Tree a = Leaf a | Node (Tree a) (Tree a)",
                "page_start": None,
                "page_end": None,
                "points": None,
                "topic": "Trees",
                "interaction_type": "free_text",
                "choices": [],
                "diagrams": [
                    {
                        "id": "q1_tree",
                        "type": "tree",
                        "title": "Example tree",
                        "root": {
                            "id": "root",
                            "label": "Node",
                            "children": [
                                {"id": "left", "label": "Leaf a"},
                                {
                                    "id": "right",
                                    "label": "Node",
                                    "children": [{"id": "right_left", "label": "Leaf b"}],
                                },
                            ],
                        },
                        "highlighted_nodes": ["left"],
                    }
                ],
                "subquestions": [],
            }
        ],
        "warnings": [],
    }

    validate_question_extraction_result(result)


def test_generated_question_schema_accepts_valid_chart_diagram() -> None:
    result = {
        "source_file": "generated_exam",
        "exam_title": "Generated",
        "course_code": "INF",
        "language": "english",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "Compare growth rates.",
                "context": "Use the chart.",
                "page_start": None,
                "page_end": None,
                "points": None,
                "topic": "Runtime",
                "interaction_type": "free_text",
                "choices": [],
                "diagrams": [
                    {
                        "id": "q1_chart",
                        "type": "chart",
                        "title": "Runtime growth",
                        "chart_type": "line",
                        "x_label": "n",
                        "y_label": "ms",
                        "data": [
                            {"label": "10", "value": 1},
                            {"label": "20", "value": 4},
                        ],
                    }
                ],
                "subquestions": [],
            }
        ],
        "warnings": [],
    }

    validate_question_extraction_result(result)


def test_normalize_generated_diagrams_drops_malformed_graph_parts() -> None:
    result = {
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "diagrams": [
                    {
                        "id": " messy ",
                        "type": "graph",
                        "title": " Graph ",
                        "nodes": [
                            {"id": "A", "label": "Start"},
                            {"id": "A", "label": "Duplicate"},
                            {"id": "B"},
                            {"id": "C"},
                        ],
                        "edges": [
                            {"id": "ab", "source": "A", "target": "B", "weight": 4},
                            {"id": "ab2", "source": "A", "target": "B", "weight": 4},
                            {"id": "bad", "source": "A", "target": "Z"},
                            {"source": "B", "target": "C", "directed": True},
                        ],
                        "start_node": "Z",
                        "highlighted_nodes": ["A", "Z"],
                        "highlighted_edges": ["ab", "missing"],
                    },
                    {
                        "id": "invalid",
                        "type": "graph",
                        "nodes": [{"id": "A"}],
                        "edges": [],
                    },
                    {"id": "not-graph", "type": "grid"},
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    assert result["questions"][0]["diagrams"] == [
        {
            "id": "messy",
            "type": "graph",
            "nodes": [
                {"id": "A", "label": "Start"},
                {"id": "B"},
                {"id": "C"},
            ],
            "edges": [
                {"source": "A", "target": "B", "id": "ab", "weight": "4"},
                {"source": "B", "target": "C", "directed": True},
            ],
            "title": "Graph",
            "highlighted_nodes": ["A"],
            "highlighted_edges": ["ab"],
        }
    ]


def test_normalize_generated_diagrams_keeps_clean_chart_points() -> None:
    result = {
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "diagrams": [
                    {
                        "id": " chart ",
                        "type": "chart",
                        "title": " Growth ",
                        "chart_type": "bar",
                        "x_label": " Input ",
                        "y_label": " Time ",
                        "data": [
                            {"label": "n=10", "value": 1},
                            {"label": "n=10", "value": 2},
                            {"label": "n=20", "value": 4.5},
                            {"label": "", "value": 8},
                            {"label": "bad", "value": "fast"},
                        ],
                    }
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    assert result["questions"][0]["diagrams"] == [
        {
            "id": "chart",
            "type": "chart",
            "chart_type": "bar",
            "data": [
                {"label": "n=10", "value": 1},
                {"label": "n=20", "value": 4.5},
            ],
            "title": "Growth",
            "x_label": "Input",
            "y_label": "Time",
        }
    ]


def test_normalize_generated_diagrams_adds_weighted_graph_from_text_edges() -> None:
    result = {
        "questions": [
            {
                "id": "q3",
                "question_number": "3",
                "question_text": "Vektet graf",
                "context": "Grafen har noder {A, B, C, D} og kanter: (A,B,1), (A,C,4), (B,C,2), (B,D,5), (C,D,1).",
                "topic": "Korteste vei",
                "subquestions": [
                    {
                        "id": "q3a",
                        "label": "a",
                        "text": "Hva er korteste vei fra A til D ved bruk av Dijkstras algoritme?",
                    }
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    assert result["questions"][0]["diagrams"] == [
        {
            "id": "q3_graph",
            "type": "graph",
            "title": "Weighted graph",
            "nodes": [
                {"id": "A", "label": "A"},
                {"id": "B", "label": "B"},
                {"id": "C", "label": "C"},
                {"id": "D", "label": "D"},
            ],
            "edges": [
                {"id": "a_b_1", "source": "A", "target": "B", "weight": "1"},
                {"id": "a_c_4", "source": "A", "target": "C", "weight": "4"},
                {"id": "b_c_2", "source": "B", "target": "C", "weight": "2"},
                {"id": "b_d_5", "source": "B", "target": "D", "weight": "5"},
                {"id": "c_d_1", "source": "C", "target": "D", "weight": "1"},
            ],
            "start_node": "A",
            "highlighted_nodes": ["A"],
        }
    ]


def test_normalize_generated_diagrams_keeps_clean_tree_diagram() -> None:
    result = {
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "diagrams": [
                    {
                        "id": " tree ",
                        "type": "tree",
                        "title": " Tree ",
                        "root": {
                            "id": "root",
                            "label": "Node",
                            "children": [
                                {"id": "left", "label": "Leaf"},
                                {"id": "left", "label": "Duplicate"},
                                {"id": "right", "label": "Leaf"},
                            ],
                        },
                        "highlighted_nodes": ["left", "missing"],
                    }
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    assert result["questions"][0]["diagrams"] == [
        {
            "id": "tree",
            "type": "tree",
            "root": {
                "id": "root",
                "label": "Node",
                "children": [
                    {"id": "left", "label": "Leaf"},
                    {"id": "right", "label": "Leaf"},
                ],
            },
            "title": "Tree",
            "highlighted_nodes": ["left"],
        }
    ]


def test_normalize_generated_diagrams_adds_tree_visual_for_obvious_tree_task() -> None:
    result = {
        "questions": [
            {
                "id": "q5",
                "question_number": "5",
                "question_text": "Binærtre-operasjoner",
                "context": "data Tree a = Leaf | Node a (Tree a) (Tree a)",
                "topic": "Datastrukturer og rekursjon",
                "subquestions": [
                    {
                        "id": "q5a",
                        "label": "a",
                        "text": "Skriv en funksjon treeSize:: Tree a -> Integer som teller antall noder i treet.",
                    },
                    {
                        "id": "q5b",
                        "label": "b",
                        "text": "Skriv en funksjon treeHeight:: Tree a -> Integer som beregner høyden på treet.",
                    },
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    diagram = result["questions"][0]["diagrams"][0]
    assert diagram["id"] == "q5_tree"
    assert diagram["type"] == "tree"
    assert diagram["root"]["label"] == "Node"
    assert diagram["root"]["children"][1]["children"][0]["label"] == "Leaf b"


def test_normalize_generated_diagrams_adds_tree_visual_when_diagrams_field_is_missing() -> None:
    result = {
        "questions": [
            {
                "id": "q5",
                "question_number": "5",
                "question_text": "Induktive datatyper",
                "context": "data Tree = Leaf Int | Node Tree Tree",
                "topic": "Rekursjon",
                "subquestions": [
                    {
                        "id": "q5a",
                        "label": "a",
                        "text": "Skriv en funksjon countLeaves:: Tree -> Int som teller antall blader i et tre.",
                    },
                    {
                        "id": "q5b",
                        "label": "b",
                        "text": "Skriv en funksjon sumTree:: Tree -> Int som summerer alle verdier i bladene.",
                    },
                ],
            }
        ]
    }

    normalize_generated_diagrams(result)

    assert result["questions"][0]["diagrams"][0]["type"] == "tree"


def test_generated_exam_prompt_requests_structured_graphs_not_images() -> None:
    extraction = {
        "is_text_based": True,
        "file_name": "exam.pdf",
        "page_count": 1,
        "pages": [{"page_number": 1, "clean_text": "Question 1. Run BFS on a graph."}],
    }
    original_questions = {
        "source_file": "exam.pdf",
        "exam_title": None,
        "course_code": None,
        "language": "english",
        "questions": [],
        "warnings": [],
    }

    prompt = build_generated_exam_prompt(extraction, extraction, original_questions)

    assert "structured" in prompt
    assert "type \"graph\"" in prompt
    assert "BFS/DFS" in prompt
    assert "tree diagrams" in prompt
    assert "chart diagrams" in prompt
    assert "chart_type \"bar\" or \"line\"" in prompt
    assert "tree data structure" in prompt
    assert "Do not include raster images" in prompt
    assert "SVG markup" in prompt
    assert "Mermaid syntax" in prompt
    assert "x/y coordinates" in prompt
