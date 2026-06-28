"""Generate a fresh exam from an existing exam and reference material."""

from __future__ import annotations

import json
import os
from typing import Any

from exam_parser.ai.question_extractor import (
    DEFAULT_MODEL_NAME,
    QuestionExtractionError,
    _combined_page_text,
    _create_gemini_client,
    _extract_response_text,
    _generate_content_config,
    _parse_json_response,
    post_process_questions,
    validate_question_extraction_result,
)
from exam_parser.schemas import QUESTION_EXTRACTION_SCHEMA


GENERATED_EXAM_WARNING = "AI-generated exam and solutions; not official exam material."


class GeneratedExamExtractionError(Exception):
    """Raised when AI exam generation cannot complete cleanly."""


def build_generated_exam_prompt(
    exam_extraction: dict[str, Any],
    reference_extraction: dict[str, Any],
    original_questions_result: dict[str, Any],
) -> str:
    """Build the Gemini prompt for creating a new exam."""
    original_questions_json = json.dumps(original_questions_result, ensure_ascii=False, indent=2)
    exam_text = _combined_page_text(exam_extraction)
    reference_text = _combined_page_text(reference_extraction)
    if not exam_text:
        raise GeneratedExamExtractionError("Exam PDF contains no text to use as a style reference.")
    if not reference_text:
        raise GeneratedExamExtractionError("No usable source text was found for generated exam material.")

    return f"""You are generating a fresh practice exam as structured JSON.

Rules:
- Generate a new exam, not a copy of the original exam.
- Match the original exam's approximate number of main questions, subquestion structure, interaction types, topic mix, and difficulty.
- Use the source material as topic and correctness context. It may be the original exam itself,
  or an optional syllabus, notes, official answers, marking guidance, or mixed document.
- If the source material is a syllabus or notes, turn that material into solvable exam tasks.
- If the source material is a solution key, use it as a topic and correctness guide, not as text to copy.
- Do not reuse exact question wording unless a term, formula, type signature, or code identifier must stay exact.
- Preserve Norwegian/English style from the original exam when obvious.
- Put question-specific setup, definitions, examples, code, tables, or formulas in context.
- Format code inside context as fenced Markdown code blocks with the best language tag.
- When a visual would help the student solve the task, add a structured diagrams entry on the main question.
- Use graph diagrams for node-link graph tasks, especially BFS/DFS traversal, shortest path,
  minimum spanning tree, reachability, adjacency, or graph-representation questions.
- Use tree diagrams for tree data structure, binary tree, expression tree, recursion-over-tree,
  traversal, leaf-counting, height/depth, flattening, or inductive tree tasks.
- A graph diagram must use type "graph" and include stable node ids, node labels, edges with source/target,
  optional edge label/weight, optional directed flag, and optional start_node/highlighted_nodes/highlighted_edges.
- A tree diagram must use type "tree" and include a root node with stable nested children. Nodes may include labels.
- Do not include raster images, generated image URLs, base64 image data, SVG markup, Mermaid syntax, or x/y coordinates.
- The frontend will lay out graph and tree diagrams automatically from structured data.
- Set page_start and page_end to null because generated questions do not come from original pages.
- Use stable generated IDs: q1, q2, q3 for main questions and q1a, q1b for subquestions.
- For every question and subquestion, set interaction_type and choices according to the schema.
- Add this warning exactly once in warnings: {GENERATED_EXAM_WARNING}
- Return only JSON matching the schema.

JSON schema:
{json.dumps(QUESTION_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

Original extracted question structure:
{original_questions_json}

Original exam text for style reference:
{exam_text}

Source material text for generation:
{reference_text}
"""


