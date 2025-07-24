import React from 'react';
import { Brain, Zap } from 'lucide-react';

const Header = () => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 p-1.5 shadow-sm">
              <img 
                src="/research-agent-icon-header.svg" 
                alt="Research Agent" 
                className="w-full h-full"
              />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Research Agent
              </h1>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-6">
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