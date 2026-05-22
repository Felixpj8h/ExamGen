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

## Configure Gemini

Question and solution structuring use the official Google GenAI Python SDK.

PowerShell:

```powershell
$env:GEMINI_API_KEY="your-api-key"
```

Bash:

```bash
export GEMINI_API_KEY="your-api-key"
```

The model can also be configured with `GEMINI_MODEL`; the default is `gemini-3.1-flash-lite-preview`.

## Supported Modes

1. Exam only: extract PDF text, then extract questions.
2. Exam PDF + solution PDF: extract both PDFs, extract questions and solutions separately, then build a bundle.
3. Combined PDF with questions and solutions: classify the document, extract questions from the full text, then run a second AI pass over the full text to extract and align solutions.

## Run The Whole Pipeline

Exam-only PDF:

```bash
python -m exam_parser.cli_pipeline path/to/exam.pdf --out-dir output/
```

When the pipeline can find the React `public/` folder above `--out-dir`, it also mirrors the final bundle to `public/sample-exam-bundle.json`. The current frontend loads that file, so you can quickly test a newly generated exam by rerunning the pipeline and refreshing the browser.

Exam PDF with a separate solution PDF:

```bash
python -m exam_parser.cli_pipeline path/to/exam.pdf --solutions path/to/solutions.pdf --out-dir output/
```

Exam PDF without official answers, with AI-generated practice answers:

```bash
python -m exam_parser.cli_pipeline path/to/exam.pdf --out-dir output/ --generate-missing-solutions
```

The pipeline writes intermediate files such as `extracted_exam.json`, `classification.json`, `questions.json`, `solutions.json` when available, and `exam_bundle.json`.
AI-generated answers are marked with `source_type: "ai_generated"`, each subsolution uses `source: "ai_generated"`, and `solutions.json` includes the warning `AI-generated solutions; not official answer key.`

Use `--no-public-bundle` if you want to write only backend artifacts without updating the frontend sample file. Use `--public-bundle-path path/to/sample-exam-bundle.json` to choose a specific frontend copy path.

## Frontend Contract

Use `exam_bundle.json` as the single frontend input. It contains exam metadata, questions, subquestions, attached solutions when available, and warnings. The frontend should treat `solution.source` as the authority for display labels:

- `official_solution_pdf`: official solution from a separate solution PDF
- `same_pdf`: official answer found in the same PDF
- `ai_generated`: AI-generated practice answer, not an official answer key

Questions and subquestions include frontend interaction metadata:

```json
{
  "interaction_type": "true_false",
  "choices": ["True", "False"]
}
```

Allowed `interaction_type` values are `free_text`, `true_false`, `multiple_choice`, `numeric`, `proof`, and `translation`. Use `choices` for `true_false` and `multiple_choice`; other interaction types use an empty list.

Future FastAPI code should call the stable backend wrapper instead of shelling out to the CLI:

```python
from exam_parser.pipeline import PipelineOptions, run_exam_pipeline

result = run_exam_pipeline(
    "path/to/exam.pdf",
    out_dir="output",
    options=PipelineOptions(generate_missing_solutions=True),
)
exam_bundle_path = result["artifacts"]["exam_bundle.json"]
```

## Run AI Question Extraction

```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json
```

Optional model settings:

```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json --model gemini-3.1-flash-lite-preview --temperature 0 --max-output-tokens 8192
```

## Classify A Document

```bash
python -m exam_parser.cli_classify_document extracted.json --out classification.json
```

## Extract Solutions

```bash
python -m exam_parser.cli_extract_solutions extracted_solutions.json --questions questions.json --out solutions.json
```

## Build Exam Bundle

```bash
python -m exam_parser.cli_build_bundle questions.json --solutions solutions.json --out exam_bundle.json
```

## Process Combined Question/Solution PDF

```bash
python -m exam_parser.cli_process_combined_pdf extracted.json --out-dir output/
```

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

Document classification output:

