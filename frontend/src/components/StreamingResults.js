import React, { useEffect, useRef, useState } from 'react';
import {
  Brain,
  Search,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Zap,
} from 'lucide-react';

const StreamingResults = ({ updates }) => {
  const scrollContainerRef = useRef(null);
  const [animatingIndex, setAnimatingIndex] = useState(null);
  const prevLengthRef = useRef(0);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [updates]);

  useEffect(() => {
    if (updates.length > prevLengthRef.current) {
      setAnimatingIndex(updates.length - 1);
      const timer = setTimeout(() => setAnimatingIndex(null), 500);
      prevLengthRef.current = updates.length;
      return () => clearTimeout(timer);
    }
  }, [updates]);

  const isComplete = updates.length > 0 && updates[updates.length - 1]?.type === 'report_complete';
  const latestUpdate = updates[updates.length - 1];

  const getUpdateIcon = (type) => {
    switch (type) {
      case 'planning': case 'planning_step': return Brain;
      case 'plan': return CheckCircle;
      case 'step_start': case 'step_retry': case 'search_progress': return Search;
      case 'search_result': return CheckCircle;
      case 'analysis_progress': return Brain;
      case 'step_complete': return CheckCircle;
      case 'report_generating': return FileText;
      case 'report_complete': return CheckCircle;
      case 'error': case 'stopped': return AlertCircle;
      default: return Zap;
    }
  };

  const getUpdateStyle = (type) => {
    switch (type) {
      case 'planning': case 'planning_step': case 'step_start': case 'step_retry':
      case 'search_progress': case 'analysis_progress': case 'report_generating':
        return { iconColor: '#163300', bg: 'rgba(159,232,112,0.12)', dot: '#9fe870' };
      case 'plan': case 'search_result': case 'step_complete': case 'report_complete':
        return { iconColor: '#054d28', bg: '#e2f6d5', dot: '#054d28' };
      case 'error': case 'stopped':
        return { iconColor: '#d03238', bg: '#FDECEA', dot: '#d03238' };
      default:
        return { iconColor: '#868685', bg: '#F5F8F2', dot: '#868685' };
    }
  };

  const formatTime = (timestamp) =>
    new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });

  const getUpdateTimestamp = (update) =>
    update?.timestamp || update?.data?.timestamp || Date.now();

  const getStageText = (type) => {
    switch (type) {
      case 'planning': case 'planning_step': case 'plan': return '规划研究路径中...';
      case 'step_start': case 'step_retry': case 'search_progress': case 'search_result': return '检索信息中...';
      case 'analysis_progress': case 'step_complete': return '分析整理中...';
      case 'report_generating': return '生成报告中...';
      case 'report_complete': return '报告已生成';
      case 'error': return '研究过程中出现问题';
      case 'stopped': return '研究已手动停止';
      default: return '准备开始研究...';
    }
  };

  const deriveCurrentStatus = () => {
    if (updates.length === 0) return null;

    const activeQueries = new Map();
    const completedSteps = new Set();
    let totalSteps = 0;
    let latestPlanningMessage = null;
    let latestActiveQuery = null;
    let latestCompletedQuery = null;
    let phase = 'planning';
    let statusType = latestUpdate?.type || 'planning';
    let timestamp = getUpdateTimestamp(latestUpdate);

    updates.forEach((update) => {
      timestamp = getUpdateTimestamp(update);
      switch (update.type) {
        case 'planning': case 'planning_step':
          phase = 'planning'; statusType = update.type;
          latestPlanningMessage = update.message; break;
        case 'plan':
          phase = 'researching'; statusType = 'search_progress';
          if (Array.isArray(update.data)) totalSteps = update.data.length;
          else if (Array.isArray(update.data?.sub_queries)) totalSteps = update.data.sub_queries.length;
          break;
        case 'search_progress': case 'step_start': case 'analysis_progress': case 'search_result':
          phase = 'researching'; statusType = 'search_progress';
          if (typeof update.data?.total === 'number') totalSteps = Math.max(totalSteps, update.data.total);
          if (typeof update.data?.step === 'number') activeQueries.set(update.data.step, update.data.query || update.message);
          latestActiveQuery = update.data?.query || update.message; break;
        case 'step_complete':
          phase = 'researching'; statusType = 'search_progress';
          if (typeof update.data?.step === 'number') { activeQueries.delete(update.data.step); completedSteps.add(update.data.step); }
          if (completedSteps.size > totalSteps) totalSteps = completedSteps.size;
          latestCompletedQuery = update.data?.title || update.message; break;
        case 'report_generating': phase = 'reporting'; statusType = 'report_generating'; break;
        case 'report_complete': phase = 'completed'; statusType = 'report_complete'; break;
        case 'error': phase = 'error'; statusType = 'error'; break;
        case 'stopped': phase = 'stopped'; statusType = 'stopped'; break;
        default: break;
      }
    });

    const completedCount = completedSteps.size;
    const activeCount = activeQueries.size;
    const activeQueryList = Array.from(activeQueries.values());

    switch (phase) {
      case 'planning':
        return { type: statusType, timestamp, title: latestPlanningMessage || '正在规划研究路径...', detail: totalSteps > 0 ? `已生成 ${totalSteps} 个子查询规划。` : '正在拆解问题并规划研究路径。', activeItems: [] };
      case 'researching': {
        const detailParts = [];
        if (totalSteps > 0) detailParts.push(`已完成 ${completedCount}/${totalSteps}`);
        if (activeCount > 0) detailParts.push(`进行中 ${activeCount}`);
        let title = '正在执行研究';
        if (activeCount > 0) title = activeCount > 1 ? `正在并行研究 ${activeCount} 个子查询` : '正在研究子查询';
        else if (totalSteps > 0 && completedCount === totalSteps) title = '子查询已全部完成，等待汇总';
        else if (latestCompletedQuery) title = '正在继续推进剩余子查询';
        return { type: statusType, timestamp, title, detail: detailParts.join('，') || '正在收集和分析信息。', activeItems: activeQueryList.slice(0, 3), extra: activeCount > 3 ? `还有 ${activeCount - 3} 个子查询正在进行中` : null, lastCompleted: latestCompletedQuery, latestActiveQuery };
      }
      case 'reporting':
        return { type: statusType, timestamp, title: '正在生成最终研究报告', detail: totalSteps > 0 ? `子查询已完成 ${completedCount}/${totalSteps}，正在汇总证据并撰写报告。` : '正在汇总证据并撰写最终报告。', activeItems: [], lastCompleted: latestCompletedQuery };
      case 'completed':
        return { type: statusType, timestamp, title: '研究已完成', detail: totalSteps > 0 ? `共完成 ${completedCount || totalSteps}/${totalSteps} 个子查询。` : '最终研究报告已生成。', activeItems: [] };
      case 'error':
        return { type: statusType, timestamp, title: latestUpdate?.message || '研究过程中出现问题', detail: '系统已停止当前流程，请检查错误信息。', activeItems: [] };
      case 'stopped':
        return { type: statusType, timestamp, title: '研究已手动停止', detail: '当前任务已停止，不会继续执行。', activeItems: [] };
      default:
        return { type: statusType, timestamp, title: latestUpdate?.message || '准备开始研究...', detail: '', activeItems: [] };
    }
  };

  const currentStatus = deriveCurrentStatus();
  const currentStatusStyle = getUpdateStyle(currentStatus?.type);
  const CurrentStatusIcon = getUpdateIcon(currentStatus?.type);

  const getHostname = (link) => {
    if (!link) return '';
    try { return new URL(link).hostname.replace(/^www\./, ''); } catch { return ''; }
  };

  const renderPills = (items, options = {}) => {
    if (!items || items.length === 0) return null;
    const { limit = items.length, getLabel = (item) => item, getHref = () => null, keyPrefix = 'pill' } = options;
    const visibleItems = items.slice(0, limit);
    const remainingCount = items.length - visibleItems.length;

    return (
      <div className="mt-2 flex flex-wrap gap-1.5">
        {visibleItems.map((item, index) => {
          const label = getLabel(item);
          const href = getHref(item);
          const pillStyle = {
            display: 'inline-flex',
            maxWidth: '100%',
            alignItems: 'center',
            borderRadius: '9999px',
            border: '1px solid #E2E5DE',
            background: '#FFFFFF',
            padding: '2px 10px',
            fontSize: '12px',
            color: '#454745',
            fontWeight: 500,
          };
          if (href) return (
            <a key={`${keyPrefix}-${index}`} href={href} target="_blank" rel="noopener noreferrer" style={{ ...pillStyle, color: '#163300', textDecoration: 'none' }}>
              <span className="truncate">{label}</span>
            </a>
          );
          return <span key={`${keyPrefix}-${index}`} style={pillStyle}><span className="truncate">{label}</span></span>;
        })}
        {remainingCount > 0 && (
          <span style={{ display: 'inline-flex', alignItems: 'center', borderRadius: '9999px', border: '1px solid #E2E5DE', background: '#FFFFFF', padding: '2px 10px', fontSize: '12px', color: '#868685', fontWeight: 400 }}>
            还有 {remainingCount} 项
          </span>
        )}
      </div>
    );
  };

  const renderUpdateData = (update) => {
    if (!update.data) return null;
    switch (update.type) {
      case 'planning_step':
        if (update.data.plan_preview) return (
          <div className="mt-2 pl-3 border-l-2 border-accent">
            <p className="text-xs font-semibold text-text-tertiary mb-1">计划预览</p>
            <div className="space-y-1">
              {update.data.plan_preview.slice(0, 2).map((step, index) => (
                <div key={index} className="text-xs text-text-secondary">
                  <span className="font-semibold">{step.step}. {step.title}</span>
                  {step.description && <span className="text-text-tertiary ml-1 font-normal">— {step.description}</span>}
                </div>
              ))}
              {update.data.plan_preview.length > 2 && <div className="text-xs text-text-tertiary font-normal">还有 {update.data.plan_preview.length - 2} 个步骤...</div>}
            </div>
          </div>
        );
        return null;

      case 'plan':
        return (
          <div className="mt-2 space-y-1">
            {update.data.map((step, index) => (
              <div key={index} className="flex items-start gap-2 text-xs">
                <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-semibold" style={{ background: '#e2f6d5', color: '#163300' }}>{step.step}</span>
                <div className="flex-1">
                  <span className="font-semibold text-text-primary">{step.title}</span>
                  {step.description && <p className="text-text-tertiary mt-0.5 font-normal">{step.description}</p>}
                </div>
              </div>
            ))}
          </div>
        );

      case 'search_result': {
        const searchQueries = update.data?.queries || (update.data?.query ? [update.data.query] : []);
        const searchSources = update.data?.sources || [];
        const searchDomains = update.data?.domains || searchSources.map((s) => s.domain || getHostname(s.link)).filter(Boolean);
        return (
          <div className="mt-2 pl-3 border-l-2" style={{ borderColor: '#E2E5DE' }}>
            {searchQueries.length > 0 && <><p className="text-xs text-text-tertiary font-medium">搜索查询</p>{renderPills(searchQueries, { keyPrefix: 'sq' })}</>}
            {searchDomains.length > 0 && <><p className="mt-2 text-xs text-text-tertiary font-medium">候选来源</p>{renderPills(searchDomains, { keyPrefix: 'sd', limit: 6 })}</>}
            {searchSources.length > 0 && <>
              <p className="mt-2 text-xs text-text-tertiary font-normal">检索结果给出了研究线索，接下来会优先阅读这些来源。</p>
              {renderPills(searchSources, { keyPrefix: 'ss', limit: 3, getLabel: (s) => s.title || s.domain || getHostname(s.link), getHref: (s) => s.link || null })}
            </>}
          </div>
        );
      }

      case 'step_start': case 'step_retry': {
        const stepQueries = update.data?.queries || (update.data?.query ? [update.data.query] : []);
        return (
          <div className="mt-2 pl-3 border-l-2" style={{ borderColor: '#E2E5DE' }}>
            <p className="text-xs font-semibold text-text-primary">{update.data.title}</p>
            {update.type === 'step_retry' ? (
              <p className="text-xs text-text-tertiary mt-0.5 font-normal">第 {update.data.retry_count} 次重试</p>
            ) : update.data.description && (
              <p className="text-xs text-text-tertiary mt-0.5 font-normal">{update.data.description}</p>
            )}
            {stepQueries.length > 0 && renderPills(stepQueries, { keyPrefix: 'stq' })}
          </div>
        );
      }

      case 'analysis_progress': {
        const analysisQueries = update.data?.queries || (update.data?.query ? [update.data.query] : []);
        const analysisSources = update.data?.sources || [];
        const analysisDomains = update.data?.domains || analysisSources.map((s) => s.domain || getHostname(s.link)).filter(Boolean);
        return (
          <div className="mt-2 pl-3 border-l-2" style={{ borderColor: '#E2E5DE' }}>
            <p className="text-xs text-text-tertiary font-normal">已读取 {update.data?.read_count || analysisSources.length || 0} 个来源，正在整理证据和结论。</p>
            {analysisQueries.length > 0 && renderPills(analysisQueries, { keyPrefix: 'aq' })}
            {analysisDomains.length > 0 && renderPills(analysisDomains, { keyPrefix: 'ad', limit: 6 })}
          </div>
        );
      }

      case 'step_complete':
        return (
          <div className="mt-2 p-3 rounded-xl" style={{ background: '#e2f6d5' }}>
            <p className="text-xs font-semibold text-text-primary">{update.data.title}</p>
            {update.data.search_sources?.length > 0 && (
              <p className="text-xs text-text-secondary mt-1 font-normal">检索了 {update.data.search_sources.length} 个信息源</p>
            )}
            {update.data.analysis && (
              <p className="text-xs text-text-tertiary mt-1 line-clamp-2 font-normal">{update.data.analysis.substring(0, 150)}...</p>
            )}
          </div>
        );

      default: return null;
    }
  };

  return (
    <div
      className="overflow-hidden bg-white"
      style={{ borderRadius: '30px', boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px' }}
    >
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-light" style={{ background: '#F5F8F2' }}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              {!isComplete ? (
                <div className="relative flex-shrink-0">
                  <div
                    className="w-5 h-5 rounded-full border-2 animate-spin"
                    style={{ borderColor: '#e2f6d5', borderTopColor: '#9fe870' }}
                  />
                </div>
              ) : (
                <CheckCircle className="w-5 h-5 flex-shrink-0" style={{ color: '#054d28' }} />
              )}
              <h3
                className="text-text-primary"
                style={{ fontSize: '16px', fontWeight: 700, lineHeight: 1.3 }}
              >
                {isComplete ? '研究完成' : '实时研究进展'}
              </h3>
            </div>
            <p className="mt-1 text-text-tertiary" style={{ fontSize: '13px', fontWeight: 400 }}>
              {getStageText(latestUpdate?.type)}
            </p>
          </div>
          <span
            className="rounded-full px-3 py-1 text-text-secondary flex-shrink-0"
            style={{ fontSize: '12px', fontWeight: 500, background: '#EBF0E7' }}
          >
            {updates.length} 个更新
          </span>
        </div>
      </div>

      {/* Current status card */}
      {currentStatus && (
        <div className="px-6 py-4 border-b border-border-light">
          <div
            className="rounded-xl px-5 py-4"
            style={{ background: currentStatusStyle.bg }}
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <CurrentStatusIcon className="w-4 h-4" style={{ color: currentStatusStyle.iconColor }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-text-tertiary mb-1">当前状态</p>
                <p className="text-text-primary" style={{ fontSize: '14px', fontWeight: 600 }}>
                  {currentStatus.title}
                </p>
                {currentStatus.detail && (
                  <p className="mt-1 text-text-secondary" style={{ fontSize: '13px', fontWeight: 400 }}>
                    {currentStatus.detail}
                  </p>
                )}
                {currentStatus.activeItems?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {currentStatus.activeItems.map((item, index) => (
                      <p key={`${item}-${index}`} className="text-xs text-text-primary line-clamp-1 font-medium">{item}</p>
                    ))}
                    {currentStatus.extra && <p className="text-xs text-text-tertiary font-normal">{currentStatus.extra}</p>}
                  </div>
                )}
                {currentStatus.lastCompleted && (
                  <p className="mt-2 text-xs text-text-tertiary line-clamp-1 font-normal">最近完成: {currentStatus.lastCompleted}</p>
                )}
              </div>
              <div className="flex items-center gap-1 text-text-tertiary flex-shrink-0">
                <Clock className="w-3 h-3" />
                <span style={{ fontSize: '11px', fontWeight: 400 }}>{formatTime(currentStatus.timestamp)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Update log */}
      <div className="p-6">
        <div
          ref={scrollContainerRef}
          className="space-y-2 max-h-80 overflow-y-auto"
        >
          {updates.map((update, index) => {
            const IconComponent = getUpdateIcon(update.type);
            const style = getUpdateStyle(update.type);
            const shouldAnimate = animatingIndex === index && !isComplete;

            return (
              <div
                key={`update-${index}`}
                className={`flex items-start gap-3 p-3 rounded-xl ${shouldAnimate ? 'animate-slide-in' : ''}`}
                style={{ background: style.bg }}
              >
                <div className="flex-shrink-0 mt-0.5">
                  <IconComponent className="w-3.5 h-3.5" style={{ color: style.iconColor }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-text-primary font-medium flex-1">{update.message}</p>
                    <div className="flex items-center gap-1 text-text-tertiary flex-shrink-0">
                      <Clock className="w-3 h-3" />
                      <span style={{ fontSize: '11px', fontWeight: 400 }}>
                        {formatTime(update.timestamp || update.data?.timestamp || Date.now())}
                      </span>
                    </div>
                  </div>
                  {renderUpdateData(update)}
                </div>
              </div>
            );
          })}
        </div>

        {updates.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12">
            <div
              className="w-12 h-12 rounded-full border-2 animate-spin mb-6"
              style={{ borderColor: '#e2f6d5', borderTopColor: '#9fe870' }}
            />
            <p className="text-sm text-text-secondary font-medium">等待研究开始...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StreamingResults;
