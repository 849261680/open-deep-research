import React, { useState } from 'react';
import { Zap, Search, Globe, Cpu, Leaf } from 'lucide-react';

const EmptyState = ({ onExampleClick }) => {
  const [query, setQuery] = useState('');

  const exampleQuestions = [
    {
      question: '量子计算的最新发展和应用场景',
      icon: <Cpu className="w-4 h-4" />,
    },
    {
      question: '2024年人工智能技术趋势分析',
      icon: <Zap className="w-4 h-4" />,
    },
    {
      question: '碳中和技术路径和全球进展',
      icon: <Leaf className="w-4 h-4" />,
    },
    {
      question: '区块链在供应链管理中的应用',
      icon: <Globe className="w-4 h-4" />,
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
      {/* Headline — billboard-scale */}
      <div className="text-center mb-10 max-w-3xl">
        <h1
          className="text-text-primary hero-headline"
          style={{
            fontSize: 'clamp(48px, 8vw, 96px)',
            fontWeight: 900,
            lineHeight: 0.9,
            letterSpacing: 'normal',
            fontFeatureSettings: '"calt"',
            textAlign: 'center',
          }}
        >
          <span className="hero-headline-line">深度研究，</span>
          <span className="hero-headline-line hero-headline-line--accent" style={{ color: '#9fe870' }}>无边界</span>
        </h1>
      </div>

      {/* Search bar */}
      <div className="w-full max-w-2xl mb-10">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) onExampleClick(query.trim());
          }}
        >
          <div
            className="flex items-center gap-3 p-2 bg-white rounded-full border border-border-light"
            style={{ boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px' }}
          >
            <Search className="w-5 h-5 text-text-tertiary ml-3 flex-shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (query.trim()) onExampleClick(query.trim());
                }
              }}
              placeholder="输入你想研究的主题..."
              className="flex-1 py-2.5 pr-2 bg-transparent text-base text-text-primary placeholder:text-text-tertiary focus:outline-none font-medium"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className="flex items-center gap-1.5 px-6 py-2.5 text-sm font-semibold text-accent-dark bg-accent rounded-full btn-scale transition-transform duration-fast disabled:opacity-100 disabled:cursor-not-allowed disabled:transform-none"
            >
              <Zap className="w-4 h-4" />
              开始研究
            </button>
          </div>
        </form>
      </div>

      {/* Example cards */}
      <div className="w-full max-w-2xl">
        <p
          className="text-text-tertiary mb-4 text-center"
          style={{ fontSize: '14px', fontWeight: 600, letterSpacing: '-0.084px' }}
        >
          试试这些问题
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {exampleQuestions.map((example, index) => (
            <button
              key={index}
              onClick={() => onExampleClick(example.question)}
              className="group flex items-start gap-3 p-4 bg-background-secondary border border-border-light rounded-xl text-left btn-scale transition-transform duration-fast hover:border-accent/60 hover:bg-accent-mint"
              style={{ boxShadow: 'rgba(14,15,12,0.08) 0px 0px 0px 1px' }}
            >
              <span className="text-text-tertiary group-hover:text-accent-dark transition-colors duration-fast flex-shrink-0 mt-0.5">
                {example.icon}
              </span>
              <span
                className="text-text-secondary group-hover:text-text-primary transition-colors duration-fast"
                style={{ fontSize: '15px', fontWeight: 500, lineHeight: 1.4 }}
              >
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
