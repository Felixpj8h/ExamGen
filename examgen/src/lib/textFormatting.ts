import type { AnswerItem, ExamQuestion } from '../types';

export function hasAnswer(value: unknown): boolean {
  return typeof value === 'string' && value.trim().length > 0;
}

export function getAnswerItems(question: ExamQuestion): AnswerItem[] {
  const subquestions = Array.isArray(question.subquestions) ? question.subquestions : [];
  if (subquestions.length > 0) {
    const collapsed = collapseSplitMultipleChoiceItems(question, subquestions);
    if (collapsed) {
      return [collapsed];
    }
    return subquestions;
  }

  const answerItem: AnswerItem = {
    id: question.id,
    label: 'answer',
    text: '',
    points: question.points,
    interaction_type: question.interaction_type,
    choices: Array.isArray(question.choices) ? question.choices : [],
    solution: question.solution || null,
  };
  if (question.matrix) {
    answerItem.matrix = question.matrix;
  }
  return [answerItem];
}

function collapseSplitMultipleChoiceItems(question: ExamQuestion, subquestions: AnswerItem[]): AnswerItem | null {
  const matrix = buildMatrixChoice(subquestions);
  if (!matrix) {
    return null;
  }

  const first = subquestions[0];
  return {
    id: first.id || question.id,
    label: 'answer',
    text: collapsedMultipleChoicePrompt(question),
    points: safeCollapsedPoints(subquestions),
    interaction_type: 'matrix_choice',
    choices: matrix.columns,
    matrix,
    solution: null,
  };
}

function buildMatrixChoice(subquestions: AnswerItem[]): { rows: string[]; columns: string[] } | null {
  if (!looksLikeSplitMultipleChoiceGroup(subquestions)) {
    return null;
  }

  const rows = sanitizeChoices(subquestions.map((subquestion) => subquestion.text || ''));
  const columns = commonMatrixColumns(subquestions);
  if (rows.length !== subquestions.length || columns.length < 2) {
    return null;
  }

  return { rows, columns };
}

function looksLikeSplitMultipleChoiceGroup(subquestions: AnswerItem[]): boolean {
  if (subquestions.length < 2 || subquestions.length > 6) {
    return false;
  }
  if (subquestions.some((subquestion) => subquestion.interaction_type !== 'multiple_choice')) {
    return false;
  }

  const optionTexts = subquestions.map((subquestion) => String(subquestion.text || '').trim());
  if (sanitizeChoices(optionTexts).length !== optionTexts.length) {
    return false;
  }
  if (optionTexts.some((text) => !looksLikeShortChoiceText(text))) {
    return false;
  }

  const choiceSets = subquestions.map((subquestion) => normalizedChoiceSet(subquestion.choices));
  if (choiceSets.some((choiceSet) => choiceSet.size < 2)) {
    return false;
  }

  const reference = choiceSets[0];
  return choiceSets.slice(1).every((choiceSet) => choiceSetsAreNearEqual(reference, choiceSet));
}

function commonMatrixColumns(subquestions: AnswerItem[]): string[] {
  const firstChoices = Array.isArray(subquestions[0]?.choices) ? subquestions[0].choices || [] : [];
  return sanitizeChoices(firstChoices)
    .filter((choice) => isMatrixColumnChoice(choice))
    .filter((choice) =>
      subquestions.every((subquestion) =>
        normalizedChoiceSet(subquestion.choices).has(normalizeChoice(choice)),
      ),
    );
}

function isMatrixColumnChoice(choice: string): boolean {
  const stripped = choice.trim();
  if (!stripped || looksLikeQuestionPrompt(stripped)) {
    return false;
  }
  if (stripped.length > 120) {
    return false;
  }
  if (/\b(generally|depends|specific|priority queue|fifo|lifo|recursion|exam|oppgaven|generelt)\b/i.test(stripped)) {
    return false;
  }
  const commaParts = stripped.split(',').map((part) => part.trim()).filter(Boolean);
  if (commaParts.length >= 3 && commaParts.every((part) => /^[A-Z]$/i.test(part))) {
    return true;
  }
  return commaParts.length >= 3 && commaParts.every((part) => /^[A-Z0-9 _-]{1,16}$/i.test(part));
}

function looksLikeShortChoiceText(text: string): boolean {
  const stripped = text.trim();
  if (!stripped || looksLikeQuestionPrompt(stripped)) {
    return false;
  }
  if (/^\(?[a-z]\)?[).]\s+/i.test(stripped)) {
    return false;
  }
  const words = stripped.match(/[\wæøåÆØÅ]+/g) || [];
  return words.length >= 1 && words.length <= 4 && stripped.length <= 40;
}

function normalizedChoiceSet(choices: unknown): Set<string> {
  if (!Array.isArray(choices)) {
    return new Set();
  }
  return new Set(
    choices
      .map((choice) => normalizeChoice(choice))
      .filter(Boolean),
  );
}

function choiceSetsAreNearEqual(first: Set<string>, second: Set<string>): boolean {
  let matchingChoices = 0;
  first.forEach((choice) => {
    if (second.has(choice)) {
      matchingChoices += 1;
    }
  });

  if (first.size === second.size && matchingChoices === first.size) {
    return true;
  }
  const smallerSize = Math.min(first.size, second.size);
  return smallerSize >= 3 && matchingChoices / smallerSize >= 0.8;
}

function collapsedMultipleChoicePrompt(question: ExamQuestion): string {
  return question.question_text?.trim() || question.context?.trim() || 'Answer';
}

function safeCollapsedPoints(items: AnswerItem[]): number | null {
  const points = items.map((subquestion) => subquestion.points).filter((point): point is number => typeof point === 'number');
  if (points.length === 1) {
    return points[0];
  }
  if (points.length === items.length) {
    return points.reduce((total, point) => total + point, 0);
  }
  return null;
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

