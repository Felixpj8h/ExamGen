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


def test_extract_pdf_writes_vector_figure_crops(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=420, height=360)
    page.insert_text((36, 36), "Question 1. Treet under representerer et binaert soketre.")
    for center, label in [
        ((210, 95), "40"),
        ((140, 165), "20"),
        ((280, 165), "70"),
        ((100, 240), "10"),
        ((180, 240), "30"),
    ]:
        page.draw_circle(center, 24, color=(0.1, 0.2, 0.35), fill=(0.88, 0.93, 1), width=1.5)
        page.insert_text((center[0] - 9, center[1] + 5), label)
    for start, end in [
        ((190, 110), (160, 145)),
        ((230, 110), (260, 145)),
        ((125, 185), (108, 220)),
        ((155, 185), (172, 220)),
    ]:
        page.draw_line(start, end, color=(0.45, 0.5, 0.58), width=1.5)
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
    assert image["source"] == "vector_drawing"
    assert image["width"] >= 160
    assert image["height"] >= 120
    assert 50 <= image["bbox"][1] <= 65
    assert (tmp_path / image["path"]).exists()


def test_extract_pdf_keeps_flowchart_vector_parts_in_one_crop(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    document = fitz.open()
    page = document.new_page(width=900, height=720)
    page.insert_text((80, 60), "Oppgave 4: Flytskjema til Java-kode")
    page.draw_circle((430, 140), 40, color=(0.1, 0.2, 0.35), fill=(0.88, 0.93, 1), width=1.5)
    page.draw_rect(fitz.Rect(300, 205, 560, 275), color=(0.1, 0.2, 0.35), width=1.5)
    page.draw_polyline(
        [(430, 330), (560, 430), (430, 530), (300, 430), (430, 330)],
        color=(0.1, 0.2, 0.35),
        width=1.5,
    )
    page.draw_rect(fitz.Rect(620, 390, 820, 470), color=(0.1, 0.2, 0.35), width=1.5)
    page.draw_rect(fitz.Rect(620, 520, 820, 600), color=(0.1, 0.2, 0.35), width=1.5)
    page.draw_rect(fitz.Rect(320, 590, 540, 660), color=(0.1, 0.2, 0.35), width=1.5)
    for start, end in [
        ((430, 180), (430, 205)),
        ((430, 275), (430, 330)),
        ((560, 430), (620, 430)),
        ((720, 470), (720, 520)),
        ((620, 560), (540, 625)),
        ((430, 530), (430, 590)),
    ]:
        page.draw_line(start, end, color=(0.1, 0.2, 0.35), width=1.5)
    document.save(pdf_path)
    document.close()

    result = extract_pdf(
        pdf_path,
        image_output_dir=tmp_path / "assets" / "exam",
        image_path_prefix="assets/exam",
        image_url_prefix="/sample-assets/exam",
    )

    images = result["pages"][0]["images"]
    assert len(images) == 1
    image = images[0]
    assert image["source"] == "vector_drawing"
    assert image["bbox"][1] >= 80
    assert image["bbox"][0] <= 290
    assert image["bbox"][2] >= 830
    assert image["bbox"][3] >= 670


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
