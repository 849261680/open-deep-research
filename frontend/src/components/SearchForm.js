import React, { useState } from 'react';
import { Search } from 'lucide-react';
import Button from './Button';

/**
 * SearchForm - 极简搜索表单
 *
 * 大尺寸输入框 + 按钮组合
 */
const SearchForm = ({ onSubmit, isLoading, disabled = false, initialValue = '' }) => {
  const [query, setQuery] = useState(initialValue);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading && !disabled) {
      onSubmit(query.trim());
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        {/* 搜索输入框 */}
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="开始你的研究..."
            disabled={isLoading || disabled}
            className="w-full px-md py-3 text-base border border-border-light rounded-md
              bg-background-primary text-text-primary placeholder-text-tertiary
              focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
              disabled:bg-background-tertiary disabled:cursor-not-allowed
              transition-all duration-fast"
          />
        </div>

        {/* 提交按钮 */}
        <Button
          type="submit"
          variant="primary"
          size="large"
          disabled={!query.trim() || isLoading || disabled}
          loading={isLoading}
          icon={!isLoading && <Search className="w-4 h-4" />}
        >
          {isLoading ? '研究中' : '搜索'}
        </Button>
      </div>

      {/* 提示文字 */}
      {!isLoading && (
        <p className="mt-2 text-xs text-text-tertiary">
          按 Enter 键提交，Shift + Enter 换行
        </p>
      )}
    </form>
  );
};

export default SearchForm;