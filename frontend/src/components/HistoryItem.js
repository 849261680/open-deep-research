import React from 'react';
import { CheckCircle, Clock, XCircle, Pin, Trash2, RotateCcw } from 'lucide-react';
import { useHistory } from '../contexts/HistoryContext';

const HistoryItem = ({ research, isActive, onResume }) => {
  const { loadResearch, togglePin, deleteResearch } = useHistory();

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  const truncateQuery = (query, maxLength = 50) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  const statusConfig = {
    completed: { icon: CheckCircle, color: '#054d28' },
    failed: { icon: XCircle, color: '#d03238' },
    in_progress: { icon: Clock, color: '#ffd11a', pulse: true },
    pending: { icon: Clock, color: '#ffd11a', pulse: true },
  };

  const s = statusConfig[research.status] || { icon: Clock, color: '#868685' };
  const StatusIcon = s.icon;

  return (
    <div
      onClick={() => loadResearch(research.id)}
      className="group relative px-4 py-3 rounded-xl cursor-pointer transition-colors duration-fast"
      style={{
        background: isActive ? '#e2f6d5' : 'transparent',
        borderLeft: isActive ? '3px solid #e2f6d5' : '3px solid transparent',
      }}
      onMouseEnter={(e) => {
        if (!isActive) e.currentTarget.style.background = '#F5F8F2';
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.currentTarget.style.background = 'transparent';
      }}
    >
      {research.pinned && (
        <div className="absolute top-2 right-2">
          <Pin className="w-3 h-3" style={{ color: '#9fe870', fill: '#9fe870' }} />
        </div>
      )}

      <div className="flex items-start gap-2 mb-1">
        <StatusIcon
          className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${s.pulse ? 'animate-pulse' : ''}`}
          style={{ color: s.color }}
        />
        <p
          className="flex-1 min-w-0 break-words pr-4 text-text-primary"
          style={{ fontSize: '13px', fontWeight: 500, lineHeight: 1.4 }}
        >
          {truncateQuery(research.query)}
        </p>
      </div>

      <div
        className="ml-5 text-text-tertiary"
        style={{ fontSize: '11px', fontWeight: 400 }}
      >
        {formatTime(research.timestamp)}
      </div>

      {/* Hover actions */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden group-hover:flex gap-1">
        <button
          onClick={(e) => { e.stopPropagation(); togglePin(research.id); }}
          className="p-1.5 rounded-full hover:bg-background-secondary transition-colors duration-fast"
          title={research.pinned ? '取消固定' : '固定'}
        >
          <Pin
            className="w-3 h-3"
            style={{ color: research.pinned ? '#9fe870' : '#868685', fill: research.pinned ? '#9fe870' : 'none' }}
          />
        </button>
        {(research.status === 'failed' || research.status === 'in_progress') && (
          <button
            onClick={(e) => { e.stopPropagation(); if (onResume) onResume(research); }}
            className="p-1.5 rounded-full hover:bg-background-secondary transition-colors duration-fast"
            title="恢复研究"
          >
            <RotateCcw className="w-3 h-3 text-text-tertiary" />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm('确定要删除这条研究记录吗？')) deleteResearch(research.id);
          }}
          className="p-1.5 rounded-full hover:bg-red-50 transition-colors duration-fast"
          title="删除"
        >
          <Trash2 className="w-3 h-3 text-text-tertiary hover:text-error" />
        </button>
      </div>
    </div>
  );
};

export default HistoryItem;
