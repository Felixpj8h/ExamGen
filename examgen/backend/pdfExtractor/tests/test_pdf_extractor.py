import base64
from pathlib import Path

import fitz

from exam_parser.pdf_extractor import extract_pdf


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
