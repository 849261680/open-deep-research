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
