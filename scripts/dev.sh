#!/bin/bash

# Research Agent 开发环境启动脚本

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
STARTED_AT="$(date +%s)"

echo "🚀 启动 Research Agent 开发环境..."

log_elapsed() {
    local label="$1"
    local now
    now="$(date +%s)"
    echo "⏱️  ${label}: $((now - STARTED_AT))s"
}

install_frontend_deps_if_needed() {
    cd "$ROOT_DIR/frontend"
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

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装，请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 16+"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "backend/.env" ]; then
    echo "📝 创建后端环境变量文件..."
    cp backend/.env.example backend/.env
    echo "⚠️  请编辑 backend/.env 文件，填入必要的 API 密钥"
fi

if [ ! -f "frontend/.env" ]; then
    echo "📝 创建前端环境变量文件..."
    cp frontend/.env.example frontend/.env
fi

# 启动后端
echo "🔧 启动后端服务..."
uv sync --group dev
log_elapsed "Python 依赖同步完成"

# 后台启动后端
uv run python -m uvicorn backend.app.main:app \
  --reload \
  --reload-dir backend/app \
  --host 0.0.0.0 \
  --port 8003 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 3
log_elapsed "后端启动等待完成"

# 启动前端
echo "🎨 启动前端服务..."
install_frontend_deps_if_needed

# 启动前端
HOST=0.0.0.0 \
PORT=3003 \
BROWSER="${BROWSER:-none}" \
FAST_REFRESH="${FAST_REFRESH:-true}" \
WATCHPACK_POLLING="${WATCHPACK_POLLING:-false}" \
CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-false}" \
npm start &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"

echo ""
echo "🎉 开发环境启动完成！"
echo "📱 前端地址: http://localhost:3003"
echo "🔧 后端地址: http://localhost:8003"
echo "📊 后端健康检查: http://localhost:8003/api/health"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
