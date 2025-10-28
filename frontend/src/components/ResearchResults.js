import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, CheckCircle } from 'lucide-react';
import ResultHeader from './ResultHeader';
import CollapsibleSection from './CollapsibleSection';

/**
 * ResearchResults - 极简研究结果展示
 *
 * 显示最终的研究报告和研究过程
 */
const ResearchResults = ({ data }) => {
  const [activeTab, setActiveTab] = useState('report');

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

  const handleShare = () => {
    // 复制报告到剪贴板
    if (navigator.clipboard) {
      navigator.clipboard.writeText(data.report).then(() => {
        alert('报告已复制到剪贴板');
      });
    } else {
      alert('您的浏览器不支持剪贴板功能');
    }
  };

  const handleRerun = () => {
    // 重新运行研究（可以通过父组件传递的回调实现）
    alert('重新运行功能即将上线');
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
        onShare={handleShare}
        onRerun={handleRerun}
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
