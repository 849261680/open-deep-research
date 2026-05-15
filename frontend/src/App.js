import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import SearchForm from './components/SearchForm';
import ResearchResults from './components/ResearchResults';
import LoadingSpinner from './components/LoadingSpinner';
import StreamingResults from './components/StreamingResults';
import EmptyState from './components/EmptyState';
import PlanConfirmation from './components/PlanConfirmation';
import { HistoryProvider, useHistory } from './contexts/HistoryContext';
import { AuthProvider } from './contexts/AuthContext';
import AuthPage from './components/AuthPage';
import { useResearchRun } from './hooks/useResearchRun';
import { researchAPI } from './services/api';

/**
 * Main App Component - 包含侧边栏布局的主应用
 */
function AppContent() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planDraft, setPlanDraft] = useState(null);
  const [planError, setPlanError] = useState(null);

  const {
    currentResearch,
    addResearch,
    updateResearch,
    replaceResearchId,
    setCurrentResearch,
  } = useHistory();

  const closeMobileSidebar = useCallback(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  const {
    isResearching,
    researchData,
    streamingData,
    error,
    handleStartResearch,
    handleStopResearch,
    handleResumeResearch,
    handleNewResearch,
  } = useResearchRun({
    currentResearch,
    addResearch,
    updateResearch,
    replaceResearchId,
    setCurrentResearch,
    onHistorySelection: closeMobileSidebar,
  });

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
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleNewResearchClick = () => {
    handleNewResearch();
    setPlanDraft(null);
    setPlanError(null);
    closeMobileSidebar();
  };

  const handlePlanRequest = async (query) => {
    setIsPlanning(true);
    setPlanError(null);
    setPlanDraft(null);
    try {
      const response = await researchAPI.previewResearchPlan(query);
      const data = response.data || response;
      setPlanDraft({
        query,
        plan_items: data.plan_items || [],
      });
    } catch (err) {
      console.error('研究计划生成失败:', err);
      setPlanError('研究计划生成失败，请稍后重试。');
    } finally {
      setIsPlanning(false);
    }
  };

  const handleConfirmPlan = (planItems) => {
    if (!planDraft) return;
    const query = planDraft.query;
    setPlanDraft(null);
    setPlanError(null);
    handleStartResearch(query, { planItems });
  };

  const handleExampleClick = (question) => {
    handlePlanRequest(question);
  };

  const visibleError = planError || error;
  const showEmptyState = !isPlanning && !isResearching && !researchData && !currentResearch && !planDraft;

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
          onNewResearch={handleNewResearchClick}
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
                  onSubmit={handlePlanRequest}
                  onStop={handleStopResearch}
                  isLoading={isResearching}
                  disabled={backendStatus === 'offline' || isPlanning}
                />
              </div>
            )}

            {visibleError && !showEmptyState && (
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
                    {visibleError}
                  </p>
                </div>
              </div>
            )}

            {isPlanning && (
              <div className="mt-8">
                <LoadingSpinner message="正在生成研究计划..." />
              </div>
            )}

            {planDraft && !isPlanning && !isResearching && (
              <PlanConfirmation
                plan={planDraft}
                onChange={setPlanDraft}
                onConfirm={handleConfirmPlan}
                onCancel={() => setPlanDraft(null)}
                isLoading={isResearching}
              />
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
