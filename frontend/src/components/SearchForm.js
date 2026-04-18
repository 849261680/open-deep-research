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
          {isLoading && onStop && (
            <button
              type="button"
              onClick={onStop}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-text-primary bg-background-secondary border border-border-light rounded-full btn-scale transition-transform duration-fast"
            >
              <XCircle className="w-4 h-4" />
              停止
            </button>
          )}

          <button
            type="submit"
            disabled={!query.trim() || isLoading || disabled}
            className="flex items-center gap-1.5 px-5 py-2.5 text-sm font-semibold text-accent-dark bg-accent rounded-full btn-scale transition-transform duration-fast disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isLoading ? (
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {isLoading ? '研究中' : '开始研究'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default SearchForm;
