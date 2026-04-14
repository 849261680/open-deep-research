import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, CheckCircle, ShieldCheck, ShieldAlert, Link2, FileSearch } from 'lucide-react';
import ResultHeader from './ResultHeader';
import CollapsibleSection from './CollapsibleSection';

/**
 * ResearchResults - 极简研究结果展示
 *
 * 显示最终的研究报告和研究过程
 */
const ResearchResults = ({ data }) => {
  const [activeTab, setActiveTab] = useState('report');

  const getVerificationBadge = (verification) => {
    if (!verification || typeof verification !== 'object') {
      return null;
    }

    if (verification.passed) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-1 text-xs font-medium text-success">
          <ShieldCheck className="h-3.5 w-3.5" />
          校验通过
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 px-2 py-1 text-xs font-medium text-warning">
        <ShieldAlert className="h-3.5 w-3.5" />
        需复核
      </span>
    );
  };

  const handleDownload = () => {
    // 创建 Markdown 文件下载
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
    { id: 'process', label: '研究过程', icon: CheckCircle }
  ];

  return (
    <div>
      {/* 头部 */}
      <ResultHeader
        query={data.query}
        timestamp={data.timestamp}
        status="completed"
        onDownload={handleDownload}
      />

      {/* Tab 导航 */}
      <div className="border-b border-border-light mb-lg">
        <nav className="flex gap-lg">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 pb-sm border-b-2 font-medium text-sm transition-all duration-fast ${
                  activeTab === tab.id
                    ? 'border-accent text-accent'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                <IconComponent className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* 内容区域 */}
      <div>
        {/* 研究报告 Tab */}
        {activeTab === 'report' && (
          <div className="markdown-content">
            <ReactMarkdown>{data.report}</ReactMarkdown>
          </div>
        )}

        {/* 研究过程 Tab */}
        {activeTab === 'process' && (
          <div className="space-y-lg">
            {/* 研究计划 */}
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-md">
                研究计划
              </h3>
              <div className="space-y-sm">
                {data.plan && data.plan.map((step, index) => (
                  <div key={index} className="flex items-start gap-3 p-sm bg-background-secondary rounded-md">
                    <div className="flex-shrink-0 w-6 h-6 bg-accent/10 text-accent rounded-full flex items-center justify-center text-sm font-medium">
                      {step.step}
                    </div>
                    <div className="flex-1">
                      <h5 className="font-medium text-text-primary">{step.title}</h5>
                      <p className="text-sm text-text-secondary mt-0.5">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 执行结果 */}
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-md">
                执行结果
              </h3>
              <div className="space-y-sm">
                {data.results && data.results.map((result, index) => (
                  <CollapsibleSection
                    key={index}
                    title={result.title}
                    icon={<CheckCircle className="w-4 h-4" />}
                    badge={result.status === 'completed' ? '已完成' : '进行中'}
                    defaultOpen={false}
                  >
                    <div className="text-sm text-text-secondary leading-relaxed">
                      {result.analysis || result.result || '暂无详细信息'}
                    </div>

                    {result.verification && (
                      <div className="mt-md rounded-md border border-border-light bg-background-secondary p-sm">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-text-primary">结果校验</span>
                            {getVerificationBadge(result.verification)}
                          </div>
                          {typeof result.verification.score === 'number' && (
                            <span className="text-xs text-text-secondary">
                              可信度 {(result.verification.score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>

                        {result.verification.summary && (
                          <p className="mt-xs text-xs text-text-secondary">
                            {result.verification.summary}
                          </p>
                        )}

                        {Array.isArray(result.verification.issues) && result.verification.issues.length > 0 && (
                          <div className="mt-sm">
                            <p className="text-xs font-medium text-text-secondary">需要关注</p>
                            <div className="mt-xs space-y-xs">
                              {result.verification.issues.map((issue, idx) => (
                                <p key={idx} className="text-xs text-warning">
                                  • {issue}
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {Array.isArray(result.citations) && result.citations.length > 0 && (
                      <div className="mt-md pt-md border-t border-border-light">
                        <div className="mb-xs flex items-center gap-2">
                          <Link2 className="h-4 w-4 text-text-secondary" />
                          <p className="text-xs font-medium text-text-secondary">
                            引用来源 ({result.citations.length})
                          </p>
                        </div>
                        <div className="space-y-xs">
                          {result.citations.slice(0, 5).map((citation, idx) => (
                            <a
                              key={idx}
                              href={citation.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block text-xs text-accent hover:text-accent-dark underline decoration-1 underline-offset-2 transition-colors duration-fast"
                            >
                              {citation.title || citation.link}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.compressed_evidence && (
                      <div className="mt-md pt-md border-t border-border-light">
                        <div className="mb-xs flex items-center gap-2">
                          <FileSearch className="h-4 w-4 text-text-secondary" />
                          <p className="text-xs font-medium text-text-secondary">证据压缩</p>
                        </div>
                        <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-background-secondary p-sm text-xs leading-relaxed text-text-secondary">
                          {result.compressed_evidence}
                        </pre>
                      </div>
                    )}

                    {/* 如果有搜索源，显示它们 */}
                    {result.search_sources && result.search_sources.length > 0 && (
                      <div className="mt-md pt-md border-t border-border-light">
                        <p className="text-xs font-medium text-text-secondary mb-xs">
                          信息源 ({result.search_sources.length}):
                        </p>
                        <div className="space-y-xs">
                          {result.search_sources.slice(0, 5).map((source, idx) => (
                            <a
                              key={idx}
                              href={source.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block text-xs text-accent hover:text-accent-dark underline decoration-1 underline-offset-2 transition-colors duration-fast"
                            >
                              {source.title || source.link}
                            </a>
                          ))}
                          {result.search_sources.length > 5 && (
                            <p className="text-xs text-text-tertiary">
                              还有 {result.search_sources.length - 5} 个信息源...
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </CollapsibleSection>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchResults;
