import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import SearchForm from './components/SearchForm';
import ResearchResults from './components/ResearchResults';
import LoadingSpinner from './components/LoadingSpinner';
import StreamingResults from './components/StreamingResults';
import EmptyState from './components/EmptyState';
import { HistoryProvider, useHistory } from './contexts/HistoryContext';
import { researchAPI } from './services/api';

/**
 * Main App Component - 包含侧边栏布局的主应用
 */
function AppContent() {
  const [isResearching, setIsResearching] = useState(false);
  const [researchData, setResearchData] = useState(null);
  const [streamingData, setStreamingData] = useState([]);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const { currentResearch, addResearch, updateResearch, setCurrentResearch } = useHistory();

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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
    // 每30秒检查一次
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleStartResearch = async (query) => {
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);

    // 添加到历史记录
    const research = addResearch({
      query,
      status: 'in_progress',
    });

    try {
      console.log('开始研究:', query);

      // 使用流式API
      await researchAPI.startResearchStream(query, (update) => {
        console.log('🔍 收到更新:', update.type);

        setStreamingData(prev => [...prev, update]);

        // 如果研究完成，设置最终数据
        if (update.type === 'report_complete') {
          console.log('🎯 研究完成');
          setResearchData(update.data);
          // 更新历史记录
          updateResearch(research.id, {
            result: update.data,
            status: 'completed',
          });
        } else if (update.type === 'error') {
          console.log('❌ 研究出错');
          setError(update.message);
          updateResearch(research.id, {
            status: 'failed',
            error: update.message,
          });
        }
      });

    } catch (err) {
      console.error('研究失败:', err);

      let errorMessage = '研究过程中发生错误: ' + err.message;

      if (err.message.includes('网络连接失败') ||
          err.message.includes('请求超时') ||
          err.message.includes('ERR_CONNECTION_CLOSED')) {
        errorMessage = '网络连接不稳定，请检查网络连接后重试';

        // 尝试非流式API
        try {
          console.log('网络错误，尝试非流式API...');
          const result = await researchAPI.startResearch(query);
          setResearchData(result);
          setError(null);
          updateResearch(research.id, {
            result,
            status: 'completed',
          });
        } catch (fallbackErr) {
          console.error('非流式API也失败:', fallbackErr);
          setError('无法连接到研究服务，请检查网络连接或稍后重试。');
          updateResearch(research.id, {
            status: 'failed',
            error: '无法连接到研究服务',
          });
        }
      } else {
        setError(errorMessage);
        updateResearch(research.id, {
          status: 'failed',
          error: errorMessage,
        });
      }
    } finally {
      setIsResearching(false);
    }
  };

  const handleNewResearch = () => {
    setCurrentResearch(null);
    setResearchData(null);
    setStreamingData([]);
    setError(null);

    // 移动端关闭侧边栏
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleExampleClick = (question) => {
    handleStartResearch(question);
  };

  // 当从历史加载研究时
  useEffect(() => {
    if (currentResearch && currentResearch.result) {
      setResearchData(currentResearch.result);
      setStreamingData([]);
      setError(null);
      setIsResearching(false);

      // 移动端关闭侧边栏
      if (isMobile) {
        setSidebarOpen(false);
      }
    }
  }, [currentResearch, isMobile]);

  // 判断是否显示空状态
  const showEmptyState = !isResearching && !researchData && !currentResearch;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background-primary">
      {/* 顶部导航 */}
      <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

      {/* 主布局：侧边栏 + 主内容 */}
      <div className="flex flex-1 overflow-hidden pt-12">
        {/* 侧边栏 */}
        <Sidebar
          backendStatus={backendStatus}
          onNewResearch={handleNewResearch}
          isMobile={isMobile}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* 主内容区域 */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-container mx-auto px-lg py-lg">
            {/* 空状态 */}
            {showEmptyState && (
              <EmptyState onExampleClick={handleExampleClick} />
            )}

            {/* 有内容时显示搜索框 */}
            {!showEmptyState && (
              <div className="mb-xl">
                <SearchForm
                  onSubmit={handleStartResearch}
                  isLoading={isResearching}
                  disabled={backendStatus === 'offline'}
                />
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="mb-xl p-md bg-error-bg border border-error-light rounded-lg">
                <p className="text-error text-sm">{error}</p>
              </div>
            )}

            {/* 研究中状态 */}
            {isResearching && (
              <div className="mt-xl">
                {streamingData.length > 0 ? (
                  <StreamingResults updates={streamingData} />
                ) : (
                  <LoadingSpinner message="正在进行深度研究..." />
                )}
              </div>
            )}

            {/* 研究结果 */}
            {researchData && !isResearching && (
              <div className="mt-xl">
                <ResearchResults data={researchData} />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

// 使用 HistoryProvider 包装
function App() {
  return (
    <HistoryProvider>
      <AppContent />
    </HistoryProvider>
  );
}

export default App;
