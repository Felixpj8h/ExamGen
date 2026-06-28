"""Generate a fresh exam from an existing exam and reference material."""

from __future__ import annotations

import json
import os
import re
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
- For weighted graph tasks, include every visible edge weight as an edge weight value.
- Only set edge directed to true when the task explicitly says the graph is directed/rettet.
  Otherwise leave directed absent or false so weighted shortest-path and MST graphs render as undirected.
- Use tree diagrams for tree data structure, binary tree, expression tree, recursion-over-tree,
  traversal, leaf-counting, height/depth, flattening, or inductive tree tasks.
- Use chart diagrams for small numeric datasets where a bar chart or line chart helps, such as
  growth rates, runtime comparisons, frequency counts, measurements, or time-series trends.
- A graph diagram must use type "graph" and include stable node ids, node labels, edges with source/target,
  optional edge label/weight, optional directed flag, and optional start_node/highlighted_nodes/highlighted_edges.
- A tree diagram must use type "tree" and include a root node with stable nested children. Nodes may include labels.
- A chart diagram must use type "chart", chart_type "bar" or "line", and data points with label and numeric value.
- Do not include raster images, generated image URLs, base64 image data, SVG markup, Mermaid syntax, or x/y coordinates.
- The frontend will lay out graph, tree, and chart diagrams automatically from structured data.
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
        if not cleaned:
            graph_diagram = _default_graph_diagram_from_text(question, question_index)
            if graph_diagram is not None:
                cleaned = [graph_diagram]
        if not cleaned and _looks_like_tree_visual_task(question):
            cleaned = [_default_tree_diagram(question, question_index)]
        if cleaned:
            question["diagrams"] = cleaned
        else:
            question.pop("diagrams", None)


def _looks_like_tree_visual_task(question: dict[str, Any]) -> bool:
    searchable = _question_searchable_text(question).casefold()
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


def _default_graph_diagram_from_text(question: dict[str, Any], question_index: int) -> dict[str, Any] | None:
    searchable = _question_searchable_text(question)
    if not searchable:
        return None
    if not _looks_like_graph_visual_task(searchable):
        return None

    parsed = _parse_weighted_graph_text(searchable)
    if parsed is None:
        return None
    nodes, edges = parsed
    if len(nodes) < 2 or not edges:
        return None

    question_id = _clean_string(question.get("id")) or f"q{question_index}"
    start_node = _first_referenced_start_node(searchable, {node["id"] for node in nodes})
    diagram: dict[str, Any] = {
        "id": f"{question_id}_graph",
        "type": "graph",
        "title": "Weighted graph",
        "nodes": nodes,
        "edges": edges,
    }
    if start_node:
        diagram["start_node"] = start_node
        diagram["highlighted_nodes"] = [start_node]
    return diagram


def _question_searchable_text(question: dict[str, Any]) -> str:
    searchable_parts = [
        question.get("question_text"),
        question.get("context"),
        question.get("topic"),
    ]
    for subquestion in question.get("subquestions", []):
        if isinstance(subquestion, dict):
            searchable_parts.append(subquestion.get("text"))
    return "\n".join(part for part in searchable_parts if isinstance(part, str))


def _looks_like_graph_visual_task(searchable: str) -> bool:
    normalized = searchable.casefold()
    graph_markers = ("graf", "graph", "noder", "nodes", "kanter", "edges")
    task_markers = (
        "dijkstra",
        "korteste vei",
        "shortest path",
        "vektet",
        "weighted",
        "bfs",
        "dfs",
        "minimum spanning",
        "mst",
    )
    return any(marker in normalized for marker in graph_markers) and any(
        marker in normalized for marker in task_markers
    )


def _parse_weighted_graph_text(text: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]] | None:
    node_ids = _parse_declared_graph_nodes(text)
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for match in re.finditer(r"\(\s*([A-Za-z][\w-]*)\s*,\s*([A-Za-z][\w-]*)\s*,\s*(-?\d+(?:[.,]\d+)?)\s*\)", text):
        source, target, raw_weight = match.groups()
        source = source.strip()
        target = target.strip()
        weight = raw_weight.replace(",", ".")
        node_ids.update([source, target])
        edge_key = (source, target, weight)
        reverse_key = (target, source, weight)
        if edge_key in seen_edges or reverse_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        edges.append(
            {
                "id": f"{_id_part(source)}_{_id_part(target)}_{_id_part(weight)}",
                "source": source,
                "target": target,
                "weight": weight,
            }
        )
    if len(node_ids) < 2 or not edges:
        return None
    nodes = [{"id": node_id, "label": node_id} for node_id in sorted(node_ids, key=_natural_node_sort_key)]
    valid_node_ids = {node["id"] for node in nodes}
    cleaned_edges = [edge for edge in edges if edge["source"] in valid_node_ids and edge["target"] in valid_node_ids]
    if not cleaned_edges:
        return None
    return nodes, cleaned_edges


def _parse_declared_graph_nodes(text: str) -> set[str]:
    match = re.search(r"(?:noder|nodes)\s*[:=]?\s*\{([^}]+)\}", text, flags=re.IGNORECASE)
    if not match:
        return set()
    return {
        node.strip()
        for node in re.split(r"[,;\s]+", match.group(1))
        if re.fullmatch(r"[A-Za-z][\w-]*", node.strip())
    }


def _first_referenced_start_node(text: str, node_ids: set[str]) -> str | None:
    patterns = (
        r"(?:fra|from|start(?:ing)?(?: at| node)?|startnode|start node)\s+(?:node\s+|noden\s+)?([A-Za-z][\w-]*)",
        r"([A-Za-z][\w-]*)\s+til\s+[A-Za-z][\w-]*",
        r"([A-Za-z][\w-]*)\s+to\s+[A-Za-z][\w-]*",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1)
            if candidate in node_ids:
                return candidate
    return None


def _natural_node_sort_key(value: str) -> tuple[str, int | str]:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)?", value)
    if not match:
        return (value.casefold(), value)
    prefix, suffix = match.groups()
    return (prefix.casefold(), int(suffix) if suffix is not None else "")


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
    if diagram.get("type") == "chart":
        return _clean_chart_diagram(diagram, question_index, diagram_index)
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


def _clean_chart_diagram(
    diagram: Any,
    question_index: int,
    diagram_index: int,
) -> dict[str, Any] | None:
    if not isinstance(diagram, dict) or diagram.get("type") != "chart":
        return None
    chart_type = _clean_string(diagram.get("chart_type")).casefold()
    if chart_type not in {"bar", "line"}:
        return None
    data = _clean_chart_points(diagram.get("data"))
    if not data:
        return None
    diagram_id = _clean_string(diagram.get("id")) or f"q{question_index}_chart_{diagram_index}"
    cleaned: dict[str, Any] = {
        "id": diagram_id,
        "type": "chart",
        "chart_type": chart_type,
        "data": data,
    }
    for field in ("title", "x_label", "y_label"):
        value = _clean_string(diagram.get(field))
        if value:
            cleaned[field] = value
    return cleaned


def _clean_chart_points(points: Any) -> list[dict[str, Any]]:
    if not isinstance(points, list):
        return []
    cleaned: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for point in points:
        if not isinstance(point, dict):
            continue
        label = _clean_string(point.get("label"))
        value = point.get("value")
        if not label or label in seen_labels or not isinstance(value, (int, float)):
            continue
        cleaned.append({"label": label, "value": value})
        seen_labels.add(label)
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
