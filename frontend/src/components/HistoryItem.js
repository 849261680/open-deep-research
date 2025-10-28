import React from 'react';
import { CheckCircle, Clock, XCircle, Pin, Trash2 } from 'lucide-react';
import { useHistory } from '../contexts/HistoryContext';

/**
 * HistoryItem - 单个历史记录项组件
 *
 * 显示研究查询、状态、时间戳
 * 支持点击加载、固定、删除操作
 */
const HistoryItem = ({ research, isActive }) => {
  const { loadResearch, togglePin, deleteResearch } = useHistory();

  // 格式化时间
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

  // 截取查询文本
  const truncateQuery = (query, maxLength = 50) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  // 状态图标
  const StatusIcon = () => {
    switch (research.status) {
      case 'completed':
        return <CheckCircle className="w-3.5 h-3.5 text-success" />;
      case 'failed':
        return <XCircle className="w-3.5 h-3.5 text-error" />;
      case 'pending':
      case 'in_progress':
        return <Clock className="w-3.5 h-3.5 text-warning animate-pulse" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-text-tertiary" />;
    }
  };

  // 点击加载研究
  const handleClick = () => {
    loadResearch(research.id);
  };

  // 点击固定/取消固定
  const handlePin = (e) => {
    e.stopPropagation();
    togglePin(research.id);
  };

  // 点击删除
  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这条研究记录吗？')) {
      deleteResearch(research.id);
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`
        group relative px-md py-sm rounded-md cursor-pointer
        transition-all duration-fast
        ${isActive
          ? 'bg-background-tertiary border-l-2 border-accent'
          : 'hover:bg-background-tertiary border-l-2 border-transparent'
        }
      `}
    >
      {/* 固定图标（左上角） */}
      {research.pinned && (
        <div className="absolute top-1 right-1">
          <Pin className="w-3 h-3 text-accent fill-accent" />
        </div>
      )}

      {/* 查询文本 */}
      <div className="flex items-start gap-2 mb-1">
        <div className="flex-shrink-0 mt-0.5">
          <StatusIcon />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-text-primary font-medium leading-snug break-words pr-4">
            {truncateQuery(research.query)}
          </p>
        </div>
      </div>

      {/* 时间戳 */}
      <div className="ml-5 text-xs text-text-tertiary">
        {formatTime(research.timestamp)}
      </div>

      {/* 悬停操作按钮 */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden group-hover:flex gap-1">
        <button
          onClick={handlePin}
          className="p-1 rounded hover:bg-background-secondary transition-colors duration-fast"
          title={research.pinned ? '取消固定' : '固定'}
        >
          <Pin className={`w-3.5 h-3.5 ${research.pinned ? 'text-accent fill-accent' : 'text-text-tertiary'}`} />
        </button>
        <button
          onClick={handleDelete}
          className="p-1 rounded hover:bg-error-bg hover:text-error transition-colors duration-fast"
          title="删除"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

export default HistoryItem;
