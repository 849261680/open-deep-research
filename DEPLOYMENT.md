# 🚀 部署指南

本指南将帮助您在Vercel（前端）和Railway（后端）上部署Research Agent项目。

## 📋 部署概览

- **前端**: Vercel - React应用托管
- **后端**: Railway - FastAPI应用托管
- **数据库**: 无需数据库（使用API服务）

## 🔧 前期准备

### 1. 获取API密钥

#### DeepSeek API
1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册并登录账号
3. 在API管理中创建新密钥
4. 复制API密钥备用

#### Tavily Search API
1. 访问 [Tavily官网](https://tavily.com/)
2. 注册获取免费API密钥（1000次/月）
3. 复制API密钥备用

### 2. 准备GitHub仓库
确保您的代码已推送到GitHub仓库。

## 🚂 Railway后端部署

### 步骤1: 连接GitHub仓库

1. 访问 [Railway官网](https://railway.app/)
2. 使用GitHub账号登录
3. 点击 "New Project"
4. 选择 "Deploy from GitHub repo"
5. 选择您的 `research-gpt` 仓库

### 步骤2: 配置部署设置

1. **选择服务**: 
   - 点击仓库后，Railway会检测到多个服务
   - 选择 `backend` 文件夹

2. **配置根目录**:
   ```
   Root Directory: /backend
   ```

3. **配置启动命令**:
   ```
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### 步骤3: 设置环境变量

在Railway项目设置中添加以下环境变量：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
FRONTEND_URL=https://your-vercel-domain.vercel.app
```

### 步骤4: 部署

1. 点击 "Deploy"
2. 等待构建完成
3. 获取Railway提供的域名（例如：`https://xxx.railway.app`）

## ⚡ Vercel前端部署

### 步骤1: 连接GitHub仓库

1. 访问 [Vercel官网](https://vercel.com/)
2. 使用GitHub账号登录
3. 点击 "New Project"
4. 选择您的 `research-gpt` 仓库
5. 点击 "Import"

### 步骤2: 配置项目设置

1. **Framework Preset**: 选择 `Create React App`

2. **Root Directory**: 设置为 `frontend`

3. **Build and Output Settings**:
   ```
   Build Command: npm run build
   Output Directory: build
   Install Command: npm install
   ```

### 步骤3: 设置环境变量

在Vercel项目设置中添加环境变量：

```env
REACT_APP_API_URL=https://your-railway-domain.railway.app
```

### 步骤4: 部署

1. 点击 "Deploy"
2. 等待构建完成
3. 获取Vercel提供的域名

## 🔄 更新后端CORS设置

部署完成后，需要更新Railway后端的环境变量：

```env
FRONTEND_URL=https://your-vercel-domain.vercel.app
```

## ✅ 验证部署

### 1. 测试后端API
访问Railway域名的健康检查端点：
```
https://your-railway-domain.railway.app/api/health
```

应该返回：
```json
{
  "status": "healthy",
  "service": "Deep Research Agent API"
}
```

### 2. 测试前端应用
访问Vercel域名：
```
https://your-vercel-domain.vercel.app
```

### 3. 测试完整功能
1. 在前端输入研究主题
2. 点击"开始深度研究"
3. 观察实时进度显示
4. 等待研究报告生成

## 🚨 常见问题

### 问题1: CORS错误
**症状**: 前端无法连接后端，浏览器控制台显示CORS错误

**解决方案**:
1. 确认Railway环境变量 `FRONTEND_URL` 设置正确
2. 检查Vercel域名是否正确添加到CORS设置中

### 问题2: API调用失败
**症状**: 后端返回401或403错误

**解决方案**:
1. 检查DeepSeek和Tavily API密钥是否正确设置
2. 确认API密钥仍有效且有足够配额

### 问题3: 构建失败
**症状**: Vercel或Railway构建过程中出错

**解决方案**:
1. 检查依赖项是否完整
2. 确认Node.js/Python版本兼容性
3. 查看构建日志定位具体错误

### 问题4: 应用启动失败
**症状**: Railway应用部署后无法启动

**解决方案**:
1. 检查启动命令是否正确
2. 确认端口配置使用 `$PORT` 环境变量
3. 查看Railway日志了解错误详情

## 🔧 高级配置

### 1. 自定义域名

#### Vercel
1. 在项目设置中点击 "Domains"
2. 添加您的自定义域名
3. 按照提示配置DNS记录

#### Railway
1. 在项目设置中点击 "Custom Domain"
2. 添加您的域名
3. 配置CNAME记录指向Railway

### 2. 环境管理

#### 多环境设置
```env
# 开发环境
ENVIRONMENT=development
REACT_APP_API_URL=http://localhost:8000

# 生产环境
ENVIRONMENT=production
REACT_APP_API_URL=https://your-railway-domain.railway.app
```

### 3. 监控和日志

#### Railway监控
- 在项目仪表板查看实时指标
- 设置告警规则
- 查看应用日志

#### Vercel监控
- 在项目仪表板查看部署状态
- 监控函数执行
- 查看访问分析

## 📈 性能优化

### 1. 后端优化
```python
# 在环境变量中设置
MAX_TOKENS=1500
REQUEST_TIMEOUT=60
SEARCH_RESULTS_LIMIT=8
```

### 2. 前端优化
```javascript
// 在build时优化
{
  "scripts": {
    "build": "GENERATE_SOURCEMAP=false react-scripts build"
  }
}
```

## 🔄 CI/CD自动部署

### GitHub Actions示例

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel and Railway

on:
  push:
    branches: [ main ]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          working-directory: ./frontend

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@v1.0.0
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: ${{ secrets.RAILWAY_SERVICE_ID }}
```

## 📞 获取帮助

如果遇到部署问题：

1. **查看日志**: 在Vercel和Railway控制台查看详细日志
2. **检查文档**: 参考官方文档
3. **社区支持**: 在GitHub Issues中提问
4. **联系支持**: 通过平台官方渠道获取技术支持

## 🎉 部署完成

恭喜！您的Research Agent现在已经成功部署到云端。享受您的智能研究助手吧！

---

**下一步**: 考虑设置监控、备份和扩展策略，确保应用的稳定运行。