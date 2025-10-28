// 简化的日志记录器，使用console.log替代winston
const timestamp = () => new Date().toISOString();

// 导出日志方法
const logger = {
  error: (message, meta) => console.error(`[${timestamp()}] ERROR:`, message, meta || ''),
  warn: (message, meta) => console.warn(`[${timestamp()}] WARN:`, message, meta || ''),
  info: (message, meta) => console.info(`[${timestamp()}] INFO:`, message, meta || ''),
  http: (message, meta) => console.log(`[${timestamp()}] HTTP:`, message, meta || ''),
  debug: (message, meta) => console.log(`[${timestamp()}] DEBUG:`, message, meta || '')
};

export default logger;
