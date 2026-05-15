import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, CheckCircle, ShieldCheck, ShieldAlert, Link2, FileSearch } from 'lucide-react';
import ResultHeader from './ResultHeader';
import CollapsibleSection from './CollapsibleSection';

const MAX_META_ITEMS = 3;

const safeTrim = (value) => (typeof value === 'string' ? value.trim() : '');

const extractDisplayDomain = (value) => {
  const raw = safeTrim(value);
  if (!raw) return '';
  const candidates = raw.includes('://') ? [raw] : [`https://${raw}`, raw];
  for (const candidate of candidates) {
    try {
      const parsed = new URL(candidate);
      const host = parsed.hostname || parsed.host || '';
      if (!host) continue;
      return host.replace(/^www\./i, '').toLowerCase();
    } catch { continue; }
  }
  return '';
};

const getResultDomain = (result) => {
  const references = [
    ...(Array.isArray(result?.citations) ? result.citations : []),
    ...(Array.isArray(result?.search_sources) ? result.search_sources : []),
  ];
  for (const item of references) {
    const domain = extractDisplayDomain(item?.link || item?.url || item?.host);
    if (domain) return domain;
  }
  return '';
};

const getResultMetaItems = (result) => {
  const items = [];
  const domain = getResultDomain(result);
  if (domain) items.push({ key: 'domain', label: domain });
  return items.slice(0, MAX_META_ITEMS);
};

const getCitationDomain = (citation) =>
  extractDisplayDomain(citation?.link || citation?.url || citation?.host);

const getCitationDomains = (citations) => {
  const seen = new Set();
  const items = [];
  for (const citation of Array.isArray(citations) ? citations : []) {
    const domain = getCitationDomain(citation);
    if (!domain || seen.has(domain)) continue;
    seen.add(domain);
    items.push(domain);
  }
  return items;
};

const getPlanList = (value) => (Array.isArray(value) ? value.filter(Boolean) : []);
const INTERNAL_PLAN_DESCRIPTIONS = new Set(['GPT Researcher sub-query']);

const isInternalPlanText = (value) => INTERNAL_PLAN_DESCRIPTIONS.has(safeTrim(value));

const getQualitySummary = (data) => {
  const summary = data?.quality_summary;
  if (!summary || typeof summary !== 'object') return null;
  const claimCount = Number(summary.claim_count || 0);
  if (claimCount <= 0) return null;
  return {
    claimCount,
    supported: Number(summary.supported_claim_count || 0),
    partial: Number(summary.partially_supported_claim_count || 0),
    unsupported: Number(summary.unsupported_claim_count || 0),
    supportRate: Number(summary.citation_support_rate || 0),
  };
};

const getPlanDescription = (step) => {
  const rationale = safeTrim(step?.rationale);
  if (rationale && !isInternalPlanText(rationale)) return rationale;
  const description = safeTrim(step?.description);
  if (description && !isInternalPlanText(description)) return description;
  return '';
};

const buildPlanDisplayItems = (plan) => {
  const items = Array.isArray(plan) ? plan : [];
  const titleToLabel = new Map();
  const childCounts = new Map();

  items.forEach((step, index) => {
    if (Number(step?.depth || 1) > 1) return;
    const label = String(step?.step || index + 1);
    titleToLabel.set(step?.title, label);
  });

  return items.map((step, index) => {
    const depth = Number(step?.depth || 1);
    if (depth <= 1) {
      return { ...step, displayStep: String(step?.step || index + 1), isDeepStep: false };
    }

    const parentLabel = titleToLabel.get(step.parent_query) || deriveParentLabel(step.step);
    const nextChildIndex = (childCounts.get(parentLabel) || 0) + 1;
    childCounts.set(parentLabel, nextChildIndex);
    const childLabel = deriveChildLabel(step.step) || nextChildIndex;
    return {
      ...step,
      displayStep: `${parentLabel}.${childLabel}`,
      isDeepStep: true,
      parentLabel,
    };
  });
};

const deriveParentLabel = (step) => {
  if (typeof step !== 'number' || step < 100) return '深挖';
  return String(Math.floor(step / 100));
};

const deriveChildLabel = (step) => {
  if (typeof step !== 'number' || step < 100) return null;
  const child = step % 100;
  return child > 0 ? child : null;
};

const DomainBadge = ({ domain, compact = false }) => {
  if (!domain) return null;
  return (
    <span
      className="inline-flex max-w-full items-center text-text-secondary"
      style={{
        borderRadius: '9999px',
        border: '1px solid #E2E5DE',
        background: '#F5F8F2',
        padding: compact ? '2px 8px' : '4px 10px',
        fontSize: compact ? '11px' : '12px',
        fontWeight: 500,
      }}
      title={domain}
    >
      <span className="truncate">{domain}</span>
    </span>
  );
};

