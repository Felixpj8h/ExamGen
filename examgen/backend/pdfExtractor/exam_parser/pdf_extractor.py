"""PDF text extraction logic for text-based exam documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from exam_parser.text_cleaner import clean_pages, normalize_whitespace

MIN_EXTRACTED_IMAGE_WIDTH = 80
MIN_EXTRACTED_IMAGE_HEIGHT = 80


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be validated or extracted."""


def validate_pdf_path(pdf_path: str | Path) -> Path:
    """Validate that the input path exists and points to a PDF file."""
    path = Path(pdf_path).expanduser()
    if not path.exists():
        raise PDFExtractionError(f"File does not exist: {path}")
    if not path.is_file():
        raise PDFExtractionError(f"Path is not a file: {path}")
    if path.suffix.casefold() != ".pdf":
        raise PDFExtractionError(f"File must have a .pdf extension: {path}")
    try:
        with path.open("rb") as file:
            if file.read(5) != b"%PDF-":
                raise PDFExtractionError(f"File does not appear to be a valid PDF: {path}")
    except OSError as exc:
        raise PDFExtractionError(f"Could not read file: {path}") from exc
    return path


def _extract_raw_pages(path: Path) -> list[str]:
    try:
        with fitz.open(path) as document:
            if document.page_count == 0:
                raise PDFExtractionError("PDF contains no pages.")
            return [document.load_page(index).get_text("text") for index in range(document.page_count)]
    except PDFExtractionError:
        raise
    except fitz.FileDataError as exc:
        raise PDFExtractionError(f"Could not read PDF data: {path}") from exc
    except fitz.EmptyFileError as exc:
        raise PDFExtractionError(f"PDF file is empty: {path}") from exc
    except Exception as exc:
        raise PDFExtractionError(f"Failed to extract text from PDF: {path}") from exc


def is_probably_text_based(
    page_texts: list[str],
    *,
    min_chars_per_page: int = 30,
    min_text_page_ratio: float = 0.5,
) -> bool:
    """Heuristically decide whether the PDF is probably text-based."""
    if not page_texts:
        return False

    pages_with_text = sum(
        1 for text in page_texts if len(normalize_whitespace(text)) >= min_chars_per_page
    )
    return pages_with_text / len(page_texts) >= min_text_page_ratio


def _extract_page_image_crops(
    path: Path,
    *,
    image_output_dir: Path,
    image_path_prefix: str | None = None,
    image_url_prefix: str | None = None,
) -> list[list[dict[str, Any]]]:
    """Extract rendered crops for embedded raster images, grouped by page."""
    image_output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with fitz.open(path) as document:
            page_images: list[list[dict[str, Any]]] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                images: list[dict[str, Any]] = []
                seen_rects: set[tuple[int, tuple[float, float, float, float]]] = set()
                image_index = 1
                for image_info in page.get_images(full=True):
                    xref = int(image_info[0])
                    for rect in page.get_image_rects(xref):
                        bbox = _round_bbox(rect)
                        rect_key = (xref, tuple(bbox))
                        if rect_key in seen_rects or rect.is_empty:
                            continue
                        seen_rects.add(rect_key)
                        image_id = f"page_{page_index + 1}_img_{image_index}"
                        file_name = f"{image_id}.png"
                        output_path = image_output_dir / file_name
                        pixmap = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2),
                            clip=rect,
                            alpha=False,
                        )
                        if _is_too_small_image(pixmap):
                            pixmap = None
                            continue
                        pixmap.save(output_path)
                        images.append(
                            {
                                "id": image_id,
                                "file_name": file_name,
                                "path": _join_asset_path(image_path_prefix, file_name),
                                "src": _join_asset_path(image_url_prefix, file_name),
                                "page_number": page_index + 1,
                                "bbox": bbox,
                                "width": pixmap.width,
                                "height": pixmap.height,
                            }
                        )
                        image_index += 1
                page_images.append(images)
            return page_images
    except Exception as exc:
        raise PDFExtractionError(f"Failed to extract images from PDF: {path}") from exc


def _round_bbox(rect: fitz.Rect) -> list[float]:
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def _is_too_small_image(pixmap: fitz.Pixmap) -> bool:
    return pixmap.width < MIN_EXTRACTED_IMAGE_WIDTH or pixmap.height < MIN_EXTRACTED_IMAGE_HEIGHT


def _join_asset_path(prefix: str | None, file_name: str) -> str:
    if not prefix:
        return file_name
    return f"{prefix.rstrip('/')}/{file_name}"


def extract_pdf(
    pdf_path: str | Path,
    *,
    image_output_dir: str | Path | None = None,
    image_path_prefix: str | None = None,
    image_url_prefix: str | None = None,
) -> dict[str, Any]:
    """Extract raw and cleaned page-level text from a text-based PDF."""
    path = validate_pdf_path(pdf_path)
    raw_pages = _extract_raw_pages(path)
    clean_texts = clean_pages(raw_pages)
    page_images = (
        _extract_page_image_crops(
            path,
            image_output_dir=Path(image_output_dir),
            image_path_prefix=image_path_prefix,
            image_url_prefix=image_url_prefix,
        )
        if image_output_dir is not None
        else [[] for _ in raw_pages]
    )

    pages = [
        {
            "page_number": index + 1,
            "raw_text": raw_text,
            "clean_text": clean_text,
            "images": page_images[index],
        }
        for index, (raw_text, clean_text) in enumerate(zip(raw_pages, clean_texts, strict=True))
    ]

    return {
        "file_name": path.name,
        "page_count": len(raw_pages),
        "is_text_based": is_probably_text_based(raw_pages),
        "pages": pages,
        "full_text": "\n\n".join(text for text in clean_texts if text),
        "images": [image for images in page_images for image in images],
    }
