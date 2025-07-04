import React from 'react';
import { Brain, Search, FileText, Zap } from 'lucide-react';

const LoadingSpinner = ({ message = '处理中...' }) => {
  const steps = [
    { icon: Brain, label: '制定研究计划', delay: '0s' },
    { icon: Search, label: '搜索相关信息', delay: '0.5s' },
    { icon: Zap, label: '分析处理数据', delay: '1s' },
    { icon: FileText, label: '生成研究报告', delay: '1.5s' }
  ];

  return (
    <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-100">
      <div className="text-center mb-8">
        <div className="inline-flex items-center space-x-2 mb-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <h3 className="text-xl font-semibold text-gray-900">{message}</h3>
        </div>
        <p className="text-gray-600">AI正在为您进行深度研究分析...</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {steps.map((step, index) => {
          const IconComponent = step.icon;
          return (
            <div 
              key={index}
              className="flex flex-col items-center p-4 bg-gray-50 rounded-lg"
              style={{ animationDelay: step.delay }}
            >
              <div className="mb-3 p-3 bg-primary-100 rounded-full animate-pulse-slow">
                <IconComponent className="h-6 w-6 text-primary-600" />
              </div>
              <p className="text-sm text-gray-700 text-center font-medium">
                {step.label}
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-8">
        <div className="bg-gray-200 rounded-full h-2 overflow-hidden">
          <div className="bg-gradient-to-r from-primary-500 to-primary-600 h-full rounded-full animate-pulse" 
               style={{ width: '60%' }}></div>
        </div>
        <p className="text-sm text-gray-500 text-center mt-2">
          预计需要 30-60 秒完成研究
        </p>
      </div>
    </div>
  );
};

export default LoadingSpinner;