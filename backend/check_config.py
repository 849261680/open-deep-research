#!/usr/bin/env python3
"""
配置检查工具 - 验证API Keys是否正确配置
"""
import os
from dotenv import load_dotenv

def check_api_keys():
    """检查API Keys配置状态"""
    load_dotenv()
    
    print("🔍 检查API Keys配置状态...")
    print("=" * 50)
    
    # 检查DeepSeek API Key
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key and deepseek_key != "your_deepseek_api_key_here":
        print("✅ DeepSeek API Key: 已配置")
    else:
        print("❌ DeepSeek API Key: 未配置或使用默认值")
        print("   请访问 https://platform.deepseek.com/api_keys 获取")
    
    # 检查Tavily API Key
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_api_key_here":
        print("✅ Tavily API Key: 已配置")
    else:
        print("⚠️  Tavily API Key: 未配置或使用默认值")
        print("   请访问 https://app.tavily.com/sign-up 获取")
    
    # 检查SerpAPI Key
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key and serpapi_key != "your_serpapi_api_key_here":
        print("✅ SerpAPI Key: 已配置")
    else:
        print("⚠️  SerpAPI Key: 未配置或使用默认值")
        print("   请访问 https://serpapi.com/users/sign_up 获取")
    
    print("=" * 50)
    
    # 给出建议
    has_deepseek = deepseek_key and deepseek_key != "your_deepseek_api_key_here"
    has_search = ((tavily_key and tavily_key != "your_tavily_api_key_here") or 
                  (serpapi_key and serpapi_key != "your_serpapi_api_key_here"))
    
    if has_deepseek and has_search:
        print("🎉 配置完整！系统可以正常运行")
    elif has_deepseek:
        print("⚠️  只有DeepSeek配置，搜索功能将不可用")
    elif has_search:
        print("⚠️  只有搜索配置，AI分析功能将不可用")
    else:
        print("❌ 缺少必要配置，系统无法正常运行")
    
    print("\n💡 建议：")
    print("- 必需：DeepSeek API Key (用于AI分析)")
    print("- 推荐：Tavily API Key (搜索质量最好)")
    print("- 备选：SerpAPI Key (Google搜索)")

if __name__ == "__main__":
    check_config()
