import axios from 'axios';

// API基础配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
console.log('API_BASE_URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json',
  },
});

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
    try {
      const response = await fetch(`${API_BASE_URL}/api/research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          stream: true
        })
      });

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
            onUpdate(data);
          } catch {
            pendingData = candidate;
            console.warn('等待更多数据以完成JSON解析');
          }
        }
      }

      if (pendingData) {
        try {
          const data = JSON.parse(pendingData);
          onUpdate(data);
        } catch {
          console.warn('流结束时仍存在无法解析的JSON片段:', pendingData);
        }
      }
    } catch (error) {
      console.error('流式请求失败:', error);
      throw error;
    }
  },

  // 开始研究（非流式）
  startResearch: async (query) => {
    const response = await api.post('/api/research', {
      query: query,
      stream: false
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
