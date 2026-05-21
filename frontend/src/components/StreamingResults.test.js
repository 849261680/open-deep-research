import { act, render, screen, within } from '@testing-library/react';
import StreamingResults from './StreamingResults';

const updates = [
  {
    type: 'task_created',
    message: '研究任务已创建',
    data: { status: 'planning' },
  },
  {
    type: 'planning',
    message: '正在规划研究路径...',
    data: null,
  },
  {
    type: 'plan',
    message: '规划完成，开始执行子查询',
    data: [
      { step: 1, title: '市场规模', description: '判断市场空间' },
      { step: 2, title: '竞争格局', description: '判断主要玩家' },
    ],
  },
  {
    type: 'step_start',
    message: '开始处理子查询 1',
    data: {
      step: 1,
      total: 2,
      query: '市场规模',
      title: '市场规模',
      queries: ['AI 市场规模 2026'],
    },
  },
];

test('current status follows the latest active research phase', () => {
  render(<StreamingResults updates={updates} />);

  const currentStatus = screen.getByText('当前状态').closest('div');

  expect(within(currentStatus).getByText('正在研究子查询')).toBeInTheDocument();
  expect(within(currentStatus).getByText('已完成 0/2，进行中 1')).toBeInTheDocument();
  expect(within(currentStatus).queryByText('研究任务已创建')).not.toBeInTheDocument();
  expect(screen.queryByText('研究任务已创建')).not.toBeInTheDocument();
});

test('current status expands total when deep research adds active queries', () => {
  render(
    <StreamingResults
      updates={[
        ...updates,
        {
          type: 'step_complete',
          message: '完成子查询：市场规模',
          data: {
            step: 1,
            title: '市场规模',
          },
        },
        {
          type: 'step_complete',
          message: '完成子查询：竞争格局',
          data: {
            step: 2,
            title: '竞争格局',
          },
        },
        {
          type: 'step_start',
          message: '开始处理子查询 101',
          data: {
            step: 101,
            total: 2,
            query: '海外市场规模',
            title: '海外市场规模',
          },
        },
        {
          type: 'step_start',
          message: '开始处理子查询 102',
          data: {
            step: 102,
            total: 2,
            query: '企业采购案例',
            title: '企业采购案例',
          },
        },
      ]}
    />
  );

  const currentStatus = screen.getByText('当前状态').closest('div');

  expect(within(currentStatus).getByText('正在并行研究 2 个子查询')).toBeInTheDocument();
  expect(within(currentStatus).getByText('已完成 2/4，进行中 2')).toBeInTheDocument();
  expect(within(currentStatus).queryByText('已完成 2/2，进行中 2')).not.toBeInTheDocument();
});

test('initial search result stays in planning status before sub-query plan exists', () => {
  render(
    <StreamingResults
      updates={[
        {
          type: 'task_created',
          message: '研究任务已创建',
          data: { status: 'planning' },
        },
        {
          type: 'planning',
          message: '正在进行初始搜索并规划子查询...',
          data: null,
        },
        {
          type: 'search_result',
          message: '已完成初始搜索，正在归纳研究线索...',
          data: {
            step: 0,
            query: '量子计算的最新发展和应用场景',
            queries: ['量子计算的最新发展和应用场景'],
            sources: [],
            domains: ['caict.ac.cn'],
          },
        },
      ]}
    />
  );

  const currentStatus = screen.getByText('当前状态').closest('div');

  expect(
    within(currentStatus).getByText('已完成初始搜索，正在归纳研究线索...')
  ).toBeInTheDocument();
  expect(within(currentStatus).queryByText('正在研究子查询')).not.toBeInTheDocument();
});

test('renders deep research decisions with recursion context and follow-up queries', () => {
  render(
    <StreamingResults
      updates={[
        ...updates,
        {
          type: 'deep_research_decision',
          message: '深挖判断：市场规模',
          data: {
            step: 1,
            query: '市场规模',
            depth: 2,
            parent_query: 'AI 行业研究',
            should_continue: true,
            reason: '现有证据缺少海外市场拆分。',
            evidence_gaps: ['缺少海外市场规模', '缺少企业采购案例'],
            follow_up_queries: ['AI 海外市场规模 2026', 'AI 企业采购案例'],
            stop_condition: '',
          },
        },
      ]}
    />
  );

  const currentStatus = screen.getByText('当前状态').closest('div');

  expect(within(currentStatus).getByText('发现证据缺口，继续深挖')).toBeInTheDocument();
  expect(within(currentStatus).getByText('深度 2 · 来源：AI 行业研究')).toBeInTheDocument();
  expect(within(currentStatus).getByText('AI 海外市场规模 2026')).toBeInTheDocument();
  expect(screen.getByText('证据缺口')).toBeInTheDocument();
  expect(screen.getByText('缺少海外市场规模')).toBeInTheDocument();
  expect(screen.getByText('后续追问')).toBeInTheDocument();
  expect(screen.getAllByText('AI 企业采购案例')).toHaveLength(2);
});

test('renders cost updates and keeps phase transition animation on the status card', () => {
  render(
    <StreamingResults
      updates={[
        ...updates,
        {
          type: 'cost_update',
          message: '成本统计已更新',
          data: {
            total_tokens: 12345,
            estimated_cost_usd: 0.42,
          },
        },
      ]}
    />
  );

  const currentStatusCard = screen.getByTestId('current-status-card');

  expect(currentStatusCard).toHaveClass('animate-fade-in');
  expect(within(currentStatusCard).getByText('成本：12,345 tokens · $0.4200')).toBeInTheDocument();
  expect(screen.getByText('成本统计')).toBeInTheDocument();
  expect(screen.getByText('12,345 tokens')).toBeInTheDocument();
  expect(screen.getByText('$0.4200')).toBeInTheDocument();
});

test('renders process metric updates in the live status', () => {
  render(
    <StreamingResults
      updates={[
        ...updates,
        {
          type: 'metrics_update',
          message: '研究指标已更新',
          data: {
            search_count: 4,
            read_count: 7,
            selected_source_count: 12,
            cited_source_count: 3,
            elapsed_seconds: 42.4,
            estimated_cost_usd: 0.0123,
          },
        },
      ]}
    />
  );

  const currentStatusCard = screen.getByTestId('current-status-card');

  expect(within(currentStatusCard).getByText('指标：搜索 4 · 阅读 7 · 引用 3 · 42 秒')).toBeInTheDocument();
  expect(screen.getByText('过程指标')).toBeInTheDocument();
  expect(screen.getByText('候选 12')).toBeInTheDocument();
  expect(screen.getByText('$0.0123')).toBeInTheDocument();
});

test('advances elapsed metric every second between backend updates', () => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2026-05-21T14:00:00.000Z'));

  try {
    render(
      <StreamingResults
        updates={[
          ...updates,
          {
            type: 'metrics_update',
            timestamp: '2026-05-21T14:00:00.000Z',
            message: '研究指标已更新',
            data: {
              search_count: 9,
              read_count: 22,
              selected_source_count: 22,
              cited_source_count: 15,
              elapsed_seconds: 39,
            },
          },
        ]}
      />
    );

    const currentStatusCard = screen.getByTestId('current-status-card');
    expect(within(currentStatusCard).getByText('指标：搜索 9 · 阅读 22 · 引用 15 · 39 秒')).toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(within(currentStatusCard).getByText('指标：搜索 9 · 阅读 22 · 引用 15 · 40 秒')).toBeInTheDocument();
  } finally {
    jest.useRealTimers();
  }
});
