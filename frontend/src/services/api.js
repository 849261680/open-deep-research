import axios from 'axios';
import errorHandler from './errorHandler';

// API基础配置 - 优先使用生产环境配置，然后是本地配置
const API_BASE_URL = process.env.REACT_APP_API_URL ||
                    (window.location.hostname === 'localhost' ? 'http://localhost:8000' :
                     window.location.origin.includes('railway.app') ?
                     `${window.location.protocol}//${window.location.hostname}` :
                     'http://localhost:8000');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加统一的错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const handledError = errorHandler.handleApiError(error);
    errorHandler.logError(handledError);
    return Promise.reject(handledError);
  }
);

// 请求拦截器：自动附加 JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);


// 研究API
export const researchAPI = {
  streamRequest: async (url, payload, onUpdate, options = {}) => {
    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 600000);

    const handleExternalAbort = () => controller.abort();
    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort();
      } else {
        options.signal.addEventListener('abort', handleExternalAbort, { once: true });
      }
    }

    const token = localStorage.getItem('access_token');
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
          ...authHeaders,
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let pendingData = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let eventSeparatorIndex;
        while ((eventSeparatorIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, eventSeparatorIndex).trim();
          buffer = buffer.slice(eventSeparatorIndex + 2);

          if (!rawEvent) continue;

          const dataLines = rawEvent
            .split('\n')
            .filter(line => line.startsWith('data:'))
            .map(line => line.replace(/^data:\s*/, ''));

          if (dataLines.length === 0) {
            continue;
          }

          const candidate = pendingData ? `${pendingData}${dataLines.join('\n').trim()}` : dataLines.join('\n').trim();

          try {
            const data = JSON.parse(candidate);
            pendingData = '';
            onUpdate(data);
          } catch (error) {
            pendingData = candidate;
          }
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new Error(timedOut ? '请求超时，请重试' : '研究已停止');
      } else if (error.message.includes('Failed to fetch') ||
                 error.message.includes('NetworkError') ||
                 error.message.includes('ERR_CONNECTION_CLOSED')) {
        throw new Error('网络连接失败，请检查网络连接或稍后重试');
      } else {
        throw error;
      }
    } finally {
      clearTimeout(timeoutId);
      if (options.signal) {
        options.signal.removeEventListener('abort', handleExternalAbort);
      }
    }
  },

  // 开始研究（流式）
  startResearchStream: async (query, onUpdate, options = {}) => {
    return researchAPI.streamRequest('/api/research', {
      query,
      stream: true
    }, onUpdate, options);
  },

  resumeResearchStream: async (taskId, onUpdate, options = {}) => {
    return researchAPI.streamRequest('/api/research/resume', {
      task_id: taskId,
      stream: true
    }, onUpdate, options);
  },

  stopResearch: async (taskId) => {
    const response = await api.post('/api/research/stop', {
      task_id: taskId,
    });
    return response.data;
  },

  // 开始研究（非流式）
  startResearch: async (query) => {
    const response = await errorHandler.withRetry(async () => {
      return await api.post('/api/research', {
        query: query,
        stream: false
      });
    });
    return response.data;
  },

  // 获取研究状态
  getResearchStatus: async () => {
    const response = await api.get('/api/research/status');
    return response.data;
  },

  // 获取研究历史
  getResearchHistory: async () => {
    const response = await api.get('/api/research/history');
    return response.data;
  },

  getResearchTask: async (taskId) => {
    const response = await api.get(`/api/research/${taskId}`);
    return response.data;
  },

  // 清空研究历史
  clearResearchHistory: async () => {
    const response = await api.delete('/api/research/history');
    return response.data;
  },

  // 健康检查
  healthCheck: async () => {
    const response = await api.get('/api/health');
    return response.data;
  }
};

// 认证API
export const authAPI = {
  register: async (email, password) => {
    const response = await api.post('/api/auth/register', { email, password });
    return response.data;
  },

  login: async (email, password) => {
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  claimHistory: async (taskIds) => {
    const response = await api.post('/api/auth/claim-history', { task_ids: taskIds });
    return response.data;
  },
};

export default api;
