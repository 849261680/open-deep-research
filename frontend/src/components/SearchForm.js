import React, { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';

const SearchForm = ({ onSubmit, isLoading, disabled = false }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading && !disabled) {
      onSubmit(query.trim());
    }
  };

  const exampleQueries = [
    '人工智能在医疗领域的应用现状',
    '区块链技术的发展趋势',
    '新能源汽车市场分析',
    '量子计算的最新进展'
  ];

  const handleExampleClick = (example) => {
    setQuery(example);
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="请输入您想要研究的主题，例如：人工智能的发展趋势..."
            className="block w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-gray-900 placeholder-gray-500"
            disabled={isLoading || disabled}
          />
        </div>

        <button
          type="submit"
          disabled={!query.trim() || isLoading || disabled}
          className="w-full flex items-center justify-center space-x-2 bg-primary-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Sparkles className="h-5 w-5" />
          <span>{isLoading ? '研究中...' : '开始深度研究'}</span>
        </button>
      </form>

      <div className="mt-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">示例研究主题：</h3>
        <div className="flex flex-wrap gap-2">
          {exampleQueries.map((example, index) => (
            <button
              key={index}
              onClick={() => handleExampleClick(example)}
              disabled={isLoading || disabled}
              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchForm;