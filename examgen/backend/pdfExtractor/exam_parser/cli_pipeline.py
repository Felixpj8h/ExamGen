"""One-command CLI for the full exam extraction pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.ai_question_extractor import DEFAULT_MODEL_NAME, extract_questions_with_gemini
from exam_parser.ai_solution_extractor import SolutionExtractionError, extract_solutions_with_gemini
from exam_parser.document_classifier import classify_extracted_document
from exam_parser.exam_bundle import build_exam_bundle
from exam_parser.pdf_extractor import PDFExtractionError, extract_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run PDF extraction, document classification, AI question/solution extraction, and bundle creation."
    )
    parser.add_argument("exam_pdf", help="Path to the exam PDF.")
    parser.add_argument(
        "--solutions",
        help="Optional path to a separate official solution PDF.",
    )
    parser.add_argument(
        "--out-dir",
        default="output",
        help="Directory to write extracted JSON artifacts. Defaults to output/.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Gemini model name.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument(
        "--generate-missing-solutions",
        action="store_true",
        help="Generate AI-marked practice solutions when no official answers/løsningsforslag are found.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        exam_extraction = extract_pdf(args.exam_pdf)
        _write_json(out_dir / "extracted_exam.json", exam_extraction, args.indent)

        if args.solutions:
            return _run_separate_solution_pipeline(args, out_dir, exam_extraction)
        return _run_single_pdf_pipeline(args, out_dir, exam_extraction)
    except (PDFExtractionError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_separate_solution_pipeline(
    args: argparse.Namespace,
    out_dir: Path,
    exam_extraction: dict[str, Any],
) -> int:
    classification = classify_extracted_document(exam_extraction)
    _write_json(out_dir / "classification.json", classification, args.indent)

    if classification["document_type"] not in {"questions_only", "questions_and_solutions", "unknown"}:
        print(
            f"Exam PDF was classified as {classification['document_type']}; expected questions.",
            file=sys.stderr,
        )
        return 2

    questions = extract_questions_with_gemini(
        exam_extraction,
        model_name=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
    )
    _write_json(out_dir / "questions.json", questions, args.indent)

    solution_extraction = extract_pdf(args.solutions)
    _write_json(out_dir / "extracted_solutions.json", solution_extraction, args.indent)
    solution_classification = classify_extracted_document(solution_extraction)
    _write_json(out_dir / "solution_classification.json", solution_classification, args.indent)

    solutions = extract_solutions_with_gemini(
        solution_extraction,
        questions_result=questions,
        model_name=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        source_type="separate_solution_pdf",
    )
    _write_json(out_dir / "solutions.json", solutions, args.indent)

    bundle = build_exam_bundle(questions, solutions)
    _write_json(out_dir / "exam_bundle.json", bundle, args.indent)
    _print_success(out_dir, with_solutions=True)
    return 0


def _run_single_pdf_pipeline(
    args: argparse.Namespace,
    out_dir: Path,
    exam_extraction: dict[str, Any],
) -> int:
    classification = classify_extracted_document(exam_extraction)
    _write_json(out_dir / "classification.json", classification, args.indent)
    document_type = classification["document_type"]

    if document_type == "questions_only":
        questions = extract_questions_with_gemini(
            exam_extraction,
            model_name=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        _write_json(out_dir / "questions.json", questions, args.indent)
        solutions = None
        if args.generate_missing_solutions:
            solutions = _generate_ai_solutions(args, exam_extraction, questions)
            _write_json(out_dir / "solutions.json", solutions, args.indent)
        bundle = build_exam_bundle(questions, solutions)
        _write_json(out_dir / "exam_bundle.json", bundle, args.indent)
        _print_success(out_dir, with_solutions=solutions is not None)
        return 0

    if document_type == "questions_and_solutions":
        questions = extract_questions_with_gemini(
            exam_extraction,
            model_name=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        _write_json(out_dir / "questions.json", questions, args.indent)
        try:
            solutions = extract_solutions_with_gemini(
                exam_extraction,
                questions_result=questions,
                model_name=args.model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
                source_type="same_pdf",
            )
        except SolutionExtractionError:
            if not args.generate_missing_solutions:
                raise
            solutions = _generate_ai_solutions(args, exam_extraction, questions)
        _write_json(out_dir / "solutions.json", solutions, args.indent)
        bundle = build_exam_bundle(questions, solutions)
        _write_json(out_dir / "exam_bundle.json", bundle, args.indent)
        _print_success(out_dir, with_solutions=True)
        return 0

    print(f"Unsupported or unclear document type: {document_type}. See classification.json.", file=sys.stderr)
    return 2


def _generate_ai_solutions(
    args: argparse.Namespace,
    exam_extraction: dict[str, Any],
    questions: dict[str, Any],
) -> dict[str, Any]:
    return extract_solutions_with_gemini(
        exam_extraction,
        questions_result=questions,
        model_name=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        source_type="ai_generated",
    )


def _write_json(path: Path, data: dict[str, Any], indent: int) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def _print_success(out_dir: Path, *, with_solutions: bool) -> None:
    written = ["extracted_exam.json", "classification.json", "questions.json", "exam_bundle.json"]
    if with_solutions:
        written.insert(-1, "solutions.json")
    print(f"Pipeline complete. Wrote {', '.join(written)} to {out_dir}.")


if __name__ == "__main__":
    raise SystemExit(main())
