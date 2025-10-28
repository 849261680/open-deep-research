import React, { createContext, useContext, useState, useEffect } from 'react';
import logger from '../services/logger';

/**
 * HistoryContext - 历史记录状态管理
 *
 * 管理研究历史记录的增删改查
 * 支持 localStorage 缓存
 */
const HistoryContext = createContext();

export const useHistory = () => {
  const context = useContext(HistoryContext);
  if (!context) {
    throw new Error('useHistory must be used within a HistoryProvider');
  }
  return context;
};

export const HistoryProvider = ({ children }) => {
  const [history, setHistory] = useState([]);
  const [currentResearch, setCurrentResearch] = useState(null);
  const [loading, setLoading] = useState(true);

  // 从 localStorage 加载历史记录
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem('research-history');
      if (savedHistory) {
        const parsed = JSON.parse(savedHistory);
        setHistory(parsed);
        logger.info('Loaded history from localStorage', { count: parsed.length });
      }
    } catch (error) {
      logger.error('Failed to load history from localStorage', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 保存历史记录到 localStorage
  const saveToLocalStorage = (newHistory) => {
    try {
      localStorage.setItem('research-history', JSON.stringify(newHistory));
      logger.info('Saved history to localStorage', { count: newHistory.length });
    } catch (error) {
      logger.error('Failed to save history to localStorage', error);
    }
  };

  // 添加研究记录
  const addResearch = (research) => {
    const newResearch = {
      id: Date.now().toString(),
      query: research.query,
      result: research.result || null,
      status: research.status || 'pending', // pending, completed, failed
      timestamp: new Date().toISOString(),
      pinned: false,
      ...research,
    };

    const newHistory = [newResearch, ...history];
    setHistory(newHistory);
    setCurrentResearch(newResearch);
    saveToLocalStorage(newHistory);

    logger.info('Added research to history', { id: newResearch.id, query: newResearch.query });
    return newResearch;
  };

  // 更新研究记录
  const updateResearch = (id, updates) => {
    const newHistory = history.map((item) =>
      item.id === id ? { ...item, ...updates } : item
    );
    setHistory(newHistory);
    saveToLocalStorage(newHistory);

    // 如果更新的是当前研究，也更新 currentResearch
    if (currentResearch && currentResearch.id === id) {
      setCurrentResearch({ ...currentResearch, ...updates });
    }

    logger.info('Updated research in history', { id, updates });
  };

  // 删除研究记录
  const deleteResearch = (id) => {
    const newHistory = history.filter((item) => item.id !== id);
    setHistory(newHistory);
    saveToLocalStorage(newHistory);

    // 如果删除的是当前研究，清空 currentResearch
    if (currentResearch && currentResearch.id === id) {
      setCurrentResearch(null);
    }

    logger.info('Deleted research from history', { id });
  };

  // 固定/取消固定研究
  const togglePin = (id) => {
    const newHistory = history.map((item) =>
      item.id === id ? { ...item, pinned: !item.pinned } : item
    );
    // 将固定的项目移到前面
    newHistory.sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.timestamp) - new Date(a.timestamp);
    });
    setHistory(newHistory);
    saveToLocalStorage(newHistory);

    logger.info('Toggled pin for research', { id });
  };

  // 清空历史记录
  const clearHistory = () => {
    setHistory([]);
    setCurrentResearch(null);
    localStorage.removeItem('research-history');
    logger.info('Cleared all history');
  };

  // 加载特定研究
  const loadResearch = (id) => {
    const research = history.find((item) => item.id === id);
    if (research) {
      setCurrentResearch(research);
      logger.info('Loaded research', { id, query: research.query });
    }
    return research;
  };

  // 搜索历史记录
  const searchHistory = (searchTerm) => {
    if (!searchTerm) return history;

    const lowerSearchTerm = searchTerm.toLowerCase();
    return history.filter((item) =>
      item.query.toLowerCase().includes(lowerSearchTerm)
    );
  };

  // 按时间分组历史记录
  const groupedHistory = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const groups = {
      pinned: [],
      today: [],
      yesterday: [],
      lastWeek: [],
      older: [],
    };

    history.forEach((item) => {
      if (item.pinned) {
        groups.pinned.push(item);
        return;
      }

      const itemDate = new Date(item.timestamp);
      if (itemDate >= today) {
        groups.today.push(item);
      } else if (itemDate >= yesterday) {
        groups.yesterday.push(item);
      } else if (itemDate >= lastWeek) {
        groups.lastWeek.push(item);
      } else {
        groups.older.push(item);
      }
    });

    return groups;
  };

  const value = {
    history,
    currentResearch,
    loading,
    addResearch,
    updateResearch,
    deleteResearch,
    togglePin,
    clearHistory,
    loadResearch,
    searchHistory,
    groupedHistory,
    setCurrentResearch,
  };

  return (
    <HistoryContext.Provider value={value}>
      {children}
    </HistoryContext.Provider>
  );
};
