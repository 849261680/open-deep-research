import React, { useState, useEffect, useRef } from 'react';
import { 
  Brain, 
  Search, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertCircle,
  Zap
} from 'lucide-react';

const StreamingResults = ({ updates }) => {
  const [loadingDots, setLoadingDots] = useState('');
  const scrollContainerRef = useRef(null);

  // 动态加载点动画
  useEffect(() => {
    const interval = setInterval(() => {
      setLoadingDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [updates]);

  // 判断是否有正在进行的任务
  const hasActiveTask = updates.length > 0 && updates[updates.length - 1]?.type !== 'report_complete';

  const getUpdateIcon = (type) => {
    switch (type) {
      case 'planning':
        return Brain;
      case 'planning_step':
        return Brain;
      case 'plan':
        return CheckCircle;
      case 'step_start':
        return Search;
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

  const getUpdateColor = (type) => {
    switch (type) {
      case 'planning':
      case 'planning_step':
      case 'step_start':
      case 'search_progress':
      case 'analysis_progress':
      case 'report_generating':
        return 'text-blue-600 bg-blue-100';
      case 'plan':
      case 'search_result':
      case 'step_complete':
      case 'report_complete':
        return 'text-green-600 bg-green-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN');
  };

  const renderUpdateData = (update) => {
    if (!update.data) return null;

    switch (update.type) {
      case 'planning_step':
        // 显示计划制定的具体步骤
        const stepData = update.data;
        if (stepData.plan_preview) {
          return (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-800">计划预览:</h4>
              <div className="mt-2 space-y-1">
                {stepData.plan_preview.slice(0, 2).map((step, index) => (
                  <div key={index} className="text-sm text-blue-700">
                    <span className="font-medium">{step.step}. {step.title}</span>
                    <span className="text-blue-600 ml-2">- {step.description}</span>
                  </div>
                ))}
                {stepData.plan_preview.length > 2 && (
                  <div className="text-sm text-blue-600">
                    ... 还有 {stepData.plan_preview.length - 2} 个步骤
                  </div>
                )}
              </div>
            </div>
          );
        }
        // 不显示技术性的内部步骤信息
        return null;
      
      case 'plan':
        return (
          <div className="mt-3 space-y-2">
            <h4 className="font-medium text-gray-800">研究计划:</h4>
            <div className="space-y-2">
              {update.data.map((step, index) => (
                <div key={index} className="flex items-start space-x-2 text-sm">
                  <span className="flex-shrink-0 w-5 h-5 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-xs font-medium">
                    {step.step}
                  </span>
                  <div>
                    <span className="font-medium text-gray-700">{step.title}</span>
                    <p className="text-gray-600">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      
      case 'search_result':
        // 显示搜索到的链接和标题
        const searchSources = update.data?.sources || [];
        if (searchSources.length > 0) {
          return (
            <div className="mt-3 p-3 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-800">搜索到的内容:</h4>
              <div className="mt-2 space-y-2">
                {searchSources.map((source, index) => (
                  <div key={index} className="flex items-start space-x-2 text-sm">
                    <span className="flex-shrink-0 w-4 h-4 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-xs">
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <a 
                        href={source.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="font-medium text-blue-600 hover:text-blue-800 hover:underline line-clamp-1"
                      >
                        {source.title}
                      </a>
                      <p className="text-green-600 text-xs">
                        来源: {source.source} | 查询: {update.data.query}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        return null;
      
      case 'step_start':
        return (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800">步骤详情:</h4>
            <p className="text-blue-700 text-sm mt-1">{update.data.title}</p>
            <p className="text-blue-600 text-sm">{update.data.description}</p>
          </div>
        );
      
      case 'step_complete':
        return (
          <div className="mt-3 p-3 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-800">完成步骤: {update.data.title}</h4>
            
            {/* 显示搜索源摘要 */}
            {update.data.search_sources && update.data.search_sources.length > 0 && (
              <div className="mt-2 text-sm text-green-700">
                <p className="font-medium">已检索 {update.data.search_sources.length} 个信息源</p>
              </div>
            )}
            
            {update.data.analysis && (
              <div className="mt-2 text-sm text-green-700">
                <p className="font-medium">分析结果:</p>
                <p className="mt-1 line-clamp-3">{update.data.analysis.substring(0, 200)}...</p>
              </div>
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-6 py-4">
        <h2 className="text-xl font-bold text-white mb-1">
          实时研究进展
        </h2>
        <p className="text-blue-100">
          正在进行智能研究分析{hasActiveTask ? loadingDots : ''}
        </p>
      </div>

      <div className="p-6">
        <div ref={scrollContainerRef} className="space-y-4 max-h-96 overflow-y-auto">
          {updates.map((update, index) => {
            const IconComponent = getUpdateIcon(update.type);
            const colorClass = getUpdateColor(update.type);
            
            return (
              <div key={index} className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                <div className={`p-2 rounded-full ${colorClass}`}>
                  <IconComponent className="h-5 w-5" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-gray-900">
                      {update.message.endsWith('...') && 
                       (update.type === 'planning' || update.type === 'planning_step' || 
                        update.type === 'step_start' || update.type === 'search_progress' ||
                        update.type === 'analysis_progress' || update.type === 'report_generating') &&
                       index === updates.length - 1 ? 
                        update.message.slice(0, -3) + loadingDots : 
                        update.message}
                    </p>
                    <div className="flex items-center space-x-1 text-gray-500">
                      <Clock className="h-3 w-3" />
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

        {updates.length === 0 && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">等待研究开始...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StreamingResults;