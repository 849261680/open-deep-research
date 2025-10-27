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

// JSON处理工具方法
const jsonUtils = {
  // 验证JSON字符串是否有效
  isValidJSON: (str) => {
    try {
      JSON.parse(str);
      return true;
    } catch (e) {
      return false;
    }
  },

  // 尝试修复不完整的JSON
  tryFixJSON: (jsonStr, onUpdate) => {
    if (!jsonStr || jsonStr === '[DONE]') return;
    
    try {
      // 尝试添加缺失的引号或括号
      let fixedJsonStr = jsonStr;
      
      // 检查是否缺少结束引号
      if (!fixedJsonStr.endsWith('"') && fixedJsonStr.includes('"')) {
        const quoteCount = (fixedJsonStr.match(/"/g) || []).length;
        if (quoteCount % 2 !== 0) {
          fixedJsonStr += '"';
        }
      }
      
      // 检查是否缺少结束括号
      if (!fixedJsonStr.endsWith('}') && !fixedJsonStr.endsWith(']')) {
        const openBraceCount = (fixedJsonStr.match(/{/g) || []).length;
        const closeBraceCount = (fixedJsonStr.match(/}/g) || []).length;
        const openBracketCount = (fixedJsonStr.match(/\[/g) || []).length;
        const closeBracketCount = (fixedJsonStr.match(/\]/g) || []).length;
        
        if (openBraceCount > closeBraceCount) {
          fixedJsonStr += '}';
        } else if (openBracketCount > closeBracketCount) {
          fixedJsonStr += ']';
        } else {
          // 默认添加对象结束符
          fixedJsonStr += '}';
        }
      }
      
      if (jsonUtils.isValidJSON(fixedJsonStr)) {
        const data = JSON.parse(fixedJsonStr);
        console.warn('已修复不完整的JSON数据');
        onUpdate(data);
      } else {
        console.warn('无法修复JSON数据:', fixedJsonStr);
      }
    } catch (fixError) {
      console.warn('修复JSON数据失败:', fixError);
    }
  }
};

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

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.trim() && line.startsWith('data: ')) {
              try {
              const jsonStr = line.slice(6).trim();
              // 检查JSON字符串是否完整
              if (jsonStr && jsonStr !== '[DONE]') {
                // 验证JSON格式
                if (jsonUtils.isValidJSON(jsonStr)) {
                  const data = JSON.parse(jsonStr);
                  onUpdate(data);
                } else {
                  console.warn('无效的JSON格式，跳过:', jsonStr);
                }
              }
            } catch (parseError) {
              console.warn('解析流数据失败:', parseError, '数据:', line.slice(6));
              // 尝试修复不完整的JSON
              jsonUtils.tryFixJSON(line.slice(6).trim(), onUpdate);
            }
          }
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
