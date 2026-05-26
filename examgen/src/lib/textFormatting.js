export function hasAnswer(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

export function getAnswerItems(question) {
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

export function formatLabel(label) {
  if (label === 'followup') {
    return 'Follow-up';
  }
  if (label === 'answer') {
    return 'Answer';
  }
  return label;
}

export function formatPages(question) {
  if (!question.page_start) {
    return 'unknown';
  }
  if (!question.page_end || question.page_start === question.page_end) {
    return question.page_start;
  }
  return `${question.page_start}-${question.page_end}`;
}

export function formatInteraction(type) {
  return String(type || 'free_text')
    .replaceAll('_', ' ')
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

export function formatDisplayText(text) {
  return String(text || '')
    .replace(/([∀∃][a-z])(?=[A-Z])/g, '$1 ')
    .replace(/(∃![a-z])(?=[A-Z])/g, '$1 ')
    .replace(/([∧∨→↔])(?=\S)/g, '$1 ')
    .replace(/(\S)([∧∨→↔])/g, '$1 $2')
    .replace(/\s+([),.;:?])/g, '$1')
    .replace(/([(])\s+/g, '$1');
}

export function getDisplayChoices(subquestion) {
  const choices = sanitizeChoices(Array.isArray(subquestion.choices) ? subquestion.choices : []);
  const answer = subquestion.solution?.answer;
  if (
    subquestion.interaction_type === 'multiple_choice' &&
    typeof answer === 'string' &&
    answer.trim() &&
    !choices.some((choice) => normalizeChoice(choice) === normalizeChoice(answer))
  ) {
    return sanitizeChoices([answer, ...choices], { keepFirst: true });
  }
  return choices;
}

function sanitizeChoices(choices, options = {}) {
  const sanitized = [];
  const seen = new Set();
  for (let index = 0; index < choices.length; index += 1) {
    const choice = String(choices[index] || '').trim();
    const normalized = normalizeChoice(choice);
    if (!choice || seen.has(normalized)) {
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

function normalizeChoice(choice) {
  return String(choice || '').trim().replace(/^["']|["']$/g, '').toLowerCase();
}

function looksLikeQuestionPrompt(choice) {
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

