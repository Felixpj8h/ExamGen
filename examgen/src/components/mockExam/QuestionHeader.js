import {
  formatDisplayText,
  formatInteraction,
  formatPages,
} from '../../lib/textFormatting';
import QuestionContext from './QuestionContext';
import QuestionImages from './QuestionImages';

function QuestionHeader({ question }) {
  return (
    <>
      <div className="meta-row mb-5 flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <span>Page {formatPages(question)}</span>
        {question.topic && <span className="rounded bg-white px-2 py-1">{question.topic}</span>}
        <span className="rounded bg-white px-2 py-1">{formatInteraction(question.interaction_type)}</span>
      </div>

      <article className="border-b border-slate-300 pb-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Question {question.question_number}
        </p>
        <h2 className="mt-2 max-w-4xl text-2xl font-semibold leading-snug">
          {formatDisplayText(question.question_text)}
        </h2>
        <QuestionContext context={question.context} />
        <QuestionImages images={question.images} />
      </article>
    </>
  );
}

export default QuestionHeader;

