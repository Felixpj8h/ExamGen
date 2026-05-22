import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => {
  delete global.fetch;
});

test('renders exam practice workspace from the exam bundle', async () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          exam: {
            title: 'Loaded Exam Bundle',
            course_code: 'MNF130',
            source_file: 'sample.pdf',
          },
          questions: [
            {
              id: 'q1',
              question_number: '1',
              question_text: 'What are these truth values?',
              page_start: 1,
              page_end: 1,
              topic: 'truth values',
              interaction_type: 'free_text',
              choices: [],
              subquestions: [
                {
                  id: 'q1a',
                  label: 'a',
                  text: 'P(orange).',
                  interaction_type: 'true_false',
                  choices: ['True', 'False'],
                  points: null,
                  solution: null,
                },
              ],
            },
            {
              id: 'q2',
              question_number: '2',
              question_text: 'Explain the argument error.',
              page_start: 2,
              page_end: 2,
              topic: 'logical errors',
              interaction_type: 'free_text',
              choices: [],
              subquestions: [],
              solution: {
                answer: null,
                explanation: 'Existential instantiation is used incorrectly.',
                grading_points: [],
                source: 'ai_generated',
              },
            },
          ],
          warnings: ['Loaded warning'],
        }),
    }),
  );

  render(<App />);
  expect(await screen.findByRole('heading', { name: /loaded exam bundle/i })).toBeInTheDocument();
  expect(screen.getByText(/loaded warning/i)).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: 'True' }).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole('button', { name: /question 2/i }));
  expect(screen.getByText('Answer')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /reveal solution/i }));
  expect(screen.getByText(/existential instantiation is used incorrectly/i)).toBeInTheDocument();
});
