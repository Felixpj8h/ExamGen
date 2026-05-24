"""FastAPI app for processing uploaded exam PDFs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from exam_parser.pipeline import PipelineError, PipelineOptions, run_exam_pipeline


app = FastAPI(title="Exam Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/exams/process")
async def process_exam_upload(
    exam_pdf: Annotated[UploadFile, File()],
    auto_generate_solutions: Annotated[str, Form()] = "false",
    solutions_pdf: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """Process uploaded PDFs and return an exam bundle for the frontend."""
    _validate_pdf_upload(exam_pdf, field_name="exam_pdf")
    if solutions_pdf is not None:
        _validate_pdf_upload(solutions_pdf, field_name="solutions_pdf")

    exam_id = f"exam_{uuid4().hex[:12]}"
    auto_generate = auto_generate_solutions.lower() == "true"

    try:
        with tempfile.TemporaryDirectory(prefix=f"{exam_id}_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            exam_path = tmp_path / _safe_upload_name(exam_pdf.filename or "exam.pdf")
            await _save_upload(exam_pdf, exam_path)

            solutions_path: Path | None = None
            if solutions_pdf is not None:
                solutions_path = tmp_path / _safe_upload_name(solutions_pdf.filename or "solutions.pdf")
                await _save_upload(solutions_pdf, solutions_path)

            out_dir = _project_output_dir() / exam_id
            result = run_exam_pipeline(
                exam_path,
                solutions_pdf=solutions_path,
                out_dir=out_dir,
                options=PipelineOptions(
                    generate_missing_solutions=auto_generate,
                    asset_url_prefix=f"/api/exams/{exam_id}/assets",
                    # The frontend receives the bundle directly in this response.
                    # Mirroring into public/ during dev makes CRA reload and drops the UI flow.
                    mirror_bundle_to_public=False,
                ),
            )
            bundle_path = Path(result["artifacts"]["exam_bundle.json"])
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except PipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process exam: {exc}") from exc

    return {
        "exam_id": exam_id,
        "status": "ready",
        "bundle": bundle,
    }


@app.get("/api/exams/{exam_id}/assets/{asset_path:path}")
def get_exam_asset(exam_id: str, asset_path: str) -> FileResponse:
    """Serve generated assets that belong to a processed exam."""
    if not _is_safe_exam_id(exam_id):
        raise HTTPException(status_code=404, detail="Asset not found.")

    assets_root = (_project_output_dir() / exam_id / "assets").resolve()
    asset_file = (assets_root / asset_path).resolve()
    if not _is_relative_to(asset_file, assets_root) or not asset_file.is_file():
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(asset_file)


def _validate_pdf_upload(upload: UploadFile, *, field_name: str) -> None:
    filename = upload.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a PDF file.")


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            output.write(chunk)


def _safe_upload_name(filename: str) -> str:
    safe_name = Path(filename).name.replace(" ", "_")
    return safe_name if safe_name.lower().endswith(".pdf") else f"{safe_name}.pdf"


def _is_safe_exam_id(exam_id: str) -> bool:
    return exam_id.startswith("exam_") and all(
        character.isalnum() or character == "_" for character in exam_id
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _project_output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "output" / "api"
