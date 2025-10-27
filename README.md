# Research Agent - 深度研究智能体 (UV 版本)

<div align="center">

![Research Agent](https://img.shields.io/badge/Research-Agent-blue?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![React](https://img.shields.io/badge/React-18+-blue?style=flat&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green?style=flat&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Latest-purple?style=flat)
![uv](https://img.shields.io/badge/uv-Latest-orange?style=flat&logo=python)

**基于 LangChain 和 DeepSeek 的 DeepResearch Agent - 使用 uv 管理依赖**

[功能特色](#-功能特色) • [快速开始](#-快速开始) • [部署指南](#-部署指南)

</div>

## 🚀 项目简介

Deep Research Agent 是一个基于 AI 的智能研究助手，能够自动制定研究计划、执行多源搜索、分析内容并生成专业的研究报告。系统采用现代化的前后端分离架构，使用 **uv** 统一管理 Python 依赖，提供流畅的实时交互体验。

### 🆕 UV 版本优势

- **🚀 极速安装**：比 pip 快 10-100 倍的依赖安装速度
- **🔒 锁定依赖**：确保环境一致性，避免版本冲突
- **🛠️ 现代工具链**：内置虚拟环境管理和代码质量工具
- **📦 统一管理**：单一配置文件管理所有 Python 依赖

## 📋 核心能力

- **智能计划制定** - 基于 DeepSeek AI 自动生成结构化研究计划
- **多源数据搜索** - 集成 Tavily Search 等多个搜索引擎
- **实时进度追踪** - 动态显示搜索过程和结果详情
- **专业报告生成** - 自动分析并生成结构化研究报告
- **流式用户体验** - 实时显示研究进展和中间结果

## 🛠️ 技术栈

### 后端技术

- **Python 3.10+** - 核心开发语言
- **uv** - 现代 Python 包管理工具
- **FastAPI** - 高性能 Web 框架
- **LangChain** - AI 应用开发框架
- **DeepSeek API** - 大语言模型服务
- **Tavily Search** - 搜索引擎集成

### 前端技术

- **React 18** - 用户界面框架
- **Tailwind CSS** - 样式框架
- **Lucide React** - 图标库
- **Axios** - HTTP 客户端

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- Git

### 1. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用pip
pip install uv
```

### 2. 克隆项目

```bash
git clone https://github.com/849261680/research-gpt.git
cd research-gpt
```

### 3. 一键设置环境

```bash
# 运行迁移脚本
chmod +x scripts/migrate-to-uv.sh
./scripts/migrate-to-uv.sh
```

### 4. 启动开发环境

#### 方式一：使用开发脚本（推荐）

```bash
./scripts/dev.sh
```

#### 方式二：手动启动

```bash
# 启动后端
cd backend
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 启动前端
cd frontend
npm install
npm start
```

### 5. 访问应用

打开浏览器访问：`http://localhost:3000`

## 🔧 开发工具

### 代码质量检查

```bash
# 运行所有质量检查
./scripts/lint.sh

# 单独运行后端检查
cd backend
uv run ruff check app/ --fix
uv run black app/ --check
uv run mypy app/
```

### 测试

```bash
# 运行所有测试
./scripts/test.sh

# 单独运行后端测试
cd backend
uv run pytest
```

## 📁 项目结构

```
research-gpt/
├── pyproject.toml              # uv主配置文件
├── uv.lock                   # uv锁定文件
├── .python-version            # Python版本指定
├── scripts/                  # 开发脚本
│   ├── migrate-to-uv.sh     # uv迁移脚本
│   ├── dev.sh              # 开发环境启动
│   ├── test.sh             # 测试脚本
│   └── lint.sh            # 代码质量检查
├── backend/                   # 后端服务
│   ├── pyproject.toml      # 后端依赖配置
│   └── app/               # 应用代码
└── frontend/                  # 前端应用
    ├── package.json         # Node.js依赖
    └── src/                # React源码
```

## ⚙️ 配置指南

### 环境变量

复制环境变量模板：

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

编辑 `.env` 文件，填入你的 API 密钥：

#### DeepSeek API

1. 访问 [DeepSeek 平台](https://platform.deepseek.com/)
2. 注册并登录账号
3. 在 API 管理中创建新密钥
4. 将密钥添加到 `.env` 文件中

#### Tavily Search API

1. 访问 [Tavily 官网](https://tavily.com/)
2. 注册获取免费 API 密钥（1000 次/月）
3. 将密钥添加到 `.env` 文件中

## 🚀 部署指南

### Railway（后端）

1. 连接 GitHub 仓库到 Railway
2. 设置根目录为 `backend`
3. 配置环境变量：
   ```
   DEEPSEEK_API_KEY=your_key
   TAVILY_API_KEY=your_key
   FRONTEND_URL=https://your-vercel-domain.vercel.app
   ```
4. Railway 会自动使用 uv 安装依赖并启动服务

### Vercel（前端）

1. 连接 GitHub 仓库到 Vercel
2. 设置根目录为 `frontend`
3. 配置环境变量：
   ```
   REACT_APP_API_URL=https://your-railway-domain.railway.app
   ```
4. Vercel 会自动构建和部署

## 🔧 常用命令

```bash
# uv相关
uv sync                    # 同步依赖
uv add package_name        # 添加新依赖
uv remove package_name     # 移除依赖
uv run command            # 在虚拟环境中运行命令

# 开发相关
./scripts/dev.sh          # 启动开发环境
./scripts/test.sh         # 运行测试
./scripts/lint.sh        # 代码质量检查

# 部署相关
uv build                 # 构建项目
uv publish               # 发布到PyPI（如果需要）
```

## 🐛 故障排除

### 常见问题

**Q: uv 安装失败**

```bash
# 确保系统有必要的依赖
# macOS
xcode-select --install

# Linux
sudo apt-get install build-essential
```

**Q: 依赖安装失败**

```bash
# 清理缓存重新安装
uv cache clean
uv sync --refresh
```

**Q: 前后端连接失败**

- 检查端口配置是否一致
- 确认 CORS 设置正确
- 查看浏览器控制台错误信息

## 📈 性能优化

### uv 优化配置

```toml
# pyproject.toml中的优化配置
[tool.uv]
cache-keys = ["git", "python"]
index-url = ["https://pypi.org/simple"]
```

### 开发环境优化

```bash
# 使用更快的索引
uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [uv](https://github.com/astral-sh/uv) - 现代 Python 包管理工具
- [LangChain](https://github.com/langchain-ai/langchain) - AI 应用开发框架
- [DeepSeek](https://www.deepseek.com/) - 大语言模型服务
- [Tavily](https://tavily.com/) - 搜索 API 服务

---

**🎉 享受使用 uv 带来的极速开发体验！**
