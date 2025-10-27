#!/bin/bash
echo "🚀 开始迁移到 uv..."
echo "================================"

# 检查当前目录
if [ ! -f "pyproject.toml" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 1. 检查 uv 是否已安装
if ! command -v uv &> /dev/null; then
    echo "📦 安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # 重新检查是否安装成功
    if ! command -v uv &> /dev/null; then
        echo "❌ uv 安装失败，请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
else
    echo "✅ uv 已安装"
fi

# 2. 创建 .python-version 文件
echo "🐍 设置 Python 版本..."
echo "3.11" > .python-version
echo "✅ Python 版本设置为 3.11"

# 3. 创建虚拟环境
echo "🔧 创建 Python 虚拟环境..."
uv python install 3.11
uv venv
echo "✅ 虚拟环境创建完成"

# 4. 安装根目录依赖
echo "📚 安装根目录依赖..."
uv pip install -e .
echo "✅ 根目录依赖安装完成"

# 5. 安装后端依赖
echo "🔧 安装后端依赖..."
cd backend
uv pip install -e .
cd ..
echo "✅ 后端依赖安装完成"

# 6. 验证安装
echo "🔍 验证安装..."
uv run python -c "
import sys
try:
    import fastapi, langchain, pydantic
    print('✅ Python 依赖安装成功')
    print(f'   - Python: {sys.version}')
    print(f'   - FastAPI: {fastapi.__version__}')
    print(f'   - LangChain: {langchain.__version__}')
    print(f'   - Pydantic: {pydantic.__version__}')
except ImportError as e:
    print(f'❌ 依赖安装失败: {e}')
    sys.exit(1)
"

# 7. 创建开发脚本
echo "📝 创建开发脚本..."
cat > scripts/dev.sh << 'EOF'
#!/bin/bash
echo "🚀 启动开发环境..."

# 启动后端
echo "🔧 启动后端服务..."
cd backend
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🌐 启动前端服务..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "✅ 开发环境启动完成"
echo "   - 后端: http://localhost:8000"
echo "   - 前端: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF

chmod +x scripts/dev.sh
echo "✅ 开发脚本创建完成: scripts/dev.sh"

# 8. 创建测试脚本
echo "🧪 创建测试脚本..."
cat > scripts/test.sh << 'EOF'
#!/bin/bash
echo "🧪 运行测试..."

# 后端测试
echo "🔧 运行后端测试..."
cd backend
uv run pytest ../tests/ -v
BACKEND_EXIT_CODE=$?

# 前端测试
echo "🌐 运行前端测试..."
cd ../frontend
npm test -- --coverage --watchAll=false
FRONTEND_EXIT_CODE=$?

# 汇总结果
echo ""
echo "📊 测试结果:"
echo "   - 后端测试: $([ $BACKEND_EXIT_CODE -eq 0 ] && echo '✅ 通过' || echo '❌ 失败')"
echo "   - 前端测试: $([ $FRONTEND_EXIT_CODE -eq 0 ] && echo '✅ 通过' || echo '❌ 失败')"

# 返回综合状态
if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo "🎉 所有测试通过！"
    exit 0
else
    echo "❌ 部分测试失败"
    exit 1
fi
EOF

chmod +x scripts/test.sh
echo "✅ 测试脚本创建完成: scripts/test.sh"

# 9. 创建代码质量检查脚本
echo "🔍 创建代码质量检查脚本..."
cat > scripts/lint.sh << 'EOF'
#!/bin/bash
echo "🔍 运行代码质量检查..."

# 后端检查
echo "🔧 检查后端代码..."
cd backend

echo "  - 运行 ruff..."
uv run ruff check app/ --fix
echo "  - 运行 black..."
uv run black app/ --check
echo "  - 运行 mypy..."
uv run mypy app/

BACKEND_LINT_EXIT_CODE=$?

# 前端检查
echo "🌐 检查前端代码..."
cd ../frontend

echo "  - 运行 ESLint..."
npm run lint -- --fix
echo "  - 运行 Prettier..."
npm run format -- --check

FRONTEND_LINT_EXIT_CODE=$?

# 汇总结果
echo ""
echo "📊 代码质量检查结果:"
echo "   - 后端: $([ $BACKEND_LINT_EXIT_CODE -eq 0 ] && echo '✅ 通过' || echo '❌ 失败')"
echo "   - 前端: $([ $FRONTEND_LINT_EXIT_CODE -eq 0 ] && echo '✅ 通过' || echo '❌ 失败')"

# 返回综合状态
if [ $BACKEND_LINT_EXIT_CODE -eq 0 ] && [ $FRONTEND_LINT_EXIT_CODE -eq 0 ]; then
    echo "🎉 代码质量检查通过！"
    exit 0
else
    echo "❌ 代码质量检查失败"
    exit 1
fi
EOF

chmod +x scripts/lint.sh
echo "✅ 代码质量检查脚本创建完成: scripts/lint.sh"

echo ""
echo "🎉 uv 迁移完成！"
echo "================================"
echo ""
echo "📋 可用命令:"
echo "  - 启动开发环境: ./scripts/dev.sh"
echo "  - 运行测试: ./scripts/test.sh"
echo "  - 代码质量检查: ./scripts/lint.sh"
echo "  - 启动后端: cd backend && uv run python -m uvicorn app.main:app --reload"
echo "  - 运行后端测试: cd backend && uv run pytest"
echo ""
echo "📖 更多信息请查看 README.md"
echo ""
echo "✨ 享受新的开发体验！"