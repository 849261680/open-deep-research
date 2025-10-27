import logger from './logger';

// 标准错误格式
class ApiError extends Error {
  constructor(message, statusCode, details) {
    super(message);
    this.statusCode = statusCode;
    this.details = details;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

// 全局错误处理器
const errorHandler = {
  // 处理API错误
  handleApiError: (error) => {
    if (error.response) {
      // 服务器响应错误
      return new ApiError(
        error.response.data?.message || '服务器错误',
        error.response.status,
        error.response.data
      );
    } else if (error.request) {
      // 请求已发出但无响应
      return new ApiError('网络错误，请检查网络连接', 503);
    } else {
      // 其他错误
      return new ApiError(error.message || '未知错误', 500);
    }
  },

  // 错误重试机制
  withRetry: async (fn, retries = 3, delay = 1000) => {
    try {
      return await fn();
    } catch (error) {
      if (retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
        return errorHandler.withRetry(fn, retries - 1, delay * 2);
      }
      throw error;
    }
  },

  // 日志记录
    logError: (error) => {
      logger.error({
        message: error.message,
        statusCode: error.statusCode,
        stack: error.stack,
        details: error.details,
      });
    },
};

export default errorHandler;