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
  fireEvent.click(screen.getByRole('button', { name: /执行计划/ }));
  expect(handleConfirm).toHaveBeenCalledWith([
    expect.objectContaining({ title: 'AI 企业采用率' }),
  ]);

  fireEvent.click(screen.getByRole('button', { name: '删除计划项' }));
  expect(handleChange).toHaveBeenLastCalledWith({
    ...editedPlan,
    plan_items: [],
  });
});
