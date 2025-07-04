import os
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
    
    async def generate_response(self, prompt: str, max_tokens: int = 4000) -> str:
        """使用DeepSeek API生成回复"""
        if not self.api_key:
            raise ValueError("DeepSeek API key not found")
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload
        )
        
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