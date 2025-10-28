import React, { useEffect, useRef, useState } from 'react';
import {
  Brain,
  Search,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Zap,
  Loader2
} from 'lucide-react';

/**
 * StreamingResults - 极简实时研究进展
 *
 * 显示研究过程的实时更新
 */
const StreamingResults = ({ updates }) => {
  const scrollContainerRef = useRef(null);
  const [animatingIndex, setAnimatingIndex] = useState(null);
  const prevLengthRef = useRef(0);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [updates]);

  // 触发新项动画
  useEffect(() => {
    if (updates.length > prevLengthRef.current) {
      setAnimatingIndex(updates.length - 1);
      const timer = setTimeout(() => {
        setAnimatingIndex(null);
      }, 500);
      prevLengthRef.current = updates.length;
      return () => clearTimeout(timer);
    }
  }, [updates]);

  // 判断是否完成
  const isComplete = updates.length > 0 && updates[updates.length - 1]?.type === 'report_complete';

  const getUpdateIcon = (type) => {
    switch (type) {
      case 'planning':
      case 'planning_step':
        return Brain;
      case 'plan':
        return CheckCircle;
      case 'step_start':
      case 'search_progress':
        return Search;
      case 'search_result':
        return CheckCircle;
      case 'analysis_progress':
        return Brain;
      case 'step_complete':
        return CheckCircle;
      case 'report_generating':
        return FileText;
      case 'report_complete':
        return CheckCircle;
      case 'error':
        return AlertCircle;
      default:
        return Zap;
    }
  };

  const getUpdateStyle = (type) => {
    switch (type) {
      case 'planning':
      case 'planning_step':
      case 'step_start':
      case 'search_progress':
      case 'analysis_progress':
      case 'report_generating':
        return {
          icon: 'text-accent',
          bg: 'bg-info-bg',
          text: 'text-text-primary'
        };
      case 'plan':
      case 'search_result':
      case 'step_complete':
      case 'report_complete':
        return {
          icon: 'text-success',
          bg: 'bg-success-bg',
          text: 'text-text-primary'
        };
      case 'error':
        return {
          icon: 'text-error',
          bg: 'bg-error-bg',
          text: 'text-error'
        };
      default:
        return {
          icon: 'text-text-secondary',
          bg: 'bg-background-secondary',
          text: 'text-text-primary'
        };
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const renderUpdateData = (update) => {
    if (!update.data) return null;

    switch (update.type) {
      case 'planning_step':
        const stepData = update.data;
        if (stepData.plan_preview) {
          return (
            <div className="mt-sm p-sm bg-background-secondary rounded-md border-l-2 border-accent">
              <p className="text-xs font-medium text-text-secondary mb-xs">计划预览:</p>
              <div className="space-y-xs">
                {stepData.plan_preview.slice(0, 2).map((step, index) => (
                  <div key={index} className="text-xs text-text-secondary">
                    <span className="font-medium">{step.step}. {step.title}</span>
                    {step.description && (
                      <span className="text-text-tertiary ml-1">- {step.description}</span>
                    )}
                  </div>
                ))}
                {stepData.plan_preview.length > 2 && (
                  <div className="text-xs text-text-tertiary">
                    还有 {stepData.plan_preview.length - 2} 个步骤...
                  </div>
                )}
              </div>
            </div>
          );
        }
        return null;

      case 'plan':
        return (
          <div className="mt-sm space-y-xs">
            <div className="space-y-xs">
              {update.data.map((step, index) => (
                <div key={index} className="flex items-start gap-2 text-xs">
                  <span className="flex-shrink-0 w-4 h-4 bg-accent/10 text-accent rounded-full flex items-center justify-center text-xs font-medium">
                    {step.step}
                  </span>
                  <div className="flex-1">
                    <span className="font-medium text-text-primary">{step.title}</span>
                    {step.description && (
                      <p className="text-text-tertiary mt-0.5">{step.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'search_result':
        const searchSources = update.data?.sources || [];
        if (searchSources.length > 0) {
          return (
            <div className="mt-sm p-sm bg-success-bg rounded-md border-l-2 border-success">
              <p className="text-xs font-medium text-text-secondary mb-xs">
                找到 {searchSources.length} 个信息源:
              </p>
              <div className="space-y-xs">
                {searchSources.slice(0, 3).map((source, index) => (
                  <div key={index} className="flex items-start gap-2 text-xs">
                    <span className="flex-shrink-0 text-success">•</span>
                    <a
                      href={source.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:text-accent-dark underline decoration-1 underline-offset-2 line-clamp-1 transition-colors duration-fast"
                    >
                      {source.title}
                    </a>
                  </div>
                ))}
                {searchSources.length > 3 && (
                  <p className="text-xs text-text-tertiary">
                    还有 {searchSources.length - 3} 个结果...
                  </p>
                )}
              </div>
            </div>
          );
        }
        return null;

      case 'step_start':
        return (
          <div className="mt-sm p-sm bg-background-secondary rounded-md text-xs">
            <p className="font-medium text-text-primary">{update.data.title}</p>
            {update.data.description && (
              <p className="text-text-tertiary mt-0.5">{update.data.description}</p>
            )}
          </div>
        );

      case 'step_complete':
        return (
          <div className="mt-sm p-sm bg-success-bg rounded-md border-l-2 border-success">
            <p className="text-xs font-medium text-text-primary">{update.data.title}</p>

            {update.data.search_sources && update.data.search_sources.length > 0 && (
              <p className="text-xs text-text-secondary mt-xs">
                检索了 {update.data.search_sources.length} 个信息源
              </p>
            )}

            {update.data.analysis && (
              <p className="text-xs text-text-tertiary mt-xs line-clamp-2">
                {update.data.analysis.substring(0, 150)}...
              </p>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="border border-border-light rounded-lg overflow-hidden bg-background-primary">
      {/* 头部 */}
      <div className="px-md py-sm border-b border-border-light bg-background-secondary">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {!isComplete && (
              <Loader2 className="w-4 h-4 text-accent animate-spin" />
            )}
            {isComplete && (
              <CheckCircle className="w-4 h-4 text-success" />
            )}
            <h3 className="text-base font-semibold text-text-primary">
              {isComplete ? '研究完成' : '实时研究进展'}
            </h3>
          </div>
          <span className="text-xs text-text-tertiary">
            {updates.length} 个更新
          </span>
        </div>
      </div>

      {/* 更新列表 */}
      <div className="p-md">
        <div
          ref={scrollContainerRef}
          className="space-y-sm max-h-96 overflow-y-auto"
        >
          {updates.map((update, index) => {
            const IconComponent = getUpdateIcon(update.type);
            const style = getUpdateStyle(update.type);
            const shouldAnimate = animatingIndex === index && !isComplete;

            return (
              <div
                key={`update-${index}`}
                className={`flex items-start gap-3 p-sm rounded-md ${style.bg} ${
                  shouldAnimate ? 'animate-slide-in' : ''
                }`}
              >
                {/* 图标 */}
                <div className="flex-shrink-0 mt-0.5">
                  <IconComponent className={`w-4 h-4 ${style.icon}`} />
                </div>

                {/* 内容 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-sm font-medium ${style.text} flex-1`}>
                      {update.message}
                    </p>
                    <div className="flex items-center gap-1 text-text-tertiary flex-shrink-0">
                      <Clock className="w-3 h-3" />
                      <span className="text-xs">
                        {formatTime(Date.now())}
                      </span>
                    </div>
                  </div>

                  {renderUpdateData(update)}
                </div>
              </div>
            );
          })}
        </div>

        {/* 空状态 */}
        {updates.length === 0 && (
          <div className="flex flex-col items-center justify-center py-xl">
            <Loader2 className="w-8 h-8 text-accent animate-spin mb-md" />
            <p className="text-sm text-text-secondary">等待研究开始...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StreamingResults;
