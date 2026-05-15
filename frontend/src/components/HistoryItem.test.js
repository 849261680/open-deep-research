import { render, screen } from '@testing-library/react';
import HistoryItem, { getResearchStatusLabel } from './HistoryItem';

jest.mock('../contexts/HistoryContext', () => ({
  useHistory: () => ({
    loadResearch: jest.fn(),
    togglePin: jest.fn(),
    deleteResearch: jest.fn(),
  }),
}));

// 构造历史记录，覆盖状态标签的最小可视化路径。
const historyRecord = (overrides) => ({
  id: 'task-1',
  query: '量子计算应用',
  status: 'in_progress',
  timestamp: '2026-05-15T00:00:00.000Z',
  ...overrides,
});

test('labels resumable, interrupted, and failed history states distinctly', () => {
  expect(getResearchStatusLabel(historyRecord({ status: 'in_progress' }))).toBe('可继续');
  expect(getResearchStatusLabel(historyRecord({
    status: 'failed',
    error: '研究已停止',
  }))).toBe('已中断');
  expect(getResearchStatusLabel(historyRecord({
    status: 'failed',
    error: '检索失败',
  }))).toBe('已失败');
});

test('renders the distinct history status label beside time', () => {
  render(
    <HistoryItem
      research={historyRecord({ status: 'failed', error: '研究已停止' })}
      isActive={false}
      onResume={jest.fn()}
    />
  );

  expect(screen.getByText(/已中断/)).toBeInTheDocument();
});
