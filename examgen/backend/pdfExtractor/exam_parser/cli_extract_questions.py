"""Command line interface for AI exam question extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.ai_question_extractor import (
    DEFAULT_MODEL_NAME,
    QuestionExtractionError,
    extract_questions_with_gemini,
    post_process_questions,
    validate_question_extraction_result,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured exam questions from PDF extraction JSON with Gemini."
    )
    parser.add_argument("extracted_json", help="Path to JSON produced by exam_parser.cli.")
    parser.add_argument(
        "--out",
        "-o",
        required=True,
        help="Path to write structured question JSON.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"Gemini model name. Defaults to {DEFAULT_MODEL_NAME}.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Gemini generation temperature. Defaults to 0.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8192,
        help="Maximum Gemini output tokens. Defaults to 8192.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Defaults to 2.",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise QuestionExtractionError(f"Could not read input JSON: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QuestionExtractionError(f"Invalid input JSON: {path}") from exc
    if not isinstance(parsed, dict):
        raise QuestionExtractionError("Input JSON must be an object.")
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        extraction_result = _load_json(Path(args.extracted_json))
        result = extract_questions_with_gemini(
            extraction_result,
            model_name=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        result = post_process_questions(result)
        validate_question_extraction_result(result)
    except QuestionExtractionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    json_output = json.dumps(result, ensure_ascii=False, indent=args.indent)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