```json
{
  "source_file": "exam.pdf",
  "document_type": "questions_only",
  "confidence": "high",
  "question_pages": [1, 2, 3],
  "solution_pages": [],
  "detected_headings": [],
  "warnings": []
}
```

Solution extraction output:

```json
{
  "source_file": "solutions.pdf",
  "source_type": "separate_solution_pdf",
  "exam_title": null,
  "course_code": null,
  "solutions": [
    {
      "question_id": "q1",
      "question_number": "1",
      "solution_text": null,
      "subsolutions": [
        {
          "question_id": "q1a",
          "label": "a",
          "answer": "True",
          "explanation": "The word orange contains the letter a.",
          "grading_points": ["Correct truth value"],
          "points": null,
          "source": "official_solution_pdf"
        }
      ],
      "warnings": []
    }
  ],
  "warnings": []
}
```

Exam bundle output:

```json
{
  "exam": {
    "title": "Oppgaver for group sessions uke 6",
    "course_code": "MNF130",
    "source_file": "Task1.pdf"
  },
  "questions": [
    {
      "id": "q1",
      "question_number": "1",
      "question_text": "Let P(x) be the statement...",
      "page_start": 1,
      "page_end": 1,
      "points": null,
      "topic": "Predicate Logic",
      "subquestions": [
        {
          "id": "q1a",
          "label": "a",
          "text": "P(orange).",
          "points": null,
          "solution": {
            "answer": "True",
            "explanation": "The word orange contains the letter a.",
            "grading_points": ["Correct truth value"],
            "source": "official_solution_pdf"
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

## Example Command Flow: Exam Only

```bash
python -m exam_parser.cli path/to/exam.pdf --out extracted.json
python -m exam_parser.cli_extract_questions extracted.json --out questions.json
```

## Example Command Flow: Separate Solution PDF

```bash
python -m exam_parser.cli path/to/exam.pdf --out extracted_exam.json
python -m exam_parser.cli_extract_questions extracted_exam.json --out questions.json
python -m exam_parser.cli path/to/solutions.pdf --out extracted_solutions.json
python -m exam_parser.cli_extract_solutions extracted_solutions.json --questions questions.json --out solutions.json
python -m exam_parser.cli_build_bundle questions.json --solutions solutions.json --out exam_bundle.json
```

## Example Command Flow: Same PDF

```bash
python -m exam_parser.cli path/to/exam_with_solutions.pdf --out extracted.json
python -m exam_parser.cli_process_combined_pdf extracted.json --out-dir output/
```

## What It Does

- Validates that the input exists and has a `.pdf` extension.
- Uses PyMuPDF (`fitz`) to extract text page by page.
- Cleans whitespace while preserving useful line breaks.
- Removes common page number formats such as `Page 1 of 10`, `Side 1 av 10`, and standalone page-number lines.
- Removes repeated headers and footers that appear near the top or bottom of most pages.
- Keeps question numbering such as `1.`, `1a)`, `a)`, `Question 1`, and `Oppgave 1`.
- Deterministically classifies extracted documents as questions, solutions, both, or unknown.
- Uses deterministic splitting only as a diagnostic/helper path; the main one-command pipeline uses AI over the full text for combined question/solution PDFs.
- Uses the official Google GenAI Python SDK for the AI step.
- Requests JSON structured output from Gemini and validates the returned shape.
- Extracts questions and official solutions; it does not generate missing solutions, grade answers, or do OCR.

## Limitations

The PDF extraction step does not use AI or OCR. Scanned image PDFs will usually produce little or no extracted text, and the JSON will mark `is_text_based` as `false` when most pages have very little text. OCR can be added later as a separate pipeline step.

The AI extraction step depends on the quality of the existing extracted text. It preserves extracted math as-is for now, so OCR or notation repair should be separate later pipeline steps.

Solution support works best when official answers are clearly present in the extracted text. If the AI pass cannot confidently identify solution content, the pipeline returns an error instead of writing an empty or content-free `solutions.json`, unless `--generate-missing-solutions` is set. Generated solutions are for practice and are explicitly marked as AI-generated, not official answers.
