"""Helper CLI for processing one extracted PDF containing questions and solutions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.ai_question_extractor import DEFAULT_MODEL_NAME, extract_questions_with_gemini
from exam_parser.ai_solution_extractor import extract_solutions_with_gemini
from exam_parser.document_classifier import classify_extracted_document
from exam_parser.exam_bundle import build_exam_bundle
from exam_parser.section_splitter import section_to_extraction_result, split_questions_and_solutions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process extracted JSON from a PDF that may contain both questions and solutions."
    )
    parser.add_argument("extracted_json", help="Path to extracted combined PDF JSON.")
    parser.add_argument("--out-dir", required=True, help="Directory for generated JSON files.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Gemini model name.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        extraction_result = _load_json(Path(args.extracted_json))
        classification = classify_extracted_document(extraction_result)
        _write_json(out_dir / "classification.json", classification, args.indent)

        document_type = classification["document_type"]
        if document_type == "questions_and_solutions":
            split = split_questions_and_solutions(extraction_result)
            _write_json(out_dir / "section_split.json", split, args.indent)
            if split["warnings"] or not split["question_section"]["text"] or not split["solution_section"]["text"]:
                print("Could not reliably split combined PDF; review section_split.json.", file=sys.stderr)
                return 2

            question_section = section_to_extraction_result(split, "question_section", file_suffix="questions")
            solution_section = section_to_extraction_result(split, "solution_section", file_suffix="solutions")
            _write_json(out_dir / "question_section.json", question_section, args.indent)
            _write_json(out_dir / "solution_section.json", solution_section, args.indent)

            questions = extract_questions_with_gemini(
                question_section,
                model_name=args.model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
            )
            solutions = extract_solutions_with_gemini(
                solution_section,
                questions_result=questions,
                model_name=args.model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
                source_type="same_pdf",
            )
            bundle = build_exam_bundle(questions, solutions)
            _write_json(out_dir / "questions.json", questions, args.indent)
            _write_json(out_dir / "solutions.json", solutions, args.indent)
            _write_json(out_dir / "exam_bundle.json", bundle, args.indent)
            return 0

        if document_type == "questions_only":
            questions = extract_questions_with_gemini(
                extraction_result,
                model_name=args.model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
            )
            _write_json(out_dir / "questions.json", questions, args.indent)
            return 0

        print(f"Unsupported or unclear document type: {document_type}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Input JSON must be an object.")
    return parsed


def _write_json(path: Path, data: dict[str, Any], indent: int) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
