import React, { useState } from 'react';
import { XCircle, Zap } from 'lucide-react';

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
      <div
        className="flex items-center gap-3 p-2 rounded-full border border-border-light bg-white"
        style={{ boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px' }}
      >
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="输入你想研究的主题..."
          disabled={isLoading || disabled}
          className="flex-1 min-h-[40px] max-h-[40px] resize-none overflow-hidden px-4 py-2.5 text-base leading-5 bg-transparent text-text-primary placeholder:text-text-tertiary focus:outline-none disabled:cursor-not-allowed font-medium"
        />

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            type={isLoading ? 'button' : 'submit'}
            onClick={isLoading ? onStop : undefined}
            disabled={isLoading ? !onStop : !query.trim() || disabled}
            className="flex items-center gap-1.5 px-5 py-2.5 text-sm font-semibold text-accent-dark bg-accent rounded-full btn-scale transition-transform duration-fast disabled:opacity-100 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isLoading ? (
              <XCircle className="w-4 h-4" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {isLoading ? '停止' : '开始研究'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default SearchForm;
