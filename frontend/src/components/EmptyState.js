import React, { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';
import Button from './Button';

/**
 * EmptyState - 空状态欢迎页面
 *
 * 显示在用户还没有进行任何搜索时
 * 提供示例问题卡片，引导用户开始使用
 */
const EmptyState = ({ onExampleClick }) => {
  const [query, setQuery] = useState('');
  // 示例问题
  const exampleQuestions = [
    {
      question: '量子计算的最新发展和应用场景',
      icon: <Sparkles className="w-4 h-4" />,
    },
    {
      question: '2024年人工智能技术趋势分析',
      icon: <Search className="w-4 h-4" />,
    },
    {
      question: '碳中和技术路径和全球进展',
      icon: <Sparkles className="w-4 h-4" />,
    },
    {
      question: '区块链在供应链管理中的应用',
      icon: <Search className="w-4 h-4" />,
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {/* 图标 */}
      <div className="mb-lg">
        <div className="w-16 h-16 bg-background-secondary rounded-2xl flex items-center justify-center">
          <Search className="w-8 h-8 text-text-secondary" />
        </div>
      </div>

      {/* 标题和描述 */}
      <h1 className="text-3xl font-bold text-text-primary mb-sm text-balance text-center">
        开始深度研究
      </h1>
      <p className="text-base text-text-secondary mb-lg text-center max-w-md">
        输入任何问题，获得专业的研究报告
      </p>

      {/* 搜索输入框 */}
      <div className="w-full max-w-2xl mb-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) {
              onExampleClick(query.trim());
            }
          }}
          className="flex gap-3"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (query.trim()) {
                    onExampleClick(query.trim());
                  }
                }
              }}
              placeholder="输入你想研究的主题..."
              className="w-full px-lg py-4 text-base border border-border-light rounded-lg
                bg-background-primary text-text-primary placeholder-text-tertiary
                focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
                transition-all duration-fast shadow-sm hover:shadow-md"
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            size="large"
            disabled={!query.trim()}
            icon={<Search className="w-4 h-4" />}
          >
            开始研究
          </Button>
        </form>
      </div>

      {/* 示例问题卡片 */}
      <div className="w-full max-w-2xl">
        <h2 className="text-sm font-medium text-text-secondary mb-md">
          试试这些问题
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {exampleQuestions.map((example, index) => (
            <button
              key={index}
              onClick={() => onExampleClick(example.question)}
              className="group flex items-start gap-3 p-md bg-background-secondary border border-border-light rounded-lg text-left hover:bg-background-tertiary hover:border-border-medium hover:shadow-sm transition-all duration-fast hover-lift"
            >
              <span className="text-text-secondary group-hover:text-accent transition-colors duration-fast flex-shrink-0 mt-0.5">
                {example.icon}
              </span>
              <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors duration-fast">
                {example.question}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EmptyState;
