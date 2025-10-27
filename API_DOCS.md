# API 文档

## 前端 API

### `startResearchStream(query, onUpdate)`

- **描述**: 启动流式研究任务
- **请求方法**: POST
- **请求 URL**: `/api/research`
- **请求参数**:
  - `query`: 研究问题 (string)
  - `onUpdate`: 数据更新回调函数 (function)
- **响应格式**: 流式 JSON 数据
- **示例**:

```javascript
researchAPI.startResearchStream("AI发展趋势", (data) => {
  console.log("收到更新:", data);
});
```

### `startResearch(query)`

- **描述**: 启动非流式研究任务
- **请求方法**: POST
- **请求 URL**: `/api/research`
- **请求参数**:
  - `query`: 研究问题 (string)
- **响应格式**: JSON
- **示例**:

```javascript
const result = await researchAPI.startResearch("AI发展趋势");
```

### `getResearchStatus()`

- **描述**: 获取研究状态
- **请求方法**: GET
- **请求 URL**: `/api/research/status`
- **响应格式**: JSON
- **示例**:

```javascript
const status = await researchAPI.getResearchStatus();
```

### `getResearchHistory()`

- **描述**: 获取研究历史
- **请求方法**: GET
- **请求 URL**: `/api/research/history`
- **响应格式**: JSON
- **示例**:

```javascript
const history = await researchAPI.getResearchHistory();
```

### `clearResearchHistory()`

- **描述**: 清空研究历史
- **请求方法**: DELETE
- **请求 URL**: `/api/research/history`
- **响应格式**: JSON
- **示例**:

```javascript
await researchAPI.clearResearchHistory();
```

### `healthCheck()`

- **描述**: 健康检查
- **请求方法**: GET
- **请求 URL**: `/api/health`
- **响应格式**: JSON
- **示例**:

```javascript
const health = await researchAPI.healthCheck();
```

## 后端 API

### `POST /api/research`

- **描述**: 启动研究任务
- **请求体**:
  - `query`: 研究问题 (string)
  - `stream`: 是否使用流式响应 (boolean, 可选)
- **响应格式**:
  - 流式: text/event-stream
  - 非流式: JSON
- **示例**:

```json
{
  "query": "AI发展趋势",
  "stream": true
}
```

### `GET /api/research/status`

- **描述**: 获取研究状态
- **响应格式**: JSON
- **示例响应**:

```json
{
  "status": "ready",
  "steps": [],
  "message": "研究代理已准备就绪"
}
```

### `GET /api/research/history`

- **描述**: 获取研究历史
- **响应格式**: JSON
- **示例响应**:

```json
{
  "history": [],
  "total": 0
}
```

### `DELETE /api/research/history`

- **描述**: 清空研究历史
- **响应格式**: JSON
- **示例响应**:

```json
{
  "message": "研究历史和记忆已清空"
}
```

### `GET /api/health`

- **描述**: 健康检查
- **响应格式**: JSON
- **示例响应**:

```json
{
  "status": "healthy",
  "message": "Deep Research Agent API is running"
}
```
