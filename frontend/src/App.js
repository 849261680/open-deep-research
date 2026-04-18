import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import SearchForm from './components/SearchForm';
import ResearchResults from './components/ResearchResults';
import LoadingSpinner from './components/LoadingSpinner';
import StreamingResults from './components/StreamingResults';
import EmptyState from './components/EmptyState';
import { HistoryProvider, useHistory } from './contexts/HistoryContext';
import { AuthProvider } from './contexts/AuthContext';
import AuthPage from './components/AuthPage';
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
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const activeRequestControllerRef = useRef(null);
  const activeResearchRef = useRef(null);

  const { currentResearch, addResearch, updateResearch, replaceResearchId, setCurrentResearch } = useHistory();

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

  const markResearchStopped = (research) => {
    const timestamp = new Date().toISOString();
    setError('研究已停止');
    setIsResearching(false);
    setStreamingData((previousUpdates) => {
      if (previousUpdates.some((update) => update.type === 'stopped')) {
        return previousUpdates;
      }
      return [
        ...previousUpdates,
        {
          type: 'stopped',
          message: '研究已停止',
          data: { timestamp },
        },
      ];
    });

    if (research?.id) {
      updateResearch(research.id, {
        status: 'failed',
        error: '研究已停止',
        timestamp,
      });
    }
    activeRequestControllerRef.current = null;
    activeResearchRef.current = null;
  };

  const handleStopResearch = async () => {
    const activeResearch = activeResearchRef.current || currentResearch;
    activeRequestControllerRef.current?.abort();
    markResearchStopped(activeResearch);

    if (activeResearch?.id && !activeResearch.isTemporaryId) {
      try {
        await researchAPI.stopResearch(activeResearch.id);
      } catch (err) {
        console.error('停止研究失败:', err);
      }
    }
  };

  const handleStartResearch = async (query) => {
    const requestController = new AbortController();
    activeRequestControllerRef.current = requestController;
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);

    // 添加到历史记录
    const research = addResearch({
      query,
      status: 'in_progress',
    });
    activeResearchRef.current = research;

    try {
      // 使用流式API
      await researchAPI.startResearchStream(query, (update) => {
        const normalizedUpdate = {
          ...update,
          timestamp: update.timestamp || new Date().toISOString(),
        };
        setStreamingData((prev) => [...prev, normalizedUpdate]);

        const serverTaskId = normalizedUpdate.data?.task_id || normalizedUpdate.data?.id;
        if (serverTaskId && serverTaskId !== research.id) {
          replaceResearchId(research.id, serverTaskId);
          research.id = serverTaskId;
          research.isTemporaryId = false;
          activeResearchRef.current = research;
        }

        // 如果研究完成，设置最终数据
        if (normalizedUpdate.type === 'report_complete') {
          setResearchData(normalizedUpdate.data);
          // 更新历史记录
          updateResearch(research.id, {
            result: normalizedUpdate.data,
            status: 'completed',
          });
          activeResearchRef.current = null;
        } else if (normalizedUpdate.type === 'error') {
          setError(normalizedUpdate.message);
          updateResearch(research.id, {
            status: 'failed',
            error: normalizedUpdate.message,
          });
          activeResearchRef.current = null;
        }
      }, { signal: requestController.signal });

    } catch (err) {
      console.error('研究失败:', err);

      if (err.message === '研究已停止') {
        markResearchStopped(research);
        return;
      }

      let errorMessage = '研究过程中发生错误: ' + err.message;

      if (err.message.includes('网络连接失败') ||
          err.message.includes('请求超时') ||
          err.message.includes('ERR_CONNECTION_CLOSED')) {
        errorMessage = '网络连接不稳定，请检查网络连接后重试';

        // 尝试非流式API
        try {
          const result = await researchAPI.startResearch(query);
          const finalData = result.data || result;
          if (finalData.id && finalData.id !== research.id) {
            replaceResearchId(research.id, finalData.id);
            research.id = finalData.id;
            research.isTemporaryId = false;
            activeResearchRef.current = research;
          }
          setResearchData(finalData);
          setError(null);
          updateResearch(research.id, {
            result: finalData,
            status: 'completed',
          });
        } catch (fallbackErr) {
          console.error('非流式API也失败:', fallbackErr);
          setError('无法连接到研究服务，请检查网络连接或稍后重试。');
          updateResearch(research.id, {
            status: 'failed',
            error: '无法连接到研究服务',
          });
          activeResearchRef.current = null;
        }
      } else {
        setError(errorMessage);
        updateResearch(research.id, {
          status: 'failed',
          error: errorMessage,
        });
        activeResearchRef.current = null;
      }
    } finally {
      if (activeRequestControllerRef.current === requestController) {
        activeRequestControllerRef.current = null;
      }
      setIsResearching(false);
    }
  };

  const handleResumeResearch = async (research) => {
    const requestController = new AbortController();
    activeRequestControllerRef.current = requestController;
    activeResearchRef.current = research;
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);
    setCurrentResearch(research);

    try {
      await researchAPI.resumeResearchStream(research.id, (update) => {
        const normalizedUpdate = {
          ...update,
          timestamp: update.timestamp || new Date().toISOString(),
        };
        setStreamingData((prev) => [...prev, normalizedUpdate]);

        if (normalizedUpdate.type === 'report_complete') {
          setResearchData(normalizedUpdate.data);
          updateResearch(research.id, {
            result: normalizedUpdate.data,
            status: 'completed',
            timestamp: normalizedUpdate.data.timestamp || normalizedUpdate.timestamp,
          });
          activeResearchRef.current = null;
        } else if (normalizedUpdate.type === 'error') {
          setError(normalizedUpdate.message);
          updateResearch(research.id, {
            status: 'failed',
            error: normalizedUpdate.message,
          });
          activeResearchRef.current = null;
        } else if (normalizedUpdate.type === 'step_retry') {
          updateResearch(research.id, {
            status: 'in_progress',
          });
        }
      }, { signal: requestController.signal });
    } catch (err) {
      if (err.message === '研究已停止') {
        markResearchStopped(research);
      } else {
        setError(`恢复研究失败: ${err.message}`);
      }
    } finally {
      if (activeRequestControllerRef.current === requestController) {
        activeRequestControllerRef.current = null;
      }
      setIsResearching(false);
    }
  };

  const handleNewResearch = () => {
    activeRequestControllerRef.current?.abort();
    activeRequestControllerRef.current = null;
    activeResearchRef.current = null;
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
    let cancelled = false;
    const activeStatuses = new Set(['pending', 'in_progress', 'planning', 'researching', 'reporting']);
    const isStaleActiveResearch = (timestamp) => {
      if (!timestamp) return true;
      const updatedAt = new Date(timestamp).getTime();
      return Number.isNaN(updatedAt) || Date.now() - updatedAt > 10 * 60 * 1000;
    };

    const loadCurrentResearch = async () => {
      if (!currentResearch) {
        activeRequestControllerRef.current = null;
        activeResearchRef.current = null;
        setIsResearching(false);
        setResearchData(null);
        setStreamingData([]);
        setError(null);
        return;
      }
      if (activeRequestControllerRef.current && activeResearchRef.current?.id === currentResearch.id) {
        // When switching back from a historical report to the still-active task,
        // restore the streaming view instead of bailing out with stale report UI.
        setError(null);
        setResearchData(null);
        setIsResearching(true);
        if (isMobile) {
          setSidebarOpen(false);
        }
        return;
      }

      setError(null);
      setStreamingData([]);
      setResearchData(null);
      setIsResearching(activeStatuses.has(currentResearch.status));

      if (currentResearch.status === 'failed' && currentResearch.error === '研究已停止') {
        setError('研究已停止');
        setIsResearching(false);
        if (isMobile) {
          setSidebarOpen(false);
        }
        return;
      }

      if (currentResearch.result) {
        setResearchData(currentResearch.result);
        setIsResearching(false);
      } else if (currentResearch.isTemporaryId) {
        const temporaryAgeMs = Date.now() - new Date(currentResearch.timestamp).getTime();
        if (activeStatuses.has(currentResearch.status) && temporaryAgeMs < 5000) {
          setStreamingData([
            {
              type: 'planning',
              message: '正在创建研究任务...',
              data: null,
            },
          ]);
          setIsResearching(true);
        } else {
          setIsResearching(false);
          setError('这条历史记录缺少服务器任务 ID，无法恢复。请重新发起一次研究。');
        }
        if (isMobile) {
          setSidebarOpen(false);
        }
        return;
      } else {
        try {
          const remoteResearch = await researchAPI.getResearchTask(currentResearch.id);
          if (cancelled) {
            return;
          }

          const normalizedStatus = activeStatuses.has(remoteResearch.status)
            ? 'in_progress'
            : remoteResearch.status;

          if (remoteResearch.final_report) {
            const hydrated = {
              id: remoteResearch.id,
              query: remoteResearch.query,
              status: remoteResearch.status,
              plan: (remoteResearch.sections || []).map((section) => ({
                step: section.step,
                title: section.title,
                description: section.description,
                tool: section.tool,
                search_queries: section.search_queries,
                expected_outcome: section.expected_outcome,
              })),
              sections: remoteResearch.sections || [],
              results: (remoteResearch.sections || []).map((section) => ({
                title: section.title,
                status: section.status,
                analysis: section.analysis,
                citations: section.citations || [],
                search_sources: section.search_sources || [],
                verification: section.verification || {},
                compressed_evidence: section.compressed_evidence || '',
              })),
              report: remoteResearch.final_report,
              timestamp: remoteResearch.completed_at || remoteResearch.updated_at,
            };
            setResearchData(hydrated);
            setIsResearching(false);
            updateResearch(currentResearch.id, {
              result: hydrated,
              status: remoteResearch.status === 'completed' ? 'completed' : currentResearch.status,
            });
          } else {
            const nextTimestamp = remoteResearch.updated_at || currentResearch.timestamp;
            if (activeStatuses.has(remoteResearch.status)) {
              const stale = isStaleActiveResearch(nextTimestamp);
              const nextStatus = stale ? 'failed' : normalizedStatus;
              const nextError = stale
                ? '这条研究已中断，请重新发起研究。'
                : '这条研究尚未完成，当前页面没有活跃连接。请点击历史项的恢复按钮继续。';
              if (
                currentResearch.status !== nextStatus ||
                currentResearch.error !== nextError ||
                currentResearch.timestamp !== nextTimestamp
              ) {
                updateResearch(currentResearch.id, {
                  status: nextStatus,
                  error: nextError,
                  timestamp: nextTimestamp,
                });
              }
              setError(nextError);
              setIsResearching(false);
              return;
            }

            if (remoteResearch.status === 'failed') {
              const nextError = remoteResearch.error || '研究失败';
              if (
                currentResearch.status !== 'failed' ||
                currentResearch.error !== nextError ||
                currentResearch.timestamp !== nextTimestamp
              ) {
                updateResearch(currentResearch.id, {
                  status: 'failed',
                  error: nextError,
                  timestamp: nextTimestamp,
                });
              }
              setError(nextError);
              setIsResearching(false);
              return;
            }

            if (
              currentResearch.status !== normalizedStatus ||
              currentResearch.timestamp !== nextTimestamp
            ) {
              updateResearch(currentResearch.id, {
                status: normalizedStatus,
                timestamp: nextTimestamp,
              });
            }
            setIsResearching(false);
          }
        } catch (err) {
          console.error('加载远程研究详情失败:', err);
          if (!cancelled) {
            setIsResearching(false);
          }
        }
      }

      if (isMobile) {
        setSidebarOpen(false);
      }
    };

    loadCurrentResearch();

    return () => {
      cancelled = true;
    };
  }, [currentResearch, isMobile, updateResearch]);

  // 判断是否显示空状态
  const showEmptyState = !isResearching && !researchData && !currentResearch;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white">
      <Header
        onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        onLoginClick={() => setAuthModalOpen(true)}
      />

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden pt-14">
        <Sidebar
          backendStatus={backendStatus}
          onNewResearch={handleNewResearch}
          onResumeResearch={handleResumeResearch}
          isMobile={isMobile}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-container mx-auto px-lg py-lg">
            {showEmptyState && (
              <EmptyState onExampleClick={handleExampleClick} />
            )}

            {!showEmptyState && (
              <div className="mb-8">
                <SearchForm
                  onSubmit={handleStartResearch}
                  onStop={handleStopResearch}
                  isLoading={isResearching}
                  disabled={backendStatus === 'offline'}
                />
              </div>
            )}

            {error && !showEmptyState && (
              <div
                className="mb-8"
                style={{
                  background: '#FFFFFF',
                  border: '1px solid rgba(14,15,12,0.12)',
                  borderRadius: '30px',
                  boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px',
                  padding: '14px 18px',
                }}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="inline-flex items-center justify-center rounded-full flex-shrink-0"
                    style={{ width: '32px', height: '32px', background: 'rgba(208,50,56,0.08)', color: '#d03238' }}
                  >
                    <AlertCircle className="w-4 h-4" />
                  </span>
                  <p style={{ color: '#0e0f0c', fontSize: '16px', fontWeight: 600, lineHeight: 1.4, margin: 0 }}>
                    {error}
                  </p>
                </div>
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

      {authModalOpen && (
        <AuthPage onClose={() => setAuthModalOpen(false)} />
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <HistoryProvider>
        <AppContent />
      </HistoryProvider>
    </AuthProvider>
  );
}

export default App;
