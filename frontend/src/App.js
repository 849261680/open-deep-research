import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchForm from './components/SearchForm';
import ResearchResults from './components/ResearchResults';
import LoadingSpinner from './components/LoadingSpinner';
import StreamingResults from './components/StreamingResults';
import { researchAPI } from './services/api';

function App() {
  const [isResearching, setIsResearching] = useState(false);
  const [researchData, setResearchData] = useState(null);
  const [streamingData, setStreamingData] = useState([]);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');

  // 检查后端状态
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await researchAPI.healthCheck();
        setBackendStatus('online');
      } catch (err) {
        console.error('后端连接失败:', err);
        setBackendStatus('offline');
      }
    };

    checkBackend();
  }, []);

  const handleStartResearch = async (query) => {
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);

    try {
      console.log('开始研究:', query);
      
      // 使用流式API
      await researchAPI.startResearchStream(query, (update) => {
        console.log('🔍 [前端调试] 收到更新:', update);
        console.log('🔍 [前端调试] 更新类型:', update.type);
        console.log('🔍 [前端调试] 更新数据:', update.data);
        
        setStreamingData(prev => [...prev, update]);
        
        // 如果研究完成，设置最终数据
        if (update.type === 'report_complete') {
          console.log('🎯 [前端调试] 检测到report_complete事件，设置研究数据');
          console.log('🎯 [前端调试] 研究数据内容:', update.data);
          setResearchData(update.data);
        } else if (update.type === 'error') {
          console.log('❌ [前端调试] 检测到error事件，显示错误信息');
          setError(update.message);
        } else {
          console.log('📝 [前端调试] 非完成事件，继续等待');
        }
      });
      
    } catch (err) {
      console.error('研究失败:', err);
      
      // 根据错误类型显示不同的错误信息
      let errorMessage = '研究过程中发生错误: ' + err.message;
      
      if (err.message.includes('网络连接失败') || 
          err.message.includes('请求超时') ||
          err.message.includes('ERR_CONNECTION_CLOSED')) {
        errorMessage = '网络连接不稳定，请检查网络连接后重试';
        
        // 如果是网络错误，尝试非流式API
        try {
          console.log('网络错误，尝试非流式API...');
          const result = await researchAPI.startResearch(query);
          setResearchData(result);
          setError(null);
        } catch (fallbackErr) {
          console.error('非流式API也失败:', fallbackErr);
          setError('无法连接到研究服务，请检查网络连接或稍后重试。');
        }
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsResearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Deep Research Agent
            </h1>
            <p className="text-xl text-gray-600">
              智能研究助手，为您提供深度分析和专业报告
            </p>
            
            {/* 后端状态指示器 */}
            <div className="mt-4 flex items-center justify-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                backendStatus === 'online' ? 'bg-green-500' : 
                backendStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-500">
                {backendStatus === 'online' ? '服务在线' : 
                 backendStatus === 'offline' ? '服务离线' : '检查中...'}
              </span>
            </div>
          </div>

          <SearchForm 
            onSubmit={handleStartResearch} 
            isLoading={isResearching}
            disabled={backendStatus === 'offline'}
          />

          {error && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {isResearching && (
            <div className="mt-8">
              {streamingData.length > 0 ? (
                <StreamingResults updates={streamingData} />
              ) : (
                <LoadingSpinner message="正在进行深度研究..." />
              )}
            </div>
          )}

          {researchData && !isResearching && (
            <div className="mt-8">
              <ResearchResults data={researchData} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
