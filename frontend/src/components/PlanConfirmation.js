import React from 'react';
import { Play, Trash2, X } from 'lucide-react';

const emptyPlanItem = {
  title: '',
  dimension: '',
  rationale: '',
  search_queries: [],
  expected_outcome: '',
  evidence_targets: [],
};

const splitList = (value) => value
  .split('\n')
  .map((item) => item.trim())
  .filter(Boolean);

const joinList = (value) => (Array.isArray(value) ? value.join('\n') : '');

// 可编辑的研究计划确认面板。
const PlanConfirmation = ({ plan, onChange, onConfirm, onCancel, isLoading = false }) => {
  if (!plan) return null;

  const updateItem = (index, updates) => {
    onChange({
      ...plan,
      plan_items: plan.plan_items.map((item, itemIndex) => (
        itemIndex === index ? { ...item, ...updates } : item
      )),
    });
  };

  const removeItem = (index) => {
    onChange({
      ...plan,
      plan_items: plan.plan_items.filter((_, itemIndex) => itemIndex !== index),
    });
  };

  const addItem = () => {
    onChange({
      ...plan,
      plan_items: [...plan.plan_items, { ...emptyPlanItem }],
    });
  };

  const confirmedItems = plan.plan_items.filter((item) => item.title.trim());

  return (
    <section
      className="mb-8 rounded-lg p-4"
      style={{ background: '#F5F8F2', border: '1px solid #E2E5DE' }}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black text-text-primary">研究计划</h2>
          <p className="mt-1 text-sm font-medium text-text-secondary">{plan.query}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={addItem}
            className="rounded-full border border-border-light bg-white px-4 py-2 text-sm font-semibold text-text-primary"
          >
            添加维度
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1.5 rounded-full border border-border-light bg-white px-4 py-2 text-sm font-semibold text-text-primary"
          >
            <X className="h-4 w-4" />
            取消
          </button>
          <button
            type="button"
            onClick={() => onConfirm(confirmedItems)}
            disabled={isLoading || confirmedItems.length === 0}
            className="inline-flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-accent-dark disabled:opacity-60"
          >
            <Play className="h-4 w-4" />
            执行计划
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {plan.plan_items.map((item, index) => (
          <div
            key={`${index}-${item.title}`}
            className="rounded-lg bg-white p-3"
            style={{ border: '1px solid #E2E5DE' }}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-sm font-black text-text-secondary">{index + 1}</span>
              <button
                type="button"
                aria-label="删除计划项"
                onClick={() => removeItem(index)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border-light text-text-secondary"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <PlanInput
                label="标题"
                value={item.title}
                onChange={(value) => updateItem(index, { title: value })}
              />
              <PlanInput
                label="维度"
                value={item.dimension}
                onChange={(value) => updateItem(index, { dimension: value })}
              />
              <PlanTextArea
                label="搜索语句"
                value={joinList(item.search_queries)}
                onChange={(value) => updateItem(index, { search_queries: splitList(value) })}
              />
              <PlanTextArea
                label="证据目标"
                value={joinList(item.evidence_targets)}
                onChange={(value) => updateItem(index, { evidence_targets: splitList(value) })}
              />
              <PlanTextArea
                label="拆分理由"
                value={item.rationale}
                onChange={(value) => updateItem(index, { rationale: value })}
              />
              <PlanTextArea
                label="预期产出"
                value={item.expected_outcome}
                onChange={(value) => updateItem(index, { expected_outcome: value })}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

const PlanInput = ({ label, value, onChange }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-semibold text-text-tertiary">{label}</span>
    <input
      value={value || ''}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-lg border border-border-light px-3 py-2 text-sm font-medium text-text-primary focus:outline-none"
    />
  </label>
);

const PlanTextArea = ({ label, value, onChange }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-semibold text-text-tertiary">{label}</span>
    <textarea
      value={value || ''}
      onChange={(event) => onChange(event.target.value)}
      rows={3}
      className="w-full resize-none rounded-lg border border-border-light px-3 py-2 text-sm font-medium text-text-primary focus:outline-none"
    />
  </label>
);

export default PlanConfirmation;
