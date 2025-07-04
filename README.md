# Research Agent - 深度研究智能体

<div align="center">

![Research Agent](https://img.shields.io/badge/Research-Agent-blue?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![React](https://img.shields.io/badge/React-18+-blue?style=flat&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green?style=flat&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Latest-purple?style=flat)

**基于LangChain和DeepSeek的DeepResearch Agent**

[功能特色](#-功能特色) • [快速开始](#-快速开始) • [架构设计](#-架构设计) • [API文档](#-api文档) • [部署指南](#-部署指南)

</div>

## 📖 项目简介

Research Agent是一个基于AI的智能研究助手，能够自动制定研究计划、执行多源搜索、分析内容并生成专业的研究报告。系统采用现代化的前后端分离架构，提供流畅的实时交互体验。

### 🎯 核心能力

- **智能计划制定** - 基于DeepSeek AI自动生成结构化研究计划
- **多源数据搜索** - 集成Tavily Search等多个搜索引擎
- **实时进度追踪** - 动态显示搜索过程和结果详情
- **专业报告生成** - 自动分析并生成结构化研究报告
- **流式用户体验** - 实时显示研究进展和中间结果

## 🚀 功能特色

### 📊 研究工作流
```
用户查询 → 计划制定 → 多源搜索 → 内容分析 → 报告生成
```

### 🔍 搜索能力
- **Tavily Search** - 高质量网络搜索（1000次免费配额）
- **多查询策略** - 自动生成多个相关搜索词
- **结果筛选** - 智能过滤和排序搜索结果
- **来源追踪** - 显示具体的文章标题和链接

### 🧠 AI分析
- **DeepSeek集成** - 使用高性能中文大语言模型
- **链式处理** - LangChain工作流管理
- **内容摘要** - 自动提取关键信息
- **结构化输出** - 生成专业格式的研究报告

### 💻 用户界面
- **实时进度** - 动态显示研究步骤和进度
- **搜索详情** - 展示搜索到的具体内容和链接
- **响应式设计** - 支持桌面和移动设备
- **流畅动画** - 动态加载效果和状态提示

## 🛠 技术栈

### 后端技术
- **Python 3.10+** - 核心开发语言
- **FastAPI** - 高性能Web框架
- **LangChain** - AI应用开发框架
- **DeepSeek API** - 大语言模型服务
- **Tavily Search** - 搜索引擎集成
- **Asyncio** - 异步编程支持

### 前端技术
- **React 18** - 用户界面框架
- **Tailwind CSS** - 样式框架
- **Lucide React** - 图标库
- **Axios** - HTTP客户端

### 开发工具
- **Poetry/pip** - Python依赖管理
- **npm** - 前端包管理
- **Git** - 版本控制

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 16+
- Git

### 1. 克隆项目
```bash
git clone https://github.com/849261680/research-gpt.git
cd research-gpt
```

### 2. 后端配置

#### 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 环境变量配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

配置以下API密钥：
```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key

# Tavily Search API配置
TAVILY_API_KEY=your_tavily_api_key
```

#### 启动后端服务
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 3. 前端配置

#### 安装依赖
```bash
cd frontend
npm install
```

#### 启动开发服务器
```bash
npm start
```

### 4. 访问应用
打开浏览器访问：`http://localhost:3000`

## 🏗 架构设计

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React前端     │    │   FastAPI后端   │    │   外部服务      │
│                 │    │                 │    │                 │
│ • 用户界面      │◄──►│ • 研究代理      │◄──►│ • DeepSeek API  │
│ • 实时显示      │    │ • LangChain     │    │ • Tavily Search │
│ • 状态管理      │    │ • 工具集成      │    │ • 其他API       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 核心组件

#### 后端架构
```
app/
├── agents/              # AI代理
│   ├── langchain_research_agent.py  # 主研究代理
│   └── research_agent.py           # 备用代理
├── api/                 # API路由
│   └── research.py      # 研究接口
├── chains/              # LangChain工作流
│   └── research_chains.py  # 研究链
├── llms/                # 语言模型
│   └── deepseek_llm.py  # DeepSeek集成
├── services/            # 服务层
│   ├── deepseek_service.py  # DeepSeek服务
│   └── search_tools.py      # 搜索工具
├── tools/               # LangChain工具
│   └── search_tools.py  # 搜索工具定义
└── main.py              # FastAPI应用入口
```

#### 前端架构
```
src/
├── components/          # React组件
│   ├── Header.js        # 页面头部
│   ├── SearchForm.js    # 搜索表单
│   ├── StreamingResults.js  # 实时结果
│   └── ResearchResults.js   # 研究结果
├── services/            # 服务层
│   └── api.js           # API调用
├── App.js               # 应用入口
└── index.js             # React入口
```

### 数据流程

#### 研究流程
1. **用户输入** - 提交研究主题
2. **计划制定** - AI生成研究计划
3. **并行搜索** - 多查询词并行搜索
4. **内容分析** - 提取和分析关键信息
5. **报告生成** - 结构化输出研究报告

#### 实时通信
```
用户操作 → React状态更新 → API调用 → FastAPI处理 → 
流式响应 → 前端实时显示 → 用户界面更新
```

## 📚 API文档

### 研究接口

#### POST /api/research
开始一个新的研究任务

**请求体：**
```json
{
  "query": "人工智能在医疗领域的应用"
}
```

**响应：** Server-Sent Events (SSE)流

**事件类型：**
- `planning` - 正在制定计划
- `plan` - 计划制定完成
- `step_start` - 开始执行步骤
- `search_progress` - 搜索进度
- `search_result` - 搜索结果
- `analysis_progress` - 分析进度
- `step_complete` - 步骤完成
- `report_generating` - 生成报告
- `report_complete` - 研究完成

**示例响应：**
```json
{
  "type": "search_result",
  "message": "找到 6 个结果",
  "data": {
    "query": "AI医疗应用",
    "sources": [
      {
        "title": "AI在医疗诊断中的应用",
        "link": "https://example.com/article1",
        "source": "web"
      }
    ]
  }
}
```

## 🔧 配置指南

### API密钥获取

#### DeepSeek API
1. 访问 [DeepSeek官网](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在API管理中创建新的API密钥
4. 将密钥添加到 `.env` 文件中

#### Tavily Search API
1. 访问 [Tavily官网](https://tavily.com/)
2. 注册获取免费API密钥（1000次/月）
3. 将密钥添加到 `.env` 文件中

### 性能优化

#### 后端优化
```python
# 在 app/services/deepseek_service.py 中调整
max_tokens = 2000        # 限制输出长度
timeout = 90             # 增加超时时间
max_retries = 2          # 设置重试次数
```

#### 搜索优化
```python
# 在 app/services/search_tools.py 中调整
max_results = 10         # 每次搜索结果数
max_content_length = 300 # 内容截断长度
```

## 🚀 部署指南

> 📋 **快速部署**: 查看详细的 [部署指南文档](DEPLOYMENT.md) 了解Vercel和Railway部署步骤

### 🌐 云服务部署（推荐）

#### Vercel + Railway 部署
- **前端**: Vercel（免费托管React应用）  
- **后端**: Railway（免费托管FastAPI应用）
- **优势**: 零配置、自动部署、高可用性

```bash
# 运行部署检查工具
./deploy.sh

# 按照提示完成云端部署
# 详细步骤请查看 DEPLOYMENT.md
```

### 🐳 Docker部署

#### 1. 创建Dockerfile
```dockerfile
# 后端Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Docker Compose
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

#### 3. 启动服务
```bash
docker-compose up -d
```

### 云服务部署

#### Vercel（前端）
1. 连接GitHub仓库
2. 设置构建命令：`cd frontend && npm run build`
3. 设置输出目录：`frontend/build`

#### Railway/Heroku（后端）
1. 连接GitHub仓库
2. 设置环境变量
3. 配置启动命令：`cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 🔍 故障排除

### 常见问题

#### 1. API连接失败
```bash
# 检查API密钥配置
cat backend/.env

# 测试API连接
curl -X POST "http://localhost:8000/api/research" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试查询"}'
```

#### 2. 前端无法连接后端
```javascript
// 检查 frontend/src/services/api.js 中的基础URL
const API_BASE_URL = 'http://localhost:8000';
```

#### 3. 搜索结果为空
- 检查Tavily API密钥是否有效
- 确认网络连接正常
- 查看后端日志了解错误详情

#### 4. 响应速度慢
- 调整 `max_tokens` 参数
- 优化搜索结果数量
- 检查网络延迟

### 调试模式

#### 后端调试
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload --log-level debug
```

#### 前端调试
```bash
# 启用开发模式
npm start

# 查看网络请求
# 打开浏览器开发者工具 → Network标签
```

## 🤝 贡献指南

### 开发流程
1. Fork项目仓库
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -m 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建Pull Request

### 代码规范
- Python代码遵循PEP 8规范
- JavaScript代码使用ESLint配置
- 提交信息使用约定式提交格式

### 测试
```bash
# 后端测试
cd backend
python -m pytest

# 前端测试
cd frontend
npm test
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [LangChain](https://langchain.com/) - AI应用开发框架
- [DeepSeek](https://deepseek.com/) - 高性能中文大语言模型
- [Tavily](https://tavily.com/) - 智能搜索API
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架
- [React](https://reactjs.org/) - 用户界面库

## 📞 联系方式

- **项目仓库**: [https://github.com/849261680/research-gpt](https://github.com/849261680/research-gpt)
- **问题反馈**: [GitHub Issues](https://github.com/849261680/research-gpt/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！ ⭐**

</div>