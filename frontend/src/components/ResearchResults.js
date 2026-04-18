import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
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

const ResearchResults = ({ data }) => {
  const [activeTab, setActiveTab] = useState('report');

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
        <div className="markdown-content">
          <ReactMarkdown>{data.report}</ReactMarkdown>
        </div>
      )}

      {activeTab === 'process' && (
        <div className="space-y-8">
          {/* Research plan */}
          {data.plan && data.plan.length > 0 && (
            <div>
              <h3
                className="text-text-primary mb-5"
                style={{ fontSize: '22px', fontWeight: 900, lineHeight: 0.9, letterSpacing: 'normal' }}
              >
                研究计划
              </h3>
              <div className="space-y-3">
                {data.plan.map((step, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-4 p-4 rounded-xl"
                    style={{ background: '#F5F8F2', boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}
                  >
                    <div
                      className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-black"
                      style={{ background: '#e2f6d5', color: '#163300' }}
                    >
                      {step.step}
                    </div>
                    <div className="flex-1">
                      <h5 className="text-text-primary font-semibold" style={{ fontSize: '15px' }}>{step.title}</h5>
                      <p className="text-sm text-text-secondary mt-0.5 font-normal">{step.description}</p>
                    </div>
                  </div>
                ))}
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
