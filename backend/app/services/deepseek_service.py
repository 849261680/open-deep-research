import os
import time
import asyncio
from typing import Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_response(self, prompt: str, max_tokens: int = 2000) -> str:
        """使用DeepSeek API生成回复，优化性能"""
        if not self.api_key:
            raise ValueError("DeepSeek API key not found")
        
        # 限制输入长度，避免超长文本导致超时
        max_prompt_length = 2000  # 进一步减少到 2000 字符
        if len(prompt) > max_prompt_length:
            prompt = prompt[:max_prompt_length] + "...\n\n请基于以上内容生成简洁摘要。"
            print(f"⚠️ 提示词过长，已截断至 {max_prompt_length} 字符")
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": min(max_tokens, 2000),  # 限制最大输出
            "temperature": 0.7,
            "stream": False
        }
        
        # 添加详细日志和重试机制
        print(f"📝 DeepSeek API 请求详情:")
        print(f"   - 输入长度: {len(prompt)} 字符")
        print(f"   - 最大输出: {payload['max_tokens']} tokens")
        print(f"   - 模型: {payload['model']}")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                print(f"🔄 DeepSeek API 调用尝试 {attempt + 1}/{max_retries + 1}")
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=90  # 增加到90秒超时，适应复杂请求
                )
                end_time = time.time()
                print(f"⏱️ API 响应时间: {end_time - start_time:.2f} 秒")
                break  # 成功则跳出循环
            except requests.exceptions.Timeout:
                if attempt == max_retries:
                    print("⏰ DeepSeek API 请求超时，已重试多次")
                    return "API请求超时，请稍后重试"
                else:
                    print(f"⏰ 请求超时，将重试... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)  # 等待2秒后重试
            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ DeepSeek API 连接失败: {e}")
                    return "API连接失败，请检查网络"
                else:
                    print(f"⚠️ 连接失败，将重试... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")
    
    async def stream_response(self, prompt: str, max_tokens: int = 4000):
        """流式生成回复"""
        if not self.api_key:
            raise ValueError("DeepSeek API key not found")
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": True
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            stream=True
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    yield line.decode('utf-8')
        else:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

# 全局实例
deepseek_service = DeepSeekService()