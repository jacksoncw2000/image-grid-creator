import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('axios', () => ({
  post: jest.fn(),
}));

test('renders the image grid tool', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /image grid creator/i })).toBeInTheDocument();
  expect(screen.getByText(/stretch squares/i)).toBeInTheDocument();
  expect(screen.getByText(/collage layout/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /create grid/i })).toBeDisabled();
});
