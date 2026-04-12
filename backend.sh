#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "🚀 启动后端本地开发服务..."

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ 未找到 uv，请先安装: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "📝 backend/.env 不存在，正在从示例创建..."
    cp backend/.env.example backend/.env
    echo "⚠️  请先检查 backend/.env 中的 API 配置"
fi

echo "📦 同步 Python 依赖..."
uv sync --extra dev

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8003}"

echo "✅ 后端即将运行在 http://localhost:${PORT}"
exec uv run python -m uvicorn backend.app.main:app --reload --host "$HOST" --port "$PORT"
