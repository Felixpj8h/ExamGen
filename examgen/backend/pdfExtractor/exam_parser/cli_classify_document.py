"""Command line interface for extracted-document classification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.document_classifier import classify_extracted_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify extracted PDF JSON.")
    parser.add_argument("extracted_json", help="Path to JSON produced by exam_parser.cli.")
    parser.add_argument("--out", "-o", help="Optional path to write classification JSON.")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        extraction_result = _load_json(Path(args.extracted_json))
        classification = classify_extracted_document(extraction_result)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(classification, ensure_ascii=False, indent=args.indent)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Input JSON must be an object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
