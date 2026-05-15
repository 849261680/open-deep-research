import { useCallback, useEffect, useRef, useState } from 'react';
import { researchAPI } from '../services/api';

const ACTIVE_RESEARCH_STATUSES = new Set([
  'pending',
  'in_progress',
  'planning',
  'researching',
  'reporting',
]);

// 判断后端活跃任务是否已经失去可恢复连接。
const isStaleActiveResearch = (timestamp) => {
  if (!timestamp) return true;
  const updatedAt = new Date(timestamp).getTime();
  return Number.isNaN(updatedAt) || Date.now() - updatedAt > 10 * 60 * 1000;
};

// 把后端任务详情转换成结果页可直接渲染的数据。
export const hydrateResearchTask = (remoteResearch) => ({
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
  quality_summary: remoteResearch.quality_summary || {},
  claim_checks: remoteResearch.claim_checks || [],
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
});

// 管理单个研究运行、恢复、停止和历史详情加载状态。
export const useResearchRun = ({
  currentResearch,
  addResearch,
  updateResearch,
  replaceResearchId,
  setCurrentResearch,
  onHistorySelection,
}) => {
  const [isResearching, setIsResearching] = useState(false);
  const [researchData, setResearchData] = useState(null);
  const [streamingData, setStreamingData] = useState([]);
  const [error, setError] = useState(null);
  const activeRequestControllerRef = useRef(null);
  const activeResearchRef = useRef(null);
  const currentResearchIdRef = useRef(null);
  const streamingUpdatesByResearchIdRef = useRef(new Map());

  useEffect(() => {
    currentResearchIdRef.current = currentResearch?.id || null;
  }, [currentResearch?.id]);

  const appendStreamingUpdate = useCallback((researchId, update) => {
    const previousUpdates = streamingUpdatesByResearchIdRef.current.get(researchId) || [];
    const nextUpdates = [...previousUpdates, update];
    streamingUpdatesByResearchIdRef.current.set(researchId, nextUpdates);
    if (currentResearchIdRef.current === researchId) {
      setStreamingData(nextUpdates);
    }
  }, []);

  const resetStreamingUpdates = useCallback((researchId) => {
    streamingUpdatesByResearchIdRef.current.set(researchId, []);
    if (currentResearchIdRef.current === researchId) {
      setStreamingData([]);
    }
  }, []);

  const migrateStreamingUpdates = useCallback((oldId, newId) => {
    const updates = streamingUpdatesByResearchIdRef.current.get(oldId) || [];
    streamingUpdatesByResearchIdRef.current.delete(oldId);
    streamingUpdatesByResearchIdRef.current.set(newId, updates);
    if (currentResearchIdRef.current === oldId) {
      currentResearchIdRef.current = newId;
      setStreamingData(updates);
    }
  }, []);

  const restoreStreamingUpdates = useCallback((researchId) => {
    setStreamingData(streamingUpdatesByResearchIdRef.current.get(researchId) || []);
  }, []);

  const markResearchStopped = useCallback((research) => {
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
  }, [updateResearch]);

  const handleStopResearch = useCallback(async () => {
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
  }, [currentResearch, markResearchStopped]);

  const handleStartResearch = useCallback(async (query) => {
    const requestController = new AbortController();
    activeRequestControllerRef.current = requestController;
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);

    const research = addResearch({
      query,
      status: 'in_progress',
    });
    activeResearchRef.current = research;
    currentResearchIdRef.current = research.id;
    resetStreamingUpdates(research.id);

    try {
      await researchAPI.startResearchStream(query, (update) => {
        const normalizedUpdate = {
          ...update,
          timestamp: update.timestamp || new Date().toISOString(),
        };

        const serverTaskId = normalizedUpdate.data?.task_id || normalizedUpdate.data?.id;
        if (serverTaskId && serverTaskId !== research.id) {
          migrateStreamingUpdates(research.id, serverTaskId);
          replaceResearchId(research.id, serverTaskId);
          research.id = serverTaskId;
          research.isTemporaryId = false;
          activeResearchRef.current = research;
        }
        appendStreamingUpdate(research.id, normalizedUpdate);

        if (normalizedUpdate.type === 'report_complete') {
          if (currentResearchIdRef.current === research.id) {
            setResearchData(normalizedUpdate.data);
          }
          updateResearch(research.id, {
            result: normalizedUpdate.data,
            status: 'completed',
          });
          activeResearchRef.current = null;
        } else if (normalizedUpdate.type === 'error') {
          if (currentResearchIdRef.current === research.id) {
            setError(normalizedUpdate.message);
          }
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
  }, [
    addResearch,
    appendStreamingUpdate,
    markResearchStopped,
    migrateStreamingUpdates,
    replaceResearchId,
    resetStreamingUpdates,
    updateResearch,
  ]);

  const handleResumeResearch = useCallback(async (research) => {
    const requestController = new AbortController();
    activeRequestControllerRef.current = requestController;
    activeResearchRef.current = research;
    setIsResearching(true);
    setError(null);
    setResearchData(null);
    setStreamingData([]);
    setCurrentResearch(research);
    currentResearchIdRef.current = research.id;
    resetStreamingUpdates(research.id);

    try {
      await researchAPI.resumeResearchStream(research.id, (update) => {
        const normalizedUpdate = {
          ...update,
          timestamp: update.timestamp || new Date().toISOString(),
        };
        appendStreamingUpdate(research.id, normalizedUpdate);

        if (normalizedUpdate.type === 'report_complete') {
          if (currentResearchIdRef.current === research.id) {
            setResearchData(normalizedUpdate.data);
          }
          updateResearch(research.id, {
            result: normalizedUpdate.data,
            status: 'completed',
            timestamp: normalizedUpdate.data.timestamp || normalizedUpdate.timestamp,
          });
          activeResearchRef.current = null;
        } else if (normalizedUpdate.type === 'error') {
          if (currentResearchIdRef.current === research.id) {
            setError(normalizedUpdate.message);
          }
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
  }, [
    appendStreamingUpdate,
    markResearchStopped,
    resetStreamingUpdates,
    setCurrentResearch,
    updateResearch,
  ]);

  const handleNewResearch = useCallback(() => {
    activeRequestControllerRef.current?.abort();
    activeRequestControllerRef.current = null;
    activeResearchRef.current = null;
    setCurrentResearch(null);
    setResearchData(null);
    setStreamingData([]);
    setError(null);
  }, [setCurrentResearch]);

  useEffect(() => {
    let cancelled = false;

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
        setError(null);
        setResearchData(null);
        restoreStreamingUpdates(currentResearch.id);
        setIsResearching(true);
        onHistorySelection?.();
        return;
      }

      setError(null);
      setStreamingData([]);
      setResearchData(null);
      setIsResearching(ACTIVE_RESEARCH_STATUSES.has(currentResearch.status));

      if (currentResearch.status === 'failed' && currentResearch.error === '研究已停止') {
        setError('研究已停止');
        setIsResearching(false);
        onHistorySelection?.();
        return;
      }

      if (currentResearch.result) {
        setResearchData(currentResearch.result);
        setIsResearching(false);
      } else if (currentResearch.isTemporaryId) {
        const temporaryAgeMs = Date.now() - new Date(currentResearch.timestamp).getTime();
        if (ACTIVE_RESEARCH_STATUSES.has(currentResearch.status) && temporaryAgeMs < 5000) {
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
        onHistorySelection?.();
        return;
      } else {
        try {
          const remoteResearch = await researchAPI.getResearchTask(currentResearch.id);
          if (cancelled) {
            return;
          }

          const normalizedStatus = ACTIVE_RESEARCH_STATUSES.has(remoteResearch.status)
            ? 'in_progress'
            : remoteResearch.status;

          if (remoteResearch.final_report) {
            const hydrated = hydrateResearchTask(remoteResearch);
            setResearchData(hydrated);
            setIsResearching(false);
            updateResearch(currentResearch.id, {
              result: hydrated,
              status: remoteResearch.status === 'completed' ? 'completed' : currentResearch.status,
            });
          } else {
            const nextTimestamp = remoteResearch.updated_at || currentResearch.timestamp;
            if (ACTIVE_RESEARCH_STATUSES.has(remoteResearch.status)) {
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

      onHistorySelection?.();
    };

    loadCurrentResearch();

    return () => {
      cancelled = true;
    };
  }, [
    currentResearch,
    onHistorySelection,
    restoreStreamingUpdates,
    updateResearch,
  ]);

  return {
    isResearching,
    researchData,
    streamingData,
    error,
    handleStartResearch,
    handleStopResearch,
    handleResumeResearch,
    handleNewResearch,
  };
};
