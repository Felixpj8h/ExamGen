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
              context: 'Use the provided inference rule setup.\n\n```haskell\nmodule Shop where\ntype Money = Integer\n```\n\n```kotlin\nfun total(var amount: Int): Int\n```',
              page_start: 2,
              page_end: 2,
              topic: 'logical errors',
              interaction_type: 'free_text',
              choices: [],
              images: [
                {
                  id: 'page_2_img_1',
                  src: '/sample-assets/exam/page_2_img_1.png',
                  alt: 'Image from page 2',
                  page_number: 2,
                  width: 220,
                  height: 180,
                },
                {
                  id: 'page_2_img_2',
                  src: '/sample-assets/exam/page_2_img_2.png',
                  alt: 'Tiny icon from page 2',
                  page_number: 2,
                  width: 8,
                  height: 8,
                },
              ],
              subquestions: [],
              solution: {
                answer: null,
                explanation: 'Existential instantiation is used incorrectly.\n\npublic static void takeItem(int itemId, Map<Integer, Integer> inventory) { if (inventory.containsKey(itemId)) { int count = inventory.get(itemId); if (count > 1) inventory.put(itemId, count - 1); else inventory.remove(itemId); } }',
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
  expect(screen.getByText(/use the provided inference rule setup/i)).toBeInTheDocument();
  expect(screen.getByText('haskell')).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName.toLowerCase() === 'code' && element.textContent.includes('module Shop where'))).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName.toLowerCase() === 'code' && element.textContent.includes('type Money = Integer'))).toBeInTheDocument();
  expect(screen.getByText('kotlin')).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName.toLowerCase() === 'code' && element.textContent.includes('fun total'))).toBeInTheDocument();
  expect(screen.getByText('Answer')).toBeInTheDocument();
  expect(screen.getByRole('img', { name: /image from page 2/i })).toBeInTheDocument();
  expect(screen.queryByRole('img', { name: /tiny icon from page 2/i })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /reveal solution/i }));
  expect(screen.getByText(/existential instantiation is used incorrectly/i)).toBeInTheDocument();
  expect(screen.getByText('java')).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName.toLowerCase() === 'code' && element.textContent.includes('public static void takeItem'))).toBeInTheDocument();
});
