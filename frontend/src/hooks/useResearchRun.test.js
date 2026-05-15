import { act, renderHook, waitFor } from '@testing-library/react';
import { useResearchRun } from './useResearchRun';
import { researchAPI } from '../services/api';

jest.mock('../services/api', () => ({
  researchAPI: {
    startResearchStream: jest.fn(),
    resumeResearchStream: jest.fn(),
    startResearch: jest.fn(),
    getResearchTask: jest.fn(),
    stopResearch: jest.fn(),
  },
}));

const historyActions = () => ({
  addResearch: jest.fn(() => ({
    id: 'local-task',
    query: 'AI 趋势',
    status: 'in_progress',
    timestamp: '2026-05-15T00:00:00.000Z',
    isTemporaryId: true,
  })),
  updateResearch: jest.fn(),
  replaceResearchId: jest.fn(),
  setCurrentResearch: jest.fn(),
  onHistorySelection: jest.fn(),
});

const renderResearchRun = (props = {}) => {
  const actions = historyActions();
  const hook = renderHook((currentResearch) => useResearchRun({
    currentResearch,
    ...actions,
    ...props,
  }), {
    initialProps: props.currentResearch || null,
  });
  return { ...hook, actions };
};

beforeEach(() => {
  jest.clearAllMocks();
});

test('keeps active streaming task state outside history selection', async () => {
  let finishStream;
  researchAPI.startResearchStream.mockImplementation((_query, onUpdate) => {
    onUpdate({
      type: 'task_created',
      message: '研究任务已创建',
      data: { id: 'server-task', task_id: 'server-task' },
    });
    onUpdate({
      type: 'planning',
      message: '正在规划研究路径...',
      data: null,
    });
    return new Promise((resolve) => {
      finishStream = resolve;
    });
  });

  const { result, actions } = renderResearchRun();

  act(() => {
    void result.current.handleStartResearch('AI 趋势');
  });

  await waitFor(() => {
    expect(result.current.isResearching).toBe(true);
    expect(result.current.streamingData).toHaveLength(2);
  });
  expect(actions.replaceResearchId).toHaveBeenCalledWith('local-task', 'server-task');
  expect(result.current.streamingData[1].message).toBe('正在规划研究路径...');

  await act(async () => {
    finishStream();
  });
});

test('hydrates selected history detail from backend task data', async () => {
  researchAPI.getResearchTask.mockResolvedValue({
    id: 'completed-task',
    query: '量子计算',
    status: 'completed',
    final_report: '# 完成报告',
    sections: [
      {
        step: 1,
        title: '技术路线',
        description: '比较技术路线',
        search_queries: ['量子计算 技术路线'],
        expected_outcome: '形成对比',
        status: 'completed',
        analysis: '超导和离子阱路线均有进展。',
      },
    ],
    quality_summary: { unsupported_claim_count: 0 },
    claim_checks: [],
    completed_at: '2026-05-15T00:00:00.000Z',
  });
  const currentResearch = {
    id: 'completed-task',
    query: '量子计算',
    status: 'completed',
    timestamp: '2026-05-15T00:00:00.000Z',
  };

  const { result, actions } = renderResearchRun({ currentResearch });

  await waitFor(() => {
    expect(result.current.researchData?.report).toBe('# 完成报告');
  });
  expect(result.current.isResearching).toBe(false);
  expect(actions.updateResearch).toHaveBeenCalledWith('completed-task', {
    result: expect.objectContaining({
      report: '# 完成报告',
      plan: [expect.objectContaining({ title: '技术路线' })],
    }),
    status: 'completed',
  });
});

test('sets error state when the active stream reports failure', async () => {
  researchAPI.startResearchStream.mockImplementation((_query, onUpdate) => {
    onUpdate({
      type: 'error',
      message: '检索失败',
      data: null,
    });
    return Promise.resolve();
  });

  const { result, actions } = renderResearchRun();

  await act(async () => {
    await result.current.handleStartResearch('AI 风险');
  });

  expect(result.current.error).toBe('检索失败');
  expect(result.current.isResearching).toBe(false);
  expect(actions.updateResearch).toHaveBeenCalledWith('local-task', {
    status: 'failed',
    error: '检索失败',
  });
});
