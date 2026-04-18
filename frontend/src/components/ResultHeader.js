import React from 'react';
import { Download, Clock, CheckCircle } from 'lucide-react';

const ResultHeader = ({ query, timestamp, status, onDownload }) => {
  const formatTimestamp = (ts) => {
    return new Date(ts).toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="pb-8 mb-8 border-b border-border-light">
      <div className="flex items-start justify-between gap-4 mb-4">
        <h1
          className="flex-1 text-text-primary text-balance"
          style={{ fontSize: 'clamp(24px, 4vw, 40px)', fontWeight: 900, lineHeight: 0.9, letterSpacing: 'normal' }}
        >
          {query}
        </h1>

        <div className="flex items-center gap-2 flex-shrink-0 mt-1">
          {status === 'completed' && (
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
              style={{ background: '#e2f6d5', color: '#163300' }}
            >
              <CheckCircle className="w-3.5 h-3.5" />
              已完成
            </span>
          )}
          <button
            onClick={onDownload}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-text-primary bg-background-secondary border border-border-light rounded-full btn-scale transition-transform duration-fast"
            title="下载报告"
          >
            <Download className="w-4 h-4" />
            下载
          </button>
        </div>
      </div>

      {timestamp && (
        <div className="flex items-center gap-1.5 text-text-tertiary">
          <Clock className="w-3.5 h-3.5" />
          <span style={{ fontSize: '13px', fontWeight: 400 }}>
            {formatTimestamp(timestamp)}
          </span>
        </div>
      )}
    </div>
  );
};

export default ResultHeader;
