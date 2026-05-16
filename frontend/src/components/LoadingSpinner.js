import React from 'react';

const LoadingSpinner = ({ message = '处理中...' }) => {
  const trimmedMessage = message.replace(/[.…]+$/, '');
  const hasAnimatedDots = trimmedMessage !== message;

  return (
    <div className="flex flex-col items-center justify-center py-16">
      {/* Wise-green animated ring */}
      <div className="relative mb-8">
        <div
          className="w-16 h-16 rounded-full border-2 border-border-light animate-spin"
          style={{ borderTopColor: '#9fe870' }}
        />
        <div
          className="absolute inset-2 rounded-full flex items-center justify-center"
          style={{ background: '#e2f6d5' }}
        >
          <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5" stroke="#163300" strokeWidth="2" />
            <path d="M5.5 8.5L7 10L10.5 6" stroke="#163300" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      <p
        className="text-text-primary text-center"
        aria-label={message}
        style={{ fontSize: '18px', fontWeight: 600, lineHeight: 1.44 }}
      >
        {trimmedMessage}
        {hasAnimatedDots && (
          <span className="loading-dots" aria-hidden="true">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        )}
      </p>
    </div>
  );
};

export default LoadingSpinner;
