import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Tailwind smoke-test heading', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /tailwind works/i })).toBeInTheDocument();
});