const PlanPills = ({ items }) => {
  const visibleItems = getPlanList(items);
  if (visibleItems.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {visibleItems.map((item, index) => (
        <span
          key={`${item}-${index}`}
          className="inline-flex max-w-full items-center text-text-secondary"
          style={{
            borderRadius: '9999px',
            border: '1px solid #E2E5DE',
            background: '#FFFFFF',
            padding: '3px 9px',
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          <span className="truncate">{item}</span>
        </span>
      ))}
    </div>
  );
};

const QueryList = ({ items }) => {
  const visibleItems = getPlanList(items);
  if (visibleItems.length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {visibleItems.map((item, index) => (
        <p
          key={`${item}-${index}`}
          className="text-xs text-text-secondary font-normal"
          style={{
            borderRadius: '8px',
            border: '1px solid #E2E5DE',
            background: '#FFFFFF',
            padding: '7px 10px',
            lineHeight: 1.35,
            overflowWrap: 'anywhere',
          }}
        >
          {item}
        </p>
      ))}
    </div>
  );
};

const PlanDetail = ({ label, children, show = true }) => {
  if (!show) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold text-text-tertiary">{label}</p>
      {children}
    </div>
  );
};

const DeepResearchRecord = ({ step }) => {
  const evidenceGaps = getPlanList(step.evidence_gaps);
  const followUpQueries = getPlanList(step.follow_up_queries);
  const hasRecord = step.deep_research_reason || step.deep_research_stop_condition || evidenceGaps.length > 0 || followUpQueries.length > 0;
  if (!hasRecord) return null;
  return (
    <PlanDetail label="深挖记录">
      {step.deep_research_reason && (
        <p className="mt-1 text-xs text-text-secondary font-normal">
          {step.deep_research_reason}
        </p>
      )}
      {evidenceGaps.length > 0 && <PlanPills items={evidenceGaps} />}
      {followUpQueries.length > 0 && <PlanPills items={followUpQueries} />}
      {step.deep_research_stop_condition && (
        <p className="mt-2 text-xs text-text-tertiary font-normal">
          {step.deep_research_stop_condition}
        </p>
      )}
    </PlanDetail>
  );
};

const ClaimQualitySummary = ({ summary }) => {
  if (!summary) return null;
  const hasUnsupported = summary.unsupported > 0;
  const Icon = hasUnsupported ? ShieldAlert : ShieldCheck;
  return (
    <div
      className="mb-6 rounded-lg p-4"
      style={{ background: '#F5F8F2', boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon
            className="h-4 w-4"
            style={{ color: hasUnsupported ? '#b8960a' : '#054d28' }}
          />
          <span className="text-sm font-semibold text-text-primary">引用质量摘要</span>
        </div>
        <span className="text-xs text-text-secondary font-medium">
          支撑率 {(summary.supportRate * 100).toFixed(0)}%
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <QualityMetric label="关键断言" value={summary.claimCount} />
        <QualityMetric label="已支撑" value={summary.supported} />
        <QualityMetric label="部分支撑" value={summary.partial} />
        <QualityMetric label="未支撑" value={summary.unsupported} warning={hasUnsupported} />
      </div>
    </div>
  );
};

const QualityMetric = ({ label, value, warning = false }) => (
  <div
    className="rounded-lg px-3 py-2"
    style={{ background: '#FFFFFF', border: '1px solid #E2E5DE' }}
  >
    <p className="text-xs font-semibold text-text-tertiary">{label}</p>
    <p
      className="mt-1 text-base font-black"
      style={{ color: warning ? '#b8960a' : '#0e0f0c' }}
    >
      {value}
    </p>
  </div>
);

const ResearchResults = ({ data }) => {
  const [activeTab, setActiveTab] = useState('report');
  const planItems = buildPlanDisplayItems(data.plan);
  const qualitySummary = getQualitySummary(data);

  const getVerificationBadge = (verification) => {
    if (!verification || typeof verification !== 'object') return null;
    if (verification.passed) return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ background: '#e2f6d5', color: '#054d28' }}>
        <ShieldCheck className="h-3.5 w-3.5" /> 校验通过
      </span>
    );
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ background: '#FFF9E0', color: '#b8960a' }}>
        <ShieldAlert className="h-3.5 w-3.5" /> 需复核
      </span>
    );
  };

  const handleDownload = () => {
    const blob = new Blob([data.report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `研究报告-${data.query}-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: 'report', label: '研究报告', icon: FileText },
    { id: 'process', label: '研究过程', icon: CheckCircle },
  ];

  return (
    <div>
      <ResultHeader
        query={data.query}
        timestamp={data.timestamp}
        status="completed"
        onDownload={handleDownload}
      />

      {/* Tab nav */}
      <div className="flex gap-1 mb-8 p-1 rounded-full w-fit" style={{ background: '#F5F8F2', boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}>
        {tabs.map((tab) => {
          const IconComponent = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-5 py-2 rounded-full transition-all duration-fast btn-scale"
              style={{
                fontSize: '14px',
                fontWeight: 600,
                background: isActive ? '#FFFFFF' : 'transparent',
                color: isActive ? '#0e0f0c' : '#868685',
                boxShadow: isActive ? 'rgba(14,15,12,0.12) 0px 0px 0px 1px' : 'none',
              }}
            >
              <IconComponent className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {activeTab === 'report' && (
        <>
          <ClaimQualitySummary summary={qualitySummary} />
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.report}</ReactMarkdown>
          </div>
        </>
      )}

      {activeTab === 'process' && (
        <div className="space-y-8">
          {/* Research plan */}
          {planItems.length > 0 && (
            <div>
              <h3
                className="text-text-primary mb-5"
                style={{ fontSize: '22px', fontWeight: 900, lineHeight: 0.9, letterSpacing: 'normal' }}
              >
                研究计划
              </h3>
              <div className="space-y-3">
                {planItems.map((step, index) => {
                  const description = getPlanDescription(step);
                  const searchQueries = getPlanList(step.search_queries);
                  const evidenceTargets = getPlanList(step.evidence_targets);
                  const expectedOutcome = safeTrim(step.expected_outcome);
                  return (
                  <div
                    key={index}
                    className={`flex items-start gap-4 rounded-xl ${step.isDeepStep ? 'p-3.5' : 'p-4'}`}
                    style={{ background: '#F5F8F2', boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}
                  >
                    <div
                      className="flex-shrink-0 rounded-full flex items-center justify-center text-sm font-black"
                      style={{ background: '#e2f6d5', color: '#163300' }}
                    >
                      <span
                        className="flex items-center justify-center"
                        style={{
                          minWidth: step.isDeepStep ? '38px' : '32px',
                          height: '32px',
                          padding: step.isDeepStep ? '0 8px' : 0,
                        }}
                      >
                        {step.displayStep}
                      </span>
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h5 className="text-text-primary font-semibold" style={{ fontSize: '15px' }}>{step.title}</h5>
                        {step.isDeepStep && (
                          <span
                            className="rounded-full px-2.5 py-1 text-xs font-semibold"
                            style={{ background: '#FFFFFF', color: '#5f665c', boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px' }}
                          >
                            深挖查询
                          </span>
                        )}
                        {step.dimension && (
                          <span
                            className="rounded-full px-2.5 py-1 text-xs font-semibold"
                            style={{ background: '#e2f6d5', color: '#054d28' }}
                          >
                            {step.dimension}
                          </span>
                        )}
                      </div>
                      {step.isDeepStep && step.parent_query && (
                        <p className="text-xs text-text-tertiary mt-1 font-normal">
                          来自：{step.parent_query}
                        </p>
                      )}
                      {description && (
                        <p className="text-sm text-text-secondary mt-1 font-normal">
                          {description}
                        </p>
                      )}
                      <PlanDetail label="搜索策略" show={searchQueries.length > 0}>
                        <QueryList items={searchQueries} />
                      </PlanDetail>
                      <PlanDetail label="预期产出" show={Boolean(expectedOutcome)}>
                        <p className="mt-1 text-xs text-text-secondary font-normal">
                          {expectedOutcome}
                        </p>
                      </PlanDetail>
                      <PlanDetail label="证据目标" show={evidenceTargets.length > 0}>
                        <PlanPills items={evidenceTargets} />
                      </PlanDetail>
                      <DeepResearchRecord step={step} />
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Execution results */}
          {data.results && data.results.length > 0 && (
            <div>
              <h3
                className="text-text-primary mb-5"
                style={{ fontSize: '22px', fontWeight: 900, lineHeight: 0.9, letterSpacing: 'normal' }}
              >
                执行结果
              </h3>
              <div className="space-y-3">
                {data.results.map((result, index) => {
                  const metaItems = getResultMetaItems(result);
                  const citationDomains = getCitationDomains(result.citations);

                  return (
                    <CollapsibleSection
                      key={index}
                      title={result.title}
                      headerMeta={
                        metaItems.length > 0 ? (
                          <div className="flex flex-wrap items-center gap-1.5">
                            {metaItems.map((item) => (
                              <DomainBadge key={item.key} domain={item.label} compact />
                            ))}
                          </div>
                        ) : null
                      }
                      icon={<CheckCircle className="w-4 h-4" />}
                      badge={result.status === 'completed' ? '已完成' : '进行中'}
                      defaultOpen={false}
                    >
                      <div
                        className="text-text-secondary leading-relaxed"
                        style={{ fontSize: '14px', fontWeight: 400 }}
                      >
                        {result.analysis || result.result || '暂无详细信息'}
                      </div>

                      {result.verification && (
                        <div
                          className="mt-5 rounded-xl p-4"
                          style={{ background: '#F5F8F2', boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-text-primary">结果校验</span>
                              {getVerificationBadge(result.verification)}
                            </div>
                            {typeof result.verification.score === 'number' && (
                              <span className="text-xs text-text-secondary font-medium">
                                可信度 {(result.verification.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {result.verification.summary && (
                            <p className="mt-2 text-xs text-text-secondary font-normal">{result.verification.summary}</p>
                          )}
                          {Array.isArray(result.verification.issues) && result.verification.issues.length > 0 && (
                            <div className="mt-3">
                              <p className="text-xs font-semibold text-text-secondary">需要关注</p>
                              <div className="mt-1 space-y-1">
                                {result.verification.issues.map((issue, idx) => (
                                  <p key={idx} className="text-xs font-normal" style={{ color: '#b8960a' }}>• {issue}</p>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {Array.isArray(result.citations) && result.citations.length > 0 && (
                        <div className="mt-5 pt-5 border-t border-border-light">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <Link2 className="h-4 w-4 text-text-secondary" />
                            <p className="text-xs font-semibold text-text-secondary">
                              引用来源 ({result.citations.length})
                            </p>
                            {citationDomains.slice(0, 3).map((domain) => (
                              <DomainBadge key={domain} domain={domain} compact />
                            ))}
                          </div>
                          <div className="space-y-2">
                            {result.citations.slice(0, 5).map((citation, idx) => (
                              <a
                                key={idx}
                                href={citation.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex min-w-0 items-center gap-3 px-4 py-3 transition-all duration-fast"
                                style={{
                                  borderRadius: '12px',
                                  border: '1px solid #E2E5DE',
                                  background: '#F5F8F2',
                                  textDecoration: 'none',
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#9fe870'; e.currentTarget.style.background = '#e2f6d5'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E2E5DE'; e.currentTarget.style.background = '#F5F8F2'; }}
                              >
                                <div className="min-w-0 flex-1">
                                  <p
                                    className="truncate"
                                    style={{ fontSize: '13px', fontWeight: 600, color: '#163300', textDecoration: 'underline', textUnderlineOffset: '2px', textDecorationThickness: '1px' }}
                                  >
                                    {citation.title || citation.link}
                                  </p>
                                </div>
                                <div className="max-w-[10rem] shrink-0">
                                  <DomainBadge domain={getCitationDomain(citation)} compact />
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.compressed_evidence && (
                        <div className="mt-5 pt-5 border-t border-border-light">
                          <div className="mb-2 flex items-center gap-2">
                            <FileSearch className="h-4 w-4 text-text-secondary" />
                            <p className="text-xs font-semibold text-text-secondary">证据压缩</p>
                          </div>
                          <pre
                            className="overflow-x-auto whitespace-pre-wrap p-4 text-xs leading-relaxed text-text-secondary font-normal"
                            style={{ borderRadius: '12px', background: '#F5F8F2' }}
                          >
                            {result.compressed_evidence}
                          </pre>
                        </div>
                      )}

                      {result.search_sources && result.search_sources.length > 0 && (
                        <div className="mt-5 pt-5 border-t border-border-light">
                          <p className="text-xs font-semibold text-text-secondary mb-2">
                            信息源 ({result.search_sources.length})
                          </p>
                          <div className="space-y-1.5">
                            {result.search_sources.slice(0, 5).map((source, idx) => (
                              <a
                                key={idx}
                                href={source.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block transition-colors duration-fast"
                                style={{ fontSize: '13px', fontWeight: 600, color: '#163300', textDecoration: 'underline', textUnderlineOffset: '2px' }}
                              >
                                {source.title || source.link}
                              </a>
                            ))}
                            {result.search_sources.length > 5 && (
                              <p className="text-xs text-text-tertiary font-normal">
                                还有 {result.search_sources.length - 5} 个信息源...
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </CollapsibleSection>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResearchResults;
