import {
  formatDisplayText,
  formatInteraction,
  formatPages,
} from '../../lib/textFormatting';
import QuestionContext from './QuestionContext';
import QuestionDiagrams from './QuestionDiagrams';
import QuestionImages from './QuestionImages';
import type { ExamQuestion } from '../../types';

function QuestionHeader({ question }: { question: ExamQuestion }) {
  const context = shouldShowContext(question) ? question.context : null;

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
        <QuestionContext context={context} />
        <QuestionDiagrams diagrams={question.diagrams} />
        <QuestionImages images={question.images} />
      </article>
    </>
  );
}

function shouldShowContext(question: ExamQuestion): boolean {
  const context = question.context;
  if (typeof context !== 'string' || !context.trim()) {
    return false;
  }
  const hasVectorFigure = Array.isArray(question.images)
    && question.images.some((image) => image?.source === 'vector_drawing');
  if (!hasVectorFigure) {
    return true;
  }
  return !looksLikeDiagramTranscript(context);
}

function looksLikeDiagramTranscript(context: string): boolean {
  const lines = context
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 4) {
    return false;
  }

  const diagramLikeLines = lines.filter((line) => (
    line.length <= 72 ||
    /^\|.*\|$/.test(line) ||
    /^[+\-#~]\s*\w/.test(line) ||
    /\b(?:class|interface|abstract|enum)\b/i.test(line) ||
    /\w+\s*:\s*[\w<[({]/.test(line) ||
    /\w+\([^)]*\)\s*:/.test(line)
  ));
  const proseLines = lines.filter((line) => /[.!?]$/.test(line) && line.length > 72);

  return diagramLikeLines.length / lines.length >= 0.65 && proseLines.length <= 1;
}

export default QuestionHeader;

