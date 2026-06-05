import base64
from pathlib import Path

import fitz

from exam_parser.pdf.extractor import extract_pdf


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def test_extract_pdf_writes_embedded_image_crops(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((36, 36), "Question 1. Use the figure below.")
    page.insert_image(fitz.Rect(50, 70, 150, 170), stream=ONE_PIXEL_PNG)
    document.save(pdf_path)
    document.close()

    result = extract_pdf(
        pdf_path,
        image_output_dir=tmp_path / "assets" / "exam",
        image_path_prefix="assets/exam",
        image_url_prefix="/sample-assets/exam",
    )

    assert result["images"]
    image = result["pages"][0]["images"][0]
    assert image["id"] == "page_1_img_1"
    assert image["path"] == "assets/exam/page_1_img_1.png"
    assert image["src"] == "/sample-assets/exam/page_1_img_1.png"
    assert image["page_number"] == 1
    assert image["bbox"] == [50.0, 70.0, 150.0, 170.0]
    assert (tmp_path / image["path"]).exists()


def test_extract_pdf_omits_image_files_without_output_dir(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((36, 36), "Question 1. Use the figure below.")
    page.insert_image(fitz.Rect(50, 70, 150, 170), stream=ONE_PIXEL_PNG)
    document.save(pdf_path)
    document.close()

    result = extract_pdf(pdf_path)

    assert result["images"] == []
    assert result["pages"][0]["images"] == []


def test_extract_pdf_filters_tiny_embedded_image_crops(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((36, 36), "Question 1. Ignore the tiny icon.")
    page.insert_image(fitz.Rect(50, 70, 55, 75), stream=ONE_PIXEL_PNG)
    document.save(pdf_path)
    document.close()

    result = extract_pdf(
        pdf_path,
        image_output_dir=tmp_path / "assets" / "exam",
        image_path_prefix="assets/exam",
        image_url_prefix="/sample-assets/exam",
    )

    assert result["images"] == []
    assert result["pages"][0]["images"] == []


def test_extract_pdf_auto_ocr_skips_text_based_pdf(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((36, 36), "Question 1. This page has enough selectable PDF text.")
    document.save(pdf_path)
    document.close()

    calls: list[list[int]] = []

    def fake_ocr(path, page_numbers, **kwargs):
        calls.append(page_numbers)
        return {}

    monkeypatch.setattr("exam_parser.pdf.extractor.ocr_pdf_pages_with_gemini", fake_ocr)

    result = extract_pdf(pdf_path)

    assert calls == []
    assert result["ocr_used"] is False
    assert result["ocr_pages"] == []
    assert result["pages"][0]["text_source"] == "pdf_text"


def test_extract_pdf_auto_ocr_uses_gemini_for_low_text_pages(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    document.new_page(width=300, height=300)
    document.save(pdf_path)
    document.close()

    calls: list[list[int]] = []

    def fake_ocr(path, page_numbers, **kwargs):
        calls.append(page_numbers)
        return {1: "Question 1. OCR recovered this scanned page."}

    monkeypatch.setattr("exam_parser.pdf.extractor.ocr_pdf_pages_with_gemini", fake_ocr)

    result = extract_pdf(pdf_path)

    assert calls == [[1]]
    assert result["is_text_based"] is True
    assert result["ocr_used"] is True
    assert result["ocr_pages"] == [1]
    assert result["pages"][0]["clean_text"] == "Question 1. OCR recovered this scanned page."
    assert result["pages"][0]["text_source"] == "gemini_ocr"


def test_extract_pdf_auto_ocr_only_low_text_pages_in_mixed_pdf(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((36, 36), "Question 1. This page already has enough selectable text.")
    document.new_page(width=300, height=300)
    document.save(pdf_path)
    document.close()

    def fake_ocr(path, page_numbers, **kwargs):
        assert page_numbers == [2]
        return {2: "Question 2. OCR recovered this scanned page."}

    monkeypatch.setattr("exam_parser.pdf.extractor.ocr_pdf_pages_with_gemini", fake_ocr)

    result = extract_pdf(pdf_path)

    assert result["ocr_pages"] == [2]
    assert result["pages"][0]["text_source"] == "pdf_text"
    assert result["pages"][1]["text_source"] == "gemini_ocr"


def test_extract_pdf_ocr_off_preserves_low_text_result(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    document.new_page(width=300, height=300)
    document.save(pdf_path)
    document.close()

    def fake_ocr(path, page_numbers, **kwargs):
        raise AssertionError("OCR should not be called")

    monkeypatch.setattr("exam_parser.pdf.extractor.ocr_pdf_pages_with_gemini", fake_ocr)

    result = extract_pdf(pdf_path, ocr_mode="off")

    assert result["is_text_based"] is False
    assert result["ocr_used"] is False
    assert result["ocr_pages"] == []
    assert result["pages"][0]["text_source"] == "empty"
