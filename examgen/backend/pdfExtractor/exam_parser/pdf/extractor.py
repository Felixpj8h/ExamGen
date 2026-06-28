"""PDF text extraction logic with optional OCR fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from exam_parser.pdf.text_cleaner import clean_pages, normalize_whitespace
from exam_parser.pdf.ocr import OCRError, ocr_pdf_pages_with_gemini

MIN_EXTRACTED_IMAGE_WIDTH = 80
MIN_EXTRACTED_IMAGE_HEIGHT = 80
MIN_VECTOR_DRAWING_WIDTH = 80
MIN_VECTOR_DRAWING_HEIGHT = 80
MIN_VECTOR_DRAWING_ITEMS = 3
VECTOR_DRAWING_CLUSTER_GAP = 45
VECTOR_DRAWING_CROP_PADDING = 12
OCR_MODES = {"auto", "off", "always"}
TEXT_SOURCE_PDF = "pdf_text"
TEXT_SOURCE_OCR = "gemini_ocr"
TEXT_SOURCE_EMPTY = "empty"


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


def _has_enough_text(text: str, min_chars: int) -> bool:
    return len(normalize_whitespace(text)) >= min_chars


def _pages_needing_ocr(
    page_texts: list[str],
    *,
    ocr_mode: str,
    min_chars_per_page: int,
) -> list[int]:
    if ocr_mode == "off":
        return []
    if ocr_mode == "always":
        return list(range(1, len(page_texts) + 1))
    if all(_has_enough_text(text, min_chars_per_page) for text in page_texts):
        return []
    return [
        index + 1
        for index, text in enumerate(page_texts)
        if not _has_enough_text(text, min_chars_per_page)
    ]


def _extract_page_image_crops(
    path: Path,
    *,
    image_output_dir: Path,
    image_path_prefix: str | None = None,
    image_url_prefix: str | None = None,
) -> list[list[dict[str, Any]]]:
    """Extract rendered crops for embedded raster images and vector figures, grouped by page."""
    image_output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with fitz.open(path) as document:
            page_images: list[list[dict[str, Any]]] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                images: list[dict[str, Any]] = []
                seen_rects: set[tuple[int, tuple[float, float, float, float]]] = set()
                embedded_image_rects: list[fitz.Rect] = []
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
                        embedded_image_rects.append(fitz.Rect(rect))
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
                for rect in _vector_figure_rects(page, embedded_image_rects):
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
                            "bbox": _round_bbox(rect),
                            "width": pixmap.width,
                            "height": pixmap.height,
                            "source": "vector_drawing",
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


def _vector_figure_rects(page: fitz.Page, embedded_image_rects: list[fitz.Rect]) -> list[fitz.Rect]:
    drawing_rects = _candidate_vector_drawing_rects(page, embedded_image_rects)
    clusters = _cluster_rects(drawing_rects)
    return [
        _padded_page_rect(rect, page.rect)
        for rect in clusters
        if rect.width >= MIN_VECTOR_DRAWING_WIDTH and rect.height >= MIN_VECTOR_DRAWING_HEIGHT
    ]


def _candidate_vector_drawing_rects(page: fitz.Page, embedded_image_rects: list[fitz.Rect]) -> list[fitz.Rect]:
    page_area = max(1.0, page.rect.width * page.rect.height)
    candidates: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect_value = drawing.get("rect")
        if rect_value is None:
            continue
        rect = fitz.Rect(rect_value)
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            continue
        if rect.width * rect.height > page_area * 0.55:
            continue
        if any(_rect_overlap_ratio(rect, image_rect) > 0.8 for image_rect in embedded_image_rects):
            continue
        candidates.append(rect)
    return candidates


def _cluster_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
    clusters: list[dict[str, Any]] = []
    for rect in rects:
        search_rect = _pad_rect(rect, VECTOR_DRAWING_CLUSTER_GAP)
        matching_indexes = [
            index
            for index, cluster in enumerate(clusters)
            if cluster["search_rect"].intersects(search_rect)
        ]
        if not matching_indexes:
            clusters.append({"rect": fitz.Rect(rect), "search_rect": search_rect, "count": 1})
            continue
        first = matching_indexes[0]
        clusters[first]["rect"].include_rect(rect)
        clusters[first]["search_rect"].include_rect(search_rect)
        clusters[first]["count"] += 1
        for index in reversed(matching_indexes[1:]):
            clusters[first]["rect"].include_rect(clusters[index]["rect"])
            clusters[first]["search_rect"].include_rect(clusters[index]["search_rect"])
            clusters[first]["count"] += clusters[index]["count"]
            clusters.pop(index)
    return [
        cluster["rect"]
        for cluster in clusters
        if cluster["count"] >= MIN_VECTOR_DRAWING_ITEMS
    ]


def _rect_overlap_ratio(rect: fitz.Rect, other: fitz.Rect) -> float:
    intersection = rect & other
    if intersection.is_empty:
        return 0.0
    area = max(1.0, rect.width * rect.height)
    return (intersection.width * intersection.height) / area


def _padded_page_rect(rect: fitz.Rect, page_rect: fitz.Rect) -> fitz.Rect:
    padded = _pad_rect(rect, VECTOR_DRAWING_CROP_PADDING)
    return padded & page_rect


def _pad_rect(rect: fitz.Rect, padding: float) -> fitz.Rect:
    return fitz.Rect(
        rect.x0 - padding,
        rect.y0 - padding,
        rect.x1 + padding,
        rect.y1 + padding,
    )


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
    ocr_mode: str = "auto",
    ocr_model_name: str | None = None,
    ocr_min_chars_per_page: int = 30,
    ocr_min_text_page_ratio: float = 0.5,
    ocr_render_scale: float = 2.0,
) -> dict[str, Any]:
    """Extract raw and cleaned page-level text from a PDF.

    In auto OCR mode, low-text pages are transcribed with Gemini vision only
    when normal PDF text extraction leaves them too sparse.
    """
    if ocr_mode not in OCR_MODES:
        raise PDFExtractionError(f"Invalid OCR mode: {ocr_mode}")

    path = validate_pdf_path(pdf_path)
    raw_pages = _extract_raw_pages(path)
    warnings: list[str] = []
    ocr_page_numbers = _pages_needing_ocr(
        raw_pages,
        ocr_mode=ocr_mode,
        min_chars_per_page=ocr_min_chars_per_page,
    )
    ocr_text_by_page: dict[int, str] = {}
    if ocr_page_numbers:
        try:
            ocr_text_by_page = ocr_pdf_pages_with_gemini(
                path,
                ocr_page_numbers,
                model_name=ocr_model_name,
                render_scale=ocr_render_scale,
            )
        except OCRError as exc:
            raise PDFExtractionError(str(exc)) from exc
        warnings.append(
            "Gemini OCR was used for low-text PDF pages: "
            + ", ".join(str(page_number) for page_number in ocr_page_numbers)
            + "."
        )

    merged_pages: list[str] = []
    text_sources: list[str] = []
    for index, raw_text in enumerate(raw_pages, start=1):
        ocr_text = ocr_text_by_page.get(index, "")
        if ocr_text:
            merged_pages.append(ocr_text)
            text_sources.append(TEXT_SOURCE_OCR)
        elif _has_enough_text(raw_text, ocr_min_chars_per_page):
            merged_pages.append(raw_text)
            text_sources.append(TEXT_SOURCE_PDF)
        else:
            merged_pages.append(raw_text)
            text_sources.append(TEXT_SOURCE_EMPTY)

    clean_texts = clean_pages(merged_pages)
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
            "text_source": text_sources[index],
            "images": page_images[index],
        }
        for index, (raw_text, clean_text) in enumerate(zip(raw_pages, clean_texts, strict=True))
    ]

    is_text_based = is_probably_text_based(
        merged_pages,
        min_chars_per_page=ocr_min_chars_per_page,
        min_text_page_ratio=ocr_min_text_page_ratio,
    )
    return {
        "file_name": path.name,
        "page_count": len(raw_pages),
        "is_text_based": is_text_based,
        "pages": pages,
        "full_text": "\n\n".join(text for text in clean_texts if text),
        "images": [image for images in page_images for image in images],
        "ocr_used": bool(ocr_text_by_page),
        "ocr_pages": sorted(ocr_text_by_page),
        "warnings": warnings,
    }
