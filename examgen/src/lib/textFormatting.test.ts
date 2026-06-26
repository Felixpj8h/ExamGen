import { getAnswerItems, getDisplayChoices } from './textFormatting';
import type { AnswerItem, ExamQuestion } from '../types';

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

test('collapses already-generated split multiple choice items into a matrix for display', () => {
  const question: ExamQuestion = {
    id: 'q7',
    question_number: '7',
    question_text: 'Which algorithm gives this traversal order?',
    topic: 'Graph Algorithms',
    interaction_type: 'free_text',
    choices: [],
    subquestions: [
      {
        id: 'q7_dijkstra',
        label: 'Dijkstra',
        text: 'Dijkstra',
        interaction_type: 'multiple_choice',
        choices: [
          'The specific order depends on the graph structure provided in the exam. Generally, BFS uses a FIFO queue, DFS uses a LIFO stack (or recursion), Dijkstra uses a priority queue based on path weights, and Prim uses a priority queue based on edge weights.',
          'A,B,C,D,E,F,G,H,I',
          'A,B,C,D,E,H,F,G,I',
          'A,B,C,E,F,D,G,H,I',
        ],
      },
      {
        id: 'q7_bfs',
        label: 'BFS',
        text: 'BFS',
        interaction_type: 'multiple_choice',
        choices: [
          'The specific order depends on the graph structure provided in the exam. Generally, BFS uses a FIFO queue, DFS uses a LIFO stack (or recursion), Dijkstra uses a priority queue based on path weights, and Prim uses a priority queue based on edge weights.',
          'A,B,C,D,E,F,G,H,I',
          'A,B,C,D,E,H,F,G,I',
          'A,B,C,E,F,D,G,H,I',
        ],
      },
      {
        id: 'q7_dfs',
        label: 'DFS',
        text: 'DFS',
        interaction_type: 'multiple_choice',
        choices: [
          'The specific order depends on the graph structure provided in the exam. Generally, BFS uses a FIFO queue, DFS uses a LIFO stack (or recursion), Dijkstra uses a priority queue based on path weights, and Prim uses a priority queue based on edge weights.',
          'A,B,C,D,E,F,G,H,I',
          'A,B,C,D,E,H,F,G,I',
          'A,B,C,E,F,D,G,H,I',
        ],
      },
      {
        id: 'q7_prim',
        label: 'Prim',
        text: 'Prim',
        interaction_type: 'multiple_choice',
        choices: [
          'The specific order depends on the graph structure provided in the exam. Generally, BFS uses a FIFO queue, DFS uses a LIFO stack (or recursion), Dijkstra uses a priority queue based on path weights, and Prim uses a priority queue based on edge weights.',
          'A,B,C,D,E,F,G,H,I',
          'A,B,C,D,E,H,F,G,I',
          'A,B,C,E,F,D,G,H,I',
        ],
      },
    ],
  };

  expect(getAnswerItems(question)).toEqual([
    {
      id: 'q7_dijkstra',
      label: 'answer',
      text: 'Which algorithm gives this traversal order?',
      points: null,
      interaction_type: 'matrix_choice',
      choices: ['A,B,C,D,E,F,G,H,I', 'A,B,C,D,E,H,F,G,I', 'A,B,C,E,F,D,G,H,I'],
      matrix: {
        rows: ['Dijkstra', 'BFS', 'DFS', 'Prim'],
        columns: ['A,B,C,D,E,F,G,H,I', 'A,B,C,D,E,H,F,G,I', 'A,B,C,E,F,D,G,H,I'],
      },
      solution: null,
    },
  ]);
});

test('keeps regular multiple choice question item unchanged', () => {
  const question: ExamQuestion = {
    id: 'q1',
    question_number: '1',
    question_text: 'What is polymorphism?',
    points: 2,
    interaction_type: 'multiple_choice',
    choices: ['Inheritance', 'Encapsulation'],
    subquestions: [],
    solution: null,
  };

  expect(getAnswerItems(question)).toEqual([
    {
      id: 'q1',
      label: 'answer',
      text: '',
      points: 2,
      interaction_type: 'multiple_choice',
      choices: ['Inheritance', 'Encapsulation'],
      solution: null,
    },
  ]);
});

test('keeps regular subquestion list unchanged', () => {
  const question: ExamQuestion = {
    id: 'q2',
    question_number: '2',
    question_text: 'Answer both parts.',
    subquestions: [
      {
        id: 'q2a',
        label: 'a',
        text: 'a) Which data structure supports FIFO removal?',
        interaction_type: 'multiple_choice',
        choices: ['Stack', 'Queue', 'Tree'],
      },
      {
        id: 'q2b',
        label: 'b',
        text: 'b) Which data structure supports LIFO removal?',
        interaction_type: 'multiple_choice',
        choices: ['Stack', 'Queue', 'Tree'],
      },
    ],
  };

  expect(getAnswerItems(question)).toEqual(question.subquestions);
});
