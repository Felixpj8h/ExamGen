import { Fragment } from 'react';
import { getDisplayChoices } from '../../lib/textFormatting';
import type { AnswerItem } from '../../types';

interface AnswerInputProps {
  subquestion: AnswerItem;
  value: string;
  onAnswer: (value: string) => void;
}

function AnswerInput({ subquestion, value, onAnswer }: AnswerInputProps) {
  if (subquestion.interaction_type === 'matrix_choice') {
    const matrix = subquestion.matrix;
    const matrixRows = matrix?.rows;
    const matrixColumns = matrix?.columns;
    const rows = Array.isArray(matrixRows) ? matrixRows : [];
    const columns = Array.isArray(matrixColumns) ? matrixColumns : getDisplayChoices(subquestion);
    const selections = parseMatrixAnswer(value);

    return (
      <div className="matrix-choice" role="group" aria-label="Select one option for each row">
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
                    <button
                      key={`${row}-${column}`}
                      type="button"
                      onClick={() => onAnswer(serializeMatrixAnswer({ ...selections, [row]: column }))}
                      className={`matrix-choice__button ${isSelected ? 'is-selected' : ''}`}
                      aria-pressed={isSelected}
                      aria-label={`${row}: ${column}`}
                    >
                      <span />
                    </button>
                  );
                })}
              </Fragment>
            ))}
          </div>
        </div>
      </div>
    );
  }

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

function parseMatrixAnswer(value: string): Record<string, string> {
  if (!value.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(value);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const selections: Record<string, string> = {};
    Object.keys(parsed).forEach((key) => {
      if (typeof parsed[key] === 'string') {
        selections[key] = parsed[key];
      }
    });
    return selections;
  } catch {
    return {};
  }
}

function serializeMatrixAnswer(value: Record<string, string>): string {
  return JSON.stringify(value);
}

export default AnswerInput;

