# Exam PDF Parser

Small backend-ready Python module for extracting clean, page-level text from mostly text-based exam PDFs, then optionally converting that extracted text into structured exam-question JSON with Gemini.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run the CLI

Print JSON to the terminal:

```bash
python -m exam_parser.cli path/to/exam.pdf
```

Write JSON to a file:

```bash
python -m exam_parser.cli path/to/exam.pdf --out extracted.json
```

## Run AI Question Extraction


```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json
```

Optional model settings:

```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json --model gemini-3.1-flash-lite-preview --temperature 0 --max-output-tokens 8192
```

The model can also be configured with `GEMINI_MODEL`; the default is `gemini-3.1-flash-lite-preview`.

## Output Shape

PDF extraction output:

```json
{
  "file_name": "exam.pdf",
  "page_count": 10,
  "is_text_based": true,
  "pages": [
    {
      "page_number": 1,
      "raw_text": "...",
      "clean_text": "..."
    }
  ],
  "full_text": "..."
}
```

AI question extraction output:

```json
{
  "source_file": "exam.pdf",
  "exam_title": "Oppgaver for group sessions uke 6",
  "course_code": "MNF130",
  "language": "mixed",
  "questions": [
    {
      "id": "1",
      "question_number": "1",
      "question_text": "Let P(x) be the statement \"The word x contains the letter a\".",
      "page_start": 1,
      "page_end": 1,
      "points": null,
      "topic": "predicate logic",
      "subquestions": [
        {
          "id": "1a",
          "label": "a",
          "text": "P(orange).",
          "points": null
        }
      ]
    }
  ],
  "warnings": []
}
```

## Example Command Flow

```bash
python -m exam_parser.cli path/to/exam.pdf --out extracted.json
python -m exam_parser.cli_extract_questions extracted.json --out questions.json
```

## What It Does

- Validates that the input exists and has a `.pdf` extension.
- Uses PyMuPDF (`fitz`) to extract text page by page.
- Cleans whitespace while preserving useful line breaks.
- Removes common page number formats such as `Page 1 of 10`, `Side 1 av 10`, and standalone page-number lines.
- Removes repeated headers and footers that appear near the top or bottom of most pages.
- Keeps question numbering such as `1.`, `1a)`, `a)`, `Question 1`, and `Oppgave 1`.
- Uses the official Google GenAI Python SDK for the AI step.
- Requests JSON structured output from Gemini and validates the returned shape.
- Extracts questions only; it does not generate solutions, grade answers, or do OCR.

## Limitations

The PDF extraction step does not use AI or OCR. Scanned image PDFs will usually produce little or no extracted text, and the JSON will mark `is_text_based` as `false` when most pages have very little text. OCR can be added later as a separate pipeline step.

The AI extraction step depends on the quality of the existing extracted text. It preserves extracted math as-is for now, so OCR or notation repair should be separate later pipeline steps.
