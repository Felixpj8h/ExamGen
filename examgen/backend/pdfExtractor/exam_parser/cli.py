"""Command line interface for exam PDF extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from exam_parser.pdf_extractor import PDFExtractionError, extract_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract clean page-level text from a text-based exam PDF."
    )
    parser.add_argument("pdf_path", help="Path to the exam PDF file.")
    parser.add_argument(
        "--out",
        "-o",
        help="Optional path to write JSON output. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Defaults to 2.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = extract_pdf(args.pdf_path)
    except PDFExtractionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    json_output = json.dumps(result, ensure_ascii=False, indent=args.indent)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output + "\n", encoding="utf-8")
    else:
        print(json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
