import { getDisplayChoices } from '../../lib/textFormatting';
import type { AnswerItem } from '../../types';

interface AnswerInputProps {
  subquestion: AnswerItem;
  value: string;
  onAnswer: (value: string) => void;
}

function AnswerInput({ subquestion, value, onAnswer }: AnswerInputProps) {
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

export default AnswerInput;

