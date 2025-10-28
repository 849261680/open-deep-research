import React from 'react';
import { Download, Share2, RefreshCw, Clock, CheckCircle } from 'lucide-react';
import Button from './Button';

/**
 * ResultHeader - 结果页头部组件
 *
 * 显示查询标题、时间戳、状态标签、操作按钮
 */
const ResultHeader = ({ query, timestamp, status, onDownload, onShare, onRerun }) => {
  // 格式化时间
  const formatTimestamp = (ts) => {
    const date = new Date(ts);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 状态标签
  const StatusBadge = () => {
    if (status === 'completed') {
      return (
        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-success-bg text-success text-sm font-medium rounded-full">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>已完成</span>
        </div>
      );
    }
    if (status === 'in_progress') {
      return (
        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-info-bg text-info text-sm font-medium rounded-full">
          <Clock className="w-3.5 h-3.5 animate-pulse" />
          <span>进行中</span>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="border-b border-border-light bg-background-primary pb-lg mb-xl">
      {/* 标题和操作按钮 */}
      <div className="flex items-start justify-between gap-4 mb-md">
        <h1 className="text-3xl font-bold text-text-primary flex-1 text-balance">
          {query}
        </h1>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            variant="secondary"
            size="small"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={onRerun}
            title="重新运行"
          />
          <Button
            variant="secondary"
            size="small"
            icon={<Download className="w-4 h-4" />}
            onClick={onDownload}
            title="下载报告"
          />
          <Button
            variant="secondary"
            size="small"
            icon={<Share2 className="w-4 h-4" />}
            onClick={onShare}
            title="分享"
          />
        </div>
      </div>

      {/* 时间戳和状态 */}
      <div className="flex items-center gap-3 text-sm">
        <span className="text-text-tertiary flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {timestamp ? formatTimestamp(timestamp) : ''}
        </span>
        <StatusBadge />
      </div>
    </div>
  );
};

export default ResultHeader;
