"""Command line interface for AI solution extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.ai.solution_extractor import (
    SolutionExtractionError,
    extract_solutions_with_gemini,
)
from exam_parser.ai.question_extractor import DEFAULT_MODEL_NAME


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured official solutions from extracted solution JSON."
    )
    parser.add_argument("extracted_json", help="Path to extracted solution JSON.")
    parser.add_argument("--questions", help="Optional questions.json for solution alignment.")
    parser.add_argument("--out", "-o", required=True, help="Path to write solutions.json.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Gemini model name.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument(
        "--source-type",
        default="separate_solution_pdf",
        choices=["separate_solution_pdf", "same_pdf", "ai_generated", "manual"],
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        extraction_result = _load_json(Path(args.extracted_json))
        questions_result = _load_json(Path(args.questions)) if args.questions else None
        result = extract_solutions_with_gemini(
            extraction_result,
            questions_result=questions_result,
            model_name=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
            source_type=args.source_type,
        )
    except (OSError, json.JSONDecodeError, ValueError, SolutionExtractionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=args.indent) + "\n", encoding="utf-8")
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Input JSON must be an object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
