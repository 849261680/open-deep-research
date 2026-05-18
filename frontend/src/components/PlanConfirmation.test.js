import { fireEvent, render, screen } from '@testing-library/react';
import PlanConfirmation from './PlanConfirmation';

const plan = {
  query: 'AI 产业趋势',
  plan_items: [
    {
      title: 'AI 产业采用率',
      dimension: '数据趋势',
      rationale: '需要量化趋势。',
      search_queries: ['AI adoption survey'],
      expected_outcome: '获得采用率数据。',
      evidence_targets: ['统计数据'],
    },
  ],
};

test('edits, deletes, and confirms plan items', () => {
  const handleChange = jest.fn();
  const handleConfirm = jest.fn();

  const { rerender } = render(
    <PlanConfirmation
      plan={plan}
      onChange={handleChange}
      onConfirm={handleConfirm}
      onCancel={jest.fn()}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: '编辑步骤 1' }));
  fireEvent.change(screen.getByLabelText('标题'), {
    target: { value: 'AI 企业采用率' },
  });
  expect(handleChange).toHaveBeenCalledWith({
    ...plan,
    plan_items: [
      {
        ...plan.plan_items[0],
        title: 'AI 企业采用率',
      },
    ],
  });

  const editedPlan = handleChange.mock.calls[0][0];
  rerender(
    <PlanConfirmation
      plan={editedPlan}
      onChange={handleChange}
      onConfirm={handleConfirm}
      onCancel={jest.fn()}
    />
  );
  fireEvent.click(screen.getByRole('button', { name: /确认计划并开始研究/ }));
  expect(handleConfirm).toHaveBeenCalledWith([
    expect.objectContaining({ title: 'AI 企业采用率' }),
  ]);

  fireEvent.click(screen.getByRole('button', { name: '删除计划项' }));
  expect(handleChange).toHaveBeenLastCalledWith({
    ...editedPlan,
    plan_items: [],
  });
});

test('presents the research plan as an agent execution contract', () => {
  render(
    <PlanConfirmation
      plan={plan}
      onChange={jest.fn()}
      onConfirm={jest.fn()}
      onCancel={jest.fn()}
    />
  );

  expect(screen.getByText('Agent Plan')).toBeInTheDocument();
  expect(screen.getByText('1 个研究维度')).toBeInTheDocument();
  expect(screen.getByText('1 条搜索查询')).toBeInTheDocument();
  expect(screen.getByText('1 个证据目标')).toBeInTheDocument();
  expect(screen.getByText('步骤 1')).toBeInTheDocument();
  expect(screen.getByText('数据趋势')).toBeInTheDocument();
  expect(screen.getByText('为什么要查')).toBeInTheDocument();
  expect(screen.getAllByText('需要量化趋势。').length).toBeGreaterThan(0);
  expect(screen.getByText('搜索查询')).toBeInTheDocument();
  expect(screen.getAllByText('AI adoption survey').length).toBeGreaterThan(0);
  expect(screen.getByText('预期证据')).toBeInTheDocument();
  expect(screen.getAllByText('统计数据').length).toBeGreaterThan(0);
  expect(screen.getAllByText('预期产出').length).toBeGreaterThan(0);
  expect(screen.getAllByText('获得采用率数据。').length).toBeGreaterThan(0);
  expect(screen.queryByLabelText('标题')).not.toBeInTheDocument();
});

test('opens one plan step for editing on demand', () => {
  render(
    <PlanConfirmation
      plan={plan}
      onChange={jest.fn()}
      onConfirm={jest.fn()}
      onCancel={jest.fn()}
    />
  );

  expect(screen.queryByLabelText('标题')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '编辑步骤 1' }));
  expect(screen.getByLabelText('标题')).toHaveValue('AI 产业采用率');
  expect(screen.getByLabelText('搜索语句')).toHaveValue('AI adoption survey');
});
