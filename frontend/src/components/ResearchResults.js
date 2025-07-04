import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  ChevronDown, 
  ChevronRight, 
  Download,
  Share2 
} from 'lucide-react';

const ResearchResults = ({ data }) => {
  const [activeTab, setActiveTab] = useState('report');
  const [expandedSteps, setExpandedSteps] = useState(new Set());

  const toggleStep = (stepIndex) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepIndex)) {
      newExpanded.delete(stepIndex);
    } else {
      newExpanded.add(stepIndex);
    }
    setExpandedSteps(newExpanded);
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const tabs = [
    { id: 'report', label: '研究报告', icon: FileText },
    { id: 'process', label: '研究过程', icon: CheckCircle }
  ];

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">
              研究完成
            </h2>
            <p className="text-primary-100">
              主题: {data.query}
            </p>
          </div>
          <div className="flex items-center space-x-2 text-primary-100">
            <Clock className="h-4 w-4" />
            <span className="text-sm">{formatDate(data.timestamp)}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-6">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <IconComponent className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'report' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">
                研究报告
              </h3>
              <div className="flex space-x-2">
                <button className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
                  <Download className="h-4 w-4" />
                  <span>下载</span>
                </button>
                <button className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
                  <Share2 className="h-4 w-4" />
                  <span>分享</span>
                </button>
              </div>
            </div>
            
            <div className="markdown-content">
              <ReactMarkdown>{data.report}</ReactMarkdown>
            </div>
          </div>
        )}

        {activeTab === 'process' && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-6">
              研究过程详情
            </h3>
            
            {/* Research Plan */}
            <div className="mb-8">
              <h4 className="text-md font-medium text-gray-800 mb-4">研究计划</h4>
              <div className="space-y-3">
                {data.plan.map((step, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">
                      {step.step}
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">{step.title}</h5>
                      <p className="text-sm text-gray-600">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Research Results */}
            <div>
              <h4 className="text-md font-medium text-gray-800 mb-4">执行结果</h4>
              <div className="space-y-4">
                {data.results.map((result, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg">
                    <button
                      onClick={() => toggleStep(index)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="h-5 w-5 text-green-500" />
                        <div>
                          <h5 className="font-medium text-gray-900">
                            {result.title}
                          </h5>
                          <p className="text-sm text-gray-600">
                            {result.status === 'completed' ? '已完成' : '进行中'}
                          </p>
                        </div>
                      </div>
                      {expandedSteps.has(index) ? (
                        <ChevronDown className="h-5 w-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                    
                    {expandedSteps.has(index) && (
                      <div className="px-4 pb-4 border-t border-gray-100">
                        <div className="pt-4">
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {result.analysis || result.result || '暂无详细信息'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchResults;