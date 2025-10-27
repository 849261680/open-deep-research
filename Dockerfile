# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt (如果存在)
COPY requirements.txt* ./

# 安装 Python 依赖
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# 复制后端代码
COPY backend ./backend

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8000

# 启动命令 - 使用 PORT 环境变量(Railway 提供)
CMD python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
