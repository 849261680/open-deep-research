# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖和 uv
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制 uv 依赖元数据
COPY pyproject.toml uv.lock ./

# 使用 uv 同步 Python 依赖
RUN uv sync --locked --no-dev

# 复制项目代码
COPY backend ./backend

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 8000

# 启动命令 - 使用 PORT 环境变量(Railway 提供)
CMD ["sh", "-c", "uv run python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