def extract_generated_exam_questions_with_gemini(
    exam_extraction: dict[str, Any],
    reference_extraction: dict[str, Any],
    original_questions_result: dict[str, Any],
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = 0.2,
    max_output_tokens: int = 16384,
) -> dict[str, Any]:
    """Create structured questions for a new exam using Gemini."""
    if model_name == DEFAULT_MODEL_NAME:
        model_name = os.getenv("GEMINI_QUESTION_MODEL") or os.getenv("GEMINI_MODEL", model_name)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeneratedExamExtractionError("Missing GEMINI_API_KEY environment variable.")

    prompt = build_generated_exam_prompt(exam_extraction, reference_extraction, original_questions_result)
    try:
        client = _create_gemini_client(api_key)
        config = _generate_content_config(temperature, max_output_tokens)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        result = _parse_json_response(_extract_response_text(response))
    except QuestionExtractionError as exc:
        raise GeneratedExamExtractionError(str(exc)) from exc
    except Exception as exc:
        raise GeneratedExamExtractionError(f"Gemini API request failed: {exc}") from exc

    result = post_process_questions(result)
    normalize_generated_question_ids(result)
    normalize_generated_matrix_choices(result)
    normalize_generated_diagrams(result)
    _ensure_generated_warning(result)
    validate_question_extraction_result(result)
    return result


def normalize_generated_question_ids(result: dict[str, Any]) -> None:
    """Make generated question IDs deterministic before solution generation."""
    for question_index, question in enumerate(result.get("questions", []), start=1):
        if not isinstance(question, dict):
            continue
        question_number = str(question.get("question_number") or question_index).strip()
        question["id"] = _canonical_answer_id(question_number)
        for sub_index, subquestion in enumerate(question.get("subquestions", []), start=1):
            if not isinstance(subquestion, dict):
                continue
            label = str(subquestion.get("label") or sub_index).strip()
            subquestion["id"] = _canonical_answer_id(question_number, label)


def normalize_generated_matrix_choices(result: dict[str, Any]) -> None:
    """Repair or downgrade generated matrix choices missing valid matrix metadata."""
    for question in result.get("questions", []):
        if not isinstance(question, dict):
            continue
        _normalize_matrix_choice_item(question)
        for subquestion in question.get("subquestions", []):
            if isinstance(subquestion, dict):
                _normalize_matrix_choice_item(subquestion)


def _normalize_matrix_choice_item(item: dict[str, Any]) -> None:
    if item.get("interaction_type") != "matrix_choice":
        return

    matrix = _clean_matrix(item.get("matrix"))
    if matrix is not None:
        item["matrix"] = matrix
        item["choices"] = matrix["columns"]
        return

    choices = _clean_string_list(item.get("choices"))
    if len(choices) >= 2:
        item["interaction_type"] = "multiple_choice"
        item["choices"] = choices
    else:
        item["interaction_type"] = "free_text"
        item["choices"] = []
    item.pop("matrix", None)


def _clean_matrix(matrix: Any) -> dict[str, list[str]] | None:
    if not isinstance(matrix, dict):
        return None
    rows = _clean_string_list(matrix.get("rows"))
    columns = _clean_string_list(matrix.get("columns"))
    if len(rows) < 1 or len(columns) < 2:
        return None
    return {
        "rows": rows,
        "columns": columns,
    }


def _clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _clean_string(value)
        if not normalized or normalized in seen:
            continue
        cleaned.append(normalized)
        seen.add(normalized)
    return cleaned


def normalize_generated_diagrams(result: dict[str, Any]) -> None:
    """Clean generated structured diagrams without rejecting the whole exam."""
    for question_index, question in enumerate(result.get("questions", []), start=1):
        if not isinstance(question, dict):
            continue
        diagrams = question.get("diagrams")
        if not isinstance(diagrams, list):
            diagrams = []
        cleaned = [
            diagram
            for diagram in (
                _clean_diagram(diagram, question_index, diagram_index)
                for diagram_index, diagram in enumerate(diagrams, start=1)
            )
            if diagram is not None
        ]
        if not cleaned and _looks_like_tree_visual_task(question):
            cleaned = [_default_tree_diagram(question, question_index)]
        if cleaned:
            question["diagrams"] = cleaned
        else:
            question.pop("diagrams", None)


