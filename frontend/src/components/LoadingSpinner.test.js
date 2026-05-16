import { render, screen } from '@testing-library/react';
import LoadingSpinner from './LoadingSpinner';

test('renders loading title with animated dots and no helper text', () => {
  const { container } = render(<LoadingSpinner message="正在生成研究计划..." />);

  expect(screen.getByLabelText('正在生成研究计划...')).toBeInTheDocument();
  expect(screen.queryByText('通常需要 30–60 秒')).not.toBeInTheDocument();
  expect(container.querySelector('.loading-dots')).toBeInTheDocument();
  expect(container.querySelectorAll('.loading-dots span')).toHaveLength(3);
});
