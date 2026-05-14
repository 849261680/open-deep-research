import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authAPI, getGuestId } from '../services/api';

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

function readOAuthTokenFromHash() {
  // 从后端 OAuth callback 写入的 URL fragment 中取出 JWT。
  const hash = window.location.hash.replace(/^#/, '');
  if (!hash) {
    return null;
  }

  const params = new URLSearchParams(hash);
  return params.get('auth_token');
}

function clearOAuthTokenFromUrl() {
  // 清理地址栏中的 token，避免用户复制 URL 时泄露登录态。
  window.history.replaceState(
    {},
    document.title,
    `${window.location.pathname}${window.location.search}`
  );
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // 初始化时检查 token

  // 启动时尝试恢复登录状态
  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      const oauthToken = readOAuthTokenFromHash();
      const token = oauthToken || localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      localStorage.setItem('access_token', token);
      if (oauthToken) {
        clearOAuthTokenFromUrl();
      }

      try {
        const u = await authAPI.getMe();
        if (oauthToken) {
          const taskIds = getAnonymousTaskIds();
          if (taskIds.length > 0) {
            await authAPI.claimHistory(taskIds, getGuestId());
          }
        }
        if (!cancelled) setUser(u);
      } catch (_error) {
        localStorage.removeItem('access_token');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    restoreSession();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token } = await authAPI.login(email, password);
    localStorage.setItem('access_token', access_token);
    const taskIds = getAnonymousTaskIds();
    if (taskIds.length > 0) {
      await authAPI.claimHistory(taskIds, getGuestId());
    }
    const u = await authAPI.getMe();
    setUser(u);
  }, []);

  const register = useCallback(async (email, password) => {
    const { access_token } = await authAPI.register(email, password);
    localStorage.setItem('access_token', access_token);
    const taskIds = getAnonymousTaskIds();
    if (taskIds.length > 0) {
      await authAPI.claimHistory(taskIds, getGuestId());
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