def _looks_like_tree_visual_task(question: dict[str, Any]) -> bool:
    searchable_parts = [
        question.get("question_text"),
        question.get("context"),
        question.get("topic"),
    ]
    for subquestion in question.get("subquestions", []):
        if isinstance(subquestion, dict):
            searchable_parts.append(subquestion.get("text"))
    searchable = "\n".join(part for part in searchable_parts if isinstance(part, str)).casefold()
    if not searchable:
        return False
    tree_markers = (
        "data tree",
        "binary tree",
        "binært",
        "binærtre",
        "treet",
        "tree a",
        "leaf",
        "node (tree",
    )
    task_markers = (
        "recursion",
        "rekursjon",
        "treesize",
        "treeheight",
        "countleaves",
        "flatten",
        "height",
        "depth",
        "leaves",
        "traversal",
        "beregner høyden",
        "teller antall",
    )
    return any(marker in searchable for marker in tree_markers) and any(
        marker in searchable for marker in task_markers
    )


def _default_tree_diagram(question: dict[str, Any], question_index: int) -> dict[str, Any]:
    question_id = _clean_string(question.get("id")) or f"q{question_index}"
    return {
        "id": f"{question_id}_tree",
        "type": "tree",
        "title": "Example tree",
        "root": {
            "id": "root",
            "label": "Node",
            "children": [
                {
                    "id": "left",
                    "label": "Leaf a",
                },
                {
                    "id": "right",
                    "label": "Node",
                    "children": [
                        {
                            "id": "right_left",
                            "label": "Leaf b",
                        },
                        {
                            "id": "right_right",
                            "label": "Leaf c",
                        },
                    ],
                },
            ],
        },
    }


def _clean_diagram(diagram: Any, question_index: int, diagram_index: int) -> dict[str, Any] | None:
    if not isinstance(diagram, dict):
        return None
    if diagram.get("type") == "tree":
        return _clean_tree_diagram(diagram, question_index, diagram_index)
    return _clean_graph_diagram(diagram, question_index, diagram_index)


def _clean_graph_diagram(
    diagram: Any,
    question_index: int,
    diagram_index: int,
) -> dict[str, Any] | None:
    if not isinstance(diagram, dict) or diagram.get("type") != "graph":
        return None

    nodes = _clean_graph_nodes(diagram.get("nodes"))
    if len(nodes) < 2:
        return None
    node_ids = {node["id"] for node in nodes}

    edges = _clean_graph_edges(diagram.get("edges"), node_ids)
    if not edges:
        return None

    diagram_id = _clean_string(diagram.get("id")) or f"q{question_index}_diagram_{diagram_index}"
    cleaned: dict[str, Any] = {
        "id": diagram_id,
        "type": "graph",
        "nodes": nodes,
        "edges": edges,
    }
    title = _clean_string(diagram.get("title"))
    if title:
        cleaned["title"] = title

    start_node = _clean_string(diagram.get("start_node"))
    if start_node in node_ids:
        cleaned["start_node"] = start_node

    highlighted_nodes = _clean_reference_list(diagram.get("highlighted_nodes"), node_ids)
    if highlighted_nodes:
        cleaned["highlighted_nodes"] = highlighted_nodes

    edge_ids = {edge["id"] for edge in edges if isinstance(edge.get("id"), str)}
    highlighted_edges = _clean_reference_list(diagram.get("highlighted_edges"), edge_ids)
    if highlighted_edges:
        cleaned["highlighted_edges"] = highlighted_edges

    return cleaned


