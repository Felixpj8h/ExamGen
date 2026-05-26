import { useEffect, useMemo, useState } from 'react';
import './App.css';
import FileDropzone from './components/FileDropzone';
import LoadingOverlay from './components/LoadingOverlay';
import { getApiUrl, processExamUpload } from './lib/api';

const fallbackExamBundle = {
  exam: {
    title: 'Oppgaver for group sessions uke 6',
    course_code: 'MNF130',
    source_file: 'Task2.pdf',
  },
  questions: [
    {
      id: 'q1',
      question_number: '1',
      question_text:
        'Let P(x) be the statement "The word x contains the letter a". What are these truth values?',
      page_start: 1,
      page_end: 1,
      points: null,
      topic: 'predicates / truth values',
      interaction_type: 'free_text',
      choices: [],
      subquestions: [
        {
          id: 'q1a',
          label: 'a',
          text: 'P(orange).',
          points: null,
          interaction_type: 'true_false',
          choices: ['True', 'False'],
          solution: {
            answer: 'True',
            explanation: 'The word orange contains the letter a.',
            grading_points: ['Correct truth value'],
            source: 'same_pdf',
          },
        },
        {
          id: 'q1b',
          label: 'b',
          text: 'P(lemon).',
          points: null,
          interaction_type: 'true_false',
          choices: ['True', 'False'],
          solution: {
            answer: 'False',
            explanation: 'The word lemon does not contain the letter a.',
            grading_points: ['Correct truth value'],
            source: 'same_pdf',
          },
        },
      ],
    },
    {
      id: 'q4',
      question_number: '4',
      question_text:
        'Translate the statement into predicate logic using quantifiers and logical connectives.',
      page_start: 2,
      page_end: 2,
      points: null,
      topic: 'translating English to logic',
      interaction_type: 'translation',
      choices: [],
      subquestions: [
        {
          id: 'q4a',
          label: 'a',
          text: 'Every student has read some book.',
          points: null,
          interaction_type: 'translation',
          choices: [],
          solution: {
            answer: '∀x(Student(x) → ∃y(Book(y) ∧ Read(x,y)))',
            explanation:
              'The universal quantifier ranges over students, and the existential quantifier introduces at least one book read by that student.',
            grading_points: ['Universal quantifier over students', 'Existential quantifier over books'],
            source: 'official_solution_pdf',
          },
        },
      ],
    },
    {
      id: 'q8',
      question_number: '8',
      question_text:
        'Consider the statements below and determine whether the conclusion follows.',
      page_start: 3,
      page_end: 3,
      points: null,
      topic: 'logical implication / quantifiers',
      interaction_type: 'proof',
      choices: [],
      subquestions: [
        {
          id: 'q8c',
          label: 'c',
          text: 'No professors are vain.',
          points: null,
          interaction_type: 'free_text',
          choices: [],
          solution: null,
        },
        {
          id: 'q8_followup',
          label: 'followup',
          text: 'Does (c) follow from (a) and (b)?',
          points: null,
          interaction_type: 'true_false',
          choices: ['True', 'False'],
          solution: {
            answer: 'False',
            explanation:
              'From no professors are ignorant and all ignorant people are vain, it does not follow that no professors are vain.',
            grading_points: ['Identifies invalid inference', 'Explains why the conclusion is not forced'],
            source: 'ai_generated',
          },
        },
      ],
    },
  ],
  warnings: ['AI-generated solutions; not official answer key.'],
};

const sourceLabels = {
  official_solution_pdf: 'Official solution',
  same_pdf: 'Official answer from PDF',
  ai_generated: 'AI-generated practice answer',
  manual: 'Manual solution',
};

