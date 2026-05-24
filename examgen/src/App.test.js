import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
  window.localStorage.clear();
  window.history.pushState(null, '', '/');
});

const uploadedBundle = {
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
      context:
        'Use the provided inference rule setup.\n\ntype Env = [(String, Int)] data Expr = Lit Int | Var String\n\nlookupEnv :: String -> Env -> Maybe Int lookupEnv x [] = Nothing lookupEnv x ((y,v):rest) | x == y = Just v | otherwise = lookupEnv x rest\n\neval env expr = case expr of Lit n -> __________________________\n\n```kotlin\nfun total(var amount: Int): Int\n```',
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
        explanation:
          'Existential instantiation is used incorrectly.\n\npublic static void takeItem(int itemId, Map<Integer, Integer> inventory) { if (inventory.containsKey(itemId)) { int count = inventory.get(itemId); if (count > 1) inventory.put(itemId, count - 1); else inventory.remove(itemId); } }',
        grading_points: [],
        source: 'ai_generated',
      },
    },
  ],
  warnings: ['Loaded warning'],
};

test('renders the upload landing page first', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /exam generator/i })).toBeInTheDocument();
  expect(screen.getByText('EG')).toBeInTheDocument();
  expect(screen.getByLabelText(/exam pdf/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/solutions pdf/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /start/i })).toBeDisabled();
});

test('rejects non-pdf files in the upload flow', () => {
  render(<App />);

  const textFile = new File(['not a pdf'], 'notes.txt', { type: 'text/plain' });
  fireEvent.change(screen.getByLabelText(/exam pdf/i), {
    target: { files: [textFile] },
  });

  expect(screen.getByText(/only pdf files are supported/i)).toBeInTheDocument();
});

test('uploads files and connects to the existing mock exam workspace', async () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () =>
        Promise.resolve({
          exam_id: 'exam_123',
          status: 'ready',
          bundle: uploadedBundle,
        }),
    }),
  );

  render(<App />);

  const examFile = new File(['exam'], 'exam.pdf', { type: 'application/pdf' });
  const solutionsFile = new File(['solutions'], 'solutions.pdf', {
    type: 'application/pdf',
  });

  fireEvent.change(screen.getByLabelText(/exam pdf/i), {
    target: { files: [examFile] },
  });
  fireEvent.change(screen.getByLabelText(/solutions pdf/i), {
    target: { files: [solutionsFile] },
  });
  fireEvent.click(screen.getByRole('button', { name: /start/i }));

  expect(await screen.findByText(/generating your mock exam/i)).toBeInTheDocument();

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  const [url, options] = global.fetch.mock.calls[0];
  expect(url).toBe('/api/exams/process');
  expect(options.method).toBe('POST');
  expect(options.body.get('exam_pdf')).toBe(examFile);
  expect(options.body.get('solutions_pdf')).toBe(solutionsFile);
  expect(options.body.get('auto_generate_solutions')).toBe('false');

  expect(await screen.findByRole('heading', { name: /loaded exam bundle/i })).toBeInTheDocument();
  expect(window.location.hash).toBe('#mock-exam');
  expect(window.localStorage.getItem('exam-generator:last-bundle')).toContain('Loaded Exam Bundle');
  expect(screen.getByText(/generated exam exam_123/i)).toBeInTheDocument();
  expect(screen.getByText(/loaded warning/i)).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: 'True' }).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole('button', { name: /question 2/i }));
  expect(screen.getByText(/use the provided inference rule setup/i)).toBeInTheDocument();
  expect(screen.getByText('haskell')).toBeInTheDocument();
  expect(screen.getAllByText('haskell')).toHaveLength(1);
  expect(screen.getByText((_, element) => {
    if (element?.tagName.toLowerCase() !== 'code') {
      return false;
    }
    return element.textContent.includes('\n  = Lit Int\n  | Var String')
      && element.textContent.includes('lookupEnv :: String -> Env -> Maybe Int')
      && element.textContent.includes('eval env expr = case expr of');
  })).toBeInTheDocument();
  expect(screen.getByText('kotlin')).toBeInTheDocument();
  expect(screen.getByRole('img', { name: /image from page 2/i })).toHaveAttribute(
    'src',
    '/api/exams/exam_123/assets/exam/page_2_img_1.png',
  );
  expect(screen.queryByRole('img', { name: /tiny icon from page 2/i })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /reveal solution/i }));
  expect(screen.getByText(/existential instantiation is used incorrectly/i)).toBeInTheDocument();
  expect(screen.getByText('java')).toBeInTheDocument();
});

test('allows upload with only exam pdf when auto-generate solutions is enabled', async () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () =>
        Promise.resolve({
          exam_id: 'exam_ai',
          status: 'ready',
          bundle: uploadedBundle,
        }),
    }),
  );

  render(<App />);

  const examFile = new File(['exam'], 'exam.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getByLabelText(/exam pdf/i), {
    target: { files: [examFile] },
  });
  fireEvent.click(screen.getByRole('switch', { name: /auto-generate solutions/i }));
  fireEvent.click(screen.getByRole('button', { name: /start/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  const [, options] = global.fetch.mock.calls[0];
  expect(options.body.get('exam_pdf')).toBe(examFile);
  expect(options.body.get('solutions_pdf')).toBeNull();
  expect(options.body.get('auto_generate_solutions')).toBe('true');
});
