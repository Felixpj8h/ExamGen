# ExamGen

AI-assisted exam practice app. The React frontend remains a Create React App project, and the current backend work lives in `backend/pdfExtractor`.

## Backend PDF, Question, And Solution Extraction

Install backend dependencies:

```bash
cd backend/pdfExtractor
python -m pip install -r requirements.txt
```

Extract text from a text-based PDF:

```bash
python -m exam_parser.cli path/to/exam.pdf --out extracted.json
```

Run the whole backend pipeline with one command:

```bash
python -m exam_parser.cli_pipeline path/to/exam.pdf --out-dir output/
```

With a separate solution PDF:

```bash
python -m exam_parser.cli_pipeline path/to/exam.pdf --solutions path/to/solutions.pdf --out-dir output/
```

Convert extracted PDF JSON into structured question JSON:

```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json
```

Classify whether an extracted document contains questions, solutions, or both:

```bash
python -m exam_parser.cli_classify_document extracted.json --out classification.json
```

Extract official solutions from a separate solution PDF extraction:

```bash
python -m exam_parser.cli path/to/solutions.pdf --out extracted_solutions.json
python -m exam_parser.cli_extract_solutions extracted_solutions.json --questions questions.json --out solutions.json
```

Build an exam bundle with solutions merged into subquestions:

```bash
python -m exam_parser.cli_build_bundle questions.json --solutions solutions.json --out exam_bundle.json
```

Process a combined PDF in one command:

```bash
python -m exam_parser.cli_pipeline path/to/exam_with_solutions.pdf --out-dir output/
```

Optional model settings:

```bash
python -m exam_parser.cli_extract_questions extracted.json --out questions.json --model gemini-3.1-flash-lite-preview --temperature 0 --max-output-tokens 8192
```

Expected AI extraction output:

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

Supported backend modes are exam only, exam PDF plus separate solution PDF, and combined PDFs where official answers are present in the extracted text. This backend step does not grade answers, generate missing solutions, or perform OCR.

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
