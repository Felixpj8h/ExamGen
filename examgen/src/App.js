import { useEffect, useMemo, useState } from 'react';
import './App.css';

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
  const [examBundle, setExamBundle] = useState(fallbackExamBundle);
  const [loadState, setLoadState] = useState('loading');
  const [selectedId, setSelectedId] = useState(fallbackExamBundle.questions[0].id);
  const [answers, setAnswers] = useState({});
  const [revealed, setRevealed] = useState({});

  useEffect(() => {
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
  }, []);

  const questions = useMemo(
    () => (Array.isArray(examBundle.questions) ? examBundle.questions : []),
    [examBundle],
  );
  const selectedQuestion = useMemo(
    () => questions.find((question) => question.id === selectedId) || questions[0],
    [questions, selectedId],
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
                ? 'Loaded public/sample-exam-bundle.json'
                : loadState === 'loading'
                  ? 'Loading exam bundle...'
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
              />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function SubquestionPanel({ subquestion, value, revealed, onAnswer, onReveal }) {
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

      {revealed && <SolutionBlock solution={subquestion.solution} />}
    </section>
  );
}

function QuestionImages({ images }) {
  const visibleImages = Array.isArray(images) ? images.filter((image) => image?.src) : [];
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

function SolutionBlock({ solution }) {
  if (!solution) {
    return (
      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        No solution is available for this part yet.
      </div>
    );
  }

  const isAiGenerated = solution.source === 'ai_generated';

  return (
    <div
      className={`solution-panel ${isAiGenerated ? 'is-ai' : 'is-official'}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{sourceLabels[solution.source] || 'Solution'}</h3>
        {isAiGenerated && <span className="rounded bg-purple-200 px-2 py-1 text-xs font-semibold text-purple-950">AI</span>}
      </div>
      {solution.answer && (
        <p className="mt-3 whitespace-pre-wrap text-base font-semibold">{formatDisplayText(solution.answer)}</p>
      )}
      {solution.explanation && (
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{formatDisplayText(solution.explanation)}</p>
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
  const choices = Array.isArray(subquestion.choices) ? [...subquestion.choices] : [];
  const answer = subquestion.solution?.answer;
  if (
    subquestion.interaction_type === 'multiple_choice' &&
    typeof answer === 'string' &&
    answer.trim() &&
    !choices.some((choice) => normalizeChoice(choice) === normalizeChoice(answer))
  ) {
    return [answer, ...choices];
  }
  return choices;
}

function normalizeChoice(choice) {
  return String(choice || '').trim().replace(/^["']|["']$/g, '').toLowerCase();
}

export default App;