function App() {
  const [activeExamBundle, setActiveExamBundle] = useState(() => loadStoredExamBundle());
  const [activeExamId, setActiveExamId] = useState(() => loadStoredExamId());
  const [view, setView] = useState(() =>
    getInitialView(activeExamBundle),
  );

  useEffect(() => {
    function handleLocationChange() {
      setView(getInitialView(loadStoredExamBundle()));
    }

    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  if (view === 'mock-exam') {
    return (
      <MockExamWorkspace
        initialBundle={activeExamBundle || loadStoredExamBundle()}
        examId={activeExamId}
        loadLabel={activeExamId ? `Generated exam ${activeExamId}` : 'Generated exam'}
      />
    );
  }

  return (
    <HomePage
      onExamReady={(response) => {
        const examId = response.exam_id || response.examId || null;
        const bundle = withExamAssetUrls(getBundleFromProcessResponse(response), examId);
        setActiveExamId(examId);
        setActiveExamBundle(bundle);
        storeExamBundle(bundle, examId);
        setMockExamLocation();
        setView('mock-exam');
      }}
    />
  );
}

function getInitialView(storedBundle) {
  return window.location.hash === '#mock-exam' && isValidExamBundle(storedBundle)
    ? 'mock-exam'
    : 'landing';
}

function HomePage({ onExamReady }) {
  const [examFile, setExamFile] = useState(null);
  const [solutionsFile, setSolutionsFile] = useState(null);
  const [autoGenerateSolutions, setAutoGenerateSolutions] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  function validate() {
    const nextErrors = {};
    if (!examFile) {
      nextErrors.examFile = 'Upload an exam PDF to continue.';
    }
    if (!autoGenerateSolutions && !solutionsFile) {
      nextErrors.solutionsFile = 'Upload a solutions PDF or enable auto-generated solutions.';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleStart() {
    setSubmitError('');
    if (!validate()) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await processExamUpload({
        examFile,
        solutionsFile,
        autoGenerateSolutions,
      });
      const bundle = getBundleFromProcessResponse(response);
      if (!isValidExamBundle(bundle)) {
        throw new Error('The backend did not return an exam bundle.');
      }
      onExamReady(response);
    } catch (error) {
      console.error('Failed to process exam upload:', error);
      setSubmitError(error instanceof Error ? error.message : 'Failed to process exam upload.');
    } finally {
      setIsLoading(false);
    }
  }

  const canStart = Boolean(examFile) && (autoGenerateSolutions || Boolean(solutionsFile));

  return (
    <main className="landing-page">
      <div className={`landing-shell ${isLoading ? 'is-blurred' : ''}`}>
        <div className="landing-glow" />
        <header className="landing-header">
          <div className="eg-logo">
            EG
          </div>
        </header>

        <div className="landing-center">
          <div className="landing-content">
            <div className="landing-copy">
              <p className="landing-kicker">
                AI-assisted practice
              </p>
              <h1 className="landing-title">
                Exam Generator
              </h1>
              <p className="landing-subtitle">
                Upload an exam and solutions to generate a mock exam experience.
              </p>
            </div>

            <div className="upload-card">
              <div className="upload-grid">
                <FileDropzone
                  label="Exam PDF"
                  helperText="Drag and drop your exam PDF here, or click to browse"
                  file={examFile}
                  onFileChange={(file) => {
                    setExamFile(file);
                    setErrors((current) => ({ ...current, examFile: '' }));
                  }}
                  required
                  error={errors.examFile}
                />
                <FileDropzone
                  label="Solutions PDF"
                  helperText="Drag and drop your solution PDF here, or click to browse"
                  file={solutionsFile}
                  onFileChange={(file) => {
                    setSolutionsFile(file);
                    setErrors((current) => ({ ...current, solutionsFile: '' }));
                  }}
                  required={!autoGenerateSolutions}
                  optionalTone={autoGenerateSolutions}
                  error={errors.solutionsFile}
                />
              </div>

              <div className="toggle-panel">
                <div className="toggle-row">
                  <div>
                    <label htmlFor="auto-generate-solutions" className="toggle-title">
                      Auto-generate solutions
                    </label>
                    <p className="toggle-help">
                      Use this if you do not have a solution PDF. You can review generated solutions before grading.
                    </p>
                  </div>
                  <button
                    id="auto-generate-solutions"
                    type="button"
                    role="switch"
                    aria-label="Auto-generate solutions"
                    aria-checked={autoGenerateSolutions}
                    onClick={() => {
                      setAutoGenerateSolutions((enabled) => !enabled);
                      setErrors((current) => ({ ...current, solutionsFile: '' }));
                    }}
                    className={`toggle-switch ${autoGenerateSolutions ? 'is-on' : ''}`}
                  >
                    <span
                      className="toggle-knob"
                    />
                  </button>
                </div>
              </div>

              {submitError && (
                <div
                  className="upload-error"
                  role="alert"
                  aria-live="polite"
                >
                  {submitError}
                </div>
              )}

              <div className="start-row">
                <button
                  type="button"
                  onClick={handleStart}
                  disabled={!canStart || isLoading}
                  className="start-button"
                >
                  Start
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isLoading && <LoadingOverlay />}
    </main>
  );
}

function getBundleFromProcessResponse(response) {
  return response?.bundle || response?.exam_bundle || response?.examBundle || null;
}

function isValidExamBundle(bundle) {
  return Boolean(bundle && typeof bundle === 'object' && Array.isArray(bundle.questions));
}

function storeExamBundle(bundle, examId) {
  try {
    window.localStorage.setItem(
      'exam-generator:last-bundle',
      JSON.stringify(withExamAssetUrls(bundle, examId)),
    );
    if (examId) {
      window.localStorage.setItem('exam-generator:last-exam-id', examId);
    }
  } catch (error) {
    console.warn('Could not store generated exam bundle:', error);
  }
}

function setMockExamLocation() {
  if (window.location.hash !== '#mock-exam') {
    window.history.pushState(null, '', '#mock-exam');
  }
}

function loadStoredExamBundle() {
  try {
    const stored = window.localStorage.getItem('exam-generator:last-bundle');
    if (!stored) {
      return null;
    }
    const parsed = JSON.parse(stored);
    return isValidExamBundle(parsed) ? withExamAssetUrls(parsed, loadStoredExamId()) : null;
  } catch (error) {
    console.warn('Could not load stored exam bundle:', error);
    return null;
  }
}

function loadStoredExamId() {
  try {
    return window.localStorage.getItem('exam-generator:last-exam-id');
  } catch (error) {
    console.warn('Could not load stored exam id:', error);
    return null;
  }
}

function withExamAssetUrls(bundle, examId) {
  if (!isValidExamBundle(bundle) || !examId) {
    return bundle;
  }

  return {
    ...bundle,
    questions: bundle.questions.map((question) => ({
      ...question,
      images: Array.isArray(question.images)
        ? question.images.map((image) => withExamAssetUrl(image, examId))
        : question.images,
    })),
  };
}

function withExamAssetUrl(image, examId) {
  if (!image || typeof image !== 'object') {
    return image;
  }

  const src = String(image.src || '');
  if (src.startsWith(`/api/exams/${examId}/assets/`)) {
    return {
      ...image,
      src: getApiUrl(src),
    };
  }
  if (src.startsWith('/sample-assets/')) {
    return {
      ...image,
      src: getApiUrl(`/api/exams/${examId}/assets/${src.slice('/sample-assets/'.length)}`),
    };
  }

  const path = String(image.path || '');
  if (path.startsWith('assets/')) {
    return {
      ...image,
      src: getApiUrl(`/api/exams/${examId}/assets/${path.slice('assets/'.length)}`),
    };
  }

  return image;
}

function MockExamWorkspace({ initialBundle = null, examId = null, loadLabel = 'Loaded public/sample-exam-bundle.json' }) {
  const normalizedInitialBundle = useMemo(
    () => withExamAssetUrls(initialBundle, examId),
    [initialBundle, examId],
  );
  const initialQuestions = Array.isArray(normalizedInitialBundle?.questions) && normalizedInitialBundle.questions.length > 0
    ? normalizedInitialBundle.questions
    : fallbackExamBundle.questions;
  const [examBundle, setExamBundle] = useState(normalizedInitialBundle || fallbackExamBundle);
  const [loadState, setLoadState] = useState(normalizedInitialBundle ? 'uploaded' : 'loading');
  const [selectedId, setSelectedId] = useState(initialQuestions[0].id);
  const [answers, setAnswers] = useState({});
  const [revealed, setRevealed] = useState({});

  useEffect(() => {
    if (normalizedInitialBundle) {
      const questions = Array.isArray(normalizedInitialBundle.questions) ? normalizedInitialBundle.questions : [];
      setExamBundle(normalizedInitialBundle);
      setSelectedId(questions[0]?.id || fallbackExamBundle.questions[0].id);
      setAnswers({});
      setRevealed({});
      setLoadState('uploaded');
      return undefined;
    }

    let isMounted = true;

    fetch('/sample-exam-bundle.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Could not load exam bundle: ${response.status}`);
        }
        return response.json();
      })
      .then((loadedBundle) => {
        if (!isMounted) {
          return;
        }
        const questions = Array.isArray(loadedBundle.questions) ? loadedBundle.questions : [];
        if (questions.length === 0) {
          throw new Error('Exam bundle has no questions.');
        }
        setExamBundle(loadedBundle);
        setSelectedId(questions[0].id);
        setAnswers({});
        setRevealed({});
        setLoadState('loaded');
      })
      .catch(() => {
        if (isMounted) {
          setLoadState('fallback');
        }
      });

    return () => {
      isMounted = false;
    };
  }, [normalizedInitialBundle]);

  const questions = useMemo(
    () => (Array.isArray(examBundle.questions) ? examBundle.questions : []),
    [examBundle],
  );
  const selectedQuestion = useMemo(
    () => questions.find((question) => question.id === selectedId) || questions[0],
    [questions, selectedId],
  );
  const bundleHasAiGeneratedSolutions = useMemo(
    () =>
      (examBundle.warnings || []).some((warning) =>
        String(warning).toLowerCase().includes('ai-generated'),
      ),
    [examBundle.warnings],
  );

  const allSubquestions = useMemo(
    () =>
      questions.flatMap((question) => getAnswerItems(question)),
    [questions],
  );
  const answeredCount = allSubquestions.filter((subquestion) => hasAnswer(answers[subquestion.id])).length;

  if (!selectedQuestion) {
    return (
      <main className="min-h-screen bg-slate-100 text-slate-950">
        <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col lg:flex-row">
          <section className="flex-1 p-4 sm:p-6 lg:p-8">
            <h1>No questions found</h1>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col lg:flex-row">
        <aside className="border-b border-slate-300 bg-white lg:w-80 lg:border-b-0 lg:border-r">
          <div className="border-b border-slate-200 p-5">
            <p className="text-sm font-medium text-slate-500">{examBundle.exam.course_code}</p>
            <h1 className="mt-1 text-2xl font-semibold leading-tight">{examBundle.exam.title}</h1>
            <p className="mt-2 text-sm text-slate-600">{examBundle.exam.source_file}</p>
            <p className="mt-2 text-xs text-slate-500">
              {loadState === 'loaded'
                ? loadLabel
                : loadState === 'loading'
                  ? 'Loading exam bundle...'
                  : loadState === 'uploaded'
                    ? loadLabel
                    : 'Using fallback sample'}
            </p>
          </div>

          <div className="border-b border-slate-200 p-5">
            <div className="progress-summary flex items-center justify-between text-sm">
              <span className="font-medium">Progress</span>
              <span className="text-slate-600">
                {answeredCount}/{allSubquestions.length} answered
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded bg-slate-200">
              <div
                className="h-full bg-emerald-600"
                style={{ width: `${allSubquestions.length === 0 ? 0 : (answeredCount / allSubquestions.length) * 100}%` }}
              />
            </div>
          </div>

          {examBundle.warnings.length > 0 && (
            <section className="border-b border-amber-200 bg-amber-50 p-5">
              <h2 className="text-sm font-semibold text-amber-950">Warnings</h2>
              <ul className="mt-2 space-y-2 text-sm text-amber-900">
                {examBundle.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </section>
          )}

          <nav className="p-3">
            {questions.map((question) => (
              <button
                key={question.id}
                type="button"
                onClick={() => setSelectedId(question.id)}
                className={`question-nav-button ${selectedId === question.id ? 'is-active' : ''}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold">Question {question.question_number}</span>
                </div>
                <p className={selectedId === question.id ? 'mt-1 text-xs text-slate-300' : 'mt-1 text-xs text-slate-600'}>
                  {question.topic || 'No topic'}
                </p>
              </button>
            ))}
          </nav>
        </aside>

        <section className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="meta-row mb-5 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <span>Page {formatPages(selectedQuestion)}</span>
            {selectedQuestion.topic && <span className="rounded bg-white px-2 py-1">{selectedQuestion.topic}</span>}
            <span className="rounded bg-white px-2 py-1">{formatInteraction(selectedQuestion.interaction_type)}</span>
          </div>

          <article className="border-b border-slate-300 pb-6">
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Question {selectedQuestion.question_number}
            </p>
            <h2 className="mt-2 max-w-4xl text-2xl font-semibold leading-snug">
              {formatDisplayText(selectedQuestion.question_text)}
            </h2>
            <QuestionContext context={selectedQuestion.context} />
            <QuestionImages images={selectedQuestion.images} />
          </article>

          <div className="mt-6 space-y-5">
            {getAnswerItems(selectedQuestion).map((subquestion) => (
              <SubquestionPanel
                key={subquestion.id}
                subquestion={subquestion}
                value={answers[subquestion.id] || ''}
                revealed={Boolean(revealed[subquestion.id])}
                onAnswer={(value) => setAnswers((current) => ({ ...current, [subquestion.id]: value }))}
                onReveal={() => setRevealed((current) => ({ ...current, [subquestion.id]: !current[subquestion.id] }))}
                fallbackSolutionSource={bundleHasAiGeneratedSolutions ? 'ai_generated' : null}
              />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function SubquestionPanel({ subquestion, value, revealed, onAnswer, onReveal, fallbackSolutionSource }) {
  return (
    <section className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="subquestion-meta flex flex-wrap items-center gap-2">
            <span className="rounded bg-slate-100 px-2 py-1 text-sm font-semibold">
              {formatLabel(subquestion.label)}
            </span>
            <span className="rounded bg-sky-50 px-2 py-1 text-xs font-medium text-sky-800">
              {formatInteraction(subquestion.interaction_type)}
            </span>
          </div>
          {subquestion.text && (
            <p className="mt-3 whitespace-pre-wrap text-lg leading-relaxed">{formatDisplayText(subquestion.text)}</p>
          )}
        </div>
        {subquestion.points != null && (
          <span className="rounded bg-slate-100 px-2 py-1 text-sm text-slate-700">{subquestion.points} pts</span>
        )}
      </div>

      <div className="mt-5">
        <AnswerInput subquestion={subquestion} value={value} onAnswer={onAnswer} />
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-slate-200 pt-4">
        <p className="text-sm text-slate-500">{hasAnswer(value) ? 'Answer saved locally' : 'Not answered yet'}</p>
        <button
          type="button"
          onClick={onReveal}
          className={`reveal-button ${revealed ? 'is-active' : ''}`}
        >
          {revealed ? 'Hide solution' : 'Reveal solution'}
        </button>
      </div>

      {revealed && <SolutionBlock solution={subquestion.solution} fallbackSource={fallbackSolutionSource} />}
    </section>
  );
}

function QuestionImages({ images }) {
  const visibleImages = Array.isArray(images) ? images.filter(isVisibleQuestionImage) : [];
  if (visibleImages.length === 0) {
    return null;
  }

  return (
    <div className="question-images">
      {visibleImages.map((image) => (
        <figure key={image.id || image.src}>
          <img src={image.src} alt={image.alt || `Image from page ${image.page_number || ''}`} />
          {image.page_number && <figcaption>Page {image.page_number}</figcaption>}
        </figure>
      ))}
    </div>
  );
}

function isVisibleQuestionImage(image) {
  if (!image?.src) {
    return false;
  }
  const width = Number(image.width || 0);
  const height = Number(image.height || 0);
  return width >= 80 && height >= 80;
}

function QuestionContext({ context }) {
  if (typeof context !== 'string' || !context.trim()) {
    return null;
  }
  const blocks = parseContextBlocks(context, { detectCode: true });

  return (
    <section className="question-context" aria-label="Question context">
      <h3>Context</h3>
      <div className="context-blocks">
        {blocks.map((block, index) =>
          block.type === 'code' ? (
            <CodeBlock key={`${block.type}-${index}`} language={block.language} code={block.content} />
          ) : (
            <MarkdownText key={`${block.type}-${index}`} text={block.content} />
          ),
        )}
      </div>
    </section>
  );
}

function RichTextBlocks({ text, className = '', detectCode = false }) {
  if (typeof text !== 'string' || !text.trim()) {
    return null;
  }
  const blocks = parseContextBlocks(text, { detectCode });
  return (
    <div className={`rich-text-blocks ${className}`}>
      {blocks.map((block, index) =>
        block.type === 'code' ? (
          <CodeBlock key={`${block.type}-${index}`} language={block.language} code={block.content} />
        ) : (
          <MarkdownText key={`${block.type}-${index}`} text={block.content} />
        ),
      )}
    </div>
  );
}

function MarkdownText({ text }) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trimEnd());
  const elements = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 3, 6);
      const HeadingTag = `h${level}`;
      elements.push(
        <HeadingTag key={`heading-${index}`} className="markdown-heading">
          {renderInlineMarkdown(heading[2])}
        </HeadingTag>,
      );
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ''));
        index += 1;
      }
      elements.push(
        <ul key={`ul-${index}`} className="markdown-list">
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ''));
        index += 1;
      }
      elements.push(
        <ol key={`ol-${index}`} className="markdown-list markdown-list-ordered">
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const tableLines = [];
      while (index < lines.length && looksLikeMarkdownTableRow(lines[index])) {
        tableLines.push(lines[index].trim());
        index += 1;
      }
      elements.push(<MarkdownTable key={`table-${index}`} lines={tableLines} />);
      continue;
    }

    const paragraphLines = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+/.test(lines[index].trim()) &&
      !/^[-*]\s+/.test(lines[index].trim()) &&
      !/^\d+\.\s+/.test(lines[index].trim()) &&
      !isMarkdownTableStart(lines, index)
    ) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    elements.push(
      <p key={`p-${index}`}>
        {paragraphLines.map((paragraphLine, lineIndex) => (
          <span key={`${lineIndex}-${paragraphLine}`}>
            {lineIndex > 0 && <br />}
            {renderInlineMarkdown(paragraphLine)}
          </span>
        ))}
      </p>,
    );
  }

  return <div className="markdown-text">{elements}</div>;
}

function MarkdownTable({ lines }) {
  const rows = lines
    .filter((line, index) => index !== 1 || !looksLikeMarkdownTableDivider(line))
    .map(parseMarkdownTableRow)
    .filter((cells) => cells.length > 0);

  if (rows.length === 0) {
    return null;
  }

  const [headers, ...bodyRows] = rows;

  return (
    <div className="markdown-table-wrap">
      <table className="markdown-table">
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={`${index}-${header}`}>{renderInlineMarkdown(header)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {headers.map((_, cellIndex) => (
                <td key={`cell-${rowIndex}-${cellIndex}`}>
                  {renderInlineMarkdown(row[cellIndex] || '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isMarkdownTableStart(lines, index) {
  return (
    looksLikeMarkdownTableRow(lines[index]) &&
    looksLikeMarkdownTableDivider(lines[index + 1])
  );
}

function looksLikeMarkdownTableRow(line) {
  const trimmed = String(line || '').trim();
  return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.split('|').length >= 3;
}

function looksLikeMarkdownTableDivider(line) {
  const trimmed = String(line || '').trim();
  return looksLikeMarkdownTableRow(trimmed) && /^(\|\s*:?-{3,}:?\s*)+\|$/.test(trimmed);
}

function parseMarkdownTableRow(line) {
  return String(line || '')
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function renderInlineMarkdown(text) {
  const formattedText = formatDisplayText(text);
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(formattedText)) !== null) {
    if (match.index > lastIndex) {
      parts.push(formattedText.slice(lastIndex, match.index));
    }

    const token = match[0];
    const key = `${match.index}-${token}`;
    if (token.startsWith('`')) {
      parts.push(
        <code key={key} className="inline-code">
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith('**') || token.startsWith('__')) {
      parts.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else {
      parts.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < formattedText.length) {
    parts.push(formattedText.slice(lastIndex));
  }

  return parts;
}

function CodeBlock({ language, code }) {
  const normalizedLanguage = normalizeCodeLanguage(language);
  const displayCode = formatCodeForLanguage(code, normalizedLanguage);
  return (
    <div className="code-block">
      <div className="code-block-header">{normalizedLanguage}</div>
      <pre>
        <code>{highlightCode(displayCode, normalizedLanguage)}</code>
      </pre>
    </div>
  );
}

function AnswerInput({ subquestion, value, onAnswer }) {
  if (subquestion.interaction_type === 'true_false' || subquestion.interaction_type === 'multiple_choice') {
    const choices = getDisplayChoices(subquestion);
    return (
      <div className="flex flex-wrap gap-2">
        {choices.map((choice) => (
          <button
            key={choice}
            type="button"
            onClick={() => onAnswer(choice)}
            className={`answer-choice ${value === choice ? 'is-selected' : ''}`}
            aria-pressed={value === choice}
          >
            {choice}
          </button>
        ))}
      </div>
    );
  }

  if (subquestion.interaction_type === 'numeric') {
    return (
      <input
        type="number"
        value={value}
        onChange={(event) => onAnswer(event.target.value)}
        className="w-full max-w-xs rounded-md border border-slate-300 px-3 py-2 focus:border-slate-900 focus:outline-none"
        placeholder="Enter a number"
      />
    );
  }

  return (
    <textarea
      value={value}
      onChange={(event) => onAnswer(event.target.value)}
      className="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 leading-relaxed focus:border-slate-900 focus:outline-none"
      placeholder="Write your answer"
    />
  );
}

function SolutionBlock({ solution, fallbackSource = null }) {
  if (!solution) {
    return (
      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        No solution is available for this part yet.
      </div>
    );
  }

  const source = solution.source || fallbackSource;
  const isAiGenerated = source === 'ai_generated';

  return (
    <div
      className={`solution-panel ${isAiGenerated ? 'is-ai' : 'is-official'}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{sourceLabels[source] || 'Solution'}</h3>
        {isAiGenerated && <span className="rounded bg-purple-200 px-2 py-1 text-xs font-semibold text-purple-950">AI</span>}
      </div>
      {solution.answer && (
        <RichTextBlocks text={solution.answer} className="solution-answer" detectCode />
      )}
      {solution.explanation && (
        <RichTextBlocks text={solution.explanation} className="solution-explanation" detectCode />
      )}
      {solution.grading_points?.length > 0 && (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
          {solution.grading_points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function hasAnswer(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function getAnswerItems(question) {
  const subquestions = Array.isArray(question.subquestions) ? question.subquestions : [];
  if (subquestions.length > 0) {
    return subquestions;
  }

  return [
    {
      id: question.id,
      label: 'answer',
      text: '',
      points: question.points,
      interaction_type: question.interaction_type,
      choices: Array.isArray(question.choices) ? question.choices : [],
      solution: question.solution || null,
    },
  ];
}

function formatLabel(label) {
  if (label === 'followup') {
    return 'Follow-up';
  }
  if (label === 'answer') {
    return 'Answer';
  }
  return label;
}

function formatPages(question) {
  if (!question.page_start) {
    return 'unknown';
  }
  if (!question.page_end || question.page_start === question.page_end) {
    return question.page_start;
  }
  return `${question.page_start}-${question.page_end}`;
}

function formatInteraction(type) {
  return String(type || 'free_text')
    .replaceAll('_', ' ')
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

function formatDisplayText(text) {
  return String(text || '')
    .replace(/([∀∃][a-z])(?=[A-Z])/g, '$1 ')
    .replace(/(∃![a-z])(?=[A-Z])/g, '$1 ')
    .replace(/([∧∨→↔])(?=\S)/g, '$1 ')
    .replace(/(\S)([∧∨→↔])/g, '$1 $2')
    .replace(/\s+([),.;:?])/g, '$1')
    .replace(/([(])\s+/g, '$1');
}

function getDisplayChoices(subquestion) {
  const choices = sanitizeChoices(Array.isArray(subquestion.choices) ? subquestion.choices : []);
  const answer = subquestion.solution?.answer;
  if (
    subquestion.interaction_type === 'multiple_choice' &&
    typeof answer === 'string' &&
    answer.trim() &&
    !choices.some((choice) => normalizeChoice(choice) === normalizeChoice(answer))
  ) {
    return sanitizeChoices([answer, ...choices], { keepFirst: true });
  }
  return choices;
}

function sanitizeChoices(choices, options = {}) {
  const sanitized = [];
  const seen = new Set();
  for (let index = 0; index < choices.length; index += 1) {
    const choice = String(choices[index] || '').trim();
    const normalized = normalizeChoice(choice);
    if (!choice || seen.has(normalized)) {
      continue;
    }
    if (!(options.keepFirst && index === 0) && looksLikeQuestionPrompt(choice)) {
      continue;
    }
    sanitized.push(choice);
    seen.add(normalized);
    if (sanitized.length >= 6) {
      break;
    }
  }
  return sanitized;
}

function normalizeChoice(choice) {
  return String(choice || '').trim().replace(/^["']|["']$/g, '').toLowerCase();
}

function looksLikeQuestionPrompt(choice) {
  const normalized = choice.trim().toLowerCase();
  return (
    normalized.startsWith('hva er ') ||
    normalized.startsWith('hvilken ') ||
    normalized.startsWith('which ') ||
    normalized.startsWith('what ') ||
    normalized.startsWith('husk at ') ||
    normalized.startsWith('hint:') ||
    normalized.startsWith('remember ') ||
    normalized.startsWith('note:') ||
    normalized.startsWith('anta at ') ||
    normalized.endsWith('?')
  );
}

function parseContextBlocks(context, options = {}) {
  const blocks = [];
  const fencePattern = /```([A-Za-z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = fencePattern.exec(context)) !== null) {
    pushTextBlocks(blocks, context.slice(lastIndex, match.index));
    blocks.push({
      type: 'code',
      language: match[1] || 'text',
      content: normalizeCodeWhitespace(match[2]),
    });
    lastIndex = fencePattern.lastIndex;
  }

  pushTextBlocks(blocks, context.slice(lastIndex));
  if (blocks.length === 0) {
    pushTextBlocks(blocks, context);
  }
  return options.detectCode ? applyCodeDetection(blocks) : blocks;
}

function pushTextBlocks(blocks, text) {
  const paragraphs = String(text || '')
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  paragraphs.forEach((paragraph) => blocks.push({ type: 'text', content: paragraph }));
}

function applyCodeDetection(blocks) {
  const detectedBlocks = blocks.map((block) => {
    if (block.type !== 'text' || !looksLikeCode(block.content)) {
      return block;
    }
    const language = inferCodeLanguage(block.content);
    return {
      type: 'code',
      language,
      content: normalizeCodeWhitespace(formatDetectedCode(block.content, language)),
    };
  });
  return mergeAdjacentCodeBlocks(detectedBlocks);
}

function mergeAdjacentCodeBlocks(blocks) {
  return blocks.reduce((merged, block) => {
    const previous = merged[merged.length - 1];
    if (
      previous?.type === 'code' &&
      block.type === 'code' &&
      previous.language === block.language
    ) {
      previous.content = `${previous.content}\n\n${block.content}`;
      return merged;
    }
    merged.push({ ...block });
    return merged;
  }, []);
}

function looksLikeCode(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed || trimmed.length < 12) {
    return false;
  }
  if (looksLikePseudoInterfaceCode(trimmed)) {
    return true;
  }
  const codeSignals = [
    /\b(public|private|protected|static|class|interface|enum|record|void|int|boolean|String|Map|List|HashMap|new|return|var|fun|val|let|const|function|fn|mut|use|impl|match|struct|enum)\b/,
    /\b(type|data|case|of)\b/,
    /\bprintln!\s*\(|\bvec!\s*\[|String::from|::/,
    /[{};]/,
    /\w+\s*\([^)]*\)\s*\{/,
    /<\s*\w+\s*,\s*\w+\s*>/,
    /\b(if|else|for|while|switch)\s*\(/,
    /=>|->|::/,
  ];
  const signalCount = codeSignals.filter((pattern) => pattern.test(trimmed)).length;
  const proseWords = trimmed.split(/\s+/).filter((word) => /^[A-ZÆØÅa-zæøå]{4,}$/.test(word)).length;
  return signalCount >= 2 && proseWords < 18;
}

function inferCodeLanguage(text) {
  const trimmed = String(text || '');
  if (looksLikePseudoInterfaceCode(trimmed)) {
    return 'pseudocode';
  }
  if (/\b(fn|let|mut|use|impl|match|struct|enum|trait)\b|println!\s*\(|vec!\s*\[|String::from|&mut\b/.test(trimmed)) {
    return 'rust';
  }
  if (/\b(module|where|data\s+\w+|deriving|case\b.*\bof\b|Maybe\s+Int|Either\s+String\s+Int|::)\b/.test(trimmed)) {
    return 'haskell';
  }
  if (/\b(public|private|protected|static|class|interface|enum|record|void|int|boolean|String|HashMap|implements|extends)\b/.test(trimmed)) {
    return 'java';
  }
  if (/\b(fun|val|var|data class|object)\b/.test(trimmed)) {
    return 'kotlin';
  }
  if (/\b(function|const|let|=>|console\.)\b/.test(trimmed)) {
    return 'javascript';
  }
  return 'text';
}

function formatDetectedCode(text, language = inferCodeLanguage(text)) {
  const trimmed = String(text || '').trim();
  if (language === 'pseudocode') {
    return formatPseudoInterfaceCode(trimmed);
  }
  if (language === 'haskell') {
    return formatFlattenedHaskellCode(trimmed);
  }
  if (trimmed.includes('\n')) {
    return trimmed;
  }
  if (!/[{};]/.test(trimmed)) {
    return trimmed;
  }
  return trimmed
    .replace(/\{\s*/g, '{\n  ')
    .replace(/;\s*/g, ';\n  ')
    .replace(/\s*\}\s*/g, '\n}\n')
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function looksLikePseudoInterfaceCode(text) {
  const trimmed = String(text || '').trim();
  return /\binterface\s+\w+\s*\{/.test(trimmed) && /\bmethod\s+\w+\s*\(/.test(trimmed);
}

function formatPseudoInterfaceCode(code) {
  return String(code || '')
    .replace(/\s*\{\s*/g, ' {\n')
    .replace(/\s*}\s*/g, '\n}')
    .replace(/\s*\/\/\s*/g, '\n  // ')
    .replace(/\s+(method\s+\w+\s*\()/g, '\n  $1')
    .replace(/;\s*/g, ';\n')
    .replace(/\n[ \t]*\n[ \t]*\n+/g, '\n\n')
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .trim();
}

function formatFlattenedHaskellCode(code) {
  return String(code || '')
    .replace(/\s+data\s+/g, '\ndata ')
    .replace(/data ([^=\n]+)\s+=\s+/g, 'data $1\n  = ')
    .replace(/\s+\|\s+/g, '\n  | ')
    .replace(/(Maybe Int|Either String Int)\s+(lookupEnv\b)/g, '$1\n$2')
    .replace(/(Maybe Int|Either String Int)\s+(eval\b)/g, '$1\n$2')
    .replace(/(Nothing|Just v)\s+(lookupEnv\b)/g, '$1\n$2')
    .replace(/(:rest\))\s+(\| )/g, '$1\n  $2')
    .replace(/(Just v)\s+(\| )/g, '$1\n  $2')
    .replace(/(case expr of)\s+/g, '$1\n')
    .replace(/\s+(Lit n ->)/g, '\n  $1')
    .replace(/\s+(Var x ->)/g, '\n  $1')
    .replace(/\s+(Add e1 e2 ->)/g, '\n  $1')
    .replace(/\s+(Mul e1 e2 ->)/g, '\n  $1')
    .replace(/\s+(Let x e body ->)/g, '\n  $1')
    .replace(/\s+(IfZero c t f ->)/g, '\n  $1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function normalizeCodeWhitespace(code) {
  return String(code || '')
    .replace(/^\s*\n/, '')
    .replace(/\n\s*$/, '');
}

function formatCodeForLanguage(code, language) {
  const normalizedCode = normalizeCodeWhitespace(code);
  if (language === 'haskell') {
    return repairFlattenedHaskellIndentation(normalizedCode);
  }
  return normalizedCode;
}

function repairFlattenedHaskellIndentation(code) {
  const lines = String(code || '').split('\n');
  if (lines.some((line) => /^ {2,}\S/.test(line))) {
    return code;
  }

  return lines
    .map((line) => {
      const trimmed = line.trimStart();
      if (!trimmed) {
        return '';
      }
      if (/^(=|\|)\s/.test(trimmed) || /^(Lit|Var|Add|Mul|Let|IfZero)\b.*->/.test(trimmed)) {
        return `  ${trimmed}`;
      }
      return trimmed;
    })
    .join('\n');
}

function normalizeCodeLanguage(language) {
  const normalized = String(language || 'text').trim().toLowerCase();
  if (['hs', 'haskell'].includes(normalized)) {
    return 'haskell';
  }
  if (['py', 'python'].includes(normalized)) {
    return 'python';
  }
  if (['js', 'javascript', 'jsx'].includes(normalized)) {
    return 'javascript';
  }
  if (['ts', 'typescript', 'tsx'].includes(normalized)) {
    return 'typescript';
  }
  if (['rs', 'rust'].includes(normalized)) {
    return 'rust';
  }
  if (['java'].includes(normalized)) {
    return 'java';
  }
  if (['kt', 'kotlin'].includes(normalized)) {
    return 'kotlin';
  }
  return normalized || 'text';
}

function highlightCode(code, language) {
  const syntax = getSyntaxConfig(language);
  if (!syntax) {
    return code;
  }

  const tokenPattern = syntax.pattern;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = tokenPattern.exec(code)) !== null) {
    if (match.index > lastIndex) {
      parts.push(code.slice(lastIndex, match.index));
    }
    const token = match[0];
    parts.push(
      <span key={`${match.index}-${token}`} className={`syntax-${classifyToken(token, syntax)}`}>
        {token}
      </span>,
    );
    lastIndex = tokenPattern.lastIndex;
  }

  if (lastIndex < code.length) {
    parts.push(code.slice(lastIndex));
  }
  return parts;
}

function getSyntaxConfig(language) {
  const commonOperatorPattern = String.raw`==|!=|<=|>=|&&|\|\||::|->|=>|[=+\-*/%<>!|&{}[\]().,;:]`;
  const configs = {
    haskell: {
      pattern: new RegExp(
        String.raw`(--.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:module|where|import|qualified|as|type|data|newtype|deriving|instance|class|case|of|let|in|if|then|else|do)\b|\b(?:Integer|String|Bool|Char|Maybe|Map|IO|Eq|Show|Ord|Int|Double|Float)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Integer|String|Bool|Char|Maybe|Map|IO|Eq|Show|Ord|Int|Double|Float)$/,
    },
    rust: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:as|async|await|break|const|continue|crate|else|enum|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while)\b|\b(?:String|Vec|Option|Result|Some|None|Ok|Err|Box|usize|isize|u8|u16|u32|u64|i8|i16|i32|i64|bool|char|str)\b|\b\w+!|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Vec|Option|Result|Some|None|Ok|Err|Box|usize|isize|u8|u16|u32|u64|i8|i16|i32|i64|bool|char|str)$/,
    },
    java: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|extends|final|finally|float|for|if|implements|import|instanceof|int|interface|long|new|null|package|private|protected|public|record|return|short|static|strictfp|super|switch|synchronized|this|throw|throws|transient|try|var|void|volatile|while)\b|\b(?:String|Integer|Boolean|Character|Double|Float|Long|Short|Byte|Object|List|Map|Set|HashMap|ArrayList|Optional)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Integer|Boolean|Character|Double|Float|Long|Short|Byte|Object|List|Map|Set|HashMap|ArrayList|Optional)$/,
    },
    kotlin: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:as|break|class|continue|data|do|else|false|for|fun|if|import|in|interface|is|null|object|package|return|super|this|throw|true|try|typealias|val|var|when|while)\b|\b(?:String|Int|Boolean|Char|Double|Float|Long|Short|Byte|Any|Unit|List|Map|Set|MutableList|MutableMap)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Int|Boolean|Char|Double|Float|Long|Short|Byte|Any|Unit|List|Map|Set|MutableList|MutableMap)$/,
    },
    javascript: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|` + '`' + String.raw`(?:\\.|[^` + '`' + String.raw`\\])*` + '`' + String.raw`|\b(?:async|await|break|case|catch|class|const|continue|default|do|else|export|extends|finally|for|from|function|if|import|in|let|new|null|return|static|super|switch|this|throw|try|typeof|undefined|var|while|yield)\b|\b(?:Array|Boolean|Date|Map|Number|Object|Promise|Set|String)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Array|Boolean|Date|Map|Number|Object|Promise|Set|String)$/,
    },
    typescript: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|` + '`' + String.raw`(?:\\.|[^` + '`' + String.raw`\\])*` + '`' + String.raw`|\b(?:abstract|any|as|async|await|boolean|break|case|catch|class|const|continue|default|do|else|enum|export|extends|false|finally|for|from|function|if|implements|import|in|interface|keyof|let|namespace|new|null|number|private|protected|public|readonly|return|static|string|super|switch|this|throw|true|try|type|typeof|undefined|var|void|while|yield)\b|\b(?:Array|Boolean|Date|Map|Number|Object|Promise|Set|String)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Array|Boolean|Date|Map|Number|Object|Promise|Set|String)$/,
    },
  };
  return configs[language] || null;
}

function classifyToken(token, syntax) {
  if (token.startsWith('--') || token.startsWith('//') || token.startsWith('/*')) {
    return 'comment';
  }
  if (token.startsWith('"') || token.startsWith("'") || token.startsWith('`')) {
    return 'string';
  }
  if (syntax.types.test(token)) {
    return 'type';
  }
  if (/^(==|!=|<=|>=|&&|\|\||::|->|=>|[=+\-*/%<>!|&{}[\]().,;:])$/.test(token)) {
    return 'operator';
  }
  return 'keyword';
}

export default App;
