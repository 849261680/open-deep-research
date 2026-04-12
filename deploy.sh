#!/bin/bash

# Research Agent 部署脚本
# 用于验证环境和配置

echo "🚀 Research Agent 部署检查工具"
echo "================================"

# 检查必需的环境变量
check_env() {
    echo "📋 检查环境变量..."
    
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        echo "❌ DEEPSEEK_API_KEY 未设置"
        echo "   请访问 https://platform.deepseek.com/ 获取API密钥"
        return 1
    else
        echo "✅ DEEPSEEK_API_KEY 已设置"
    fi
    
    if [ -z "$TAVILY_API_KEY" ]; then
        echo "❌ TAVILY_API_KEY 未设置"
        echo "   请访问 https://tavily.com/ 获取API密钥"
        return 1
    else
        echo "✅ TAVILY_API_KEY 已设置"
    fi
    
    return 0
}

# 检查Python依赖
check_python_deps() {
    echo "🐍 检查Python依赖..."
    
    if [ ! -f "pyproject.toml" ] || [ ! -f "uv.lock" ]; then
        echo "❌ pyproject.toml 或 uv.lock 不存在"
        return 1
    fi
    
    echo "✅ uv 依赖配置存在"
    
    # 检查关键依赖
    if grep -q "fastapi" pyproject.toml; then
        echo "✅ FastAPI 依赖存在"
    else
        echo "❌ FastAPI 依赖缺失"
        return 1
    fi
    
    if grep -q "langchain" pyproject.toml; then
        echo "✅ LangChain 依赖存在"
    else
        echo "❌ LangChain 依赖缺失"
        return 1
    fi
    
    return 0
}

# 检查Node.js依赖
check_node_deps() {
    echo "📦 检查Node.js依赖..."
    
    if [ ! -f "frontend/package.json" ]; then
        echo "❌ frontend/package.json 不存在"
        return 1
    fi
    
    echo "✅ package.json 存在"
    
    # 检查关键依赖
    if grep -q "react" frontend/package.json; then
        echo "✅ React 依赖存在"
    else
        echo "❌ React 依赖缺失"
        return 1
    fi
    
    return 0
}

# 检查配置文件
check_config_files() {
    echo "⚙️ 检查配置文件..."
    
    # 检查Vercel配置
    if [ -f "frontend/vercel.json" ]; then
        echo "✅ Vercel配置存在"
    else
        echo "❌ frontend/vercel.json 不存在"
        return 1
    fi
    
    # 检查Railway配置
    if [ -f "railway.json" ]; then
        echo "✅ Railway配置存在"
    else
        echo "❌ railway.json 不存在"
        return 1
    fi
    
    # 检查Procfile
    if [ -f "backend/Procfile" ]; then
        echo "✅ Procfile存在"
    else
        echo "❌ backend/Procfile 不存在"
        return 1
    fi
    
    return 0
}

# 生成部署命令
generate_deploy_commands() {
    echo ""
    echo "🚀 部署命令参考："
    echo "=================="
    echo ""
    echo "1. 后端部署到Railway："
    echo "   - 访问 https://railway.app"
    echo "   - 连接GitHub仓库"
    echo "   - 设置根目录为 'backend'"
    echo "   - 添加环境变量："
    echo "     DEEPSEEK_API_KEY=your_key"
    echo "     TAVILY_API_KEY=your_key"
    echo ""
    echo "2. 前端部署到Vercel："
    echo "   - 访问 https://vercel.com"
    echo "   - 连接GitHub仓库" 
    echo "   - 设置根目录为 'frontend'"
    echo "   - 添加环境变量："
    echo "     REACT_APP_API_URL=https://your-railway-app.railway.app"
    echo ""
    echo "3. 更新CORS设置："
    echo "   - 在Railway中添加："
    echo "     FRONTEND_URL=https://your-vercel-app.vercel.app"
    echo ""
}

# 主函数
main() {
    echo "开始部署检查..."
    echo ""
    
    # 检查当前目录
    if [ ! -f "README.md" ] || [ ! -d "frontend" ] || [ ! -d "backend" ]; then
        echo "❌ 请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 运行所有检查
    check_env || exit 1
    echo ""
    check_python_deps || exit 1
    echo ""
    check_node_deps || exit 1
    echo ""
    check_config_files || exit 1
    
    echo ""
    echo "🎉 所有检查通过！"
    echo ""
    
    generate_deploy_commands
    
    echo "📖 详细部署说明请查看 README.md"
    echo ""
    echo "✨ 祝您部署顺利！"
}

# 运行主函数
main "$@"
