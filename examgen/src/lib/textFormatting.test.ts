import { getDisplayChoices } from './textFormatting';
import type { AnswerItem } from '../types';

test('does not render standalone answer label when labelled option text exists', () => {
  const subquestion: AnswerItem = {
    id: 'q1a',
    label: 'a',
    text: 'What is the primary purpose of polymorphism in OOP?',
    interaction_type: 'multiple_choice',
    choices: [
      'A. To allow objects to be treated as instances of their parent class',
      'B. To restrict access to private class members',
      'C. To force all classes to have the same name',
      'D. To eliminate the need for constructors',
    ],
    solution: {
      answer: 'A',
      explanation: 'Polymorphism allows objects to be treated through a common superclass.',
      grading_points: [],
      source: 'ai_generated',
    },
  };

  expect(getDisplayChoices(subquestion)).toEqual([
    'A. To allow objects to be treated as instances of their parent class',
    'B. To restrict access to private class members',
    'C. To force all classes to have the same name',
    'D. To eliminate the need for constructors',
  ]);
});

test('removes duplicated standalone labels from multiple choice options', () => {
  const subquestion: AnswerItem = {
    id: 'q1a',
    label: 'a',
    text: 'What is the primary purpose of polymorphism in OOP?',
    interaction_type: 'multiple_choice',
    choices: [
      'A',
      'A. To allow objects to be treated as instances of their parent class',
      'B. To restrict access to private class members',
    ],
    solution: null,
  };

  expect(getDisplayChoices(subquestion)).toEqual([
    'A. To allow objects to be treated as instances of their parent class',
    'B. To restrict access to private class members',
  ]);
});
