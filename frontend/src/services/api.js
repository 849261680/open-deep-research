import axios from 'axios';
import errorHandler from './errorHandler';

// API基础配置 - 优先使用生产环境配置，然后是本地配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                    (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 
                     window.location.origin.includes('railway.app') ? 
                     `${window.location.protocol}//${window.location.hostname}` : 
                     'http://localhost:8000');
console.log('API_BASE_URL:', API_BASE_URL);
console.log('当前域名:', window.location.hostname);

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

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log('API请求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('API响应:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

// 研究API
export const researchAPI = {
  // 开始研究（流式）
  startResearchStream: async (query, onUpdate) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10分钟超时

    try {
      const response = await fetch(`${API_BASE_URL}/api/research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
        },
        body: JSON.stringify({
          query: query,
          stream: true
        }),
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

          const payload = dataLines.join('\n').trim();
          if (!payload || payload === '[DONE]') {
            continue;
          }

          const candidate = pendingData ? `${pendingData}${payload}` : payload;

          try {
            const data = JSON.parse(candidate);
            pendingData = '';
            console.log('🔍 [API调试] 成功解析JSON数据:', data);
            console.log('🔍 [API调试] 数据类型:', data.type);
            onUpdate(data);
          } catch (error) {
            pendingData = candidate;
            console.warn('⚠️ [API调试] JSON解析失败，等待更多数据:', error);
            console.warn('⚠️ [API调试] 待解析数据:', candidate);
          }
        }
      }

      if (pendingData) {
        try {
          const data = JSON.parse(pendingData);
          console.log('🔍 [API调试] 流结束时成功解析剩余数据:', data);
          onUpdate(data);
        } catch (error) {
          console.warn('❌ [API调试] 流结束时仍存在无法解析的JSON片段:', pendingData);
          console.warn('❌ [API调试] 解析错误:', error);
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        console.error('流式请求超时:', error);
        throw new Error('请求超时，请重试');
      } else if (error.message.includes('Failed to fetch') || 
                 error.message.includes('NetworkError') ||
                 error.message.includes('ERR_CONNECTION_CLOSED')) {
        console.error('网络连接错误:', error);
        throw new Error('网络连接失败，请检查网络连接或稍后重试');
      } else {
        console.error('流式请求失败:', error);
        throw error;
      }
    }
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

export default api;
