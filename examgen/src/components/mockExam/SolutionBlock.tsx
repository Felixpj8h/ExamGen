import { RichTextBlocks } from './MarkdownText';
import type { ExamSolution, SolutionSource } from '../../types';

const sourceLabels: Record<string, string> = {
  official_solution_pdf: 'Official solution',
  same_pdf: 'Official answer from PDF',
  ai_generated: 'AI-generated practice answer',
  manual: 'Manual solution',
};

function SolutionBlock({
  solution,
  fallbackSource = null,
}: {
  solution?: ExamSolution | null;
  fallbackSource?: SolutionSource | null;
}) {
  if (!solution) {
    return (
      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        No solution is available for this part yet.
      </div>
    );
  }

  const source = solution.source || fallbackSource;
  const isAiGenerated = source === 'ai_generated';
  const gradingPoints = Array.isArray(solution.grading_points) ? solution.grading_points : [];

  return (
    <div className={`solution-panel ${isAiGenerated ? 'is-ai' : 'is-official'}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{source ? sourceLabels[source] || 'Solution' : 'Solution'}</h3>
        {isAiGenerated && <span className="rounded bg-purple-200 px-2 py-1 text-xs font-semibold text-purple-950">AI</span>}
      </div>
      {solution.answer && (
        <RichTextBlocks text={solution.answer} className="solution-answer" detectCode />
      )}
      {solution.explanation && (
        <RichTextBlocks text={solution.explanation} className="solution-explanation" detectCode />
      )}
      {gradingPoints.length > 0 && (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
          {gradingPoints.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default SolutionBlock;

