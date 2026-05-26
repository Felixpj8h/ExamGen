"""Default CLI entry point for ``python -m exam_parser.cli``."""

from exam_parser.cli.extract_pdf import main


if __name__ == "__main__":
    raise SystemExit(main())

