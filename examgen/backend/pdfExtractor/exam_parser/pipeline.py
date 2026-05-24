"""Stable backend API for running the full exam processing pipeline."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exam_parser.ai_question_extractor import DEFAULT_MODEL_NAME, extract_questions_with_gemini
from exam_parser.ai_solution_extractor import SolutionExtractionError, extract_solutions_with_gemini
from exam_parser.document_classifier import classify_extracted_document
from exam_parser.exam_bundle import build_exam_bundle
from exam_parser.pdf_extractor import extract_pdf


class PipelineError(Exception):
    """Raised when the pipeline cannot complete."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class PipelineOptions:
    model_name: str = DEFAULT_MODEL_NAME
    temperature: float = 0.0
    max_output_tokens: int = 8192
    generate_missing_solutions: bool = False
    mirror_bundle_to_public: bool = True
    public_bundle_path: str | Path | None = None
    indent: int = 2


def run_exam_pipeline(
    exam_pdf: str | Path,
    *,
    solutions_pdf: str | Path | None = None,
    out_dir: str | Path = "output",
    options: PipelineOptions | None = None,
) -> dict[str, Any]:
    """Run PDF extraction, AI extraction, and bundle creation.

    This is the stable backend entry point intended for future FastAPI routes.
    It writes the same JSON artifacts as the CLI and returns their paths.
    """
    resolved_options = options or PipelineOptions()
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    exam_extraction = extract_pdf(
        exam_pdf,
        image_output_dir=output_dir / "assets" / "exam",
        image_path_prefix="assets/exam",
        image_url_prefix="/sample-assets/exam",
    )
    _write_artifact(output_dir, "extracted_exam.json", exam_extraction, resolved_options, artifacts)

    if solutions_pdf:
        _run_separate_solution_pipeline(
            solutions_pdf=solutions_pdf,
            out_dir=output_dir,
            exam_extraction=exam_extraction,
            options=resolved_options,
            artifacts=artifacts,
        )
    else:
        _run_single_pdf_pipeline(
            out_dir=output_dir,
            exam_extraction=exam_extraction,
            options=resolved_options,
            artifacts=artifacts,
        )

    return {"out_dir": str(output_dir), "artifacts": artifacts}


def _run_separate_solution_pipeline(
    *,
    solutions_pdf: str | Path,
    out_dir: Path,
    exam_extraction: dict[str, Any],
    options: PipelineOptions,
    artifacts: dict[str, str],
) -> None:
    classification = classify_extracted_document(exam_extraction)
    _write_artifact(out_dir, "classification.json", classification, options, artifacts)

    if classification["document_type"] not in {"questions_only", "questions_and_solutions", "unknown"}:
        raise PipelineError(
            f"Exam PDF was classified as {classification['document_type']}; expected questions.",
            exit_code=2,
        )

    questions = extract_questions_with_gemini(
        exam_extraction,
        model_name=options.model_name,
        temperature=options.temperature,
        max_output_tokens=options.max_output_tokens,
    )
    _write_artifact(out_dir, "questions.json", questions, options, artifacts)

    solution_extraction = extract_pdf(
        solutions_pdf,
        image_output_dir=out_dir / "assets" / "solutions",
        image_path_prefix="assets/solutions",
        image_url_prefix="/sample-assets/solutions",
    )
    _write_artifact(out_dir, "extracted_solutions.json", solution_extraction, options, artifacts)
    solution_classification = classify_extracted_document(solution_extraction)
    _write_artifact(out_dir, "solution_classification.json", solution_classification, options, artifacts)

    solutions = extract_solutions_with_gemini(
        solution_extraction,
        questions_result=questions,
        model_name=options.model_name,
        temperature=options.temperature,
        max_output_tokens=options.max_output_tokens,
        source_type="separate_solution_pdf",
    )
    _write_artifact(out_dir, "solutions.json", solutions, options, artifacts)

    bundle = build_exam_bundle(questions, solutions, extraction_result=exam_extraction)
    _write_artifact(out_dir, "exam_bundle.json", bundle, options, artifacts)


