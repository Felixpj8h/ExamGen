import { useEffect, useMemo, useState } from 'react';
import AnswerInput from '../components/mockExam/AnswerInput';
import QuestionHeader from '../components/mockExam/QuestionHeader';
import QuestionSidebar from '../components/mockExam/QuestionSidebar';
import SolutionBlock from '../components/mockExam/SolutionBlock';
import {
  formatDisplayText,
  formatInteraction,
  formatLabel,
  getAnswerItems,
  hasAnswer,
} from '../lib/textFormatting';
import { withExamAssetUrls } from '../lib/examStorage';

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
  ],
  warnings: ['AI-generated solutions; not official answer key.'],
};

function MockExamPage({
  initialBundle = null,
  examId = null,
  loadLabel = 'Loaded public/sample-exam-bundle.json',
}) {
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
    () => questions.flatMap((question) => getAnswerItems(question)),
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
        <QuestionSidebar
          examBundle={examBundle}
          questions={questions}
          selectedId={selectedId}
          onSelectQuestion={setSelectedId}
          answeredCount={answeredCount}
          totalAnswerCount={allSubquestions.length}
          loadState={loadState}
          loadLabel={loadLabel}
        />

        <section className="flex-1 p-4 sm:p-6 lg:p-8">
          <QuestionHeader question={selectedQuestion} />

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

export default MockExamPage;

