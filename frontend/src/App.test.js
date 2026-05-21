import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from './App';
import { researchAPI } from './services/api';

jest.mock('remark-gfm', () => 'remark-gfm-plugin');
jest.mock('react-markdown', () => ({ children }) => <div>{children}</div>);

jest.mock('./services/api', () => ({
  researchAPI: {
    healthCheck: jest.fn(),
    previewResearchPlan: jest.fn(),
    startResearchStream: jest.fn(),
    getResearchHistory: jest.fn(),
    getResearchTask: jest.fn(),
    stopResearch: jest.fn(),
  },
  authAPI: {
    getMe: jest.fn(),
    claimHistory: jest.fn(),
    googleLoginUrl: jest.fn(() => 'http://localhost:8003/api/auth/google/login'),
  },
  getGuestId: jest.fn(() => 'guest-id'),
}));

const completedHistoryItem = {
  id: 'completed-task',
  query: '已完成研究主题',
  result: {
    id: 'completed-task',
    query: '已完成研究主题',
    status: 'completed',
    report: '# 已完成报告',
    plan: [],
    results: [],
    timestamp: '2026-05-14T00:00:00.000Z',
  },
  status: 'completed',
  timestamp: '2026-05-14T00:00:00.000Z',
};

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
  researchAPI.healthCheck.mockResolvedValue({ status: 'healthy' });
  researchAPI.previewResearchPlan.mockResolvedValue({
    status: 'planned',
    data: {
      query: '正在运行研究主题',
      plan_items: [
        {
          step: 1,
          title: '正在运行研究主题',
          dimension: '核心问题',
          rationale: '保留原始问题。',
          search_queries: ['正在运行研究主题'],
          expected_outcome: '形成直接回答。',
          evidence_targets: ['综合资料'],
        },
      ],
    },
  });
  researchAPI.getResearchHistory.mockResolvedValue({});
  researchAPI.getResearchTask.mockResolvedValue(null);
  localStorage.setItem('research-history', JSON.stringify([completedHistoryItem]));
});

test('restores active stream updates after switching away and back', async () => {
  researchAPI.startResearchStream.mockImplementation((_query, onUpdate) => {
    onUpdate({
      type: 'task_created',
      message: '研究任务已创建',
      data: {
        id: 'server-task',
        task_id: 'server-task',
        status: 'planning',
      },
    });
    onUpdate({
      type: 'planning',
      message: '正在规划研究路径...',
      data: null,
    });
    return new Promise(() => {});
  });

  const { unmount } = render(<App />);

  await screen.findByText('已完成研究主题');

  fireEvent.change(screen.getByPlaceholderText('输入你想研究的主题...'), {
    target: { value: '正在运行研究主题' },
  });
  fireEvent.click(screen.getByRole('button', { name: /开始研究/ }));

  await screen.findByText('研究计划');
  expect(researchAPI.startResearchStream).not.toHaveBeenCalled();
  const planStartButtons = screen.getAllByRole('button', { name: /^开始研究$/ });
  fireEvent.click(planStartButtons[planStartButtons.length - 1]);

  await screen.findByText('当前状态');
  expect(researchAPI.startResearchStream.mock.calls[0][2].planItems[0].title)
    .toBe('正在运行研究主题');
  expect(screen.queryByText('正在进行深度研究...')).not.toBeInTheDocument();

  fireEvent.click(screen.getByText('已完成研究主题'));
  await screen.findByText(/已完成报告/);

  fireEvent.click(screen.getByText('正在运行研究主题'));

  await waitFor(() => {
    expect(screen.getByText('当前状态')).toBeInTheDocument();
  });
  const currentStatus = screen.getByText('当前状态').closest('div');
  expect(within(currentStatus).getByText('正在规划研究路径...')).toBeInTheDocument();
  expect(screen.queryByText('正在进行深度研究...')).not.toBeInTheDocument();
  unmount();
}, 15000);
