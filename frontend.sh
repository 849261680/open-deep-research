#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/frontend"
STARTED_AT="$(date +%s)"

echo "🚀 启动前端本地开发服务..."

log_elapsed() {
    local label="$1"
    local now
    now="$(date +%s)"
    echo "⏱️  ${label}: $((now - STARTED_AT))s"
}

install_frontend_deps_if_needed() {
    if [ ! -d "node_modules" ] || \
       [ ! -f "node_modules/.package-lock.json" ] || \
       [ "package-lock.json" -nt "node_modules/.package-lock.json" ]; then
        echo "📦 前端依赖缺失或 package-lock.json 已更新，正在安装..."
        npm install --prefer-offline --no-audit --no-fund
        log_elapsed "前端依赖检查完成"
        return
    fi

    echo "✅ 前端依赖已就绪，跳过 npm install"
    log_elapsed "前端依赖检查完成"
}

if ! command -v npm >/dev/null 2>&1; then
    echo "❌ 未找到 npm，请先安装 Node.js 16+"
    exit 1
fi
log_elapsed "npm 检查完成"

if [ ! -f ".env" ]; then
    echo "📝 frontend/.env 不存在，正在从示例创建..."
    cp .env.example .env
fi
log_elapsed "环境文件检查完成"

install_frontend_deps_if_needed

PORT="${PORT:-3003}"
HOST="${HOST:-0.0.0.0}"
BROWSER="${BROWSER:-none}"
FAST_REFRESH="${FAST_REFRESH:-true}"
WATCHPACK_POLLING="${WATCHPACK_POLLING:-false}"
CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-false}"

echo "✅ 前端即将运行在 http://localhost:${PORT}"
echo "♻️  前端热重载已启用，监听 frontend/src"
echo "🧭 浏览器自动打开: ${BROWSER}"
log_elapsed "交给 react-scripts 前的准备完成"
HOST="$HOST" \
PORT="$PORT" \
BROWSER="$BROWSER" \
FAST_REFRESH="$FAST_REFRESH" \
WATCHPACK_POLLING="$WATCHPACK_POLLING" \
CHOKIDAR_USEPOLLING="$CHOKIDAR_USEPOLLING" \
exec npm start
