# Research Agent - 深度研究智能体

<div align="center">

![Research Agent](https://img.shields.io/badge/Research-Agent-blue?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![React](https://img.shields.io/badge/React-18+-blue?style=flat&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green?style=flat&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Latest-purple?style=flat)

**基于LangChain和DeepSeek的DeepResearch Agent**

[功能特色](#-功能特色) • [快速开始](#-快速开始) 

</div>

##  项目简介

Research Agent是一个基于AI的深度研究智能体，能够自动制定研究计划、执行联网搜索、分析内容并生成专业的研究报告。系统采用现代化的前后端分离架构，提供流畅的实时交互体验。

###  核心能力

- **智能计划制定** - 基于DeepSeek AI自动生成结构化研究计划
- **联网数据搜索** - 集成Tavily搜索引擎
- **实时进度追踪** - 动态显示搜索过程和结果详情
- **专业报告生成** - 自动分析并生成结构化研究报告


##  功能特色

###  研究工作流
```
用户查询 → 计划制定 → 联网搜索 → 内容分析 → 报告生成
```

###  搜索能力
- **Tavily Search** - 高质量网络搜索（1000次免费配额）
- **多查询策略** - 自动生成多个相关搜索词
- **结果筛选** - 智能过滤和排序搜索结果
- **来源追踪** - 显示具体的文章标题和链接

###  AI分析
- **DeepSeek集成** - 使用高性能中文大语言模型
- **链式处理** - LangChain工作流管理
- **内容摘要** - 自动提取关键信息
- **结构化输出** - 生成专业格式的研究报告

###  用户界面
- **实时进度** - 动态显示研究步骤和进度
- **搜索详情** - 展示搜索到的具体内容和链接
- **响应式设计** - 支持桌面和移动设备
- **流畅动画** - 动态加载效果和状态提示

##  技术栈

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




