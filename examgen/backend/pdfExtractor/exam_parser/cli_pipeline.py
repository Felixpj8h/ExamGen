"""One-command CLI for the full exam extraction pipeline."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from exam_parser.pdf.extractor import PDFExtractionError
from exam_parser.pipeline import PipelineError, PipelineOptions, run_exam_pipeline


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
    parser.add_argument(
        "--model",
        default=None,
        help="Backward-compatible Gemini model name for all AI steps.",
    )
    parser.add_argument(
        "--question-model",
        default=None,
        help="Gemini model for question extraction. Defaults to GEMINI_QUESTION_MODEL, GEMINI_MODEL, then the app default.",
    )
    parser.add_argument(
        "--solution-model",
        default=None,
        help="Gemini model for solution extraction/generation. Defaults to GEMINI_SOLUTION_MODEL, GEMINI_MODEL, then the app default.",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument(
        "--generate-missing-solutions",
        action="store_true",
        help="Generate AI-marked practice solutions when no official answers/løsningsforslag are found.",
    )
    parser.add_argument(
        "--public-bundle-path",
        help=(
            "Optional path for a frontend-readable copy of exam_bundle.json. "
            "Defaults to public/sample-exam-bundle.json when a public/ folder is found above --out-dir."
        ),
    )
    parser.add_argument(
        "--no-public-bundle",
        action="store_true",
        help="Do not mirror exam_bundle.json into the frontend public/ folder.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_exam_pipeline(
            args.exam_pdf,
            solutions_pdf=args.solutions,
            out_dir=args.out_dir,
            options=PipelineOptions(
                model_name=args.model,
                question_model=args.question_model,
                solution_model=args.solution_model,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
                generate_missing_solutions=args.generate_missing_solutions,
                mirror_bundle_to_public=not args.no_public_bundle,
                public_bundle_path=args.public_bundle_path,
                indent=args.indent,
            ),
        )
        _print_success(result["out_dir"], result["artifacts"])
        return 0
    except PipelineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    except (PDFExtractionError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _print_success(out_dir: str, artifacts: dict[str, str]) -> None:
    print(f"Pipeline complete. Wrote {', '.join(artifacts)} to {out_dir}.")


if __name__ == "__main__":
    raise SystemExit(main())
