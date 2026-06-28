"""Typed shapes and JSON schema for AI-extracted exam questions."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


InteractionType = Literal[
    "free_text",
    "true_false",
    "multiple_choice",
    "matrix_choice",
    "numeric",
    "proof",
    "translation",
]


class ExtractedSubquestion(TypedDict):
    id: str
    label: str
    text: str
    points: float | int | None
    interaction_type: InteractionType
    choices: list[str]
    matrix: NotRequired[dict[str, list[str]]]


class ExtractedGraphNode(TypedDict):
    id: str
    label: NotRequired[str | None]


class ExtractedGraphEdge(TypedDict):
    id: NotRequired[str | None]
    source: str
    target: str
    label: NotRequired[str | None]
    weight: NotRequired[str | int | float | None]
    directed: NotRequired[bool | None]


class ExtractedGraphDiagram(TypedDict):
    id: str
    type: Literal["graph"]
    title: NotRequired[str | None]
    nodes: list[ExtractedGraphNode]
    edges: list[ExtractedGraphEdge]
    start_node: NotRequired[str | None]
    highlighted_nodes: NotRequired[list[str]]
    highlighted_edges: NotRequired[list[str]]


class ExtractedTreeNode(TypedDict):
    id: str
    label: NotRequired[str | None]
    children: NotRequired[list["ExtractedTreeNode"]]


class ExtractedTreeDiagram(TypedDict):
    id: str
    type: Literal["tree"]
    title: NotRequired[str | None]
    root: ExtractedTreeNode
    highlighted_nodes: NotRequired[list[str]]


class ExtractedQuestion(TypedDict):
    id: str
    question_number: str
    question_text: str
    context: str | None
    page_start: int | None
    page_end: int | None
    points: float | int | None
    topic: str | None
    interaction_type: InteractionType
    choices: list[str]
    matrix: NotRequired[dict[str, list[str]]]
    diagrams: NotRequired[list[ExtractedGraphDiagram | ExtractedTreeDiagram]]
    subquestions: list[ExtractedSubquestion]


class QuestionExtractionResult(TypedDict):
    source_file: str
    exam_title: str | None
    course_code: str | None
    language: str
    questions: list[ExtractedQuestion]
    warnings: list[str]


LanguageHint = Literal["english", "norwegian", "mixed"]


GRAPH_DIAGRAM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["graph"]},
        "title": {"type": "string", "nullable": True},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string", "nullable": True},
                },
                "required": ["id"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "nullable": True},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "label": {"type": "string", "nullable": True},
                    "weight": {"type": "string", "nullable": True},
                    "directed": {"type": "boolean", "nullable": True},
                },
                "required": ["source", "target"],
            },
        },
        "start_node": {"type": "string", "nullable": True},
        "highlighted_nodes": {"type": "array", "items": {"type": "string"}},
        "highlighted_edges": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "type", "nodes", "edges"],
}


TREE_NODE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string", "nullable": True},
        "children": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string", "nullable": True},
                    "children": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string", "nullable": True},
                            },
                            "required": ["id"],
                        },
                    },
                },
                "required": ["id"],
            },
        },
    },
    "required": ["id"],
}


TREE_DIAGRAM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["tree"]},
        "title": {"type": "string", "nullable": True},
        "root": TREE_NODE_SCHEMA,
        "highlighted_nodes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "type", "root"],
}


QUESTION_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source_file": {"type": "string"},
        "exam_title": {"type": "string", "nullable": True},
        "course_code": {"type": "string", "nullable": True},
        "language": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question_number": {"type": "string"},
                    "question_text": {"type": "string"},
                    "context": {
                        "type": "string",
                        "nullable": True,
                        "description": (
                            "Question-specific context needed to solve this main question, such as introductions, "
                            "definitions, helper code, data model setup, function/type signatures, rules, examples, "
                            "or figure references. Do not include general exam instructions, table of contents, "
                            "candidate metadata, time/date, allowed aids, or unrelated text."
                        ),
                    },
                    "page_start": {"type": "integer", "nullable": True},
                    "page_end": {"type": "integer", "nullable": True},
                    "points": {"type": "number", "nullable": True},
                    "topic": {"type": "string", "nullable": True},
                    "interaction_type": {
                        "type": "string",
                        "enum": [
                            "free_text",
                            "true_false",
                            "multiple_choice",
                            "matrix_choice",
                            "numeric",
                            "proof",
                            "translation",
                        ],
                    },
                    "choices": {"type": "array", "items": {"type": "string"}},
                    "matrix": {
                        "type": "object",
                        "properties": {
                            "rows": {"type": "array", "items": {"type": "string"}},
                            "columns": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "diagrams": {
                        "type": "array",
                        "items": {
                            "anyOf": [
                                GRAPH_DIAGRAM_SCHEMA,
                                TREE_DIAGRAM_SCHEMA,
                            ],
                        },
                        "description": (
                            "Optional structured diagrams for generated practice questions. "
                            "Use graph diagrams for node-link graph tasks and tree diagrams for tree/recursion tasks."
                        ),
                    },
                    "subquestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {
                                    "type": "string",
                                    "description": 'Letter label such as "a", or "followup" for an unlabelled follow-up task.',
                                },
                                "text": {"type": "string"},
                                "points": {"type": "number", "nullable": True},
                                "interaction_type": {
                                    "type": "string",
                                    "enum": [
                                        "free_text",
                                        "true_false",
                                        "multiple_choice",
                                        "matrix_choice",
                                        "numeric",
                                        "proof",
                                        "translation",
                                    ],
                                },
                                "choices": {"type": "array", "items": {"type": "string"}},
                                "matrix": {
                                    "type": "object",
                                    "properties": {
                                        "rows": {"type": "array", "items": {"type": "string"}},
                                        "columns": {"type": "array", "items": {"type": "string"}},
                                    },
                                },
                            },
                            "required": [
                                "id",
                                "label",
                                "text",
                                "points",
                                "interaction_type",
                                "choices",
                            ],
                        },
                    },
                },
                "required": [
                    "id",
                    "question_number",
                    "question_text",
                    "context",
                    "page_start",
                    "page_end",
                    "points",
                    "topic",
                    "interaction_type",
                    "choices",
                    "subquestions",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "source_file",
        "exam_title",
        "course_code",
        "language",
        "questions",
        "warnings",
    ],
}

