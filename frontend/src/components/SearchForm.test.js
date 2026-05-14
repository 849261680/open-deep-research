import { fireEvent, render, screen } from '@testing-library/react';
import SearchForm from './SearchForm';

test('shows one stop button as the primary action while researching', () => {
  const handleStop = jest.fn();

  render(
    <SearchForm
      onSubmit={jest.fn()}
      onStop={handleStop}
      isLoading
      initialValue="AI 产业趋势"
    />
  );

  const stopButtons = screen.getAllByRole('button', { name: /停止/ });

  expect(stopButtons).toHaveLength(1);
  expect(screen.queryByRole('button', { name: /研究中/ })).not.toBeInTheDocument();

  fireEvent.click(stopButtons[0]);

  expect(handleStop).toHaveBeenCalledTimes(1);
});
