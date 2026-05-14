import { render, screen, within } from '@testing-library/react';
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
