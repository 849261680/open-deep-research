import React from 'react';
import { Search, Brain, Zap } from 'lucide-react';

const Header = () => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-500 rounded-lg">
              <Brain className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Research Agent
              </h1>
              <p className="text-sm text-gray-500">智能研究助手</p>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-6">
            <div className="flex items-center space-x-2 text-gray-600">
              <Search className="h-5 w-5" />
              <span className="text-sm">多源搜索</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <Zap className="h-5 w-5" />
              <span className="text-sm">AI分析</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <Brain className="h-5 w-5" />
              <span className="text-sm">深度报告</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;