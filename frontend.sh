#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/frontend"

echo "🚀 启动前端本地开发服务..."

if ! command -v npm >/dev/null 2>&1; then
    echo "❌ 未找到 npm，请先安装 Node.js 16+"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "📝 frontend/.env 不存在，正在从示例创建..."
    cp .env.example .env
fi

if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

PORT="${PORT:-3003}"
HOST="${HOST:-0.0.0.0}"
FAST_REFRESH="${FAST_REFRESH:-true}"
WATCHPACK_POLLING="${WATCHPACK_POLLING:-false}"
CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-false}"

echo "✅ 前端即将运行在 http://localhost:${PORT}"
echo "♻️  前端热重载已启用，监听 frontend/src"
HOST="$HOST" \
PORT="$PORT" \
FAST_REFRESH="$FAST_REFRESH" \
WATCHPACK_POLLING="$WATCHPACK_POLLING" \
CHOKIDAR_USEPOLLING="$CHOKIDAR_USEPOLLING" \
exec npm start
