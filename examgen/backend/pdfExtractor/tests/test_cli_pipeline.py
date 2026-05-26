import json
from pathlib import Path

from exam_parser.ai.solution_extractor import SolutionExtractionError
from exam_parser.cli_pipeline import main as pipeline_main
from exam_parser.pipeline import PipelineOptions, run_exam_pipeline


def sample_extraction(file_name: str = "exam.pdf") -> dict:
    text = "Questions\n1. What is P(orange)?"
    return sample_extraction_with_text(text, file_name=file_name)


def sample_extraction_with_text(text: str, file_name: str = "exam.pdf") -> dict:
    return {
        "file_name": file_name,
        "page_count": 1,
        "is_text_based": True,
        "pages": [
            {
                "page_number": 1,
                "raw_text": text,
                "clean_text": text,
            }
        ],
        "full_text": text,
    }


def sample_questions() -> dict:
    return {
        "source_file": "exam.pdf",
        "exam_title": "Sample",
        "course_code": "MNF130",
        "language": "english",
        "questions": [
            {
                "id": "q1",
                "question_number": "1",
                "question_text": "What is P(orange)?",
                "page_start": 1,
                "page_end": 1,
                "points": None,
                "topic": "predicates",
                "subquestions": [
                    {"id": "q1a", "label": "a", "text": "P(orange).", "points": None}
                ],
            }
        ],
        "warnings": [],
    }


def sample_solutions() -> dict:
    return {
        "source_file": "solutions.pdf",
        "source_type": "separate_solution_pdf",
        "exam_title": "Sample",
        "course_code": "MNF130",
        "solutions": [
            {
                "question_id": "q1",
                "question_number": "1",
                "solution_text": None,
                "subsolutions": [
                    {
                        "question_id": "q1a",
                        "label": "a",
                        "answer": "True",
                        "explanation": "Orange contains a.",
                        "grading_points": [],
                        "points": None,
                        "source": "official_solution_pdf",
                    }
                ],
                "warnings": [],
            }
        ],
        "warnings": [],
    }


def test_pipeline_exam_only_writes_questions_and_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: sample_extraction())
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    exit_code = pipeline_main(["exam.pdf", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "extracted_exam.json").exists()
    assert (out_dir / "classification.json").exists()
    assert (out_dir / "questions.json").exists()
    bundle = json.loads((out_dir / "exam_bundle.json").read_text(encoding="utf-8"))
    assert bundle["exam"]["title"] == "Sample"


def test_pipeline_uses_configured_asset_url_prefix(tmp_path: Path, monkeypatch) -> None:
    out_dir = tmp_path / "out"

    def fake_extract_pdf(path, **kwargs):
        extraction = sample_extraction()
        extraction["pages"][0]["images"] = [
            {
                "id": "page_1_img_1",
                "path": "assets/exam/page_1_img_1.png",
                "src": f"{kwargs['image_url_prefix']}/page_1_img_1.png",
                "page_number": 1,
                "bbox": [0, 0, 100, 100],
                "width": 100,
                "height": 100,
            }
        ]
        extraction["images"] = extraction["pages"][0]["images"]
        return extraction

    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", fake_extract_pdf)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    run_exam_pipeline(
        "exam.pdf",
        out_dir=out_dir,
        options=PipelineOptions(
            asset_url_prefix="/api/exams/exam_123/assets",
            mirror_bundle_to_public=False,
        ),
    )

    bundle = json.loads((out_dir / "exam_bundle.json").read_text(encoding="utf-8"))
    assert bundle["questions"][0]["images"][0]["src"] == (
        "/api/exams/exam_123/assets/exam/page_1_img_1.png"
    )


