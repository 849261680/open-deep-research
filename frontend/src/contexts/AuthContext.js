import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);
const RESEARCH_HISTORY_KEY = 'research-history';

function getAnonymousTaskIds() {
  try {
    const raw = localStorage.getItem(RESEARCH_HISTORY_KEY);
    if (!raw) {
      return [];
    }

    const history = JSON.parse(raw);
    if (!Array.isArray(history)) {
      return [];
    }

    return history
      .filter((item) => item && typeof item.id === 'string' && !item.isTemporaryId)
      .map((item) => item.id);
  } catch (_error) {
    return [];
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // 初始化时检查 token

  // 启动时尝试恢复登录状态
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    authAPI.getMe()
      .then((u) => setUser(u))
      .catch(() => localStorage.removeItem('access_token'))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token } = await authAPI.login(email, password);
    localStorage.setItem('access_token', access_token);
    const taskIds = getAnonymousTaskIds();
    if (taskIds.length > 0) {
      await authAPI.claimHistory(taskIds);
    }
    const u = await authAPI.getMe();
    setUser(u);
  }, []);

  const register = useCallback(async (email, password) => {
    const { access_token } = await authAPI.register(email, password);
    localStorage.setItem('access_token', access_token);
    const taskIds = getAnonymousTaskIds();
    if (taskIds.length > 0) {
      await authAPI.claimHistory(taskIds);
    }
    const u = await authAPI.getMe();
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
