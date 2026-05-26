import type { ExamBundle, ExamQuestion } from '../../types';

interface QuestionSidebarProps {
  examBundle: ExamBundle;
  questions: ExamQuestion[];
  selectedId: string;
  onSelectQuestion: (id: string) => void;
  answeredCount: number;
  totalAnswerCount: number;
  loadState: string;
  loadLabel: string;
}

function QuestionSidebar({
  examBundle,
  questions,
  selectedId,
  onSelectQuestion,
  answeredCount,
  totalAnswerCount,
  loadState,
  loadLabel,
}: QuestionSidebarProps) {
  return (
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
            {answeredCount}/{totalAnswerCount} answered
          </span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded bg-slate-200">
          <div
            className="h-full bg-emerald-600"
            style={{ width: `${totalAnswerCount === 0 ? 0 : (answeredCount / totalAnswerCount) * 100}%` }}
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
            onClick={() => onSelectQuestion(question.id)}
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
  );
}

export default QuestionSidebar;

