import React from 'react';
import { FileText, Play, Search, Target, Trash2, X } from 'lucide-react';

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

// 统计计划字段数量，用于展示 Agent 执行契约摘要。
const countNestedItems = (items, field) => items.reduce((total, item) => {
  const value = item[field];
  return total + (Array.isArray(value) ? value.filter(Boolean).length : 0);
}, 0);

// 将可选文案规范成演示面板里的明确占位。
const displayText = (value, fallback) => {
  const text = String(value || '').trim();
  return text || fallback;
};

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
  const searchQueryCount = countNestedItems(plan.plan_items, 'search_queries');
  const evidenceTargetCount = countNestedItems(plan.plan_items, 'evidence_targets');

  return (
    <section
      className="mb-8 rounded-lg p-4"
      style={{ background: '#F5F8F2', border: '1px solid #D8DED1' }}
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex items-center rounded-full bg-white px-3 py-1 text-xs font-black uppercase text-text-tertiary">
            Agent Plan
          </div>
          <h2 className="text-lg font-black text-text-primary">研究计划</h2>
          <p className="mt-1 text-sm font-medium text-text-secondary">{plan.query}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-text-secondary">
            <PlanMetric label={`${plan.plan_items.length} 个研究维度`} />
            <PlanMetric label={`${searchQueryCount} 条搜索查询`} />
            <PlanMetric label={`${evidenceTargetCount} 个证据目标`} />
          </div>
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
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <span className="text-xs font-black uppercase text-text-tertiary">
                  步骤 {index + 1}
                </span>
                <h3 className="mt-1 text-base font-black text-text-primary">
                  {displayText(item.title, '未命名研究维度')}
                </h3>
                <p className="mt-1 text-sm font-semibold text-text-secondary">
                  {displayText(item.dimension, '待补充维度')}
                </p>
              </div>
              <button
                type="button"
                aria-label="删除计划项"
                onClick={() => removeItem(index)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border-light text-text-secondary"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <div className="mb-4 grid gap-2 md:grid-cols-2">
              <PlanSummary
                icon={FileText}
                label="为什么要查"
                items={[displayText(item.rationale, '待补充拆分理由')]}
              />
              <PlanSummary
                icon={Search}
                label="搜索查询"
                items={item.search_queries}
                fallback="待补充搜索查询"
              />
              <PlanSummary
                icon={Target}
                label="预期证据"
                items={item.evidence_targets}
                fallback="待补充证据目标"
              />
              <PlanSummary
                icon={FileText}
                label="预期产出"
                items={[displayText(item.expected_outcome, '待补充预期产出')]}
              />
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

const PlanMetric = ({ label }) => (
  <span className="rounded-full border border-border-light bg-white px-3 py-1">
    {label}
  </span>
);

// 展示单个计划步骤的只读摘要，同时保留下面的可编辑表单。
const PlanSummary = ({ icon: Icon, label, items, fallback = '' }) => {
  const visibleItems = Array.isArray(items) ? items.filter(Boolean) : [];
  const content = visibleItems.length > 0 ? visibleItems : [fallback];
  return (
    <div className="rounded-lg border border-border-light bg-background-secondary p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-black text-text-tertiary">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="space-y-1">
        {content.map((item, itemIndex) => (
          <p key={`${label}-${itemIndex}-${item}`} className="text-sm font-semibold text-text-primary">
            {item}
          </p>
        ))}
      </div>
    </div>
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