def _clean_tree_diagram(
    diagram: Any,
    question_index: int,
    diagram_index: int,
) -> dict[str, Any] | None:
    if not isinstance(diagram, dict) or diagram.get("type") != "tree":
        return None
    seen_ids: set[str] = set()
    root = _clean_tree_node(diagram.get("root"), seen_ids)
    if root is None:
        return None
    diagram_id = _clean_string(diagram.get("id")) or f"q{question_index}_tree_{diagram_index}"
    cleaned: dict[str, Any] = {
        "id": diagram_id,
        "type": "tree",
        "root": root,
    }
    title = _clean_string(diagram.get("title"))
    if title:
        cleaned["title"] = title
    highlighted_nodes = _clean_reference_list(diagram.get("highlighted_nodes"), seen_ids)
    if highlighted_nodes:
        cleaned["highlighted_nodes"] = highlighted_nodes
    return cleaned


def _clean_tree_node(node: Any, seen_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        return None
    node_id = _clean_string(node.get("id"))
    if not node_id or node_id in seen_ids:
        return None
    seen_ids.add(node_id)
    cleaned: dict[str, Any] = {"id": node_id}
    label = _clean_string(node.get("label"))
    if label:
        cleaned["label"] = label
    raw_children = node.get("children", [])
    if not isinstance(raw_children, list):
        raw_children = []
    children = [
        child
        for child in (_clean_tree_node(child, seen_ids) for child in raw_children)
        if child is not None
    ]
    if children:
        cleaned["children"] = children
    return cleaned


def _clean_graph_nodes(nodes: Any) -> list[dict[str, str]]:
    if not isinstance(nodes, list):
        return []
    cleaned: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = _clean_string(node.get("id"))
        if not node_id or node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        cleaned_node = {"id": node_id}
        label = _clean_string(node.get("label"))
        if label:
            cleaned_node["label"] = label
        cleaned.append(cleaned_node)
    return cleaned


def _clean_graph_edges(edges: Any, node_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(edges, list):
        return []
    cleaned: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str, bool]] = set()
    seen_edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = _clean_string(edge.get("source"))
        target = _clean_string(edge.get("target"))
        if source not in node_ids or target not in node_ids:
            continue
        label = _clean_string(edge.get("label"))
        weight = _clean_string(edge.get("weight"))
        directed = edge.get("directed") is True
        edge_key = (source, target, label or "", weight or "", directed)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)

        cleaned_edge: dict[str, Any] = {
            "source": source,
            "target": target,
        }
        edge_id = _clean_string(edge.get("id"))
        if edge_id and edge_id not in seen_edge_ids:
            cleaned_edge["id"] = edge_id
            seen_edge_ids.add(edge_id)
        if label:
            cleaned_edge["label"] = label
        if weight:
            cleaned_edge["weight"] = weight
        if directed:
            cleaned_edge["directed"] = True
        cleaned.append(cleaned_edge)
    return cleaned


def _clean_reference_list(values: Any, valid_values: set[str]) -> list[str]:
    if not isinstance(values, list) or not valid_values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _clean_string(value)
        if not normalized or normalized in seen or normalized not in valid_values:
            continue
        cleaned.append(normalized)
        seen.add(normalized)
    return cleaned


def _clean_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _canonical_answer_id(question_number: str, label: str = "") -> str:
    parts = [_id_part(question_number)]
    label_part = _id_part(_normalize_subquestion_label(label, question_number))
    if label_part:
        parts.append(label_part)
    return "q" + "_".join(part for part in parts if part)


def _normalize_subquestion_label(label: str, question_number: str) -> str:
    normalized = str(label or "").strip()
    if question_number and normalized != question_number and normalized.startswith(question_number):
        normalized = normalized[len(question_number) :]
    return normalized.strip(" .):-")


def _id_part(value: str) -> str:
    import re

    normalized = re.sub(r"[^0-9A-Za-z]+", "_", str(value or "").strip()).strip("_")
    return normalized.lower()


def _ensure_generated_warning(result: dict[str, Any]) -> None:
    warnings = result.setdefault("warnings", [])
    if not isinstance(warnings, list):
        result["warnings"] = [GENERATED_EXAM_WARNING]
        return
    if GENERATED_EXAM_WARNING not in warnings:
        warnings.append(GENERATED_EXAM_WARNING)
