import React, { useState } from 'react';
import { XCircle, Zap } from 'lucide-react';
import Button from './Button';

/**
 * SearchForm - 极简搜索表单
 *
 * 大尺寸输入框 + 按钮组合
 */
const SearchForm = ({
  onSubmit,
  onStop,
  isLoading,
  disabled = false,
  initialValue = '',
}) => {
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
      <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        {/* 搜索输入框 */}
        <div className="relative flex-1 min-h-[48px]">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="输入你想研究的主题..."
            disabled={isLoading || disabled}
            className="h-full min-h-[48px] max-h-[48px] w-full resize-none overflow-hidden px-md py-3 text-base leading-6 border border-border-light rounded-md
              bg-background-primary text-text-primary placeholder:text-text-secondary
              focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
              disabled:bg-background-tertiary disabled:cursor-not-allowed
              transition-all duration-fast"
          />
        </div>

        {/* 提交按钮 */}
        <div className="flex items-stretch gap-2">
          <Button
            type="submit"
            variant="primary"
            size="medium"
            className="h-12 min-h-0 py-0"
            disabled={!query.trim() || isLoading || disabled}
            loading={isLoading}
            icon={!isLoading && <Zap className="w-4 h-4" />}
          >
            {isLoading ? '研究中' : '开始研究'}
          </Button>

          {isLoading && onStop && (
            <Button
              type="button"
              variant="secondary"
              size="medium"
              className="h-12 min-h-0 py-0"
              onClick={onStop}
              icon={<XCircle className="w-4 h-4" />}
            >
              停止
            </Button>
          )}
        </div>
      </div>
    </form>
  );
};

export default SearchForm;
