"""Command line interface for building exam_bundle.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from exam_parser.exam_bundle import build_exam_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build exam_bundle.json from questions and solutions.")
    parser.add_argument("questions_json", help="Path to questions.json.")
    parser.add_argument("--solutions", help="Optional path to solutions.json.")
    parser.add_argument("--out", "-o", required=True, help="Path to write exam_bundle.json.")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        questions_result = _load_json(Path(args.questions_json))
        solutions_result = _load_json(Path(args.solutions)) if args.solutions else None
        bundle = build_exam_bundle(questions_result, solutions_result)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=args.indent) + "\n", encoding="utf-8")
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Input JSON must be an object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