def test_pipeline_mirrors_exam_bundle_to_frontend_public(
    tmp_path: Path, monkeypatch
) -> None:
    project_dir = tmp_path / "project"
    out_dir = project_dir / "backend" / "pdfExtractor" / "output"
    public_dir = project_dir / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "index.html").write_text("<div id=\"root\"></div>", encoding="utf-8")
    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: sample_extraction())
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    exit_code = pipeline_main(["exam.pdf", "--out-dir", str(out_dir)])

    assert exit_code == 0
    public_bundle = json.loads((public_dir / "sample-exam-bundle.json").read_text(encoding="utf-8"))
    assert public_bundle["exam"]["title"] == "Sample"


def test_pipeline_can_skip_public_bundle_mirror(
    tmp_path: Path, monkeypatch
) -> None:
    project_dir = tmp_path / "project"
    out_dir = project_dir / "backend" / "pdfExtractor" / "output"
    public_dir = project_dir / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "index.html").write_text("<div id=\"root\"></div>", encoding="utf-8")
    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: sample_extraction())
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    exit_code = pipeline_main(["exam.pdf", "--out-dir", str(out_dir), "--no-public-bundle"])

    assert exit_code == 0
    assert not (public_dir / "sample-exam-bundle.json").exists()


def test_pipeline_exam_only_can_generate_ai_marked_solutions(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: sample_extraction())
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    def fake_extract_solutions(extraction_result, **kwargs):
        generated = sample_solutions()
        generated["source_type"] = "ai_generated"
        generated["warnings"] = ["AI-generated solutions; not official answer key."]
        generated["solutions"][0]["subsolutions"][0]["source"] = "ai_generated"
        return generated

    monkeypatch.setattr(
        "exam_parser.pipeline.extract_ai_solutions_per_question_with_gemini",
        fake_extract_solutions,
    )

    exit_code = pipeline_main(
        ["exam.pdf", "--out-dir", str(out_dir), "--generate-missing-solutions"]
    )

    assert exit_code == 0
    solutions = json.loads((out_dir / "solutions.json").read_text(encoding="utf-8"))
    assert solutions["source_type"] == "ai_generated"
    assert solutions["solutions"][0]["subsolutions"][0]["source"] == "ai_generated"
    assert "AI-generated solutions; not official answer key." in solutions["warnings"]


def test_pipeline_uses_separate_question_and_solution_models(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    seen: dict[str, str] = {}
    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: sample_extraction())

    def fake_extract_questions(extraction_result, **kwargs):
        seen["question_model"] = kwargs["model_name"]
        return sample_questions()

    def fake_generate_solutions(extraction_result, **kwargs):
        seen["solution_model"] = kwargs["model_name"]
        generated = sample_solutions()
        generated["source_type"] = "ai_generated"
        generated["warnings"] = ["AI-generated solutions; not official answer key."]
        generated["solutions"][0]["subsolutions"][0]["source"] = "ai_generated"
        return generated

    monkeypatch.setattr("exam_parser.pipeline.extract_questions_with_gemini", fake_extract_questions)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_ai_solutions_per_question_with_gemini",
        fake_generate_solutions,
    )

    run_exam_pipeline(
        "exam.pdf",
        out_dir=out_dir,
        options=PipelineOptions(
            question_model="cheap-question-model",
            solution_model="strong-solution-model",
            generate_missing_solutions=True,
            mirror_bundle_to_public=False,
        ),
    )

    assert seen == {
        "question_model": "cheap-question-model",
        "solution_model": "strong-solution-model",
    }


def test_pipeline_model_options_use_env_specific_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "legacy-model")
    monkeypatch.setenv("GEMINI_QUESTION_MODEL", "question-env-model")
    monkeypatch.setenv("GEMINI_SOLUTION_MODEL", "solution-env-model")

    options = PipelineOptions()

    assert options.resolved_question_model() == "question-env-model"
    assert options.resolved_solution_model() == "solution-env-model"


