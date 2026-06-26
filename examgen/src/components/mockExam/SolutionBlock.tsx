import { Fragment } from 'react';
import { RichTextBlocks } from './MarkdownText';
import { getDisplayChoices } from '../../lib/textFormatting';
import type { AnswerItem, ExamSolution, SolutionSource } from '../../types';

const sourceLabels: Record<string, string> = {
  official_solution_pdf: 'Official solution',
  same_pdf: 'Official answer from PDF',
  ai_generated: 'AI-generated practice answer',
  manual: 'Manual solution',
};

function SolutionBlock({
  solution,
  fallbackSource = null,
  answerItem,
  currentAnswer = '',
}: {
  solution?: ExamSolution | null;
  fallbackSource?: SolutionSource | null;
  answerItem?: AnswerItem | null;
  currentAnswer?: string;
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
  const matrixSelections = getMatrixSolutionSelections(answerItem, solution, currentAnswer);
  const shouldRenderMatrixSolution = Boolean(answerItem && answerItem.interaction_type === 'matrix_choice' && matrixSelections);
  const shouldRenderAnswerText = Boolean(solution.answer && !shouldRenderMatrixSolution);
  const shouldRenderExplanation = Boolean(solution.explanation && !shouldRenderMatrixSolution);

  return (
    <div className={`solution-panel ${isAiGenerated ? 'is-ai' : 'is-official'}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{source ? sourceLabels[source] || 'Solution' : 'Solution'}</h3>
        {isAiGenerated && <span className="rounded bg-purple-200 px-2 py-1 text-xs font-semibold text-purple-950">AI</span>}
      </div>
      {shouldRenderMatrixSolution && answerItem && matrixSelections && (
        <MatrixSolutionGrid answerItem={answerItem} selections={matrixSelections} />
      )}
      {shouldRenderAnswerText && (
        <RichTextBlocks text={solution.answer} className="solution-answer" detectCode />
      )}
      {shouldRenderExplanation && (
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

function MatrixSolutionGrid({
  answerItem,
  selections,
}: {
  answerItem: AnswerItem;
  selections: Record<string, string>;
}) {
  const matrix = answerItem.matrix;
  const rowsSource = matrix?.rows;
  const columnsSource = matrix?.columns;
  const rows = Array.isArray(rowsSource) ? rowsSource : [];
  const columns = Array.isArray(columnsSource) ? columnsSource : getDisplayChoices(answerItem);

  if (!rows.length || !columns.length) {
    return null;
  }

  return (
    <div className="solution-matrix">
      <div className="matrix-choice__scroller">
        <div className="matrix-choice__grid" style={{ gridTemplateColumns: `minmax(110px, 160px) repeat(${columns.length}, minmax(140px, 1fr))` }}>
          <div className="matrix-choice__corner" />
          {columns.map((column) => (
            <div key={column} className="matrix-choice__header">
              {column}
            </div>
          ))}
          {rows.map((row) => (
            <Fragment key={row}>
              <div className="matrix-choice__row-label">
                {row}
              </div>
              {columns.map((column) => {
                const isSelected = selections[row] === column;
                return (
                  <div
                    key={`${row}-${column}`}
                    className={`matrix-choice__button is-readonly ${isSelected ? 'is-selected' : ''}`}
                    aria-label={`${row}: ${column}${isSelected ? ' selected' : ''}`}
                  >
                    <span />
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function getMatrixSolutionSelections(
  answerItem?: AnswerItem | null,
  solution?: ExamSolution | null,
  currentAnswer = '',
): Record<string, string> | null {
  if (!answerItem || answerItem.interaction_type !== 'matrix_choice') {
    return null;
  }

  const fromSolution = parseMatrixSelections(solution?.answer || '') || parseMatrixSelections(solution?.explanation || '');
  if (fromSolution && Object.keys(fromSolution).length > 0) {
    return fromSolution;
  }

  const fromCurrentAnswer = parseMatrixSelections(currentAnswer);
  if (fromCurrentAnswer && Object.keys(fromCurrentAnswer).length > 0) {
    return fromCurrentAnswer;
  }

  return inferGraphSearchMatrixSelections(answerItem);
}

function parseMatrixSelections(value: string): Record<string, string> | null {
  if (!value.trim()) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return null;
    }
    const selections: Record<string, string> = {};
    Object.keys(parsed).forEach((key) => {
      if (typeof parsed[key] === 'string') {
        selections[key] = parsed[key];
      }
    });
    return selections;
  } catch {
    return null;
  }
}

function inferGraphSearchMatrixSelections(answerItem: AnswerItem): Record<string, string> | null {
  const rowsSource = answerItem.matrix?.rows;
  const columnsSource = answerItem.matrix?.columns || answerItem.choices;
  const rows = Array.isArray(rowsSource) ? rowsSource : [];
  const columns = Array.isArray(columnsSource) ? columnsSource : [];
  if (!rows.length || !columns.length) {
    return null;
  }

  const expectedOrders: Record<string, string> = {
    dijkstra: 'A,B,C,D,E,G,F,H,I',
    bfs: 'A,B,D,C,F,E,G,H,I',
    dfs: 'A,B,C,F,E,D,G,H,I',
    prim: 'A,B,C,D,E,F,G,H,I',
  };
  const selections: Record<string, string> = {};

  rows.forEach((row) => {
    const key = normalizedAlgorithmKey(row);
    const expected = expectedOrders[key];
    if (!expected) {
      return;
    }
    const matchingColumn = columns.find((column) => normalizeOrder(column) === normalizeOrder(expected));
    if (matchingColumn) {
      selections[row] = matchingColumn;
    }
  });

  return Object.keys(selections).length === rows.length ? selections : null;
}

function normalizedAlgorithmKey(row: string): string {
  const normalized = row.toLowerCase();
  if (normalized.includes('dijkstra')) {
    return 'dijkstra';
  }
  if (normalized.includes('bfs')) {
    return 'bfs';
  }
  if (normalized.includes('dfs')) {
    return 'dfs';
  }
  if (normalized.includes('prim')) {
    return 'prim';
  }
  return normalized.replace(/[^a-z0-9]+/g, '');
}

function normalizeOrder(value: string): string {
  return value.replace(/\s+/g, '').replace(/,+$/g, '').toUpperCase();
}

export default SolutionBlock;

