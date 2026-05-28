import type { AnswerItem, ExamQuestion } from '../types';

export function hasAnswer(value: unknown): boolean {
  return typeof value === 'string' && value.trim().length > 0;
}

export function getAnswerItems(question: ExamQuestion): AnswerItem[] {
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

export function formatLabel(label?: string | null): string {
  if (label === 'followup') {
    return 'Follow-up';
  }
  if (label === 'answer') {
    return 'Answer';
  }
  return label || '';
}

export function formatPages(question: ExamQuestion): string | number {
  if (!question.page_start) {
    return 'unknown';
  }
  if (!question.page_end || question.page_start === question.page_end) {
    return question.page_start;
  }
  return `${question.page_start}-${question.page_end}`;
}

export function formatInteraction(type?: string | null): string {
  return String(type || 'free_text')
    .replaceAll('_', ' ')
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

export function formatDisplayText(text: unknown): string {
  return String(text || '')
    .replace(/([∀∃][a-z])(?=[A-Z])/g, '$1 ')
    .replace(/(∃![a-z])(?=[A-Z])/g, '$1 ')
    .replace(/([∧∨→↔])(?=\S)/g, '$1 ')
    .replace(/(\S)([∧∨→↔])/g, '$1 $2')
    .replace(/\s+([),.;:?])/g, '$1')
    .replace(/([(])\s+/g, '$1');
}

export function getDisplayChoices(subquestion: AnswerItem): string[] {
  const choices = sanitizeChoices(Array.isArray(subquestion.choices) ? subquestion.choices : []);
  const answer = subquestion.solution?.answer;
  if (
    subquestion.interaction_type === 'multiple_choice' &&
    typeof answer === 'string' &&
    answer.trim() &&
    !choices.some((choice) => choicesMatchAnswer(choice, answer))
  ) {
    return sanitizeChoices([answer, ...choices], { keepFirst: true });
  }
  return choices;
}

interface SanitizeChoiceOptions {
  keepFirst?: boolean;
}

function sanitizeChoices(choices: unknown[], options: SanitizeChoiceOptions = {}): string[] {
  const rawChoices = choices.map((choice) => String(choice || '').trim()).filter(Boolean);
  const labelledOptions = new Set(
    rawChoices
      .map(getChoiceLabel)
      .filter((label): label is string => Boolean(label)),
  );
  const sanitized: string[] = [];
  const seen = new Set<string>();
  for (let index = 0; index < rawChoices.length; index += 1) {
    const choice = rawChoices[index];
    const normalized = normalizeChoice(choice);
    if (!choice || seen.has(normalized)) {
      continue;
    }
    if (!(options.keepFirst && index === 0) && isStandaloneChoiceLabel(choice, labelledOptions)) {
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

function normalizeChoice(choice: unknown): string {
  return String(choice || '').trim().replace(/^["']|["']$/g, '').toLowerCase();
}

function choicesMatchAnswer(choice: string, answer: string): boolean {
  const normalizedAnswer = normalizeChoice(answer);
  return normalizeChoice(choice) === normalizedAnswer || getChoiceLabel(choice)?.toLowerCase() === normalizedAnswer;
}

function getChoiceLabel(choice: string): string | null {
  const match = choice.trim().match(/^([A-Z])[\).:]\s+\S/i);
  return match ? match[1].toUpperCase() : null;
}

function isStandaloneChoiceLabel(choice: string, labelledOptions: Set<string>): boolean {
  return /^[A-Z]$/i.test(choice.trim()) && labelledOptions.has(choice.trim().toUpperCase());
}

function looksLikeQuestionPrompt(choice: string): boolean {
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