def test_pipeline_legacy_model_overrides_env_specific_models(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_QUESTION_MODEL", "question-env-model")
    monkeypatch.setenv("GEMINI_SOLUTION_MODEL", "solution-env-model")

    options = PipelineOptions(model_name="cli-legacy-model")

    assert options.resolved_question_model() == "cli-legacy-model"
    assert options.resolved_solution_model() == "cli-legacy-model"


def test_pipeline_with_separate_solution_pdf_writes_solutions_and_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"

    def fake_extract_pdf(path, **kwargs):
        if str(path).endswith("solutions.pdf"):
            return sample_extraction("solutions.pdf")
        return sample_extraction("exam.pdf")

    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", fake_extract_pdf)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_solutions_with_gemini",
        lambda extraction_result, **kwargs: sample_solutions(),
    )

    exit_code = pipeline_main(["exam.pdf", "--solutions", "solutions.pdf", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "extracted_solutions.json").exists()
    assert (out_dir / "solutions.json").exists()
    bundle = json.loads((out_dir / "exam_bundle.json").read_text(encoding="utf-8"))
    assert bundle["questions"][0]["subquestions"][0]["solution"]["answer"] == "True"


def test_pipeline_combined_heading_with_correct_answers_uses_full_text_ai_path(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    combined_text = "Questions with correct answers\n1. P(orange).\nCorrect answer: True."
    extraction = sample_extraction_with_text(combined_text)
    questions = sample_questions()

    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: extraction)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: questions,
    )

    def fake_extract_solutions(extraction_result, **kwargs):
        assert extraction_result is extraction
        assert "Questions with correct answers" in extraction_result["full_text"]
        assert kwargs["questions_result"] is questions
        assert kwargs["source_type"] == "same_pdf"
        return sample_solutions()

    monkeypatch.setattr(
        "exam_parser.pipeline.extract_solutions_with_gemini",
        fake_extract_solutions,
    )

    exit_code = pipeline_main(["exam.pdf", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "solutions.json").exists()
    assert not (out_dir / "section_split.json").exists()


def test_pipeline_combined_interleaved_answers_uses_full_text_ai_path(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    combined_text = "Questions\n1. P(orange).\nAnswers\n1. True.\n2. False."
    extraction = sample_extraction_with_text(combined_text)

    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: extraction)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_solutions_with_gemini",
        lambda extraction_result, **kwargs: sample_solutions(),
    )

    exit_code = pipeline_main(["exam.pdf", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "questions.json").exists()
    assert (out_dir / "solutions.json").exists()


def test_pipeline_combined_falls_back_to_ai_generated_when_requested(
    tmp_path: Path, monkeypatch
) -> None:
    out_dir = tmp_path / "out"
    combined_text = "Questions\n1. P(orange).\nAnswers\nNo reliable answer key found."
    extraction = sample_extraction_with_text(combined_text)
    calls: list[str] = []

    monkeypatch.setattr("exam_parser.pipeline.extract_pdf", lambda path, **kwargs: extraction)
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_questions_with_gemini",
        lambda extraction_result, **kwargs: sample_questions(),
    )

    def fake_extract_solutions(extraction_result, **kwargs):
        calls.append(kwargs["source_type"])
        raise SolutionExtractionError("No solutions were extracted.")

    def fake_generate_solutions(extraction_result, **kwargs):
        calls.append("ai_generated")
        generated = sample_solutions()
        generated["source_type"] = "ai_generated"
        generated["warnings"] = ["AI-generated solutions; not official answer key."]
        generated["solutions"][0]["subsolutions"][0]["source"] = "ai_generated"
        return generated

    monkeypatch.setattr(
        "exam_parser.pipeline.extract_solutions_with_gemini",
        fake_extract_solutions,
    )
    monkeypatch.setattr(
        "exam_parser.pipeline.extract_ai_solutions_per_question_with_gemini",
        fake_generate_solutions,
    )

    exit_code = pipeline_main(
        ["exam.pdf", "--out-dir", str(out_dir), "--generate-missing-solutions"]
    )

    assert exit_code == 0
    assert calls == ["same_pdf", "ai_generated"]
    solutions = json.loads((out_dir / "solutions.json").read_text(encoding="utf-8"))
    assert solutions["source_type"] == "ai_generated"