def _run_single_pdf_pipeline(
    *,
    out_dir: Path,
    exam_extraction: dict[str, Any],
    options: PipelineOptions,
    artifacts: dict[str, str],
) -> None:
    classification = classify_extracted_document(exam_extraction)
    _write_artifact(out_dir, "classification.json", classification, options, artifacts)
    document_type = classification["document_type"]

    if document_type == "questions_only":
        questions = extract_questions_with_gemini(
            exam_extraction,
            model_name=options.model_name,
            temperature=options.temperature,
            max_output_tokens=options.max_output_tokens,
        )
        _write_artifact(out_dir, "questions.json", questions, options, artifacts)
        solutions = None
        if options.generate_missing_solutions:
            solutions = _generate_ai_solutions(options, exam_extraction, questions)
            _write_artifact(out_dir, "solutions.json", solutions, options, artifacts)
        bundle = build_exam_bundle(questions, solutions, extraction_result=exam_extraction)
        _write_artifact(out_dir, "exam_bundle.json", bundle, options, artifacts)
        return

    if document_type == "questions_and_solutions":
        questions = extract_questions_with_gemini(
            exam_extraction,
            model_name=options.model_name,
            temperature=options.temperature,
            max_output_tokens=options.max_output_tokens,
        )
        _write_artifact(out_dir, "questions.json", questions, options, artifacts)
        try:
            solutions = extract_solutions_with_gemini(
                exam_extraction,
                questions_result=questions,
                model_name=options.model_name,
                temperature=options.temperature,
                max_output_tokens=options.max_output_tokens,
                source_type="same_pdf",
            )
        except SolutionExtractionError:
            if not options.generate_missing_solutions:
                raise
            solutions = _generate_ai_solutions(options, exam_extraction, questions)
        _write_artifact(out_dir, "solutions.json", solutions, options, artifacts)
        bundle = build_exam_bundle(questions, solutions, extraction_result=exam_extraction)
        _write_artifact(out_dir, "exam_bundle.json", bundle, options, artifacts)
        return

    raise PipelineError(
        f"Unsupported or unclear document type: {document_type}. See classification.json.",
        exit_code=2,
    )


def _generate_ai_solutions(
    options: PipelineOptions,
    exam_extraction: dict[str, Any],
    questions: dict[str, Any],
) -> dict[str, Any]:
    return extract_solutions_with_gemini(
        exam_extraction,
        questions_result=questions,
        model_name=options.model_name,
        temperature=options.temperature,
        max_output_tokens=max(options.max_output_tokens, 16384),
        source_type="ai_generated",
    )


def _write_artifact(
    out_dir: Path,
    file_name: str,
    data: dict[str, Any],
    options: PipelineOptions,
    artifacts: dict[str, str],
) -> None:
    path = out_dir / file_name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=options.indent) + "\n", encoding="utf-8")
    artifacts[file_name] = str(path)
    if file_name == "exam_bundle.json" and options.mirror_bundle_to_public:
        _write_public_exam_bundle(out_dir, data, options, artifacts)


def _write_public_exam_bundle(
    out_dir: Path,
    data: dict[str, Any],
    options: PipelineOptions,
    artifacts: dict[str, str],
) -> None:
    public_bundle_path = _resolve_public_bundle_path(out_dir, options.public_bundle_path)
    if public_bundle_path is None:
        return
    public_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    public_bundle_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=options.indent) + "\n",
        encoding="utf-8",
    )
    artifacts["public/sample-exam-bundle.json"] = str(public_bundle_path)
    _mirror_public_assets(out_dir, public_bundle_path.parent, artifacts)


def _resolve_public_bundle_path(out_dir: Path, configured_path: str | Path | None) -> Path | None:
    if configured_path is not None:
        return Path(configured_path)

    for parent in [out_dir.resolve(), *out_dir.resolve().parents]:
        candidate = parent / "public"
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate / "sample-exam-bundle.json"

    return None


def _mirror_public_assets(out_dir: Path, public_dir: Path, artifacts: dict[str, str]) -> None:
    source_assets = out_dir / "assets"
    if not source_assets.is_dir():
        return
    target_assets = public_dir / "sample-assets"
    shutil.copytree(source_assets, target_assets, dirs_exist_ok=True)
    artifacts["public/sample-assets"] = str(target_assets)
