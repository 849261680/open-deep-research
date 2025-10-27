#!/bin/bash

# Research Agent 开发环境启动脚本

echo "🚀 启动 Research Agent 开发环境..."

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
cd backend
uv sync
if [ $? -ne 0 ]; then
    echo "❌ 后端依赖安装失败"
    exit 1
fi

# 后台启动后端
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动前端服务..."
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo "❌ 前端依赖安装失败"
    kill $BACKEND_PID
    exit 1
fi

# 启动前端
npm start &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"

echo ""
echo "🎉 开发环境启动完成！"
echo "📱 前端地址: http://localhost:3000"
echo "🔧 后端地址: http://localhost:8000"
echo "📊 后端健康检查: http://localhost:8000/api/health"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait